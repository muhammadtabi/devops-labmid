import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest
from unittest.mock import patch

from scripts import run_tests
from scripts.demo_defect import BAD_BLOCK, GOOD_BLOCK, change_defect

ROOT = Path(__file__).resolve().parents[1]


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)
        self.tests = self.directory / "cases"
        self.tests.mkdir()
        self.output = self.directory / "report.json"

    def tearDown(self):
        self.temporary.cleanup()

    def run_fixture(self, source, metadata=None):
        (self.tests / "test_fixture.py").write_text(textwrap.dedent(source), encoding="utf-8")
        environment = {key: value for key, value in os.environ.items() if not key.startswith("GITHUB_")}
        environment.update(metadata or {})
        process = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "run_tests.py"), "--start-dir", str(self.tests), "--output", str(self.output)],
            cwd=self.directory, env=environment, capture_output=True, text=True, timeout=20,
        )
        self.assertTrue(self.output.is_file(), process.stdout + process.stderr)
        return process.returncode, json.loads(self.output.read_text(encoding="utf-8"))

    def test_passing_fixture_returns_zero_and_real_names(self):
        code, report = self.run_fixture("""
            import unittest
            class RealTests(unittest.TestCase):
                def test_addition(self):
                    self.assertEqual(2 + 2, 4)
        """)
        self.assertEqual(code, 0)
        self.assertEqual(report["summary"], {"total": 1, "passed": 1, "failed": 0, "skipped": 0, "status": "passed"})
        self.assertEqual(report["tests"][0]["name"], "test_fixture.RealTests.test_addition")
        self.assertEqual(report["tests"][0]["failure_message"], "")

    def test_failure_error_and_skip_are_reported_and_return_nonzero(self):
        code, report = self.run_fixture("""
            import unittest
            class RealTests(unittest.TestCase):
                def test_pass(self):
                    self.assertTrue(True)
                def test_failure(self):
                    self.assertEqual(1, 2, 'actual assertion failure')
                def test_error(self):
                    raise RuntimeError('actual runtime error')
                @unittest.skip('not available')
                def test_skip(self):
                    pass
        """)
        self.assertEqual(code, 1)
        self.assertEqual(report["summary"], {"total": 4, "passed": 1, "failed": 2, "skipped": 1, "status": "failed"})
        records = {item["result"]: item for item in report["tests"]}
        self.assertIn("actual assertion failure", records["failed"]["failure_message"])
        self.assertIn("actual runtime error", records["error"]["failure_message"])
        self.assertEqual(records["skipped"]["failure_message"], "not available")

    def test_subtest_failures_change_parent_result(self):
        code, report = self.run_fixture("""
            import unittest
            class RealTests(unittest.TestCase):
                def test_subtests(self):
                    for number in (1, 2):
                        with self.subTest(number=number):
                            self.assertEqual(number, 1)
        """)
        self.assertEqual(code, 1)
        self.assertEqual(report["summary"]["failed"], 1)
        self.assertIn("number=2", report["tests"][0]["failure_message"])

    def test_class_setup_errors_are_not_lost(self):
        code, report = self.run_fixture("""
            import unittest
            class RealTests(unittest.TestCase):
                @classmethod
                def setUpClass(cls):
                    raise RuntimeError('setup exploded')
                def test_never_started(self):
                    pass
        """)
        self.assertEqual(code, 1)
        self.assertEqual(report["summary"]["failed"], 1)
        self.assertIn("setUpClass", report["tests"][0]["name"])
        self.assertIn("setup exploded", report["tests"][0]["failure_message"])

    def test_import_error_produces_report_and_failure(self):
        code, report = self.run_fixture("raise RuntimeError('bad test import')")
        self.assertEqual(code, 1)
        self.assertEqual(report["tests"][0]["result"], "error")
        self.assertIn("bad test import", report["tests"][0]["failure_message"])

    def test_no_tests_is_not_false_success(self):
        code, report = self.run_fixture("# no tests")
        self.assertEqual(code, 1)
        self.assertEqual(report["summary"], {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "status": "failed"})

    def test_github_metadata_uses_full_actual_environment_values(self):
        values = {"GITHUB_REPOSITORY": "student/portal", "GITHUB_REF_NAME": "demo-defect", "GITHUB_SHA": "b" * 40, "GITHUB_RUN_ID": "987654321"}
        code, report = self.run_fixture("""
            import unittest
            class RealTests(unittest.TestCase):
                def test_ok(self): pass
        """, values)
        self.assertEqual(code, 0)
        for field, env in (("repository", "GITHUB_REPOSITORY"), ("branch", "GITHUB_REF_NAME"), ("commit_sha", "GITHUB_SHA"), ("run_id", "GITHUB_RUN_ID")):
            self.assertEqual(report[field], values[env])
        self.assertTrue(report["timestamp"].endswith("Z"))

    def test_missing_metadata_is_null_and_git_fallback_is_real(self):
        with patch.dict(os.environ, {}, clear=True), patch("scripts.run_tests.git_value", return_value=None):
            data = run_tests.metadata()
        for field in ("repository", "branch", "commit_sha", "run_id"):
            self.assertIsNone(data[field])
        values = {("remote", "get-url", "origin"): "git@example.com:student/portal.git", ("symbolic-ref", "--quiet", "--short", "HEAD"): "main", ("rev-parse", "HEAD"): "c" * 40}
        with patch.dict(os.environ, {}, clear=True), patch("scripts.run_tests.git_value", side_effect=lambda *args: values.get(args)):
            data = run_tests.metadata()
        self.assertEqual(data["commit_sha"], "c" * 40)
        self.assertEqual(data["repository"], values[("remote", "get-url", "origin")])
        self.assertIsNone(data["run_id"])

    def test_default_report_path_is_repo_root_not_current_directory(self):
        self.assertEqual(run_tests.DEFAULT_REPORT, ROOT / "test-report.json")

    def test_expected_failure_and_unexpected_success(self):
        code, report = self.run_fixture("""
            import unittest
            class RealTests(unittest.TestCase):
                @unittest.expectedFailure
                def test_expected(self): self.fail('known defect')
                @unittest.expectedFailure
                def test_unexpected(self): pass
        """)
        self.assertEqual(code, 1)
        self.assertEqual(report["summary"]["skipped"], 1)
        self.assertEqual(report["summary"]["failed"], 1)


class DefectScriptTests(unittest.TestCase):
    def test_exact_target_is_changed_and_restored_without_touching_other_code(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "validation.py"
            original = "# unrelated code stays exactly the same\n" + GOOD_BLOCK + "\nOTHER = 42\n"
            target.write_text(original, encoding="utf-8")
            self.assertTrue(change_defect("introduce", target))
            self.assertEqual(target.read_text(), original.replace(GOOD_BLOCK, BAD_BLOCK))
            self.assertFalse(change_defect("introduce", target))
            self.assertTrue(change_defect("fix", target))
            self.assertEqual(target.read_text(), original)
            self.assertFalse(change_defect("fix", target))

    def test_refuses_unrelated_edits_to_marked_function(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "validation.py"
            original = GOOD_BLOCK.replace("return _is_http_url(value)", "return custom_validator(value)")
            target.write_text(original, encoding="utf-8")
            for action in ("introduce", "fix"):
                with self.assertRaises(ValueError):
                    change_defect(action, target)
                self.assertEqual(target.read_text(), original)
