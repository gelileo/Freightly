import pytest

from app.db import connect, init_db
from app import repo, router, cases
from engine.llm import FakeLlmClient


def _net():
    c = connect(":memory:"); init_db(c)
    repo.create_org(c, "Cust", "customer", id="c1")
    repo.create_org(c, "Agent", "agent", id="a1")
    repo.create_engagement(c, "c1", "a1", id="e1"); repo.approve_engagement(c, "e1")
    repo.create_broker(c, "Priority-1", id="b1")
    repo.connect_broker_account(c, "a1", "b1", mailbox="ltlwest@priority1.com", id="ba1")
    return c


def test_open_customer_case_produces_pending_draft():
    c = _net()
    case = router.open_customer_case(
        c, engagement_id="e1", broker_account_id="ba1", bol="60114338678", pro=None,
        issue_type="pickup", wechat_text="请尽快安排提货", llm=FakeLlmClient())
    assert case.status == "PENDING_APPROVAL" and case.origin == "customer"
    msgs = c.execute("SELECT party, channel, lang, status FROM messages WHERE case_id=?",
                     (case.id,)).fetchall()
    assert len(msgs) == 1
    assert msgs[0]["status"] == "pending_approval" and msgs[0]["channel"] == "email"


def test_open_customer_case_honors_issue_type_and_keeps_bol():
    c = _net()
    case = router.open_customer_case(
        c, engagement_id="e1", broker_account_id="ba1", bol="60114839031", pro=None,
        issue_type="delivery-window", wechat_text="收件人要求直接送达，不用预约",
        llm=FakeLlmClient())
    assert case.issue_type == "delivery-window"
    body = c.execute("SELECT body FROM messages WHERE case_id=?", (case.id,)).fetchone()[0]
    # the declared type drives the template, and the trusted BOL is filled (not [[MISSING]])
    assert "60114839031" in body and "[[MISSING: BOL]]" not in body


def test_open_customer_case_requires_active_engagement():
    c = _net()
    repo.create_org(c, "Cust2", "customer", id="c2")
    repo.create_engagement(c, "c2", "a1", id="e2")  # pending, not approved
    with pytest.raises(ValueError):
        router.open_customer_case(c, engagement_id="e2", broker_account_id="ba1", bol="1",
                                  pro=None, issue_type="pickup", wechat_text="x",
                                  llm=FakeLlmClient())


def test_ingest_skip_creates_nothing():
    c = _net()
    out = router.ingest_broker_email(
        c, eml="LTL-mail-2/10% Off Freight Promo LTL, Truckload And Expedited.eml",
        to_mailbox="ltlwest@priority1.com", llm=FakeLlmClient())
    assert out is None
    assert c.execute("SELECT COUNT(*) FROM cases").fetchone()[0] == 0
    assert c.execute("SELECT COUNT(*) FROM messages").fetchone()[0] == 0


def test_ingest_new_broker_case_creates_pending_draft():
    c = _net()
    case = router.ingest_broker_email(
        c, eml="LTL-mail-2/FFBA BOL# 60112079078.eml",
        to_mailbox="ltlwest@priority1.com", llm=FakeLlmClient())
    assert case is not None and case.origin == "broker" and case.status == "PENDING_APPROVAL"
    assert case.customer_org_id is None  # unattributed broker-initiated case
    assert case.issue_type == "billing-dispute"
    statuses = {r["status"] for r in
                c.execute("SELECT status FROM messages WHERE case_id=?", (case.id,))}
    assert "received" in statuses and "pending_approval" in statuses


def test_ingest_unknown_mailbox_raises():
    c = _net()
    with pytest.raises(ValueError):
        router.ingest_broker_email(c, eml="LTL-mail-2/FFBA BOL# 60112079078.eml",
                                   to_mailbox="nobody@nowhere.com", llm=FakeLlmClient())


def test_ingest_matched_thread_appends_reply():
    c = _net()
    # a prior case awaiting a broker reply, keyed by mail_thread_id
    case = cases.create_case(c, agent_org_id="a1", customer_org_id="c1", origin="customer",
                             status="AWAITING_BROKER", mail_thread_id="T1", id="pc1")
    out = router.ingest_broker_email(
        c, eml="LTL-mail-2/FFBA BOL# 60112079078.eml", to_mailbox="ltlwest@priority1.com",
        thread_id="T1", llm=FakeLlmClient())
    assert out.id == "pc1"
    assert out.status == "PENDING_APPROVAL"  # fresh status (not the stale REPLY_DRAFTED)
    statuses = [r["status"] for r in
                c.execute("SELECT status FROM messages WHERE case_id='pc1' ORDER BY rowid")]
    assert statuses == ["received", "pending_approval"]
    # no NEW case was created — it matched the existing thread
    assert c.execute("SELECT COUNT(*) FROM cases").fetchone()[0] == 1


def test_broker_reply_relayed_to_customer_as_zh():
    c = _net()
    cases.create_case(c, agent_org_id="a1", customer_org_id="c1", origin="customer",
                      status="AWAITING_BROKER", mail_thread_id="T1", id="pc1")
    out = router.ingest_broker_email(
        c, eml="LTL-mail-2/FFBA BOL# 60112079078.eml", to_mailbox="ltlwest@priority1.com",
        thread_id="T1", llm=FakeLlmClient())
    assert out.status == "PENDING_APPROVAL"
    # the pending message is a Chinese, app-channel customer update (the relayed summary)
    m = c.execute("SELECT id, channel, lang, body FROM messages "
                  "WHERE case_id='pc1' AND status='pending_approval'").fetchone()
    assert m["channel"] == "app" and m["lang"] == "zh" and m["body"].startswith("[summary->zh]")
    # approving the app-channel message posts it to the customer
    cases.approve_message(c, m["id"], "op")
    assert cases.get_case(c, "pc1").status == "POSTED_TO_CUSTOMER"


def test_onboard_customer_creates_org_user_membership_and_active_engagement():
    c = connect(":memory:"); init_db(c)
    repo.create_org(c, "Justnano", "agent", id="a1")
    out = router.onboard_customer(c, agent_org_id="a1", customer_name="Acme Shipping",
                                  login="acme")
    assert out["login"] == "acme"
    # the new customer user exists and is a member of the new customer org
    assert repo.is_member(c, "acme", out["customer_org_id"])
    # the engagement is active between the agent and the new customer org
    row = c.execute("SELECT status, agent_org_id, customer_org_id FROM engagements WHERE id=?",
                    (out["engagement_id"],)).fetchone()
    assert row["status"] == "active" and row["agent_org_id"] == "a1"
    assert row["customer_org_id"] == out["customer_org_id"]
    # the org is a customer org
    assert c.execute("SELECT type FROM orgs WHERE id=?",
                     (out["customer_org_id"],)).fetchone()["type"] == "customer"
    # onboarding sets a login password so the customer can log in via /auth/login
    from app import auth
    assert out["temp_password"]                       # generated + returned when none provided
    assert auth.login_password(c, "acme", out["temp_password"]) is not None
    assert auth.login_password(c, "acme", "wrong") is None
