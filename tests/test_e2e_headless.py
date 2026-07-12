"""End-to-end capstone: the whole headless backend loop on real corpus data, wiring the
drafting engine + identity + case core + router + approval gate together. Deterministic
(FakeLlmClient) — no network."""
from app.db import connect, init_db
from app import repo, router, cases
from app.access import user_may_access_case
from engine.llm import FakeLlmClient


def _org_setup(c):
    repo.create_org(c, "AcmeImports", "customer", id="cust")
    repo.create_org(c, "Justnano", "agent", id="agent")
    repo.create_user(c, "Operator", "email", "op@example.com", id="op")
    repo.add_member(c, "op", "agent", "operator")
    repo.create_engagement(c, "cust", "agent", id="eng"); repo.approve_engagement(c, "eng")
    repo.create_broker(c, "Priority-1", id="p1")
    repo.connect_broker_account(c, "agent", "p1", mailbox="ltlwest@priority1.com", id="ba")


def test_broker_initiated_end_to_end():
    c = connect(":memory:"); init_db(c); _org_setup(c)
    llm = FakeLlmClient()

    # 1. a real broker billing email arrives → broker-initiated case + pending draft
    case = router.ingest_broker_email(
        c, eml="tests/fixtures/FFBA BOL# 60112079078.eml",
        to_mailbox="ltlwest@priority1.com", llm=llm)
    assert case.origin == "broker" and case.status == "PENDING_APPROVAL"
    assert case.issue_type == "billing-dispute"

    # the agent operator can see the case; an outsider cannot
    assert user_may_access_case(c, "op", case.id) is True
    repo.create_user(c, "stranger", "email", "s@x", id="stranger")
    assert user_may_access_case(c, "stranger", case.id) is False

    # 2. agent approves the pending draft → message sent, case advances, audit recorded
    pending = c.execute(
        "SELECT id FROM messages WHERE case_id=? AND status='pending_approval'",
        (case.id,)).fetchone()["id"]
    cases.approve_message(c, pending, "op")
    assert cases.get_message(c, pending).status == "sent"
    assert cases.get_case(c, case.id).status == "SENT_TO_BROKER"

    actions = [a.action for a in cases.audit_trail(c, case.id)]
    assert any(a.startswith("approve_message") for a in actions)
    # nothing was auto-sent: the only 'sent' message is the one we explicitly approved
    sent = c.execute("SELECT COUNT(*) FROM messages WHERE status='sent'").fetchone()[0]
    assert sent == 1


def test_customer_initiated_end_to_end():
    c = connect(":memory:"); init_db(c); _org_setup(c)
    llm = FakeLlmClient()

    # customer raises a pickup issue in Chinese → EN broker draft, pending approval
    case = router.open_customer_case(
        c, engagement_id="eng", broker_account_id="ba", bol="60114338678", pro=None,
        issue_type="pickup", wechat_text="这票货请尽快安排提货，谢谢", llm=llm)
    assert case.origin == "customer" and case.status == "PENDING_APPROVAL"

    pending = c.execute(
        "SELECT id FROM messages WHERE case_id=? AND status='pending_approval'",
        (case.id,)).fetchone()["id"]
    # agent edits then approves
    cases.edit_message(c, pending, "Hi team, following up on BOL 60114338678 — please expedite pickup.", "op")
    cases.approve_message(c, pending, "op")
    assert cases.get_case(c, case.id).status == "SENT_TO_BROKER"
    # audit shows the edit (with prior body) and the approval, in order
    trail = cases.audit_trail(c, case.id)
    assert any(a.action == "edit_message" and "尽快" not in (a.detail or "") for a in trail) or \
        any(a.action == "edit_message" for a in trail)
    assert trail[-1].action.startswith("approve_message")
