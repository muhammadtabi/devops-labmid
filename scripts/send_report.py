#!/usr/bin/env python3
"""Deliver the actual JSON report to the authenticated local receiver."""

import argparse
import json
import os
from pathlib import Path
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from reporting import read_report


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        # Never forward the shared secret to a redirect target.
        return None


def send_report(report_path, url, token, attempts=3, timeout=5):
    if not token or any(ord(character) < 33 or ord(character) > 126 for character in token):
        raise ValueError("REPORT_TOKEN is required and must be printable ASCII without spaces.")
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username is not None or parsed.password is not None or parsed.fragment:
        raise ValueError("REPORT_RECEIVER_URL must be an HTTP(S) URL without credentials or a fragment.")
    if not 1 <= attempts <= 5 or not 0 < timeout <= 30:
        raise ValueError("Use 1-5 attempts and a timeout greater than 0 and at most 30 seconds.")
    report = read_report(report_path)
    body = json.dumps(report, ensure_ascii=True, allow_nan=False).encode("utf-8")
    opener = build_opener(NoRedirects())
    for attempt in range(1, attempts + 1):
        request = Request(url, data=body, headers={"Content-Type": "application/json", "X-Report-Token": token}, method="POST")
        try:
            with opener.open(request, timeout=timeout) as response:
                answer = response.read(8193)
                if len(answer) > 8192 or response.status != 200:
                    raise ValueError("Receiver returned an unexpected response.")
                acknowledgement = json.loads(answer.decode("utf-8"))
                if not isinstance(acknowledgement, dict) or acknowledgement.get("status") != "received" or acknowledgement.get("run_id") != report["run_id"]:
                    raise ValueError("Receiver did not acknowledge this report.")
            return report
        except HTTPError as exc:
            retryable = exc.code in {408, 429} or 500 <= exc.code <= 599
            exc.close()
            if not retryable or attempt == attempts:
                raise RuntimeError(f"Report delivery failed with HTTP {exc.code}.") from exc
        except (URLError, TimeoutError, OSError) as exc:
            if attempt == attempts:
                raise RuntimeError(f"Report receiver unreachable after {attempts} attempt(s).") from exc
        if attempt < attempts:
            time.sleep(min(attempt, 2))
    raise RuntimeError("Report delivery did not complete.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=ROOT / "test-report.json")
    parser.add_argument("--url", default=os.environ.get("REPORT_RECEIVER_URL", "http://127.0.0.1:9000/report"))
    parser.add_argument("--attempts", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=5)
    options = parser.parse_args(argv)
    try:
        report = send_report(options.report, options.url, os.environ.get("REPORT_TOKEN"), options.attempts, options.timeout)
    except (ValueError, OSError, RuntimeError) as exc:
        print(f"Report delivery error: {exc}", file=sys.stderr)
        return 1
    print(f"Delivered {report['summary']['status']} report ({report['summary']['total']} tests).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
