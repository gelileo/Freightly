"""Case + Message + AuditLog persistence, the guarded case state machine, and the
approval actions. The approval gate: a message reaches 'sent'/'posted' ONLY via
approve_message; illegal state transitions raise and write no audit."""
from __future__ import annotations

import sqlite3
import uuid

from app.models import Case, Message, AuditLog


def _id(x: str | None) -> str:
    return x if x is not None else uuid.uuid4().hex


# --- state machine ---------------------------------------------------------------

ALLOWED: dict[str, set[str]] = {
    "NEW": {"DRAFTING"},
    "DRAFTING": {"PENDING_APPROVAL"},
    "PENDING_APPROVAL": {"SENT_TO_BROKER", "POSTED_TO_CUSTOMER", "DRAFTING", "RESOLVED"},
    "SENT_TO_BROKER": {"AWAITING_BROKER", "RESOLVED"},
    "POSTED_TO_CUSTOMER": {"AWAITING_BROKER", "RESOLVED"},
    "AWAITING_BROKER": {"REPLY_DRAFTED", "RESOLVED"},
    "REPLY_DRAFTED": {"PENDING_APPROVAL"},
    "RESOLVED": {"CLOSED"},
    "CLOSED": set(),
}


def _row_to_case(r: sqlite3.Row) -> Case:
    return Case(id=r["id"], agent_org_id=r["agent_org_id"], customer_org_id=r["customer_org_id"],
                broker_account_id=r["broker_account_id"], shipment_bol=r["shipment_bol"],
                shipment_pro=r["shipment_pro"], origin=r["origin"], issue_type=r["issue_type"],
                status=r["status"], mail_thread_id=r["mail_thread_id"])


def create_case(conn, *, agent_org_id, customer_org_id=None, origin, broker_account_id=None,
                bol=None, pro=None, issue_type=None, mail_thread_id=None, status="NEW",
                id=None) -> Case:
    cid = _id(id)
    conn.execute(
        "INSERT INTO cases (id, agent_org_id, customer_org_id, broker_account_id, shipment_bol,"
        " shipment_pro, origin, issue_type, status, mail_thread_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (cid, agent_org_id, customer_org_id, broker_account_id, bol, pro, origin, issue_type,
         status, mail_thread_id))
    conn.commit()
    return get_case(conn, cid)


def get_case(conn, case_id) -> Case | None:
    r = conn.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
    return _row_to_case(r) if r else None


def add_message(conn, *, case_id, party, channel, body, lang=None, status="draft",
                classification=None, mail_message_id=None, in_reply_to=None, id=None) -> Message:
    mid = _id(id)
    conn.execute(
        "INSERT INTO messages (id, case_id, party, channel, lang, body, status, "
        "mail_message_id, in_reply_to, classification) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (mid, case_id, party, channel, lang, body, status, mail_message_id, in_reply_to,
         classification))
    conn.commit()
    return get_message(conn, mid)


def get_message(conn, message_id) -> Message | None:
    r = conn.execute("SELECT * FROM messages WHERE id=?", (message_id,)).fetchone()
    if not r:
        return None
    return Message(id=r["id"], case_id=r["case_id"], party=r["party"], channel=r["channel"],
                   lang=r["lang"], body=r["body"], status=r["status"],
                   classification=r["classification"], mail_message_id=r["mail_message_id"],
                   in_reply_to=r["in_reply_to"])


def _audit(conn, case_id, actor, action, from_status, to_status) -> None:
    conn.execute(
        "INSERT INTO audit_log (id, case_id, actor, action, from_status, to_status) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (uuid.uuid4().hex, case_id, actor, action, from_status, to_status))


def transition(conn, case_id, to_status, actor, action="transition") -> None:
    case = get_case(conn, case_id)
    if case is None:
        raise ValueError(f"case {case_id!r} does not exist")
    if to_status not in ALLOWED.get(case.status, set()):
        raise ValueError(f"illegal transition {case.status!r} -> {to_status!r}")
    conn.execute("UPDATE cases SET status=? WHERE id=?", (to_status, case_id))
    _audit(conn, case_id, actor, action, case.status, to_status)
    conn.commit()


def audit_trail(conn, case_id) -> list[AuditLog]:
    return [AuditLog(id=r["id"], case_id=r["case_id"], actor=r["actor"], action=r["action"],
                     from_status=r["from_status"], to_status=r["to_status"])
            for r in conn.execute(
                "SELECT * FROM audit_log WHERE case_id=? ORDER BY rowid", (case_id,))]


# --- approval actions (the ONLY way a message becomes sent/posted) --------------

def approve_message(conn, message_id, actor) -> None:
    m = get_message(conn, message_id)
    if m is None:
        raise ValueError(f"message {message_id!r} does not exist")
    if m.status != "pending_approval":
        raise ValueError(f"cannot approve message in status {m.status!r}")
    if m.channel == "email":
        new_msg_status, to_case = "sent", "SENT_TO_BROKER"
    else:  # app
        new_msg_status, to_case = "posted", "POSTED_TO_CUSTOMER"
    conn.execute("UPDATE messages SET status=? WHERE id=?", (new_msg_status, message_id))
    transition(conn, m.case_id, to_case, actor, action=f"approve_message:{new_msg_status}")


def edit_message(conn, message_id, new_body, actor) -> None:
    m = get_message(conn, message_id)
    if m is None:
        raise ValueError(f"message {message_id!r} does not exist")
    if m.status != "pending_approval":
        raise ValueError(f"cannot edit message in status {m.status!r}")
    conn.execute("UPDATE messages SET body=? WHERE id=?", (new_body, message_id))
    case = get_case(conn, m.case_id)
    _audit(conn, m.case_id, actor, "edit_message", case.status, case.status)
    conn.commit()


def reject_message(conn, message_id, actor) -> None:
    m = get_message(conn, message_id)
    if m is None:
        raise ValueError(f"message {message_id!r} does not exist")
    if m.status != "pending_approval":
        raise ValueError(f"cannot reject message in status {m.status!r}")
    conn.execute("UPDATE messages SET status='draft' WHERE id=?", (message_id,))
    transition(conn, m.case_id, "DRAFTING", actor, action="reject_message")
