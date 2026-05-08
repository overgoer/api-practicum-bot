"""Simple HTTP backend that echoes request info. Used in balance_lab demo."""
import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler

NAME = os.environ.get("BACKEND_NAME", "unknown")
PORT = int(os.environ.get("BACKEND_PORT", 9001))


class Handler(BaseHTTPRequestHandler):

    def _respond(self, body_data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("X-Backend-Name", NAME)
        self.end_headers()
        resp = {
            "backend": NAME,
            "path": self.path,
            "method": self.command,
            "host_header": self.headers.get("Host", ""),
            "x_forwarded_for": self.headers.get("X-Forwarded-For", ""),
            "x_forwarded_host": self.headers.get("X-Forwarded-Host", ""),
            "x_real_ip": self.headers.get("X-Real-IP", ""),
            "all_headers": dict(self.headers),
        }
        if body_data is not None:
            resp["body"] = body_data
        self.wfile.write(json.dumps(resp, indent=2, ensure_ascii=False).encode())

    def do_GET(self):
        self._respond(None)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode() if length else ""
        self._respond(body)

    def log_message(self, fmt, *args):
        print(f"[{NAME}] {args[0]} {args[1]} {args[2]}")


HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
