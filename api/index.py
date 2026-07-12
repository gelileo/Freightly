"""Vercel Python serverless function: the JSON API. Vercel routes /api/* here (see vercel.json);
this strips the /api prefix and hands the request to the existing pure app.api.dispatch(). One
libSQL/Turso connection per request; llm/transport/wechat are built once per warm instance."""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api import Request, Response, dispatch  # noqa: E402
from app import db, config  # noqa: E402

_SVC = {}


def _services():
    if not _SVC:
        _SVC["llm"] = config.make_llm()
        _SVC["transport"] = config.make_transport()
        _SVC["wechat"] = config.make_wechat()
    return _SVC["llm"], _SVC["transport"], _SVC["wechat"]


def _strip_api(path: str) -> str:
    # Vercel routes /api/* to this function; dispatch expects the un-prefixed path.
    if path == "/api" or path == "/api/":
        return "/"
    if path.startswith("/api/"):
        return path[len("/api"):]        # "/api/cases" -> "/cases"
    return path


class handler(BaseHTTPRequestHandler):
    def _run(self, method: str):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        try:
            body = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            return self._write(400, {"error": "invalid JSON body"})
        req = Request(method=method, path=_strip_api(self.path),
                      user_id=self.headers.get("X-User-Id"),
                      headers={k: v for k, v in self.headers.items()}, body=body)
        llm, transport, wechat = _services()
        conn = db.connect()   # libSQL when LIBSQL_URL is set (Vercel), else sqlite (local)
        try:
            resp = dispatch(req, conn=conn, llm=llm, transport=transport,
                            webhook_secret=os.environ.get("WEBHOOK_SECRET"), wechat=wechat,
                            trust_user_header=False)  # production: never trust client X-User-Id
        except Exception:
            import traceback
            traceback.print_exc()
            resp = Response(500, {"error": "internal error"})
        finally:
            try:
                conn.close()
            except Exception:
                pass
        self._write(resp.status, resp.body)

    def do_GET(self):
        self._run("GET")

    def do_POST(self):
        self._run("POST")

    def _write(self, status: int, body: dict):
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass
