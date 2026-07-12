"""SQLite connection + schema. Dependency-free foundation for the domain core.

Two backends, one API: stdlib `sqlite3` for local/tests (default), and hosted **libSQL/Turso**
for serverless (Vercel) when `LIBSQL_URL` is set. The libSQL adapter presents the same
stateful, sqlite3-style surface the app uses (`execute`/`commit`/`rollback`/`executescript`,
cursors with `fetchone`/`fetchall`/iteration/`rowcount`, and `row["col"]` access), so
`repo.py`/`cases.py`/`auth.py`/`inbound.py` stay unchanged across backends."""
from __future__ import annotations

import os
import sqlite3

_SCHEMA = """
CREATE TABLE IF NOT EXISTS orgs (
    id   TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('customer', 'agent'))
);
CREATE TABLE IF NOT EXISTS users (
    id        TEXT PRIMARY KEY,
    name      TEXT NOT NULL,
    auth_kind TEXT NOT NULL CHECK (auth_kind IN ('wechat', 'phone', 'email')),
    auth_id   TEXT NOT NULL UNIQUE,
    union_id  TEXT
);
CREATE TABLE IF NOT EXISTS memberships (
    user_id TEXT NOT NULL REFERENCES users(id),
    org_id  TEXT NOT NULL REFERENCES orgs(id),
    role    TEXT NOT NULL CHECK (role IN ('admin', 'operator', 'member')),
    PRIMARY KEY (user_id, org_id)
);
CREATE TABLE IF NOT EXISTS engagements (
    id              TEXT PRIMARY KEY,
    customer_org_id TEXT NOT NULL REFERENCES orgs(id),
    agent_org_id    TEXT NOT NULL REFERENCES orgs(id),
    status          TEXT NOT NULL CHECK (status IN ('pending', 'active', 'revoked')),
    UNIQUE (customer_org_id, agent_org_id)
);
CREATE TABLE IF NOT EXISTS brokers (
    id   TEXT PRIMARY KEY,
    name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS broker_accounts (
    id           TEXT PRIMARY KEY,
    agent_org_id TEXT NOT NULL REFERENCES orgs(id),
    broker_id    TEXT NOT NULL REFERENCES brokers(id),
    mailbox      TEXT,   -- agent's connected mailbox (inbound routing key / send FROM)
    broker_email TEXT,   -- broker's address (send TO)
    UNIQUE (agent_org_id, broker_id)
);
-- A mailbox is the inbound-router's tenant-routing key: it must map to exactly one agent.
CREATE UNIQUE INDEX IF NOT EXISTS ux_broker_accounts_mailbox
    ON broker_accounts (mailbox) WHERE mailbox IS NOT NULL;

CREATE TABLE IF NOT EXISTS cases (
    id                TEXT PRIMARY KEY,
    agent_org_id      TEXT NOT NULL REFERENCES orgs(id),
    customer_org_id   TEXT REFERENCES orgs(id),           -- nullable: broker-initiated cases may start unattributed
    broker_account_id TEXT REFERENCES broker_accounts(id),
    shipment_bol      TEXT,
    shipment_pro      TEXT,
    origin            TEXT NOT NULL CHECK (origin IN ('customer', 'broker')),
    issue_type        TEXT,
    status            TEXT NOT NULL,
    mail_thread_id    TEXT,
    created_at        TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS messages (
    id              TEXT PRIMARY KEY,
    case_id         TEXT NOT NULL REFERENCES cases(id),
    party           TEXT NOT NULL CHECK (party IN ('customer', 'agent', 'broker', 'system')),
    channel         TEXT NOT NULL CHECK (channel IN ('app', 'email')),
    lang            TEXT CHECK (lang IN ('zh', 'en')),
    body            TEXT NOT NULL,
    status          TEXT NOT NULL CHECK (status IN
                        ('draft', 'pending_approval', 'approved', 'sent', 'posted', 'received')),
    mail_message_id TEXT,
    in_reply_to     TEXT,
    classification  TEXT,
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS audit_log (
    id          TEXT PRIMARY KEY,
    case_id     TEXT NOT NULL REFERENCES cases(id),
    actor       TEXT NOT NULL,
    action      TEXT NOT NULL,
    from_status TEXT,
    to_status   TEXT,
    detail      TEXT,
    at          TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS sessions (
    token_hash  TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL REFERENCES users(id),
    created_at  TEXT NOT NULL,
    expires_at  TEXT NOT NULL,
    revoked     INTEGER NOT NULL DEFAULT 0,
    session_key TEXT
);
CREATE TABLE IF NOT EXISTS invites (
    code_hash        TEXT PRIMARY KEY,   -- sha256(code); raw code returned once, never stored
    customer_org_id  TEXT NOT NULL REFERENCES orgs(id),
    role             TEXT NOT NULL CHECK (role IN ('admin','operator','member')),
    created_by       TEXT NOT NULL REFERENCES users(id),
    created_at       TEXT NOT NULL,
    expires_at       TEXT NOT NULL,
    consumed_by_user TEXT REFERENCES users(id),
    consumed_at      TEXT
);
CREATE TABLE IF NOT EXISTS imap_state (
    mailbox     TEXT PRIMARY KEY,
    last_uid    INTEGER NOT NULL DEFAULT 0,
    uidvalidity TEXT
);
"""


class _LibsqlCursor:
    """Wraps a libsql-client ResultSet as a sqlite3-style cursor. Its rows already support both
    positional (`row[0]`) and column (`row["col"]`) access."""
    def __init__(self, rs):
        self._rows = list(rs.rows) if rs is not None else []
        self._i = 0
        self.rowcount = getattr(rs, "rows_affected", -1)
        self.lastrowid = getattr(rs, "last_insert_rowid", None)

    def fetchone(self):
        if self._i < len(self._rows):
            row = self._rows[self._i]
            self._i += 1
            return row
        return None

    def fetchall(self):
        rest = self._rows[self._i:]
        self._i = len(self._rows)
        return rest

    def __iter__(self):
        rest = self._rows[self._i:]      # honor any prior fetchone(), like sqlite3
        self._i = len(self._rows)
        return iter(rest)


class _LibsqlConnection:
    """Stateful sqlite3-style connection backed by libsql-client (Turso over HTTP). Keeps one
    open interactive transaction; `commit()` commits it and the next `execute` opens a fresh one
    — matching the app's explicit-commit pattern. Constraint violations are re-raised as
    `sqlite3.IntegrityError` so app code (e.g. auth.bind_via_invite) catches them uniformly."""
    def __init__(self, url: str, auth_token: str | None = None):
        import libsql_client
        self._client = libsql_client.create_client_sync(url=url, auth_token=auth_token)
        self._tx = None
        try:  # best-effort: match the sqlite path's FK enforcement (Turso may default it on)
            self._client.execute("PRAGMA foreign_keys = ON")
        except Exception:
            pass

    def _tx_now(self):
        if self._tx is None:
            self._tx = self._client.transaction()
        return self._tx

    @staticmethod
    def _is_read(sql: str) -> bool:
        head = sql.lstrip()[:6].upper()
        return head == "SELECT" or head == "PRAGMA"

    def execute(self, sql: str, params=()):
        try:
            # Read-only statements autocommit when no write transaction is pending — so a SELECT
            # never holds a Turso interactive transaction open across a later network call (SMTP
            # send / LLM). This mirrors sqlite3, where SELECTs hold no write transaction. Reads
            # made while writes are pending run inside the tx to preserve read-your-writes.
            if self._is_read(sql) and self._tx is None:
                rs = self._client.execute(sql, list(params))
            else:
                rs = self._tx_now().execute(sql, list(params))
        except Exception as e:  # normalize constraint errors to the sqlite3 type the app expects
            msg = str(e)
            if "UNIQUE" in msg or "constraint" in msg.lower():
                raise sqlite3.IntegrityError(msg) from e
            raise
        return _LibsqlCursor(rs)

    def executescript(self, script: str):
        import re
        # Strip `-- ...` line comments before splitting on ';': a schema comment may itself
        # contain a ';' (e.g. "-- sha256(code); ..."), which naive splitting would cut mid-
        # statement. (stdlib sqlite3.executescript parses this natively; the split is ours.)
        cleaned = re.sub(r"--[^\n]*", "", script)
        for stmt in cleaned.split(";"):
            if stmt.strip():
                self._tx_now().execute(stmt)
        self.commit()

    def commit(self):
        if self._tx is not None:
            self._tx.commit()
            self._tx = None

    def rollback(self):
        if self._tx is not None:
            self._tx.rollback()
            self._tx = None

    def close(self):
        try:
            if self._tx is not None:
                self._tx.rollback()
        finally:
            self._client.close()


def connect(path: str = ":memory:"):
    """libSQL/Turso when `LIBSQL_URL` is set (serverless), else stdlib sqlite3 (local/tests)."""
    url = os.environ.get("LIBSQL_URL")
    if url:
        return _LibsqlConnection(url, os.environ.get("LIBSQL_AUTH_TOKEN"))
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn) -> None:
    conn.executescript(_SCHEMA)
    conn.commit()
