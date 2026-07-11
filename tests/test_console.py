"""Smoke test: the stdlib server serves the agent console HTML at `/`, and still serves the
JSON API on other paths. The interactive behavior is verified in a real browser separately."""
import http.client
import json
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

from app.db import connect, init_db
from app.server import make_handler
from engine.llm import FakeLlmClient

WEB_ROOT = str(Path(__file__).resolve().parent.parent / "web")


def _factory():
    c = connect(":memory:"); init_db(c); return c


def test_console_served_and_api_still_json():
    srv = ThreadingHTTPServer(("127.0.0.1", 0),
                              make_handler(_factory, FakeLlmClient(), web_root=WEB_ROOT))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        port = srv.server_address[1]
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)

        conn.request("GET", "/")
        r = conn.getresponse(); body = r.read().decode("utf-8")
        assert r.status == 200
        assert "text/html" in r.getheader("Content-Type")
        assert "代理控制台" in body and "/cases" in body  # console markup + it calls the API

        conn.request("GET", "/cases", headers={"X-User-Id": "op"})
        r2 = conn.getresponse()
        assert r2.status == 200 and json.loads(r2.read()) == {"cases": []}  # API still JSON

        conn.request("GET", "/customer")  # customer app served too
        r3 = conn.getresponse(); cbody = r3.read().decode("utf-8")
        assert r3.status == 200 and "text/html" in r3.getheader("Content-Type")
        assert "客户中心" in cbody
    finally:
        srv.shutdown(); srv.server_close()
