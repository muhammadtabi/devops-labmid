#!/usr/bin/env python3
"""Run the SQLite-backed assignment portal: python3 server.py."""

import argparse
from contextlib import closing
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path
import sqlite3
from urllib.parse import urlsplit

from http_support import JSONHandler, RequestError
from validation import validate_submission

ROOT = Path(__file__).resolve().parent
DEFAULT_DB = ROOT / "data" / "submissions.db"
MAX_BODY_BYTES = 16 * 1024


def initialize_database(path):
    path = Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path, timeout=10)) as connection:
        connection.execute("PRAGMA journal_mode=WAL")
        with connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS submissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    registration_number TEXT NOT NULL,
                    assignment_title TEXT NOT NULL,
                    submission_url TEXT NOT NULL,
                    submitted_at TEXT NOT NULL
                )
            """)
    return path


class PortalHandler(JSONHandler):
    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/api/submissions":
            try:
                with closing(sqlite3.connect(self.server.db_path, timeout=10)) as connection:
                    connection.row_factory = sqlite3.Row
                    rows = connection.execute("SELECT * FROM submissions ORDER BY id DESC").fetchall()
                self.send_json(200, {"submissions": [dict(row) for row in rows]})
            except sqlite3.Error:
                self.send_json(503, {"error": "Could not read submissions. Please try again."})
            return
        if path == "/config.json":
            self.send_json(200, {"mode": "server"})
            return
        assets = {
            "/": ("index.html", "text/html; charset=utf-8"),
            "/index.html": ("index.html", "text/html; charset=utf-8"),
            "/app.js": ("app.js", "text/javascript; charset=utf-8"),
            "/styles.css": ("styles.css", "text/css; charset=utf-8"),
        }
        if path not in assets:
            self.send_json(404, {"error": "Not found."})
            return
        name, content_type = assets[path]
        try:
            self.send_bytes(200, (ROOT / "static" / name).read_bytes(), content_type)
        except OSError:
            self.send_json(500, {"error": "Static asset unavailable."})

    def do_POST(self):
        if urlsplit(self.path).path != "/api/submissions":
            self.send_json(404, {"error": "Not found."})
            return
        try:
            cleaned, errors = validate_submission(self.read_json(MAX_BODY_BYTES))
        except RequestError as exc:
            self.send_json(exc.status, {"error": str(exc)})
            return
        if errors:
            self.send_json(400, {"error": "Please correct the highlighted fields.", "errors": errors})
            return
        submitted_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        try:
            with closing(sqlite3.connect(self.server.db_path, timeout=10)) as connection:
                with connection:
                    cursor = connection.execute(
                        "INSERT INTO submissions (name, registration_number, assignment_title, submission_url, submitted_at) VALUES (?, ?, ?, ?, ?)",
                        (*[cleaned[field] for field in ("name", "registration_number", "assignment_title", "submission_url")], submitted_at),
                    )
                    submission_id = cursor.lastrowid
            self.send_json(201, {"submission": {"id": submission_id, **cleaned, "submitted_at": submitted_at}})
        except sqlite3.Error:
            self.send_json(503, {"error": "Could not save your submission. Please try again."})


def create_server(host="127.0.0.1", port=8000, db_path=DEFAULT_DB):
    """Construct an initialized server; port=0 selects a free port for tests."""
    database = initialize_database(db_path)
    server = ThreadingHTTPServer((host, port), PortalHandler)
    server.db_path = database
    return server


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    options = parser.parse_args(argv)
    server = create_server(options.host, options.port, options.db)
    print(f"Assignment portal: http://{options.host}:{server.server_port}")
    print(f"SQLite database: {server.db_path}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
