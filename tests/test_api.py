from app.db import connect, init_db
from app import repo
from app.api import Request, dispatch
from engine.llm import FakeLlmClient
from app.transport import FakeTransport

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
    repo.connect_broker_account(c, "agent", "p1", mailbox="ltlwest@priority1.com",
                                broker_email="ltlwest@priority1.com", id="ba")
    return c


def _d(c, method, path, user=None, body=None, headers=None, transport=None):
    return dispatch(Request(method=method, path=path, user_id=user, headers=headers or {},
                            body=body or {}), conn=c, llm=LLM,
                    transport=transport or FakeTransport(), webhook_secret=SECRET)


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
    # customer intake: the only message is the internal English draft, withheld from the customer
    assert len(r.body["messages"]) == 0
    cid = r.body["case"]["id"]
    # the customer and agent can read it; an unrelated agent org cannot
    assert _d(c, "GET", f"/cases/{cid}", user="uc").status == 200
    assert _d(c, "GET", f"/cases/{cid}", user="op").status == 200
    assert _d(c, "GET", f"/cases/{cid}", user="ox").status == 403
    assert _d(c, "GET", "/cases/missing", user="op").status == 404


def test_customer_message_view_filtered_server_side():
    """A customer must NEVER receive the internal English broker draft from the API — the
    filtering is enforced server-side in _get_case, not just hidden by the web client."""
    c = _net()
    cid = _open_case(c, "uc").body["case"]["id"]
    # agent sees the pending English draft; customer sees nothing (nothing posted app/zh yet)
    assert len(_d(c, "GET", f"/cases/{cid}", user="op").body["messages"]) == 1
    cust_msgs = _d(c, "GET", f"/cases/{cid}", user="uc").body["messages"]
    assert cust_msgs == []
    # approve the draft (sends to broker) — still not customer-visible (it's an email message)
    mid = _d(c, "GET", f"/cases/{cid}", user="op").body["messages"][0]["id"]
    _d(c, "POST", f"/cases/{cid}/messages/{mid}/approve", user="op")
    assert _d(c, "GET", f"/cases/{cid}", user="uc").body["messages"] == []
    # only an approved app/zh message reaches the customer
    from app import cases
    cases.add_message(c, case_id=cid, party="agent", channel="app", lang="zh",
                      body="您的货件已更新", status="posted")
    got = _d(c, "GET", f"/cases/{cid}", user="uc").body["messages"]
    assert len(got) == 1 and got[0]["lang"] == "zh" and got[0]["body"] == "您的货件已更新"


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
    # after sending, the case awaits the broker's reply
    assert r.body["case"]["status"] == "AWAITING_BROKER"
    # approving again → 409 (already sent)
    assert _d(c, "POST", f"/cases/{cid}/messages/{mid}/approve", user="op").status == 409
    # audit reachable
    assert _d(c, "GET", f"/cases/{cid}/audit", user="op").status == 200


def test_issue_types_endpoint():
    c = _net()
    r = _d(c, "GET", "/issue-types", user="uc")
    assert r.status == 200 and any(i["slug"] == "delivery-window" for i in r.body["issue_types"])
    assert _d(c, "GET", "/issue-types").status == 401  # needs X-User-Id


def test_engagements_scoped():
    c = _net()
    r = _d(c, "GET", "/engagements", user="uc")  # uc ∈ cust, engagement eng is active
    assert r.status == 200
    engs = r.body["engagements"]
    assert len(engs) == 1 and engs[0]["agent_name"] == "Agent"
    assert engs[0]["broker_accounts"][0]["broker_name"] == "P1"
    assert _d(c, "GET", "/engagements", user="ox").body["engagements"] == []  # outsider: none


def test_create_case_with_category_fields():
    c = _net()
    r = _d(c, "POST", "/cases", user="uc", body={
        "engagement_id": "eng", "broker_account_id": "ba", "bol": "60114839031",
        "issue_type": "delivery-window", "wechat_text": "请直送",
        "fields": {"requested_window": "6号中午前，无需预约"}})
    assert r.status == 201
    cid = r.body["case"]["id"]
    body = _d(c, "GET", f"/cases/{cid}", user="op").body["messages"][0]["body"]
    assert "6号中午前" in body  # the category field flowed into the draft


def test_fields_cannot_forge_factual_slots():
    # a client cannot override the trusted BOL/PRO or inject off-schema factual slots via fields
    c = _net()
    r = _d(c, "POST", "/cases", user="uc", body={
        "engagement_id": "eng", "broker_account_id": "ba", "bol": "60114338678",
        "issue_type": "pickup", "wechat_text": "help",
        "fields": {"BOL": "99999999999", "charge_ref": "FORGED", "pickup_address": "123 Real St"}})
    assert r.status == 201
    cid = r.body["case"]["id"]
    body = _d(c, "GET", f"/cases/{cid}", user="op").body["messages"][0]["body"]
    assert "60114338678" in body and "99999999999" not in body   # trusted BOL, not the forged one
    assert "FORGED" not in body                                    # off-schema slot dropped
    assert "123 Real St" in body                                   # legit schema field kept
    assert r.body["case"]["shipment_bol"] == "60114338678"


def test_broker_account_must_belong_to_engagement_agent():
    c = _net()
    # 'other' agent org gets its own broker account; the customer's engagement is with 'agent'
    repo.create_broker(c, "AAA", id="b2")
    repo.connect_broker_account(c, "other", "b2", mailbox="x@other.com", id="ba-other")
    r = _d(c, "POST", "/cases", user="uc", body={
        "engagement_id": "eng", "broker_account_id": "ba-other", "bol": "1",
        "issue_type": "pickup", "wechat_text": "x"})
    assert r.status == 400  # cross-agent broker account rejected


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
