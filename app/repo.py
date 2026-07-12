"""Repository layer over app.db. Plain functions, explicit connection, typed returns."""
from __future__ import annotations

import sqlite3
import uuid

from app.models import Org, User, Membership, Engagement, Broker, BrokerAccount


def _id(given: str | None) -> str:
    return given if given is not None else uuid.uuid4().hex


def _org_type(conn: sqlite3.Connection, org_id: str) -> str | None:
    row = conn.execute("SELECT type FROM orgs WHERE id=?", (org_id,)).fetchone()
    return row["type"] if row else None


# --- orgs / users / memberships -------------------------------------------------

def create_org(conn, name, type, id=None) -> Org:
    oid = _id(id)
    conn.execute("INSERT INTO orgs (id, name, type) VALUES (?, ?, ?)", (oid, name, type))
    conn.commit()
    return Org(id=oid, name=name, type=type)


def create_user(conn, name, auth_kind, auth_id, id=None, union_id=None) -> User:
    uid = _id(id)
    conn.execute(
        "INSERT INTO users (id, name, auth_kind, auth_id, union_id) VALUES (?, ?, ?, ?, ?)",
        (uid, name, auth_kind, auth_id, union_id))
    conn.commit()
    return User(id=uid, name=name, auth_kind=auth_kind, auth_id=auth_id, union_id=union_id)


def user_by_auth_id(conn, auth_kind, auth_id) -> User | None:
    row = conn.execute("SELECT * FROM users WHERE auth_kind=? AND auth_id=?",
                       (auth_kind, auth_id)).fetchone()
    return User(id=row["id"], name=row["name"], auth_kind=row["auth_kind"],
                auth_id=row["auth_id"], union_id=row["union_id"]) if row else None


def add_member(conn, user_id, org_id, role) -> Membership:
    conn.execute("INSERT INTO memberships (user_id, org_id, role) VALUES (?, ?, ?)",
                 (user_id, org_id, role))
    conn.commit()
    return Membership(user_id=user_id, org_id=org_id, role=role)


def is_member(conn, user_id, org_id) -> bool:
    return conn.execute("SELECT 1 FROM memberships WHERE user_id=? AND org_id=?",
                        (user_id, org_id)).fetchone() is not None


def member_org_ids(conn, user_id) -> set[str]:
    return {r["org_id"] for r in
            conn.execute("SELECT org_id FROM memberships WHERE user_id=?", (user_id,))}


# --- engagements (customer <-> agent) -------------------------------------------

def create_engagement(conn, customer_org_id, agent_org_id, id=None) -> Engagement:
    if _org_type(conn, customer_org_id) != "customer":
        raise ValueError(f"customer_org_id {customer_org_id!r} is not a customer org")
    if _org_type(conn, agent_org_id) != "agent":
        raise ValueError(f"agent_org_id {agent_org_id!r} is not an agent org")
    eid = _id(id)
    conn.execute(
        "INSERT INTO engagements (id, customer_org_id, agent_org_id, status) "
        "VALUES (?, ?, ?, 'pending')", (eid, customer_org_id, agent_org_id))
    conn.commit()
    return Engagement(id=eid, customer_org_id=customer_org_id,
                      agent_org_id=agent_org_id, status="pending")


def _engagement_status(conn, engagement_id) -> str | None:
    row = conn.execute("SELECT status FROM engagements WHERE id=?", (engagement_id,)).fetchone()
    return row["status"] if row else None


def approve_engagement(conn, engagement_id) -> None:
    """pending -> active. Guarded: a missing engagement or a non-pending status raises,
    so a revoked relationship cannot be silently reactivated outside the invite/approve flow
    (re-engagement after revoke is not supported yet — it would need an explicit path)."""
    status = _engagement_status(conn, engagement_id)
    if status is None:
        raise ValueError(f"engagement {engagement_id!r} does not exist")
    if status != "pending":
        raise ValueError(f"cannot approve engagement in status {status!r} (must be 'pending')")
    conn.execute("UPDATE engagements SET status='active' WHERE id=?", (engagement_id,))
    conn.commit()


def revoke_engagement(conn, engagement_id) -> None:
    """pending|active -> revoked (terminal). Missing or already-revoked raises."""
    status = _engagement_status(conn, engagement_id)
    if status is None:
        raise ValueError(f"engagement {engagement_id!r} does not exist")
    if status not in ("pending", "active"):
        raise ValueError(f"cannot revoke engagement in status {status!r}")
    conn.execute("UPDATE engagements SET status='revoked' WHERE id=?", (engagement_id,))
    conn.commit()


def active_agents_for_customer(conn, customer_org_id) -> set[str]:
    return {r["agent_org_id"] for r in conn.execute(
        "SELECT agent_org_id FROM engagements WHERE customer_org_id=? AND status='active'",
        (customer_org_id,))}


def active_customers_for_agent(conn, agent_org_id) -> set[str]:
    return {r["customer_org_id"] for r in conn.execute(
        "SELECT customer_org_id FROM engagements WHERE agent_org_id=? AND status='active'",
        (agent_org_id,))}


# --- brokers / broker accounts (agent <-> broker) -------------------------------

def create_broker(conn, name, id=None) -> Broker:
    bid = _id(id)
    conn.execute("INSERT INTO brokers (id, name) VALUES (?, ?)", (bid, name))
    conn.commit()
    return Broker(id=bid, name=name)


def connect_broker_account(conn, agent_org_id, broker_id, mailbox=None, broker_email=None,
                           id=None) -> BrokerAccount:
    if _org_type(conn, agent_org_id) != "agent":
        raise ValueError(f"agent_org_id {agent_org_id!r} is not an agent org")
    if mailbox is not None:
        owner = agent_for_mailbox(conn, mailbox)
        if owner is not None:
            raise ValueError(f"mailbox {mailbox!r} is already claimed by agent org {owner!r}")
    aid = _id(id)
    conn.execute(
        "INSERT INTO broker_accounts (id, agent_org_id, broker_id, mailbox, broker_email) "
        "VALUES (?, ?, ?, ?, ?)", (aid, agent_org_id, broker_id, mailbox, broker_email))
    conn.commit()
    return BrokerAccount(id=aid, agent_org_id=agent_org_id, broker_id=broker_id, mailbox=mailbox,
                         broker_email=broker_email)


def _row_to_broker_account(r) -> BrokerAccount:
    return BrokerAccount(id=r["id"], agent_org_id=r["agent_org_id"], broker_id=r["broker_id"],
                         mailbox=r["mailbox"], broker_email=r["broker_email"])


def broker_account(conn, account_id) -> BrokerAccount | None:
    r = conn.execute("SELECT * FROM broker_accounts WHERE id=?", (account_id,)).fetchone()
    return _row_to_broker_account(r) if r else None


def update_broker_email(conn, account_id, broker_email) -> BrokerAccount | None:
    """Set the recipient address for an existing broker account. Returns the updated account,
    or None if no account has that id."""
    conn.execute("UPDATE broker_accounts SET broker_email=? WHERE id=?",
                 (broker_email, account_id))
    conn.commit()
    return broker_account(conn, account_id)


def broker_accounts_for_agent(conn, agent_org_id) -> list[BrokerAccount]:
    return [_row_to_broker_account(r) for r in conn.execute(
        "SELECT * FROM broker_accounts WHERE agent_org_id=?", (agent_org_id,))]


def agent_for_mailbox(conn, mailbox) -> str | None:
    row = conn.execute("SELECT agent_org_id FROM broker_accounts WHERE mailbox=?",
                       (mailbox,)).fetchone()
    return row["agent_org_id"] if row else None
