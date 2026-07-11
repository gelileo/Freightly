from datetime import datetime, timezone, timedelta

import pytest

from app.db import connect, init_db
from app import repo


def _db():
    c = connect(":memory:"); init_db(c)
    return c


def test_schema_has_sessions_and_invites_and_union_id():
    c = _db()
    cols = {r["name"] for r in c.execute("PRAGMA table_info(users)")}
    assert "union_id" in cols
    tables = {r["name"] for r in
              c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"sessions", "invites"} <= tables


def test_create_user_with_union_id_and_lookup():
    c = _db()
    u = repo.create_user(c, "wx:abc", "wechat", "openid-abc", union_id="union-abc")
    assert u.union_id == "union-abc"
    found = repo.user_by_auth_id(c, "wechat", "openid-abc")
    assert found is not None and found.id == u.id and found.union_id == "union-abc"
    assert repo.user_by_auth_id(c, "wechat", "nope") is None
