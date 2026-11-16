"""Small JSON HTTP helpers shared by the portal and local report receiver."""

import json
from http.server import BaseHTTPRequestHandler


class RequestError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


class JSONHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def send_bytes(self, status, body, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        self.send_header("Connection", "close")
        self.end_headers()
        self.close_connection = True
        self.wfile.write(body)

    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=True, allow_nan=False).encode("utf-8")
        self.send_bytes(status, body, "application/json; charset=utf-8")

    def read_json(self, max_bytes):
        if self.headers.get("Transfer-Encoding"):
            raise RequestError(400, "Transfer-Encoding is not supported; send Content-Length.")
        lengths = self.headers.get_all("Content-Length", [])
        if len(lengths) != 1 or not lengths[0].isascii() or not lengths[0].isdigit():
            raise RequestError(400, "A valid Content-Length is required.")
        # Reject a huge length before converting an arbitrarily long integer.
        if len(lengths[0]) > 10:
            raise RequestError(413, "Request body is too large.")
        length = int(lengths[0])
        if length > max_bytes:
            raise RequestError(413, "Request body is too large.")
        if self.headers.get_content_type() != "application/json":
            raise RequestError(415, "Content-Type must be application/json.")
        try:
            body = self.rfile.read(length)
            if len(body) != length:
                raise RequestError(400, "Incomplete request body.")
            return json.loads(body.decode("utf-8"), parse_constant=self.reject_constant)
        except (UnicodeError, ValueError, RecursionError) as exc:
            raise RequestError(400, "Request body must be valid UTF-8 JSON.") from exc
        except (TimeoutError, OSError) as exc:
            raise RequestError(408, "Timed out while reading the request body.") from exc

    @staticmethod
    def reject_constant(value):
        raise ValueError(f"Invalid JSON constant: {value}")
