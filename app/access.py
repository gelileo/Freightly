"""Relationship-scoped access helpers — the security boundary of the multi-sided network.

A user may act within an engagement only if they are a member of one of its two party orgs
AND the engagement is ACTIVE. Cross-engagement isolation is the core guarantee (see
tests/test_access.py)."""
from __future__ import annotations

import sqlite3

from app.repo import is_member, member_org_ids


def user_can_see_org(conn: sqlite3.Connection, user_id: str, org_id: str) -> bool:
    return is_member(conn, user_id, org_id)


def visible_org_ids(conn: sqlite3.Connection, user_id: str) -> set[str]:
    return member_org_ids(conn, user_id)


def parties_connected(conn, customer_org_id, agent_org_id) -> bool:
    """True iff an ACTIVE engagement links this customer org to this agent org."""
    return conn.execute(
        "SELECT 1 FROM engagements "
        "WHERE customer_org_id=? AND agent_org_id=? AND status='active'",
        (customer_org_id, agent_org_id)).fetchone() is not None


def user_may_access_engagement(conn, user_id, engagement_id) -> bool:
    """True iff the engagement is ACTIVE and the user is a member of either party org."""
    row = conn.execute(
        "SELECT customer_org_id, agent_org_id, status FROM engagements WHERE id=?",
        (engagement_id,)).fetchone()
    if row is None or row["status"] != "active":
        return False
    return is_member(conn, user_id, row["customer_org_id"]) or \
        is_member(conn, user_id, row["agent_org_id"])
