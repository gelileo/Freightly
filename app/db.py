"""SQLite connection + schema. Dependency-free foundation for the domain core.
Postgres is a later migration (swap this module's DDL/driver); the repo layer stays."""
from __future__ import annotations

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
    auth_id   TEXT NOT NULL UNIQUE
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
    mailbox      TEXT,
    UNIQUE (agent_org_id, broker_id)
);
"""


def connect(path: str = ":memory:") -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)
    conn.commit()
