#!/usr/bin/env python3
"""Serve the Muster setup page on this computer only, and save the owner's choices.

Usage: python3 serve.py <project-folder>

Prints the page address. When the owner presses Start, the choices are saved to
<project-folder>/muster/setup-choices.json and the helper stops. Nothing leaves this computer.
"""
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    if len(sys.argv) != 2 or not os.path.isdir(sys.argv[1]):
        print("usage: serve.py <project-folder>")
        return 2
    out_dir = os.path.join(os.path.abspath(sys.argv[1]), "muster")
    out_file = os.path.join(out_dir, "setup-choices.json")
    with open(os.path.join(HERE, "index.html"), "rb") as fh:
        page = fh.read()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            if self.path not in ("/", "/index.html"):
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(page)))
            self.end_headers()
            self.wfile.write(page)

        def do_POST(self):
            if self.path != "/save":
                self.send_error(404)
                return
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 100_000:
                self.send_error(400)
                return
            try:
                choices = json.loads(self.rfile.read(length).decode("utf-8"))
                if not isinstance(choices, dict) or not str(choices.get("vision", "")).strip():
                    raise ValueError("missing vision")
            except ValueError:
                self.send_error(400)
                return
            os.makedirs(out_dir, exist_ok=True)
            with open(out_file, "w", encoding="utf-8") as fh:
                json.dump(choices, fh, indent=2, ensure_ascii=False)
            body = b'{"saved": true}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            threading.Thread(target=server.shutdown, daemon=True).start()

    server = HTTPServer(("127.0.0.1", 0), Handler)
    print("http://localhost:%d/" % server.server_address[1], flush=True)
    server.serve_forever()
    print("saved: %s" % out_file, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
