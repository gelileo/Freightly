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
    # A settled state is not terminal: another broker reply reopens the draft-review cycle
    # (→ REPLY_DRAFTED), so a case can round-trip as many times as the conversation runs.
    "SENT_TO_BROKER": {"AWAITING_BROKER", "REPLY_DRAFTED", "RESOLVED"},
    "POSTED_TO_CUSTOMER": {"AWAITING_BROKER", "REPLY_DRAFTED", "RESOLVED"},
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


def _audit(conn, case_id, actor, action, from_status, to_status, detail=None) -> None:
    conn.execute(
        "INSERT INTO audit_log (id, case_id, actor, action, from_status, to_status, detail) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (uuid.uuid4().hex, case_id, actor, action, from_status, to_status, detail))


def _check_transition(from_status, to_status) -> None:
    if to_status not in ALLOWED.get(from_status, set()):
        raise ValueError(f"illegal transition {from_status!r} -> {to_status!r}")


def _apply_transition(conn, case_id, from_status, to_status, actor, action) -> None:
    """Write the status + audit row. NO commit — caller owns the transaction boundary."""
    conn.execute("UPDATE cases SET status=? WHERE id=?", (to_status, case_id))
    _audit(conn, case_id, actor, action, from_status, to_status)


def transition(conn, case_id, to_status, actor, action="transition") -> None:
    case = get_case(conn, case_id)
    if case is None:
        raise ValueError(f"case {case_id!r} does not exist")
    _check_transition(case.status, to_status)  # validate BEFORE any write
    try:
        _apply_transition(conn, case_id, case.status, to_status, actor, action)
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def audit_trail(conn, case_id) -> list[AuditLog]:
    return [AuditLog(id=r["id"], case_id=r["case_id"], actor=r["actor"], action=r["action"],
                     from_status=r["from_status"], to_status=r["to_status"], detail=r["detail"])
            for r in conn.execute(
                "SELECT * FROM audit_log WHERE case_id=? ORDER BY rowid", (case_id,))]


# --- approval actions (the ONLY way a message becomes sent/posted) --------------
# Each action validates the case transition BEFORE mutating the message, and wraps both
# writes in one commit with rollback-on-error, so a failed action leaves NOTHING changed
# (no half-applied message flip, no missing audit).

def approve_message(conn, message_id, actor) -> None:
    m = get_message(conn, message_id)
    if m is None:
        raise ValueError(f"message {message_id!r} does not exist")
    if m.status != "pending_approval":
        raise ValueError(f"cannot approve message in status {m.status!r}")
    new_msg_status, to_case = ("sent", "SENT_TO_BROKER") if m.channel == "email" \
        else ("posted", "POSTED_TO_CUSTOMER")
    case = get_case(conn, m.case_id)
    _check_transition(case.status, to_case)  # validate before mutating the message
    try:
        conn.execute("UPDATE messages SET status=? WHERE id=?", (new_msg_status, message_id))
        _apply_transition(conn, m.case_id, case.status, to_case, actor,
                          f"approve_message:{new_msg_status}")
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def edit_message(conn, message_id, new_body, actor) -> None:
    m = get_message(conn, message_id)
    if m is None:
        raise ValueError(f"message {message_id!r} does not exist")
    if m.status != "pending_approval":
        raise ValueError(f"cannot edit message in status {m.status!r}")
    case = get_case(conn, m.case_id)
    try:
        conn.execute("UPDATE messages SET body=? WHERE id=?", (new_body, message_id))
        _audit(conn, m.case_id, actor, "edit_message", case.status, case.status,
               detail=f"prev_body: {m.body}")  # prior body preserved in the audit trail
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def reject_message(conn, message_id, actor) -> None:
    m = get_message(conn, message_id)
    if m is None:
        raise ValueError(f"message {message_id!r} does not exist")
    if m.status != "pending_approval":
        raise ValueError(f"cannot reject message in status {m.status!r}")
    case = get_case(conn, m.case_id)
    _check_transition(case.status, "DRAFTING")
    try:
        conn.execute("UPDATE messages SET status='draft' WHERE id=?", (message_id,))
        _apply_transition(conn, m.case_id, case.status, "DRAFTING", actor, "reject_message")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
