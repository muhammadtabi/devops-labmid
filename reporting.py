"""Test report validation and atomic JSON persistence (no third-party packages)."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import tempfile

MAX_REPORT_BYTES = 2 * 1024 * 1024
RESULTS = {"passed", "failed", "error", "skipped"}


def validate_report(report):
    """Raise ValueError for malformed/internally inconsistent reports."""
    if not isinstance(report, dict) or type(report.get("schema_version")) is not int or report["schema_version"] != 1:
        raise ValueError("Report must be a version 1 JSON object.")
    for field in ("repository", "branch", "commit_sha", "run_id"):
        if field not in report:
            raise ValueError(f"Missing metadata field: {field}.")
        value = report[field]
        if value is not None and (not isinstance(value, str) or not value.strip() or len(value) > 2048):
            raise ValueError(f"{field} must be nonempty text or null when unavailable.")
    sha = report["commit_sha"]
    if sha is not None and not re.fullmatch(r"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})", sha):
        raise ValueError("commit_sha must be a full hexadecimal SHA or null.")
    timestamp = report.get("timestamp")
    if not isinstance(timestamp, str) or not timestamp.endswith("Z"):
        raise ValueError("timestamp must be an ISO-8601 UTC timestamp ending in Z.")
    try:
        if datetime.fromisoformat(timestamp[:-1] + "+00:00").utcoffset() != timezone.utc.utcoffset(None):
            raise ValueError("timestamp must be UTC.")
    except ValueError as exc:
        raise ValueError("timestamp must be a valid UTC timestamp.") from exc
    tests = report.get("tests")
    summary = report.get("summary")
    if not isinstance(tests, list) or len(tests) > 10000 or not isinstance(summary, dict):
        raise ValueError("tests must be a bounded list and summary must be an object.")
    counts = {"total": len(tests), "passed": 0, "failed": 0, "skipped": 0}
    names = set()
    for test in tests:
        if not isinstance(test, dict):
            raise ValueError("Each test must be an object.")
        name = test.get("name")
        result = test.get("result")
        message = test.get("failure_message")
        if not isinstance(name, str) or not name.strip() or len(name) > 2048 or name in names:
            raise ValueError("Test names must be unique, nonempty strings.")
        names.add(name)
        if not isinstance(result, str) or result not in RESULTS or not isinstance(message, str):
            raise ValueError("Test result or failure_message is invalid.")
        if result in {"failed", "error"} and not message.strip():
            raise ValueError("Failing tests must include a failure message.")
        if result == "passed" and message:
            raise ValueError("Passing tests must not have a failure message.")
        counts["failed" if result in {"failed", "error"} else result] += 1
    for field, expected in counts.items():
        if type(summary.get(field)) is not int or summary[field] != expected:
            raise ValueError(f"Inconsistent summary {field}.")
    expected_status = "failed" if counts["failed"] or not counts["total"] else "passed"
    if summary.get("status") != expected_status:
        raise ValueError("Overall status does not match test outcomes.")
    return report


def read_report(path):
    with Path(path).open("rb") as handle:
        body = handle.read(MAX_REPORT_BYTES + 1)
    if len(body) > MAX_REPORT_BYTES:
        raise ValueError("Report exceeds the maximum size.")
    report = json.loads(body.decode("utf-8"), parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"Invalid constant {value}")))
    return validate_report(report)


def write_report_atomic(path, report):
    validate_report(report)
    path = Path(path).resolve()
    body = (json.dumps(report, indent=2, ensure_ascii=True, allow_nan=False) + "\n").encode("utf-8")
    if len(body) > MAX_REPORT_BYTES:
        raise ValueError("Report exceeds the maximum size.")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(body)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
