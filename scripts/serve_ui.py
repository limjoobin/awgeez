"""Serve the matching visualization and its read/compute API."""

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from scripts.visualization_data import available_waves, load_iteration  # noqa: E402


STATIC = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.css": ("app.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/favicon.svg": ("favicon.svg", "image/svg+xml"),
}


class Handler(BaseHTTPRequestHandler):
    def respond(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, status: int, payload: dict) -> None:
        self.respond(status, json.dumps(payload, allow_nan=False).encode(), "application/json")

    def do_GET(self) -> None:
        request = urlparse(self.path)
        if request.path in STATIC:
            filename, content_type = STATIC[request.path]
            self.respond(200, (ROOT / "web" / filename).read_bytes(), content_type)
            return
        if request.path == "/health":
            try:
                waves = available_waves()
            except Exception as exc:
                self.send_json(503, {"ok": False, "error": str(exc)})
                return
            self.send_json(200 if waves else 503, {"ok": bool(waves), "waves": waves})
            return
        if request.path == "/api/waves":
            try:
                waves = available_waves()
                self.send_json(200, {"waves": waves, "default": 2 if 2 in waves else waves[0]})
            except IndexError:
                self.send_json(503, {"error": "No ingested waves are available"})
            except Exception as exc:
                self.send_json(503, {"error": str(exc)})
            return
        if request.path == "/api/iteration":
            try:
                params = parse_qs(request.query, strict_parsing=True)
                wave = int(params.get("wave", ["2"])[0])
                iteration = int(params.get("iteration", ["1"])[0])
                removal = int(params.get("removal", ["5"])[0])
                seed = int(params.get("seed", ["7"])[0])
                self.send_json(200, load_iteration(wave, iteration, removal, seed))
            except (ValueError, KeyError) as exc:
                self.send_json(400, {"error": str(exc)})
            except Exception as exc:
                self.send_json(500, {"error": str(exc)})
            return
        self.send_json(404, {"error": "Not found"})


def main() -> None:
    port = int(os.environ.get("UI_PORT", "8000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"Matching UI listening on port {port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
