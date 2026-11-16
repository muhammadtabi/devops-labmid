#!/usr/bin/env python3
"""Receive authenticated test reports locally; REPORT_TOKEN is required."""

import argparse
import hmac
from http.server import ThreadingHTTPServer
import os
from pathlib import Path
import threading
from urllib.parse import urlsplit

from http_support import JSONHandler, RequestError
from reporting import MAX_REPORT_BYTES, validate_report, write_report_atomic


class ReceiverHandler(JSONHandler):
    def do_GET(self):
        if urlsplit(self.path).path == "/health":
            self.send_json(200, {"status": "ok"})
        else:
            self.send_json(404, {"error": "Not found."})

    def do_POST(self):
        if urlsplit(self.path).path != "/report":
            self.send_json(404, {"error": "Not found."})
            return
        tokens = self.headers.get_all("X-Report-Token", [])
        if len(tokens) != 1 or not hmac.compare_digest(tokens[0].encode("utf-8"), self.server.report_token.encode("utf-8")):
            self.send_json(401, {"error": "A valid X-Report-Token is required."})
            return
        try:
            report = self.read_json(MAX_REPORT_BYTES)
            validate_report(report)
            with self.server.output_lock:
                write_report_atomic(self.server.output_path, report)
        except RequestError as exc:
            self.send_json(exc.status, {"error": str(exc)})
            return
        except (ValueError, RecursionError):
            self.send_json(400, {"error": "Report schema or result counts are invalid."})
            return
        except OSError:
            self.send_json(500, {"error": "Could not persist the report."})
            return
        self.send_json(200, {"status": "received", "run_id": report["run_id"]})


def create_server(host="127.0.0.1", port=9000, output_path=None, token=None):
    token = os.environ.get("REPORT_TOKEN") if token is None else token
    if not token or not token.strip() or any(ord(character) < 33 or ord(character) > 126 for character in token):
        raise ValueError("REPORT_TOKEN is required and must contain printable ASCII without spaces.")
    server = ThreadingHTTPServer((host, port), ReceiverHandler)
    server.report_token = token
    server.output_path = Path(output_path if output_path is not None else Path.cwd() / "test-report.json").resolve()
    server.output_lock = threading.Lock()
    return server


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9000)
    parser.add_argument("--output", type=Path, default=Path.cwd() / "test-report.json")
    options = parser.parse_args(argv)
    try:
        server = create_server(options.host, options.port, options.output)
    except ValueError as exc:
        parser.error(str(exc))
    print(f"Report receiver: http://{options.host}:{server.server_port}/report")
    print(f"Atomic report output: {server.output_path}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
