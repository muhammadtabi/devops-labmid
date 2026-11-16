"""Shared server-side validation; the demo changes exactly one marked line."""

import ipaddress
import re
from urllib.parse import urlsplit

FIELD_LIMITS = {
    "name": 120,
    "registration_number": 80,
    "assignment_title": 200,
    "submission_url": 2048,
}
FIELD_LABELS = {
    "name": "Name",
    "registration_number": "Registration number",
    "assignment_title": "Assignment title",
    "submission_url": "Submission URL",
}
URL_ERROR = "Submission URL must be a valid HTTP or HTTPS URL without credentials."


def _is_http_url(value):
    if any(character.isspace() or ord(character) < 32 or ord(character) == 127
           for character in value) or "\\" in value:
        return False
    try:
        parsed = urlsplit(value)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
            return False
        if parsed.username is not None or parsed.password is not None:
            return False
        host = parsed.hostname
        if not host or (parsed.port is not None and not 1 <= parsed.port <= 65535):
            return False
        if parsed.netloc.endswith(":"):
            return False
        if ":" in host:
            ipaddress.IPv6Address(host)
            return True
        ascii_host = host.encode("idna").decode("ascii").rstrip(".")
        if not ascii_host or len(ascii_host) > 253:
            return False
        # Numeric hosts must be actual dotted IPv4 addresses, not browser shortcuts.
        if re.fullmatch(r"[0-9.]+", ascii_host):
            ipaddress.IPv4Address(ascii_host)
            return True
        return all(re.fullmatch(r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?", label)
                   for label in ascii_host.split("."))
    except (ValueError, UnicodeError):
        return False


def validate_submission_url(value):
    # DEMO_DEFECT_TARGET: URL protocol/host validation (do not move).
    return _is_http_url(value)


def validate_submission(payload):
    if not isinstance(payload, dict):
        return {}, {"request": "The JSON body must be an object."}
    cleaned = {}
    errors = {}
    for field, limit in FIELD_LIMITS.items():
        raw = payload.get(field)
        if not isinstance(raw, str) or not raw.strip():
            errors[field] = f"{FIELD_LABELS[field]} is required and must be text."
            continue
        value = raw.strip()
        cleaned[field] = value
        if len(value) > limit:
            errors[field] = f"{FIELD_LABELS[field]} must be at most {limit} characters."
        elif any(ord(character) < 32 or ord(character) == 127 for character in value):
            errors[field] = f"{FIELD_LABELS[field]} must not contain control characters."
    if "submission_url" in cleaned and "submission_url" not in errors:
        if not validate_submission_url(cleaned["submission_url"]):
            errors["submission_url"] = URL_ERROR
    return cleaned, errors
