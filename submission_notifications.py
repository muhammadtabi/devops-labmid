"""Standard-library SMTP confirmation for accepted portal submissions."""

from email.message import EmailMessage
import os
import smtplib
import ssl


def smtp_settings(environment=None):
    environment = os.environ if environment is None else environment
    required = ("SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_FROM")
    missing = [key for key in required if not environment.get(key)]
    if missing:
        return None
    try:
        port = int(environment.get("SMTP_PORT") or "587")
    except ValueError:
        raise ValueError("SMTP_PORT must be 587 (STARTTLS) or 465 (TLS).")
    if port not in {587, 465}:
        raise ValueError("SMTP_PORT must be 587 (STARTTLS) or 465 (TLS).")
    settings = {key: environment[key] for key in required}
    settings["SMTP_PORT"] = port
    for key in ("SMTP_HOST", "SMTP_USERNAME", "SMTP_FROM"):
        if "\r" in settings[key] or "\n" in settings[key]:
            raise ValueError(f"{key} must not contain newlines.")
    if "\r" in settings["SMTP_PASSWORD"] or "\n" in settings["SMTP_PASSWORD"]:
        raise ValueError("SMTP_PASSWORD must not contain newlines.")
    return settings


def send_submission_confirmation(submission, environment=None):
    try:
        settings = smtp_settings(environment)
        if settings is None:
            return "not_configured"
        recipient = submission["email"]
        if "\r" in recipient or "\n" in recipient:
            return "failed"
        message = EmailMessage()
        message["From"] = settings["SMTP_FROM"]
        message["To"] = recipient
        message["Subject"] = f"Assignment Submission Received: Task is Running in GitHub Workflow ({submission['assignment_title']})"
        message.set_content(
            f"Hello {submission['name']},\n\n"
            "Your assignment submission was saved successfully!\n\n"
            "Status: Your task is recorded and running in the automated verification workflow on GitHub.\n\n"
            "Submission Summary:\n"
            f"- Username / Name: {submission['name']}\n"
            f"- Email Address: {submission['email']}\n"
            f"- Registration Number: {submission['registration_number']}\n"
            f"- Assignment Title: {submission['assignment_title']}\n"
            f"- Submission URL: {submission['submission_url']}\n"
            f"- Submitted At (UTC): {submission['submitted_at']}\n\n"
            "Once the automated CI/CD pipeline completes all verification checks, your test report will be finalized.\n"
        )
        context = ssl.create_default_context()
        if settings["SMTP_PORT"] == 465:
            client = smtplib.SMTP_SSL(settings["SMTP_HOST"], 465, timeout=15, context=context)
        else:
            client = smtplib.SMTP(settings["SMTP_HOST"], 587, timeout=15)
        with client:
            if settings["SMTP_PORT"] == 587:
                client.ehlo()
                client.starttls(context=context)
                client.ehlo()
            client.login(settings["SMTP_USERNAME"], settings["SMTP_PASSWORD"])
            refused = client.send_message(message)
            if refused:
                return "failed"
        return "sent"
    except (ValueError, OSError, RuntimeError, smtplib.SMTPException):
        return "failed"
