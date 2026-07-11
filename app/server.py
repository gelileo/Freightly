"""Thin stdlib http.server shell around app.api.dispatch. No framework dependency.

The real logic + tests live in app/api.py (the pure dispatch function); this module only
translates HTTP <-> Request/Response and owns the socket."""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from app.api import Request, Response, dispatch


def make_handler(conn_factory, llm, transport=None, webhook_secret=None):
    """conn_factory() -> a fresh sqlite connection per request (sqlite connections are not
    shareable across threads; ThreadingHTTPServer serves each request on its own thread)."""

    class Handler(BaseHTTPRequestHandler):
        def _handle(self, method: str):
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b""
            try:
                body = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                return self._write(400, {"error": "invalid JSON body"})
            req = Request(method=method, path=self.path,
                          user_id=self.headers.get("X-User-Id"),
                          headers={k: v for k, v in self.headers.items()}, body=body)
            conn = conn_factory()
            try:
                resp = dispatch(req, conn=conn, llm=llm, transport=transport,
                                webhook_secret=webhook_secret)
            except Exception:  # controlled 500 — never let the request thread die / leak a trace
                resp = Response(500, {"error": "internal error"})
            finally:
                conn.close()
            self._write(resp.status, resp.body)

        def _write(self, status: int, body: dict):
            payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            self._handle("GET")

        def do_POST(self):
            self._handle("POST")

        def log_message(self, *args):  # quiet by default
            pass

    return Handler


def serve(conn_factory, llm=None, transport=None, *, host="127.0.0.1", port=8000,
          webhook_secret=None):
    if llm is None or transport is None:
        from app import config
        llm = llm or config.make_llm()
        transport = transport or config.make_transport()
    handler = make_handler(conn_factory, llm, transport, webhook_secret)
    ThreadingHTTPServer((host, port), handler).serve_forever()
