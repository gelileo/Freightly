from engine.llm import FakeLlmClient
from engine.drafting import DraftRequest, draft


def test_draft_skip_returns_empty():
    r = draft(DraftRequest(body="We have a 10% promotion for new shippers",
                           sender="Ashton.Johnson@priority1.com", subject="promo",
                           facts={}, source_text=""), FakeLlmClient())
    assert r.triage == "skip"
    assert r.draft_body == "" and r.template_slug == ""


def test_draft_billing_routes_to_billing_template():
    r = draft(DraftRequest(body="processed through Priority1's Free Freight Bill Audit; pricing variance additional charge",
                           sender="Jalen.Turner@priority1.com", subject="FFBA BOL# 60112079078",
                           facts={"BOL": "60112079078"}, source_text="BOL 60112079078"),
              FakeLlmClient())
    assert r.triage == "billing-dispute"
    assert r.template_slug == "billing-dispute"
    assert "60112079078" in r.draft_body


def test_draft_shipment_classifies_issue():
    r = draft(DraftRequest(body="please pick up the shipment", sender="ltlwest@priority1.com",
                           subject="pickup --- 60114338678",
                           facts={"BOL": "60114338678"}, source_text="BOL 60114338678"),
              FakeLlmClient())
    assert r.triage == "shipment"
    assert r.issue == "pickup" and r.template_slug == "pickup"
