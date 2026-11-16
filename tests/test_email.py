from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from reporting import write_report_atomic
from scripts.email_report import build_message, email_report, smtp_settings


class EmailTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.report_path = Path(self.temporary.name) / "test-report.json"
        self.report = {
            "schema_version": 1, "repository": "student/portal", "branch": "main", "commit_sha": "d" * 40,
            "run_id": "5678", "timestamp": "2026-10-30T12:00:00Z",
            "tests": [{"name": "test_invalid_url", "result": "failed", "failure_message": "AssertionError: invalid URL accepted"}],
            "summary": {"total": 1, "passed": 0, "failed": 1, "skipped": 0, "status": "failed"},
        }
        write_report_atomic(self.report_path, self.report)
        self.environment = {"SMTP_HOST": "smtp.example.invalid", "SMTP_USERNAME": "lab-user", "SMTP_PASSWORD": "unit-test-not-a-real-secret", "SMTP_FROM": "lab@example.invalid", "SMTP_TO": "teacher@example.invalid"}

    def tearDown(self):
        self.temporary.cleanup()

    def test_email_contains_required_metadata_and_attaches_actual_json(self):
        message = build_message(self.report_path, smtp_settings(self.environment))
        body = message.get_body(preferencelist=("plain",)).get_content()
        for value in ("student/portal", "main", "d" * 40, "5678", self.report["timestamp"], "test_invalid_url", "AssertionError: invalid URL accepted", "Total: 1; passed: 0; failed (including errors): 1; skipped: 0"):
            self.assertIn(value, body)
        attachments = list(message.iter_attachments())
        self.assertEqual(len(attachments), 1)
        self.assertEqual(attachments[0].get_payload(decode=True), self.report_path.read_bytes())

    def test_missing_config_bad_ports_and_header_injection_are_rejected(self):
        with self.assertRaises(ValueError):
            smtp_settings({})
        for port in ("25", "not-a-number"):
            with self.assertRaises(ValueError):
                smtp_settings({**self.environment, "SMTP_PORT": port})
        with self.assertRaises(ValueError):
            smtp_settings({**self.environment, "SMTP_TO": "someone@example.invalid\nBcc: other@example.invalid"})

    def test_starttls_happens_before_login_without_actual_email(self):
        client = MagicMock()
        client.__enter__.return_value = client
        client.send_message.return_value = {}
        with patch("scripts.email_report.smtplib.SMTP", return_value=client) as smtp, patch("scripts.email_report.smtplib.SMTP_SSL") as smtp_ssl:
            email_report(self.report_path, self.environment)
        smtp.assert_called_once_with("smtp.example.invalid", 587, timeout=15)
        smtp_ssl.assert_not_called()
        methods = [call[0] for call in client.method_calls]
        self.assertLess(methods.index("starttls"), methods.index("login"))
        self.assertLess(methods.index("login"), methods.index("send_message"))

    def test_ssl_port_465_without_actual_email(self):
        client = MagicMock()
        client.__enter__.return_value = client
        client.send_message.return_value = {}
        with patch("scripts.email_report.smtplib.SMTP_SSL", return_value=client) as smtp_ssl, patch("scripts.email_report.smtplib.SMTP") as smtp:
            email_report(self.report_path, {**self.environment, "SMTP_PORT": "465"})
        self.assertEqual(smtp_ssl.call_args.args, ("smtp.example.invalid", 465))
        smtp.assert_not_called()
        client.starttls.assert_not_called()
        client.send_message.assert_called_once()
