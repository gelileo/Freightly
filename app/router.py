"""Entry points that create/advance cases and produce agent-review drafts via the engine.

Two entry points:
- open_customer_case: customer form/WeChat → case → EN broker-email draft (pending_approval).
- ingest_broker_email: inbound broker email → parse → triage → skip / match-thread / new case
  → EN broker-facing draft (pending_approval).

Both produce ONLY pending_approval drafts (never sent/posted — that needs cases.approve_message).
`triage=skip` inbound creates nothing.

Broker-facing drafts are English (the engine's competency). A matched-thread broker reply is
also relayed to the customer as an approval-gated Chinese message via
`engine.drafting.summarize_for_customer` (Slice 8)."""
from __future__ import annotations

import json
import secrets

from scripts.parse_eml import parse_eml, parse_eml_bytes
from scripts.triage import triage
from app import repo, cases, forms
from app.models import Case
from engine.drafting import DraftRequest, draft as engine_draft, summarize_for_customer


def _classification_json(result) -> str:
    return json.dumps({
        "triage": result.triage, "issue": result.issue, "template": result.template_slug,
        "missing": result.missing, "warnings": getattr(result, "warnings", []),
    }, ensure_ascii=False)


def onboard_customer(conn, *, agent_org_id, customer_name, login, password=None,
                     contact_name=None) -> dict:
    """Agent-initiated customer onboarding: create a customer org, a customer login user (logs in
    with `login` + password), a membership, and an ACTIVE engagement with the agent org. If no
    `password` is given, a temp one is generated and returned as `temp_password` for the agent to
    hand off (else `temp_password` is None). A taken `login` raises sqlite3.IntegrityError → 409."""
    from app import auth
    org = repo.create_org(conn, customer_name, "customer")
    user = repo.create_user(conn, contact_name or f"{customer_name} (customer)",
                            "email", login, id=login)
    repo.add_member(conn, user.id, org.id, "member")
    eng = repo.create_engagement(conn, org.id, agent_org_id)
    repo.approve_engagement(conn, eng.id)
    # ~96 bits of entropy for the auto-generated temp password (still short enough for the agent
    # to relay). Follow-ups: force a reset on first login + rate-limit /auth/login (gateway).
    pw = password or secrets.token_urlsafe(12)
    auth.set_password(conn, user.id, pw)
    return {"customer_org_id": org.id, "engagement_id": eng.id, "login": user.id,
            "temp_password": None if password else pw}


def add_agent_operator(conn, *, agent_org_id, name, email, password=None,
                       role="operator") -> dict:
    """Create another AGENT user (email+password login) as a member of `agent_org_id`. If no
    `password` is given, a temp one is generated and returned as `temp_password` (else None).
    A taken `email` raises sqlite3.IntegrityError → 409."""
    from app import auth
    user = repo.create_user(conn, name, "email", email, id=email)
    repo.add_member(conn, user.id, agent_org_id, role)
    pw = password or secrets.token_urlsafe(12)
    auth.set_password(conn, user.id, pw)
    return {"login": user.id, "role": role, "temp_password": None if password else pw}


def add_broker(conn, *, agent_org_id, name, broker_email, mailbox=None) -> dict:
    """Register a broker for an agent org and connect an account carrying the recipient address
    (and optionally the agent's own sending mailbox). A mailbox already claimed by another agent
    org raises ValueError. Returns the created broker + account ids and their stored fields."""
    broker = repo.create_broker(conn, name)
    acct = repo.connect_broker_account(conn, agent_org_id, broker.id, mailbox=mailbox or None,
                                       broker_email=broker_email)
    return {"account_id": acct.id, "broker_id": broker.id, "name": name,
            "mailbox": acct.mailbox, "broker_email": acct.broker_email}


def set_broker_email(conn, *, agent_org_id, account_id, broker_email) -> dict | None:
    """Update a broker account's recipient address. Returns None (→ 404) when the account does not
    exist OR belongs to a different agent org, so one org can never edit another's broker."""
    acct = repo.broker_account(conn, account_id)
    if acct is None or acct.agent_org_id != agent_org_id:
        return None
    updated = repo.update_broker_email(conn, account_id, broker_email)
    return {"account_id": updated.id, "broker_email": updated.broker_email}


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
    is the connected mailbox it arrived in (resolves the owning agent org). `eml` may be a
    path/str (file) or raw message bytes (from the IMAP poller)."""
    parsed = parse_eml_bytes(eml) if isinstance(eml, (bytes, bytearray)) else parse_eml(eml)
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
        # Do the fallible LLM work FIRST, before persisting anything. If summarize raises (a
        # transient Gemini error), no partial state is written, so the poller's Message-ID dedup
        # won't later skip a half-processed reply — the next poll reprocesses it cleanly.
        summary = summarize_for_customer(parsed.body, llm)
        cases.add_message(conn, case_id=existing["id"], party="broker", channel="email",
                          lang="en", body=parsed.body, status="received",
                          mail_message_id=parsed.message_id or None,
                          in_reply_to=parsed.in_reply_to or None,
                          classification=_classification_json_from_triage(parsed))
        # A broker reply reopens the case from any settled/awaiting state (not just
        # AWAITING_BROKER) — a second reply after we posted a customer update, or after we sent
        # the broker a message, must still re-enter the draft-review cycle rather than orphaning
        # the new draft on a non-approvable case.
        if existing["status"] in ("AWAITING_BROKER", "SENT_TO_BROKER", "POSTED_TO_CUSTOMER"):
            cases.transition(conn, existing["id"], "REPLY_DRAFTED", actor="system",
                             action="broker_reply_received")
        # Relay the broker's reply to the customer as a Chinese update (approval-gated: the
        # agent approves this app-channel message → POSTED_TO_CUSTOMER → the customer sees it).
        cases.add_message(conn, case_id=existing["id"], party="agent", channel="app",
                          lang="zh", body=summary, status="pending_approval",
                          classification=_classification_json_from_triage(parsed))
        # REPLY_DRAFTED -> PENDING_APPROVAL (message added first, then transition)
        if cases.get_case(conn, existing["id"]).status == "REPLY_DRAFTED":
            cases.transition(conn, existing["id"], "PENDING_APPROVAL", actor="system",
                             action="draft_ready")
        return cases.get_case(conn, existing["id"])  # fresh status after any transition

    # new broker-initiated case (customer attribution deferred — starts unattributed).
    # Draft FIRST (fallible LLM) so a transient failure creates no orphan case/message and the
    # next poll reprocesses cleanly (see the matched-thread branch for the same rationale).
    result = _draft_reply(parsed, llm)
    bol = parsed.bol[0] if parsed.bol else None
    case = cases.create_case(conn, agent_org_id=agent_org_id, customer_org_id=None,
                             origin="broker", bol=bol,
                             pro=(parsed.pro[0] if parsed.pro else None),
                             mail_thread_id=tid)
    cases.transition(conn, case.id, "DRAFTING", actor="system", action="ingest_broker_email")
    cases.add_message(conn, case_id=case.id, party="broker", channel="email", lang="en",
                      body=parsed.body, status="received",
                      mail_message_id=parsed.message_id or None,
                      in_reply_to=parsed.in_reply_to or None)
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
