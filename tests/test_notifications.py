import unittest
from unittest.mock import MagicMock, patch

from submission_notifications import send_submission_confirmation


SUBMISSION = {
    "name": "Ada Lovelace",
    "email": "ada.lovelace@gmail.com",
    "registration_number": "REG-101",
    "assignment_title": "DevOps Lab",
    "submission_url": "https://example.com/assignment",
    "submitted_at": "2026-11-18T10:00:00Z",
}


class SubmissionNotificationTests(unittest.TestCase):
    def test_not_configured_does_not_raise(self):
        self.assertEqual(send_submission_confirmation(SUBMISSION, {}), "not_configured")

    def test_starttls_sends_to_submitted_email(self):
        client = MagicMock()
        client.__enter__.return_value = client
        client.send_message.return_value = {}
        environment = {
            "SMTP_HOST": "smtp.gmail.com",
            "SMTP_PORT": "587",
            "SMTP_USERNAME": "lab-user@gmail.com",
            "SMTP_PASSWORD": "unit-test-not-a-real-secret",
            "SMTP_FROM": "lab-user@gmail.com",
        }
        with patch("submission_notifications.smtplib.SMTP", return_value=client) as smtp:
            status = send_submission_confirmation(SUBMISSION, environment)
        self.assertEqual(status, "sent")
        smtp.assert_called_once_with("smtp.gmail.com", 587, timeout=15)
        message = client.send_message.call_args.args[0]
        self.assertEqual(message["To"], "ada.lovelace@gmail.com")
        methods = [call[0] for call in client.method_calls]
        self.assertLess(methods.index("starttls"), methods.index("login"))
        self.assertLess(methods.index("login"), methods.index("send_message"))

    def test_smtp_failure_is_reported_without_raising(self):
        client = MagicMock()
        client.__enter__.return_value = client
        client.login.side_effect = RuntimeError("authentication failed")
        environment = {
            "SMTP_HOST": "smtp.gmail.com",
            "SMTP_PORT": "587",
            "SMTP_USERNAME": "lab-user@gmail.com",
            "SMTP_PASSWORD": "unit-test-not-a-real-secret",
            "SMTP_FROM": "lab-user@gmail.com",
        }
        with patch("submission_notifications.smtplib.SMTP", return_value=client):
            self.assertEqual(send_submission_confirmation(SUBMISSION, environment), "failed")
