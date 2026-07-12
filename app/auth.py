"""Session + invite logic for the WeChat-login adapter. Pure functions over a connection
(like app/cases.py). Session tokens are opaque, random, and stored ONLY as a sha256 hash;
the raw token is returned to the caller once. Time is injectable for deterministic tests."""
from __future__ import annotations

import base64
import hashlib
import hmac
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
    token = _mint_session(conn, user.id, now=now, ttl_days=ttl_days, session_key=sess.session_key)
    needs_bind = not repo.member_org_ids(conn, user.id)
    return token, user, needs_bind


def _mint_session(conn, user_id: str, *, now, ttl_days: int, session_key=None) -> str:
    """Create + store an opaque session; return the raw token (only its sha256 is persisted)."""
    token = secrets.token_urlsafe(32)
    conn.execute(
        "INSERT INTO sessions (token_hash, user_id, created_at, expires_at, revoked, session_key)"
        " VALUES (?, ?, ?, ?, 0, ?)",
        (_hash(token), user_id, now.isoformat(), (now + timedelta(days=ttl_days)).isoformat(),
         session_key))
    conn.commit()
    return token


# --- email/password login (agents) ---------------------------------------------

def hash_password(password: str, *, iterations: int = 200_000) -> str:
    """PBKDF2-HMAC-SHA256 (stdlib, no deps). Returns `pbkdf2_sha256$iters$salt$hash` (b64)."""
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return (f"pbkdf2_sha256${iterations}$"
            f"{base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}")


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters, salt_b64, hash_b64 = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                                 base64.b64decode(salt_b64), int(iters))
        return hmac.compare_digest(dk, base64.b64decode(hash_b64))
    except Exception:
        return False


def set_password(conn, user_id: str, password: str) -> None:
    conn.execute("UPDATE users SET password_hash=? WHERE id=?", (hash_password(password), user_id))
    conn.commit()


def login_password(conn, email: str, password: str, *, now=None, ttl_days: int = 30):
    """Verify an email+password against an `auth_kind='email'` user; on success mint a session and
    return (raw_token, User). Returns None on unknown email / no password set / bad password."""
    now = _now(now)
    row = conn.execute("SELECT id, password_hash FROM users WHERE auth_kind='email' AND auth_id=?",
                       (email,)).fetchone()
    if row is None or not row["password_hash"] or not verify_password(password, row["password_hash"]):
        return None
    token = _mint_session(conn, row["id"], now=now, ttl_days=ttl_days)
    return token, repo.user_by_auth_id(conn, "email", email)


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


def create_invite(conn, *, customer_org_id: str, role: str, created_by: str,
                  now=None, ttl_days: int = 7) -> str:
    now = _now(now)
    # 128-bit code (not the old 32-bit token_hex(4)): an invite grants org membership, so it must
    # not be brute-forceable. token_urlsafe(16) is ~22 chars, within WeChat's 32-char QR scene
    # limit. Stored hashed like sessions; the raw code is returned to the agent exactly once.
    code = secrets.token_urlsafe(16)
    conn.execute(
        "INSERT INTO invites (code_hash, customer_org_id, role, created_by, created_at, expires_at)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (_hash(code), customer_org_id, role, created_by, now.isoformat(),
         (now + timedelta(days=ttl_days)).isoformat()))
    conn.commit()
    return code


def bind_via_invite(conn, *, user_id: str, code: str, now=None) -> Membership:
    """Validate + consume a single-use invite and add the membership in ONE transaction.
    Raises ValueError on any invalid / expired / already-consumed invite (caller -> 409)."""
    now = _now(now)
    code_hash = _hash(code)
    row = conn.execute("SELECT * FROM invites WHERE code_hash=?", (code_hash,)).fetchone()
    if row is None:
        raise ValueError("invalid invite code")
    if row["consumed_by_user"] is not None:
        raise ValueError("invite already used")
    if datetime.fromisoformat(row["expires_at"]) <= now:
        raise ValueError("invite expired")
    try:
        # Guard the consume against a concurrent bind: only succeeds while still unconsumed.
        cur = conn.execute(
            "UPDATE invites SET consumed_by_user=?, consumed_at=?"
            " WHERE code_hash=? AND consumed_by_user IS NULL",
            (user_id, now.isoformat(), code_hash))
        if cur.rowcount != 1:
            raise ValueError("invite already used")
        conn.execute("INSERT INTO memberships (user_id, org_id, role) VALUES (?, ?, ?)",
                     (user_id, row["customer_org_id"], row["role"]))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.rollback()
        raise ValueError("already a member of this org")
    except Exception:
        conn.rollback()
        raise
    return Membership(user_id=user_id, org_id=row["customer_org_id"], role=row["role"])
