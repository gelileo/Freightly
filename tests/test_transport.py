from app.db import connect, init_db
from app import repo, router
from app.api import Request, dispatch
from app.transport import FakeTransport, SentRef
from engine.llm import FakeLlmClient

LLM = FakeLlmClient()


def _net():
    c = connect(":memory:"); init_db(c)
    repo.create_org(c, "Cust", "customer", id="cust")
    repo.create_org(c, "Agent", "agent", id="agent")
    repo.create_user(c, "uc", "email", "uc@x", id="uc"); repo.add_member(c, "uc", "cust", "member")
    repo.create_user(c, "op", "email", "op@x", id="op"); repo.add_member(c, "op", "agent", "operator")
    repo.create_engagement(c, "cust", "agent", id="eng"); repo.approve_engagement(c, "eng")
    repo.create_broker(c, "P1", id="p1")
    repo.connect_broker_account(c, "agent", "p1", mailbox="agent@justnano.com",
                                broker_email="ltlwest@priority1.com", id="ba")
    return c


def _d(c, method, path, user=None, body=None, t=None):
    return dispatch(Request(method=method, path=path, user_id=user, body=body or {}),
                    conn=c, llm=LLM, transport=t, webhook_secret="x", trust_user_header=True)


def test_fake_transport_records_and_preserves_thread():
    t = FakeTransport()
    ref = t.send(from_addr="a@x", to="b@y", subject="s", body="hi")
    assert isinstance(ref, SentRef) and t.sent[0]["to"] == "b@y" and t.sent[0]["from_addr"] == "a@x"
    ref2 = t.send(from_addr="a@x", to="b@y", subject="s", body="hi", thread_id="T9")
    assert ref2.thread_id == "T9"  # a reply keeps its thread


def test_gmail_transport_constructs_without_google_libs():
    # Construction must not import googleapiclient/google-auth (deferred to _service/send),
    # so `import app.transport` + constructing the real adapter works in an env without them.
    from app.transport import GmailTransport
    assert GmailTransport(credentials=None) is not None


def test_broker_email_roundtrips():
    c = _net()
    acct = repo.broker_account(c, "ba")
    assert acct.broker_email == "ltlwest@priority1.com" and acct.mailbox == "agent@justnano.com"


def _open_case(c, t):
    r = _d(c, "POST", "/cases", user="uc", t=t, body={
        "engagement_id": "eng", "broker_account_id": "ba", "bol": "60114338678",
        "issue_type": "pickup", "wechat_text": "请尽快提货"})
    cid = r.body["case"]["id"]
    # the internal English draft is withheld from the customer's response; fetch it as the agent
    mid = _d(c, "GET", f"/cases/{cid}", user="op", t=t).body["messages"][0]["id"]
    # the raw pickup draft carries anti-fabrication placeholders; the agent reviews + completes it
    # to a clean body (a placeholder-free draft is required to send — see the guardrail test).
    _d(c, "POST", f"/cases/{cid}/messages/{mid}/edit", user="op", t=t, body={"body":
        "Hi team,\n\nFollowing up on BOL 60114338678 — please confirm the earliest pickup "
        "date and driver.\n\nThank you,\nJustnano"})
    return cid, mid


def test_send_on_approval_and_thread_continuity():
    c = _net(); t = FakeTransport()
    cid, mid = _open_case(c, t)
    r = _d(c, "POST", f"/cases/{cid}/messages/{mid}/approve", user="op", t=t)
    assert r.status == 200
    # exactly one send, to the broker, from the agent's mailbox
    assert len(t.sent) == 1
    assert t.sent[0]["to"] == "ltlwest@priority1.com"
    assert t.sent[0]["from_addr"] == "agent@justnano.com"
    # message stamped with the returned mail id; case stamped with the thread id
    mmid = c.execute("SELECT mail_message_id FROM messages WHERE id=?", (mid,)).fetchone()[0]
    assert mmid == "fakemsg-1"
    tid = c.execute("SELECT mail_thread_id FROM cases WHERE id=?", (cid,)).fetchone()[0]
    assert tid
    assert r.body["case"]["status"] == "AWAITING_BROKER"
    # a broker reply on that thread matches the SAME case (no new case)
    out = router.ingest_broker_email(c, eml="tests/fixtures/FFBA BOL# 60112079078.eml",
                                     to_mailbox="agent@justnano.com", thread_id=tid, llm=LLM)
    assert out.id == cid and out.status == "PENDING_APPROVAL"
    assert c.execute("SELECT COUNT(*) FROM cases").fetchone()[0] == 1


def test_placeholder_draft_is_blocked_then_sends_after_edit():
    # GUARDRAIL: a draft with unfilled placeholders must not reach the broker.
    c = _net(); t = FakeTransport()
    r = _d(c, "POST", "/cases", user="uc", t=t, body={
        "engagement_id": "eng", "broker_account_id": "ba", "bol": "60114338678",
        "issue_type": "pickup", "wechat_text": "请尽快提货"})   # no fields → draft has [[MISSING:…]]
    cid = r.body["case"]["id"]
    mid = _d(c, "GET", f"/cases/{cid}", user="op", t=t).body["messages"][0]["id"]
    blocked = _d(c, "POST", f"/cases/{cid}/messages/{mid}/approve", user="op", t=t)
    assert blocked.status == 409 and "placeholder" in blocked.body["error"]
    assert t.sent == []                                              # nothing sent
    assert c.execute("SELECT status FROM messages WHERE id=?", (mid,)).fetchone()[0] == "pending_approval"
    # agent completes the draft → now it sends
    _d(c, "POST", f"/cases/{cid}/messages/{mid}/edit", user="op", t=t,
       body={"body": "Hi team, please confirm pickup for BOL 60114338678. Thanks, Justnano"})
    ok = _d(c, "POST", f"/cases/{cid}/messages/{mid}/approve", user="op", t=t)
    assert ok.status == 200 and len(t.sent) == 1


class _RaisingTransport:
    def send(self, **kw):
        raise RuntimeError("SMTP connection refused")


def test_send_failure_leaves_state_untouched():
    # If transport.send raises, nothing is marked sent and no thread/mail id is stamped.
    c = _net(); t = FakeTransport()
    cid, mid = _open_case(c, t)
    import pytest
    with pytest.raises(RuntimeError):
        # dispatch has no try/except; the server shell turns this into a controlled 500.
        _d(c, "POST", f"/cases/{cid}/messages/{mid}/approve", user="op", t=_RaisingTransport())
    assert c.execute("SELECT status FROM messages WHERE id=?", (mid,)).fetchone()[0] == "pending_approval"
    row = c.execute("SELECT status, mail_thread_id FROM cases WHERE id=?", (cid,)).fetchone()
    assert row[0] == "PENDING_APPROVAL" and row[1] is None
    assert c.execute("SELECT mail_message_id FROM messages WHERE id=?", (mid,)).fetchone()[0] is None


def test_approval_without_recipient_is_409_and_sends_nothing():
    c = connect(":memory:"); init_db(c)
    repo.create_org(c, "Cust", "customer", id="cust"); repo.create_org(c, "Agent", "agent", id="agent")
    repo.create_user(c, "uc", "email", "uc@x", id="uc"); repo.add_member(c, "uc", "cust", "member")
    repo.create_user(c, "op", "email", "op@x", id="op"); repo.add_member(c, "op", "agent", "operator")
    repo.create_engagement(c, "cust", "agent", id="eng"); repo.approve_engagement(c, "eng")
    repo.create_broker(c, "P1", id="p1")
    repo.connect_broker_account(c, "agent", "p1", mailbox="agent@justnano.com", id="ba")  # NO broker_email
    t = FakeTransport()
    cid, mid = _open_case(c, t)
    r = _d(c, "POST", f"/cases/{cid}/messages/{mid}/approve", user="op", t=t)
    assert r.status == 409
    assert t.sent == []  # nothing sent
    assert c.execute("SELECT status FROM messages WHERE id=?", (mid,)).fetchone()[0] == "pending_approval"


from app.transport import AlibabaSmtpTransport


class FakeSmtp:
    def __init__(self): self.logged_in = None; self.sent = []
    def login(self, addr, pw): self.logged_in = (addr, pw)
    def send_message(self, msg): self.sent.append(msg)
    def quit(self): pass


def test_alibaba_smtp_sends_with_threading_headers():
    fake = FakeSmtp()
    t = AlibabaSmtpTransport(address="hs@justnanoinc.com", password="pw16",
                             smtp_factory=lambda h, p: fake)
    ref = t.send(from_addr="hs@justnanoinc.com", to="broker@x.com", subject="BOL 1",
                 body="hi", thread_id=None, in_reply_to=None)
    assert fake.logged_in == ("hs@justnanoinc.com", "pw16")
    msg = fake.sent[0]
    assert msg["From"] == "hs@justnanoinc.com" and msg["To"] == "broker@x.com"
    assert msg["Message-ID"] and ref.message_id == msg["Message-ID"]
    assert ref.thread_id == ref.message_id
    ref2 = t.send(from_addr="hs@justnanoinc.com", to="broker@x.com", subject="Re",
                  body="more", thread_id=ref.message_id, in_reply_to=ref.message_id)
    m2 = fake.sent[1]
    assert m2["In-Reply-To"] == ref.message_id and m2["References"] == ref.message_id
    assert ref2.thread_id == ref.message_id


def test_alibaba_smtp_rejects_wrong_from():
    import pytest
    t = AlibabaSmtpTransport(address="hs@justnanoinc.com", password="pw",
                             smtp_factory=lambda h, p: FakeSmtp())
    with pytest.raises(ValueError):
        t.send(from_addr="someone@else.com", to="b@x.com", subject="s", body="b")


import os as _os
import pytest as _pytest


@_pytest.mark.skipif(not _os.environ.get("SMTP_PASSWORD"), reason="no SMTP_PASSWORD; skip live SMTP")
def test_live_smtp_login_only():
    import smtplib
    from app.config import load_env
    load_env()
    with smtplib.SMTP_SSL("smtp.qiye.aliyun.com", 465, timeout=25) as s:
        s.login(_os.environ.get("SMTP_ADDRESS", "hs@justnanoinc.com"), _os.environ["SMTP_PASSWORD"])
    # login only — no message sent
