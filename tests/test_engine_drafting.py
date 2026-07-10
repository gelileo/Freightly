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


def test_draft_surfaces_validator_warnings():
    from engine.llm import LlmDraft
    class _DriftLlm:  # renders a factual value NOT present verbatim in the body
        def generate(self, *, system, template, facts, source_text, target_lang):
            return LlmDraft(lang="en", body="Regarding your shipment.",
                            filled_slots={"BOL": "99999999999"}, missing=[])
    r = draft(DraftRequest(body="please pick up", sender="ltlwest@priority1.com",
                           subject="pickup --- 60114338678", facts={"BOL": "99999999999"},
                           source_text="the real shipment is 60114338678"), _DriftLlm())
    assert r.triage == "shipment"
    assert r.warnings and any("BOL" in w for w in r.warnings)
