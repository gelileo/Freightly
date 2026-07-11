from app.db import connect, init_db
from app import repo
from app.api import Request, dispatch
from engine.llm import FakeLlmClient

LLM = FakeLlmClient()
SECRET = "s3cr3t"


def _net():
    c = connect(":memory:"); init_db(c)
    repo.create_org(c, "Cust", "customer", id="cust")
    repo.create_org(c, "Agent", "agent", id="agent")
    repo.create_org(c, "Other", "agent", id="other")
    repo.create_user(c, "uc", "email", "uc@x", id="uc"); repo.add_member(c, "uc", "cust", "member")
    repo.create_user(c, "op", "email", "op@x", id="op"); repo.add_member(c, "op", "agent", "operator")
    repo.create_user(c, "ox", "email", "ox@x", id="ox"); repo.add_member(c, "ox", "other", "operator")
    repo.create_engagement(c, "cust", "agent", id="eng"); repo.approve_engagement(c, "eng")
    repo.create_broker(c, "P1", id="p1")
    repo.connect_broker_account(c, "agent", "p1", mailbox="ltlwest@priority1.com", id="ba")
    return c


def _d(c, method, path, user=None, body=None, headers=None):
    return dispatch(Request(method=method, path=path, user_id=user, headers=headers or {},
                            body=body or {}), conn=c, llm=LLM, webhook_secret=SECRET)


def test_unknown_route_and_auth():
    c = _net()
    assert _d(c, "GET", "/nope", user="op").status == 404
    assert _d(c, "GET", "/cases").status == 401           # no X-User-Id
    assert _d(c, "GET", "/cases", user="op").status == 200


def _open_case(c, user="uc"):
    return _d(c, "POST", "/cases", user=user, body={
        "engagement_id": "eng", "broker_account_id": "ba", "bol": "60114338678",
        "issue_type": "pickup", "wechat_text": "请尽快提货"})


def test_create_case_and_scoping():
    c = _net()
    r = _open_case(c, "uc")
    assert r.status == 201 and r.body["case"]["status"] == "PENDING_APPROVAL"
    assert len(r.body["messages"]) == 1
    cid = r.body["case"]["id"]
    # the customer and agent can read it; an unrelated agent org cannot
    assert _d(c, "GET", f"/cases/{cid}", user="uc").status == 200
    assert _d(c, "GET", f"/cases/{cid}", user="op").status == 200
    assert _d(c, "GET", f"/cases/{cid}", user="ox").status == 403
    assert _d(c, "GET", "/cases/missing", user="op").status == 404


def test_create_case_forbidden_for_outsider():
    c = _net()
    r = _d(c, "POST", "/cases", user="ox", body={"engagement_id": "eng", "issue_type": "pickup",
                                                 "wechat_text": "x"})
    assert r.status == 403


def test_list_cases_is_scoped():
    c = _net(); _open_case(c, "uc")
    assert len(_d(c, "GET", "/cases", user="op").body["cases"]) == 1   # agent sees it
    assert len(_d(c, "GET", "/cases", user="ox").body["cases"]) == 0   # outsider sees none


def test_approval_flow_and_permissions():
    c = _net()
    cid = _open_case(c, "uc").body["case"]["id"]
    mid = _d(c, "GET", f"/cases/{cid}", user="op").body["messages"][0]["id"]
    # a customer-org member may NOT approve (agent action)
    assert _d(c, "POST", f"/cases/{cid}/messages/{mid}/approve", user="uc").status == 403
    # the agent approves → sent + case advanced
    r = _d(c, "POST", f"/cases/{cid}/messages/{mid}/approve", user="op")
    assert r.status == 200 and r.body["message"]["status"] == "sent"
    assert r.body["case"]["status"] == "SENT_TO_BROKER"
    # approving again → 409 (already sent)
    assert _d(c, "POST", f"/cases/{cid}/messages/{mid}/approve", user="op").status == 409
    # audit reachable
    assert _d(c, "GET", f"/cases/{cid}/audit", user="op").status == 200


def test_inbound_webhook():
    c = _net()
    # wrong secret
    assert _d(c, "POST", "/inbound", headers={"X-Webhook-Secret": "wrong"},
              body={"eml": "LTL-mail-2/FFBA BOL# 60112079078.eml",
                    "to_mailbox": "ltlwest@priority1.com"}).status == 401
    # skip email → skipped, no case
    r = _d(c, "POST", "/inbound", headers={"X-Webhook-Secret": SECRET},
           body={"eml": "LTL-mail-2/10% Off Freight Promo LTL, Truckload And Expedited.eml",
                 "to_mailbox": "ltlwest@priority1.com"})
    assert r.status == 200 and r.body == {"skipped": True}
    # billing email → case created
    r = _d(c, "POST", "/inbound", headers={"X-Webhook-Secret": SECRET},
           body={"eml": "LTL-mail-2/FFBA BOL# 60112079078.eml",
                 "to_mailbox": "ltlwest@priority1.com"})
    assert r.status == 200 and "case_id" in r.body


def test_malformed_requests_are_400_not_crashes():
    c = _net()
    # /inbound with valid secret but missing eml → 400 (not an uncaught TypeError)
    r = _d(c, "POST", "/inbound", headers={"X-Webhook-Secret": SECRET},
           body={"to_mailbox": "ltlwest@priority1.com"})
    assert r.status == 400
    # /inbound with a nonexistent eml path → 400 (not FileNotFoundError)
    r = _d(c, "POST", "/inbound", headers={"X-Webhook-Secret": SECRET},
           body={"eml": "does/not/exist.eml", "to_mailbox": "ltlwest@priority1.com"})
    assert r.status == 400
    # a non-object JSON body → 400 (not AttributeError on .get)
    r = dispatch(Request(method="POST", path="/cases", user_id="uc", body=["not", "a", "dict"]),
                 conn=c, llm=LLM, webhook_secret=SECRET)
    assert r.status == 400
