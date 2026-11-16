#!/usr/bin/env python3
"""Introduce/fix the single marked real URL-validation defect for the lab."""

import argparse
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "validation.py"
GOOD_BLOCK = '''def validate_submission_url(value):
    # DEMO_DEFECT_TARGET: URL protocol/host validation (do not move).
    return _is_http_url(value)
'''
BAD_BLOCK = '''def validate_submission_url(value):
    # DEMO_DEFECT_TARGET: URL protocol/host validation (do not move).
    return True  # DEMO DEFECT: bypasses actual HTTP/HTTPS URL validation.
'''


def change_defect(action, target=TARGET):
    target = Path(target)
    content = target.read_text(encoding="utf-8")
    source, destination = (GOOD_BLOCK, BAD_BLOCK) if action == "introduce" else (BAD_BLOCK, GOOD_BLOCK)
    if action not in {"introduce", "fix"}:
        raise ValueError("Choose introduce or fix.")
    if content.count("def validate_submission_url(") != 1 or content.count("DEMO_DEFECT_TARGET") != 1:
        raise ValueError("Refusing edits: the marked validation function is not unique.")
    if destination in content and source not in content:
        return False
    if content.count(source) != 1 or destination in content:
        raise ValueError("Refusing edits: the target function has unrelated changes. Restore it manually.")
    updated = content.replace(source, destination, 1)
    descriptor, temporary = tempfile.mkstemp(prefix=".validation-", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(updated)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, target.stat().st_mode)
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    # Avoid stale same-second bytecode when demonstrating rapid introduce/fix cycles.
    for cached in (target.parent / "__pycache__").glob("validation.*.pyc"):
        cached.unlink()
    return True


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("introduce", "fix"))
    options = parser.parse_args(argv)
    try:
        changed = change_defect(options.action)
    except (ValueError, OSError) as exc:
        print(f"Defect demo refused: {exc}", file=sys.stderr)
        return 1
    print(f"URL validation defect {options.action}: {'changed' if changed else 'already in requested state'}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
