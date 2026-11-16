#!/usr/bin/env python3
"""Optional SMTP delivery. Never run this unless email delivery is intended."""

import argparse
from email.message import EmailMessage
import os
from pathlib import Path
import smtplib
import ssl
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from reporting import read_report


def smtp_settings(environment):
    required = ("SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_FROM", "SMTP_TO")
    missing = [key for key in required if not environment.get(key)]
    if missing:
        raise ValueError("Missing SMTP configuration: " + ", ".join(missing))
    settings = {key: environment[key] for key in required}
    try:
        settings["SMTP_PORT"] = int(environment.get("SMTP_PORT") or "587")
    except ValueError as exc:
        raise ValueError("SMTP_PORT must be 587 (STARTTLS) or 465 (TLS).") from exc
    if settings["SMTP_PORT"] not in {587, 465}:
        raise ValueError("SMTP_PORT must be 587 (STARTTLS) or 465 (TLS).")
    for key in ("SMTP_HOST", "SMTP_USERNAME", "SMTP_FROM", "SMTP_TO"):
        if "\r" in settings[key] or "\n" in settings[key]:
            raise ValueError(f"{key} must not contain newlines.")
    return settings


def build_message(report_path, settings):
    report = read_report(report_path)
    summary = report["summary"]
    message = EmailMessage()
    message["From"] = settings["SMTP_FROM"]
    message["To"] = settings["SMTP_TO"]
    message["Subject"] = f"Assignment portal tests: {summary['status'].upper()} — {report['repository'] or 'repository unavailable'}"
    lines = [
        "Actual unittest report",
        f"Repository: {report['repository'] or 'unavailable'}",
        f"Branch: {report['branch'] or 'unavailable'}",
        f"Full commit SHA: {report['commit_sha'] or 'unavailable'}",
        f"Run ID: {report['run_id'] or 'unavailable'}",
        f"UTC timestamp: {report['timestamp']}",
        f"Overall status: {summary['status']}",
        f"Total: {summary['total']}; passed: {summary['passed']}; failed (including errors): {summary['failed']}; skipped: {summary['skipped']}",
        "",
    ]
    for test in report["tests"]:
        lines.append(f"{test['name']}: {test['result']}")
        if test["failure_message"]:
            lines.append(test["failure_message"])
    message.set_content("\n".join(lines))
    # Attach the actual bytes, not a synthetic summary.
    message.add_attachment(Path(report_path).read_bytes(), maintype="application", subtype="json", filename="test-report.json")
    return message


def email_report(report_path, environment=None):
    settings = smtp_settings(os.environ if environment is None else environment)
    message = build_message(report_path, settings)
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
            raise RuntimeError("SMTP server refused one or more recipients.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=ROOT / "test-report.json")
    options = parser.parse_args(argv)
    try:
        email_report(options.report)
    except (ValueError, OSError, RuntimeError, smtplib.SMTPException) as exc:
        print(f"Email report delivery failed: {exc}", file=sys.stderr)
        return 1
    print("Test report email sent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
