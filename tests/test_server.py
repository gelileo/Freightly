"""Smoke test for the http.server shell — proves HTTP <-> dispatch wiring over a real socket.
The real coverage is in test_api.py (pure dispatch); this is one round-trip."""
import http.client
import json
import threading
from http.server import ThreadingHTTPServer

from app.db import connect, init_db
from app.server import make_handler
from engine.llm import FakeLlmClient


def _factory():
    c = connect(":memory:"); init_db(c); return c


def test_server_smoke():
    srv = ThreadingHTTPServer(("127.0.0.1", 0),
                              make_handler(_factory, FakeLlmClient(), webhook_secret="sek",
                                           trust_user_header=True))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        port = srv.server_address[1]
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request("GET", "/cases", headers={"X-User-Id": "op"})
        resp = conn.getresponse()
        assert resp.status == 200
        assert json.loads(resp.read()) == {"cases": []}

        conn.request("GET", "/cases")  # no X-User-Id
        assert conn.getresponse().status == 401
    finally:
        srv.shutdown()
        srv.server_close()
