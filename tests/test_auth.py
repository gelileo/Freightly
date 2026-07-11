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


from app import auth
from app.wechat import FakeWeChatClient

WX = FakeWeChatClient()
NOW = datetime(2026, 7, 11, 12, 0, 0, tzinfo=timezone.utc)


def test_login_creates_user_needs_bind_then_resolves():
    c = _db()
    token, user, needs_bind = auth.login_wechat(c, WX, "alice", now=NOW)
    assert user.auth_kind == "wechat" and user.auth_id == "openid-alice"
    assert user.union_id == "union-alice"
    assert needs_bind is True                       # no memberships yet
    assert auth.resolve_session(c, token, now=NOW) == user.id
    # raw token is not stored; only its hash
    assert c.execute("SELECT token_hash FROM sessions").fetchone()["token_hash"] != token


def test_repeat_login_reuses_user():
    c = _db()
    _, u1, _ = auth.login_wechat(c, WX, "bob", now=NOW)
    _, u2, _ = auth.login_wechat(c, WX, "bob", now=NOW)
    assert u1.id == u2.id
    assert c.execute("SELECT COUNT(*) n FROM users").fetchone()["n"] == 1


def test_expired_and_revoked_sessions_do_not_resolve():
    c = _db()
    token, _, _ = auth.login_wechat(c, WX, "carol", now=NOW, ttl_days=1)
    later = NOW + timedelta(days=2)
    assert auth.resolve_session(c, token, now=later) is None      # expired
    fresh, _, _ = auth.login_wechat(c, WX, "dave", now=NOW)
    auth.revoke_session(c, fresh)
    assert auth.resolve_session(c, fresh, now=NOW) is None        # revoked
    assert auth.resolve_session(c, "garbage", now=NOW) is None    # unknown


def test_login_bad_code_raises():
    c = _db()
    with pytest.raises(ValueError):
        auth.login_wechat(c, WX, "bad", now=NOW)
