"""Vercel deployment artifacts: the API function's path handling, vercel.json validity, and
schema.sql staying in sync with app.db._SCHEMA. (Runs under stdlib python3 — importing api.index
does not pull google/libsql; those load lazily at request time.)"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_api_index_imports_and_strips_prefix():
    from api.index import _strip_api
    assert _strip_api("/api/cases") == "/cases"
    assert _strip_api("/api/cases/abc/messages/x/approve") == "/cases/abc/messages/x/approve"
    assert _strip_api("/api") == "/"
    assert _strip_api("/api/") == "/"
    assert _strip_api("/cases") == "/cases"          # already un-prefixed → unchanged


def test_vercel_json_valid_and_routes():
    cfg = json.load(open(os.path.join(ROOT, "vercel.json")))
    sources = [r["source"] for r in cfg["rewrites"]]
    assert "/" in sources and "/customer" in sources
    assert any(s.startswith("/api/") for s in sources)          # API funneled to the function
    # /api/poll routed before the catch-all so cron reaches api/poll.py
    assert sources.index("/api/poll") < sources.index("/api/(.*)")
    assert cfg["crons"][0]["path"] == "/api/poll"


def test_schema_sql_in_sync_with_db_schema():
    from app.db import _SCHEMA
    on_disk = open(os.path.join(ROOT, "schema.sql")).read()
    assert _SCHEMA.strip() in on_disk, "schema.sql stale — run scripts/export_schema.py"
