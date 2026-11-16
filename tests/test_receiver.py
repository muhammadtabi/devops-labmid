import copy
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

import receiver
from reporting import MAX_REPORT_BYTES, read_report, validate_report, write_report_atomic
from scripts.send_report import main as send_main, send_report


def sample_report(result="passed"):
    failed = result in {"failed", "error"}
    return {
        "schema_version": 1,
        "repository": "student/assignment-portal",
        "branch": "main",
        "commit_sha": "a" * 40,
        "run_id": "12345",
        "timestamp": "2026-10-30T12:00:00Z",
        "tests": [{"name": "test_example", "result": result, "failure_message": "AssertionError: invalid URL accepted" if failed else ("not applicable" if result == "skipped" else "")}],
        "summary": {"total": 1, "passed": int(result == "passed"), "failed": int(failed), "skipped": int(result == "skipped"), "status": "failed" if failed else "passed"},
    }


class ReceiverTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.output = Path(self.temporary.name) / "received.json"
        self.token = "unit-test-only-token"
        self.server = receiver.create_server(port=0, output_path=self.output, token=self.token)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}/report"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temporary.cleanup()

    def request(self, method="POST", path="/report", report=None, token=None, body=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        headers = {"Content-Type": "application/json"}
        if token is not None:
            headers["X-Report-Token"] = token
        if report is not None:
            body = json.dumps(report).encode("utf-8")
        try:
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            connection.close()

    def test_token_required_at_startup(self):
        with patch.dict("os.environ", {}, clear=True):
            for token in (None, "", "has spaces", "line\nbreak"):
                with self.subTest(token=token), self.assertRaises(ValueError):
                    receiver.create_server(port=0, token=token)

    def test_default_receiver_output_is_startup_directory(self):
        with patch("receiver.Path.cwd", return_value=Path(self.temporary.name)):
            other = receiver.create_server(port=0, token=self.token)
        try:
            self.assertEqual(other.output_path, Path(self.temporary.name) / "test-report.json")
        finally:
            other.server_close()

    def test_health_does_not_require_or_expose_secret(self):
        status, answer = self.request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(answer, {"status": "ok"})
        self.assertNotIn(self.token, json.dumps(answer))
        self.assertEqual(self.request("GET", "/report")[0], 404)

    def test_missing_wrong_and_duplicate_auth_do_not_overwrite(self):
        self.request(report=sample_report(), token=self.token)
        before = self.output.read_bytes()
        for token in (None, "wrong-token"):
            self.assertEqual(self.request(report=sample_report("failed"), token=token)[0], 401)
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        body = json.dumps(sample_report()).encode()
        try:
            connection.putrequest("POST", "/report")
            connection.putheader("Content-Type", "application/json")
            connection.putheader("Content-Length", str(len(body)))
            connection.putheader("X-Report-Token", self.token)
            connection.putheader("X-Report-Token", self.token)
            connection.endheaders(body)
            response = connection.getresponse()
            self.assertEqual(response.status, 401)
            response.read()
        finally:
            connection.close()
        self.assertEqual(before, self.output.read_bytes())

    def test_accepts_passing_and_failing_reports_with_atomic_replace(self):
        for result in ("passed", "failed", "error", "skipped"):
            with self.subTest(result=result):
                report = sample_report(result)
                self.assertEqual(self.request(report=report, token=self.token)[0], 200)
                self.assertEqual(read_report(self.output), report)
                self.assertEqual(list(self.output.parent.glob(".received.json.*.tmp")), [])

    def test_inconsistent_reports_cannot_overwrite_previous_report(self):
        self.request(report=sample_report(), token=self.token)
        before = self.output.read_bytes()
        variants = []
        for field, value in (("total", 2), ("passed", 0), ("failed", 1), ("skipped", True), ("status", "failed")):
            report = sample_report()
            report["summary"][field] = value
            variants.append(report)
        for field, value in (("commit_sha", "shortsha"), ("timestamp", "not-utc"), ("tests", "fake"), ("schema_version", True)):
            report = sample_report()
            report[field] = value
            variants.append(report)
        report = sample_report("failed")
        report["tests"][0]["failure_message"] = ""
        variants.append(report)
        report = sample_report()
        report["tests"].append(copy.deepcopy(report["tests"][0]))
        variants.append(report)
        report = sample_report()
        report["tests"][0]["result"] = []
        variants.append(report)
        for report in variants:
            with self.subTest(report=report):
                self.assertEqual(self.request(report=report, token=self.token)[0], 400)
                self.assertEqual(before, self.output.read_bytes())

    def test_malformed_and_oversized_receiver_requests(self):
        self.assertEqual(self.request(body=b"{bad", token=self.token)[0], 400)
        # Announce an oversized body without sending megabytes after early rejection.
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        try:
            connection.putrequest("POST", "/report")
            connection.putheader("Content-Type", "application/json")
            connection.putheader("Content-Length", str(MAX_REPORT_BYTES + 1))
            connection.putheader("X-Report-Token", self.token)
            connection.endheaders()
            response = connection.getresponse()
            self.assertEqual(response.status, 413)
            response.read()
        finally:
            connection.close()
        self.assertFalse(self.output.exists())

    def test_send_script_delivers_actual_pass_and_fail(self):
        source = Path(self.temporary.name) / "source.json"
        for result in ("passed", "failed"):
            report = sample_report(result)
            write_report_atomic(source, report)
            delivered = send_report(source, self.url, self.token, attempts=1, timeout=2)
            self.assertEqual(delivered, report)
            self.assertEqual(read_report(self.output), report)

    def test_delivery_errors_are_not_swallowed(self):
        source = Path(self.temporary.name) / "source.json"
        write_report_atomic(source, sample_report())
        with self.assertRaises(RuntimeError):
            send_report(source, self.url, "wrong-token", attempts=1, timeout=2)
        with patch.dict("os.environ", {"REPORT_TOKEN": "wrong-token"}, clear=True):
            self.assertEqual(send_main(["--report", str(source), "--url", self.url, "--attempts", "1"]), 1)
        with self.assertRaises(ValueError):
            send_report(source, self.url, None)
        with self.assertRaises(ValueError):
            send_report(source, self.url, self.token, attempts=6)

    def test_atomic_writer_preserves_existing_on_validation_error(self):
        write_report_atomic(self.output, sample_report())
        before = self.output.read_bytes()
        report = sample_report()
        report["summary"]["total"] = 100
        with self.assertRaises(ValueError):
            write_report_atomic(self.output, report)
        self.assertEqual(self.output.read_bytes(), before)
        local = sample_report()
        for field in ("repository", "branch", "commit_sha", "run_id"):
            local[field] = None
        self.assertIs(validate_report(local), local)
