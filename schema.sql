-- Generated from app.db._SCHEMA — do not edit by hand.
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
