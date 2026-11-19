import http.client
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest

import server
from validation import FIELD_LIMITS, validate_submission_url

VALID_SUBMISSION = {
    "name": "Ada Lovelace",
    "email": "ada.lovelace@gmail.com",
    "registration_number": "REG-101",
    "assignment_title": "DevOps Lab",
    "submission_url": "https://example.com/assignment?version=1",
}


class PortalTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temporary.name) / "data" / "submissions.db"
        self.start_server()

    def start_server(self):
        self.server = server.create_server(port=0, db_path=self.db_path)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        self.thread.start()

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def tearDown(self):
        self.stop_server()
        self.temporary.cleanup()

    def request(self, method, path="/api/submissions", payload=None, body=None, headers=None):
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        try:
            connection.request(method, path, body=body, headers=headers if headers is not None else {"Content-Type": "application/json"})
            response = connection.getresponse()
            data = response.read()
            return response.status, data, dict(response.getheaders())
        finally:
            connection.close()

    def test_valid_submission_saves_and_lists(self):
        status, data, _ = self.request("POST", payload=VALID_SUBMISSION)
        self.assertEqual(status, 201)
        saved = json.loads(data)["submission"]
        self.assertEqual(saved["id"], 1)
        self.assertTrue(saved["submitted_at"].endswith("Z"))
        status, data, _ = self.request("GET")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(data)["submissions"], [saved])

    def test_each_required_field_rejects_missing_blank_and_wrong_types(self):
        for field in VALID_SUBMISSION:
            for bad_value in (None, "", "   ", 42, [], {}):
                with self.subTest(field=field, value=bad_value):
                    payload = {**VALID_SUBMISSION, field: bad_value}
                    status, data, _ = self.request("POST", payload=payload)
                    self.assertEqual(status, 400)
                    self.assertIn(field, json.loads(data)["errors"])
            payload = dict(VALID_SUBMISSION)
            del payload[field]
            self.assertEqual(self.request("POST", payload=payload)[0], 400)
        self.assertEqual(json.loads(self.request("GET")[1])["submissions"], [])

    def test_missing_registration_number_is_rejected(self):
        payload = {**VALID_SUBMISSION, "registration_number": ""}
        status, data, _ = self.request("POST", payload=payload)
        self.assertEqual(status, 400)
        self.assertIn("Registration number is required", json.loads(data)["errors"]["registration_number"])
        self.assertEqual(json.loads(self.request("GET")[1])["submissions"], [])

    def test_missing_and_invalid_email_are_rejected(self):
        for value in (None, "", "   ", "plainaddress", "@gmail.com", "name@", "name@localhost",
                      "name@-gmail.com", "name@google..com", ".name@gmail.com", "name..part@gmail.com",
                      "name@example.com\nBcc:other@example.com", "name gmail@gmail.com", 42):
            with self.subTest(email=value):
                status, data, _ = self.request("POST", payload={**VALID_SUBMISSION, "email": value})
                self.assertEqual(status, 400)
                self.assertIn("email", json.loads(data)["errors"])
        payload = dict(VALID_SUBMISSION)
        del payload["email"]
        self.assertEqual(self.request("POST", payload=payload)[0], 400)

    def test_invalid_url_is_rejected(self):
        for value in ("not-a-url", "javascript:alert(1)", "ftp://example.com/file", "/relative", "https://", "https://user:password@example.com", "https://example.com:70000", "https://exa mple.com", "https://example.com\\evil", "http://127.1", "https://bad_host.example", "https://example.com:"):
            with self.subTest(url=value):
                status, data, _ = self.request("POST", payload={**VALID_SUBMISSION, "submission_url": value})
                self.assertEqual(status, 400)
                self.assertIn("submission_url", json.loads(data)["errors"])
        self.assertEqual(json.loads(self.request("GET")[1])["submissions"], [])

    def test_http_https_localhost_ipv4_ipv6_and_idn_urls(self):
        for value in ("http://example.com", "HTTPS://example.com/path", "http://localhost:8000", "http://127.0.0.1:8000/path", "http://[::1]:8000/path", "https://bücher.example/path"):
            with self.subTest(url=value):
                self.assertTrue(validate_submission_url(value))
                self.assertEqual(self.request("POST", payload={**VALID_SUBMISSION, "submission_url": value})[0], 201)

    def test_persistence_after_server_restart_and_database_creation(self):
        self.assertTrue(self.db_path.is_file())
        self.request("POST", payload=VALID_SUBMISSION)
        self.stop_server()
        self.start_server()
        self.assertEqual(len(json.loads(self.request("GET")[1])["submissions"]), 1)

    def test_existing_database_is_migrated_with_empty_email(self):
        self.stop_server()
        with sqlite3.connect(self.db_path) as connection:
            connection.execute("DROP TABLE submissions")
            connection.execute("""
                CREATE TABLE submissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    registration_number TEXT NOT NULL,
                    assignment_title TEXT NOT NULL,
                    submission_url TEXT NOT NULL,
                    submitted_at TEXT NOT NULL
                )
            """)
            connection.execute(
                "INSERT INTO submissions (name, registration_number, assignment_title, submission_url, submitted_at) VALUES (?, ?, ?, ?, ?)",
                ("Existing Student", "REG-OLD", "Old Assignment", "https://example.com/old", "2026-11-18T10:00:00Z"),
            )
        self.start_server()
        submissions = json.loads(self.request("GET")[1])["submissions"]
        self.assertEqual(len(submissions), 1)
        self.assertEqual(submissions[0]["email"], "")

    def test_multiple_submissions_order_and_trim(self):
        self.request("POST", payload=VALID_SUBMISSION)
        self.request("POST", payload={**VALID_SUBMISSION, "name": "  Grace Hopper  ", "assignment_title": "Second"})
        saved = json.loads(self.request("GET")[1])["submissions"]
        self.assertEqual([item["id"] for item in saved], [2, 1])
        self.assertEqual(saved[0]["name"], "Grace Hopper")

    def test_malformed_non_object_and_wrong_content_type_requests(self):
        for body in (b"{", b"\xff", b"null", b"[]", b'"text"', b'{"name": NaN}'):
            with self.subTest(body=body):
                self.assertEqual(self.request("POST", body=body)[0], 400)
        self.assertEqual(self.request("POST", body=b"{}", headers={"Content-Type": "text/plain"})[0], 415)
        self.assertEqual(self.request("POST", body=b"{}", headers={"Content-Type": "application/json", "Content-Length": "-1"})[0], 400)
        self.assertEqual(self.request("POST", body=b"{}", headers={"Content-Type": "application/json", "Transfer-Encoding": "chunked"})[0], 400)

    def test_oversize_and_field_length_requests_are_rejected(self):
        self.assertEqual(self.request("POST", body=b"x" * (server.MAX_BODY_BYTES + 1))[0], 413)
        for field, limit in FIELD_LIMITS.items():
            with self.subTest(field=field):
                self.assertEqual(self.request("POST", payload={**VALID_SUBMISSION, field: "x" * (limit + 1)})[0], 400)

    def test_literal_html_and_sql_text_round_trip_without_execution(self):
        payload = {**VALID_SUBMISSION, "name": "<script>alert(1)</script>", "assignment_title": "'); DROP TABLE submissions; --"}
        self.assertEqual(self.request("POST", payload=payload)[0], 201)
        self.assertEqual(json.loads(self.request("GET")[1])["submissions"][0]["name"], payload["name"])
        self.assertEqual(self.request("POST", payload=VALID_SUBMISSION)[0], 201)

    def test_only_allowlisted_assets_and_server_mode_are_served(self):
        for path in ("/", "/index.html", "/app.js", "/styles.css"):
            with self.subTest(path=path):
                status, body, headers = self.request("GET", path)
                self.assertEqual(status, 200)
                self.assertTrue(body)
                self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(json.loads(self.request("GET", "/config.json")[1]), {"mode": "server"})
        for path in ("/server.py", "/../server.py", "/data/submissions.db", "/static/../server.py"):
            self.assertEqual(self.request("GET", path)[0], 404)
        self.assertEqual(self.request("POST", "/unknown", payload={})[0], 404)
