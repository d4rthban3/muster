#!/usr/bin/env python3
"""Serve the Muster setup page on this computer only, and save the owner's choices.

Usage: python3 serve.py <choices-file>

Prints the page address. When the owner presses Start, the choices are saved to <choices-file>
(setup uses ~/Muster/.setup-choices.json) and the helper stops. Nothing leaves this computer.
Only the page this helper served can save: it must send the one-time key printed into the page,
from this helper's own address, as JSON, in the expected shape.
"""
import json
import os
import re
import secrets
import sys
import threading
import unicodedata
from http.server import BaseHTTPRequestHandler, HTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
LOCKED = ["Spending money", "Keys or passwords", "Deleting anything"]
CORE = ["Manager", "Builder A", "Designer", "Inspector"]
ADDONS = {"Sketchpad", "AI Socket", "Agent Teacher", "Design Inspector"}
EXTRA_BUILDER = re.compile(r"^Builder [B-Z]$")
PATH_BREAKERS = set('/\\:*?"<>|')
HIDDEN = {"Cc", "Cf", "Cs", "Co", "Cn", "Zl", "Zp"}


def project_problem(name):
    """Why a project name cannot be a folder name, in plain words, or None if it can."""
    if not name:
        return "empty"
    if len(name) > 40:
        return "too long"
    if any(ch in PATH_BREAKERS for ch in name):
        return "has a character a folder name cannot have"
    if any(unicodedata.category(ch) in HIDDEN for ch in name):
        return "has a hidden character"
    if name.startswith("."):
        return "starts with a dot"
    if not any(ch.isalnum() for ch in name):
        return "has no letter or digit"
    return None


def check_choices(choices):
    """Return the choices if they have exactly the expected shape, else raise ValueError."""
    if not isinstance(choices, dict) or set(choices) != {"project", "vision", "crew", "asks_first"}:
        raise ValueError("wrong fields")
    project, vision, crew, asks = choices["project"], choices["vision"], choices["crew"], choices["asks_first"]
    if not isinstance(project, str):
        raise ValueError("project")
    project = choices["project"] = unicodedata.normalize("NFC", project).strip()
    if project_problem(project):
        raise ValueError("project")
    if not isinstance(vision, str) or not vision.strip() or len(vision) > 4000:
        raise ValueError("vision")
    if not isinstance(crew, list) or len(crew) > 40 or len(set(crew)) != len(crew):
        raise ValueError("crew")
    for name in crew:
        if not isinstance(name, str) or not (name in CORE or name in ADDONS or EXTRA_BUILDER.match(name)):
            raise ValueError("crew name")
    if crew[:4] != CORE:
        raise ValueError("core crew")
    if not isinstance(asks, list) or len(asks) > 23 or asks[:3] != LOCKED:
        raise ValueError("asks_first")
    for item in asks:
        if not isinstance(item, str) or not item.strip() or len(item) > 200:
            raise ValueError("asks_first item")
    return choices


def main():
    if len(sys.argv) != 2:
        print("usage: serve.py <choices-file>")
        return 2
    out_file = os.path.abspath(os.path.expanduser(sys.argv[1]))
    out_dir = os.path.dirname(out_file)
    token = secrets.token_urlsafe(24)
    with open(os.path.join(HERE, "index.html"), "rb") as fh:
        page = fh.read().replace(b"__MUSTER_TOKEN__", token.encode())
    allowed = set()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def own_host(self):
            return self.headers.get("Host", "") in allowed

        def do_GET(self):
            if not self.own_host():
                self.send_error(403)
                return
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
            origin = self.headers.get("Origin")
            if (not self.own_host()
                    or (origin is not None and origin not in {"http://" + h for h in allowed})
                    or not secrets.compare_digest(self.headers.get("X-Muster-Token", "").encode("utf-8", "replace"), token.encode())
                    or not self.headers.get("Content-Type", "").startswith("application/json")):
                self.send_error(403)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = 0
            if length <= 0 or length > 100_000:
                self.send_error(400)
                return
            try:
                choices = check_choices(json.loads(self.rfile.read(length).decode("utf-8")))
            except (ValueError, UnicodeDecodeError):
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
    port = server.server_address[1]
    allowed.update({"localhost:%d" % port, "127.0.0.1:%d" % port})
    print("http://localhost:%d/" % port, flush=True)
    server.serve_forever()
    print("saved: %s" % out_file, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
