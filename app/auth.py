"""Session + invite logic for the WeChat-login adapter. Pure functions over a connection
(like app/cases.py). Session tokens are opaque, random, and stored ONLY as a sha256 hash;
the raw token is returned to the caller once. Time is injectable for deterministic tests."""
from __future__ import annotations

import hashlib
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone

from app import repo
from app.models import Membership, User
from app.wechat import WeChatClient


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _now(now):
    return now or datetime.now(timezone.utc)


def login_wechat(conn, wechat: WeChatClient, js_code: str, *, now=None,
                 ttl_days: int = 30) -> tuple[str, User, bool]:
    """code2session -> upsert the wechat user -> mint + store a session. Returns
    (raw_token, user, needs_bind). needs_bind is True when the user has no memberships."""
    now = _now(now)
    try:
        sess = wechat.code2session(js_code)
    except Exception as e:  # bad js_code / upstream error -> caller maps to 400
        raise ValueError(f"wechat login failed: {e}")
    user = repo.user_by_auth_id(conn, "wechat", sess.openid)
    if user is None:
        user = repo.create_user(conn, name=f"wx:{sess.openid[:8]}", auth_kind="wechat",
                                 auth_id=sess.openid, union_id=sess.unionid)
    elif sess.unionid and user.union_id != sess.unionid:
        conn.execute("UPDATE users SET union_id=? WHERE id=?", (sess.unionid, user.id))
        conn.commit()
        user.union_id = sess.unionid
    token = secrets.token_urlsafe(32)
    conn.execute(
        "INSERT INTO sessions (token_hash, user_id, created_at, expires_at, revoked, session_key)"
        " VALUES (?, ?, ?, ?, 0, ?)",
        (_hash(token), user.id, now.isoformat(), (now + timedelta(days=ttl_days)).isoformat(),
         sess.session_key))
    conn.commit()
    needs_bind = not repo.member_org_ids(conn, user.id)
    return token, user, needs_bind


def resolve_session(conn, token: str, *, now=None) -> str | None:
    now = _now(now)
    row = conn.execute(
        "SELECT user_id, expires_at, revoked FROM sessions WHERE token_hash=?",
        (_hash(token),)).fetchone()
    if row is None or row["revoked"]:
        return None
    if datetime.fromisoformat(row["expires_at"]) <= now:
        return None
    return row["user_id"]


def revoke_session(conn, token: str) -> None:
    conn.execute("UPDATE sessions SET revoked=1 WHERE token_hash=?", (_hash(token),))
    conn.commit()
