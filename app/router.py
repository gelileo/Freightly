"""Entry points that create/advance cases and produce agent-review drafts via the engine.

Two entry points:
- open_customer_case: customer form/WeChat → case → EN broker-email draft (pending_approval).
- ingest_broker_email: inbound broker email → parse → triage → skip / match-thread / new case
  → EN broker-facing draft (pending_approval).

Both produce ONLY pending_approval drafts (never sent/posted — that needs cases.approve_message).
`triage=skip` inbound creates nothing.

Scope note (Slice 3): drafts here are broker-facing English (the engine's competency). The
customer-facing Chinese posting (summarizing a broker reply back to the customer) needs a
dedicated engine 'summarize→ZH' capability + the customer app — deferred to a later slice."""
from __future__ import annotations

import json

from scripts.parse_eml import parse_eml
from scripts.triage import triage
from app import repo, cases, forms
from app.models import Case
from engine.drafting import DraftRequest, draft as engine_draft


def _classification_json(result) -> str:
    return json.dumps({
        "triage": result.triage, "issue": result.issue, "template": result.template_slug,
        "missing": result.missing, "warnings": getattr(result, "warnings", []),
    }, ensure_ascii=False)


def open_customer_case(conn, *, engagement_id, broker_account_id, bol, pro, issue_type,
                       wechat_text, llm, fields=None) -> Case:
    row = conn.execute(
        "SELECT customer_org_id, agent_org_id, status FROM engagements WHERE id=?",
        (engagement_id,)).fetchone()
    if row is None or row["status"] != "active":
        raise ValueError("engagement is not active")
    if broker_account_id is not None:  # the broker account must belong to THIS engagement's agent
        acct = repo.broker_account(conn, broker_account_id)
        if acct is None or acct.agent_org_id != row["agent_org_id"]:
            raise ValueError("broker_account_id does not belong to the engagement's agent")
    case = cases.create_case(conn, agent_org_id=row["agent_org_id"],
                             customer_org_id=row["customer_org_id"], origin="customer",
                             broker_account_id=broker_account_id, bol=bol, pro=pro,
                             issue_type=issue_type)
    cases.transition(conn, case.id, "DRAFTING", actor="system", action="open_customer_case")
    subject = f"{issue_type} --- {bol}" if bol else (issue_type or "")
    facts = {}
    if bol:
        facts["BOL"] = bol
    if pro:
        facts["PRO"] = pro
    # Whitelist fields to the chosen issue type's schema — a client cannot inject arbitrary
    # factual slots (charge_ref, etc.) or override the trusted BOL/PRO (never in a schema),
    # which would otherwise defeat the anti-fabrication validator (fields also land in
    # source_text). Non-factual request fields (requested_window, …) are the customer's own
    # authoritative input, so self-asserting them is legitimate.
    allowed = {f["name"] for f in forms.FORM_SCHEMAS.get(issue_type or "", [])}
    for k, v in (fields or {}).items():
        if k in allowed and v not in (None, ""):
            facts[k] = v
    # Trusted structured fields come from the form, not the free text — fold them into
    # source_text so the anti-fabrication validator accepts them (they ARE ground truth here).
    source_text = wechat_text + "".join(f"\n{k}: {v}" for k, v in facts.items())
    req = DraftRequest(body=wechat_text, sender="customer", subject=subject, facts=facts,
                       source_text=source_text, target_lang="en", issue_override=issue_type)
    result = engine_draft(req, llm)
    cases.add_message(conn, case_id=case.id, party="agent", channel="email", lang="en",
                      body=result.draft_body, status="pending_approval",
                      classification=_classification_json(result))
    cases.transition(conn, case.id, "PENDING_APPROVAL", actor="system", action="draft_ready")
    return cases.get_case(conn, case.id)


def ingest_broker_email(conn, *, eml, to_mailbox, llm, thread_id=None) -> Case | None:
    """Route an inbound broker email. `eml` is a path/str for scripts.parse_eml; `to_mailbox`
    is the connected mailbox it arrived in (resolves the owning agent org)."""
    parsed = parse_eml(eml)
    if triage(parsed.body, parsed.sender) == "skip":
        return None  # non-actionable: no case, no message

    agent_org_id = repo.agent_for_mailbox(conn, to_mailbox)
    if agent_org_id is None:
        raise ValueError(f"no agent org owns mailbox {to_mailbox!r}")

    tid = thread_id
    existing = None
    if tid:
        existing = conn.execute("SELECT id, status FROM cases WHERE mail_thread_id=?",
                                (tid,)).fetchone()

    if existing:
        cases.add_message(conn, case_id=existing["id"], party="broker", channel="email",
                          lang="en", body=parsed.body, status="received",
                          classification=_classification_json_from_triage(parsed))
        if existing["status"] == "AWAITING_BROKER":
            cases.transition(conn, existing["id"], "REPLY_DRAFTED", actor="system",
                             action="broker_reply_received")
        result = _draft_reply(parsed, llm)
        cases.add_message(conn, case_id=existing["id"], party="agent", channel="email",
                          lang="en", body=result.draft_body, status="pending_approval",
                          classification=_classification_json(result))
        # REPLY_DRAFTED -> PENDING_APPROVAL (message added first, then transition)
        if cases.get_case(conn, existing["id"]).status == "REPLY_DRAFTED":
            cases.transition(conn, existing["id"], "PENDING_APPROVAL", actor="system",
                             action="draft_ready")
        return cases.get_case(conn, existing["id"])  # fresh status after any transition

    # new broker-initiated case (customer attribution deferred — starts unattributed)
    bol = parsed.bol[0] if parsed.bol else None
    case = cases.create_case(conn, agent_org_id=agent_org_id, customer_org_id=None,
                             origin="broker", bol=bol,
                             pro=(parsed.pro[0] if parsed.pro else None),
                             mail_thread_id=tid)
    cases.transition(conn, case.id, "DRAFTING", actor="system", action="ingest_broker_email")
    cases.add_message(conn, case_id=case.id, party="broker", channel="email", lang="en",
                      body=parsed.body, status="received")
    result = _draft_reply(parsed, llm)
    # add the pending draft BEFORE advancing the case, so PENDING_APPROVAL never exists
    # without a message to approve
    cases.add_message(conn, case_id=case.id, party="agent", channel="email", lang="en",
                      body=result.draft_body, status="pending_approval",
                      classification=_classification_json(result))
    conn.execute("UPDATE cases SET issue_type=? WHERE id=?", (result.issue, case.id))
    conn.commit()
    cases.transition(conn, case.id, "PENDING_APPROVAL", actor="system", action="draft_ready")
    return cases.get_case(conn, case.id)


def _draft_reply(parsed, llm):
    req = DraftRequest(body=parsed.body, sender=parsed.sender, subject=parsed.subject,
                       facts={"BOL": parsed.bol[0]} if parsed.bol else {},
                       source_text=parsed.body, target_lang="en")
    return engine_draft(req, llm)


def _classification_json_from_triage(parsed) -> str:
    return json.dumps({"triage": triage(parsed.body, parsed.sender)}, ensure_ascii=False)
