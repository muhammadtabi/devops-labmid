#!/usr/bin/env python3
"""Run real unittest discovery and always write actual test outcomes as JSON."""

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from reporting import write_report_atomic

DEFAULT_REPORT = ROOT / "test-report.json"


class ReportingResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records = []
        self.current = None

    def startTest(self, test):
        super().startTest(test)
        self.current = {"name": test.id(), "result": "passed", "failure_message": ""}

    def stopTest(self, test):
        self.records.append(self.current)
        self.current = None
        super().stopTest(test)

    def record(self, result, message=""):
        if self.current is not None:
            if self.current["result"] in {"failed", "error"}:
                self.current["failure_message"] += "\n" + message
                if result == "error":
                    self.current["result"] = "error"
            else:
                self.current.update(result=result, failure_message=message)

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.record("failed", self._exc_info_to_string(err, test))

    def addError(self, test, err):
        super().addError(test, err)
        message = self._exc_info_to_string(err, test)
        if self.current is None:
            # setUpClass/tearDownClass failures are unittest error holders, not started tests.
            self.records.append({"name": test.id(), "result": "error", "failure_message": message})
        else:
            self.record("error", message)

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        if self.current is None:
            self.records.append({"name": test.id(), "result": "skipped", "failure_message": reason})
        else:
            self.record("skipped", reason)

    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test, err)
        self.record("skipped", "Expected failure:\n" + self._exc_info_to_string(err, test))

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        self.record("failed", "Unexpected success: a test marked expectedFailure passed.")

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err is not None:
            result = "failed" if issubclass(err[0], test.failureException) else "error"
            self.record(result, f"Subtest {subtest.id()}:\n" + self._exc_info_to_string(err, test))


def git_value(*arguments):
    try:
        process = subprocess.run(["git", "-C", str(ROOT), *arguments], capture_output=True, text=True, timeout=5, check=False)
        return process.stdout.strip() or None if process.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def metadata():
    return {
        "repository": os.environ.get("GITHUB_REPOSITORY") or git_value("remote", "get-url", "origin"),
        "branch": os.environ.get("GITHUB_HEAD_REF") or os.environ.get("GITHUB_REF_NAME") or git_value("symbolic-ref", "--quiet", "--short", "HEAD"),
        "commit_sha": os.environ.get("GITHUB_SHA") or git_value("rev-parse", "HEAD"),
        "run_id": os.environ.get("GITHUB_RUN_ID") or None,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
    }


def run_tests(start_dir, pattern, output, verbosity=2):
    try:
        suite = unittest.defaultTestLoader.discover(str(start_dir), pattern=pattern)
    except Exception:
        # Make discovery failure a real error test so even this failure produces a report.
        error = sys.exc_info()

        class DiscoveryError(unittest.TestCase):
            def runTest(self):
                raise error[1].with_traceback(error[2])

        suite = unittest.TestSuite([DiscoveryError()])
    runner = unittest.TextTestRunner(verbosity=verbosity, resultclass=ReportingResult)
    result = runner.run(suite)
    records = result.records
    summary = {
        "total": len(records),
        "passed": sum(test["result"] == "passed" for test in records),
        "failed": sum(test["result"] in {"failed", "error"} for test in records),
        "skipped": sum(test["result"] == "skipped" for test in records),
    }
    summary["status"] = "passed" if result.wasSuccessful() and records else "failed"
    report = {"schema_version": 1, **metadata(), "tests": records, "summary": summary}
    write_report_atomic(output, report)
    print(f"JSON report: {Path(output).resolve()}")
    if not records:
        print("No tests discovered; refusing to report success.", file=sys.stderr)
    return 0 if summary["status"] == "passed" else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-dir", type=Path, default=ROOT / "tests")
    parser.add_argument("--pattern", default="test*.py")
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT)
    options = parser.parse_args(argv)
    try:
        return run_tests(options.start_dir.resolve(), options.pattern, options.output)
    except (OSError, ValueError) as exc:
        print(f"Could not write a trustworthy report: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
