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
                    conn=c, llm=LLM, transport=t, webhook_secret="x")


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
    return r.body["case"]["id"], r.body["messages"][0]["id"]


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
    out = router.ingest_broker_email(c, eml="LTL-mail-2/FFBA BOL# 60112079078.eml",
                                     to_mailbox="agent@justnano.com", thread_id=tid, llm=LLM)
    assert out.id == cid and out.status == "PENDING_APPROVAL"
    assert c.execute("SELECT COUNT(*) FROM cases").fetchone()[0] == 1


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
