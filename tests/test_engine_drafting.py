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


def test_issue_override_selects_template():
    # a customer-declared issue type is honored, not re-classified from the subject
    r = draft(DraftRequest(body="anything", sender="customer", subject="whatever --- 1",
                           facts={}, source_text="", issue_override="delivery-window"),
              FakeLlmClient())
    assert r.triage == "shipment"
    assert r.issue == "delivery-window" and r.template_slug == "delivery-window"


def test_broker_contact_prefilled_default_team():
    # {broker_contact} is filled server-side (default "team"), never left for the LLM to guess
    r = draft(DraftRequest(body="老黄，请提货", sender="customer", subject="pickup --- 1",
                           facts={"BOL": "1"}, source_text="BOL 1", issue_override="pickup"),
              FakeLlmClient())
    assert "Hi team," in r.draft_body
    assert "broker_contact" not in r.draft_body and "broker_contact" not in r.missing


def test_broker_contact_uses_resolved_name_when_known():
    r = draft(DraftRequest(body="x", sender="customer", subject="pickup --- 1",
                           facts={"BOL": "1", "broker_contact": "Laura"}, source_text="BOL 1",
                           issue_override="pickup"), FakeLlmClient())
    assert "Hi Laura," in r.draft_body


def test_shipper_signoff_injected_deterministically(monkeypatch):
    # {shipper_signoff} is injected from the SHIPPER_SIGNOFF env var (PII kept out of git),
    # never left as [[MISSING]] regardless of the LLM. \n escapes become real newlines.
    monkeypatch.setenv("SHIPPER_SIGNOFF", "Best Regards\\n\\nJane Agent\\nDemo Freight Co")
    r = draft(DraftRequest(body="please pick up", sender="broker@example.com",
                           subject="pickup --- 60114338678", facts={"BOL": "60114338678"},
                           source_text="BOL 60114338678"), FakeLlmClient())
    assert "Jane Agent" in r.draft_body and "Demo Freight Co" in r.draft_body
    assert "shipper_signoff" not in r.draft_body and "shipper_signoff" not in r.missing


def test_issue_override_unknown_slug_falls_back_to_pickup():
    r = draft(DraftRequest(body="x", sender="customer", subject="s", facts={}, source_text="",
                           issue_override="other"), FakeLlmClient())
    assert r.template_slug == "pickup"  # no templates/other.md → safe default


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


from engine.validate import find_placeholders


def test_pro_clause_empty_when_no_pro_and_no_placeholder():
    # a no-PRO shipment must NOT leave a {pro_clause}/[[MISSING: pro_clause]] placeholder
    r = draft(DraftRequest(body="please pick up", sender="customer", subject="pickup --- 60114338678",
                           facts={"BOL": "60114338678"}, source_text="BOL 60114338678",
                           issue_override="pickup"), FakeLlmClient())
    assert "pro_clause" not in r.draft_body and "PRO#" not in r.draft_body
    assert "[[MISSING: pro_clause]]" not in r.draft_body


def test_pro_clause_filled_when_pro_present():
    r = draft(DraftRequest(body="please pick up", sender="customer", subject="pickup --- 60114338678",
                           facts={"BOL": "60114338678", "PRO": "3100034"},
                           source_text="BOL 60114338678 PRO 3100034",
                           issue_override="pickup"), FakeLlmClient())
    assert "(PRO# 3100034)" in r.draft_body


def test_customer_request_optional_renders_empty_no_placeholder():
    # customer_request is an optional language slot: when unfilled it must render empty (not a
    # [[MISSING]] placeholder) so a fully-specified draft has no placeholders and no repeated line.
    src = "BOL 60114338678 addr 88 Harbor Blvd contact Grace Liu 562-555-0199"
    r = draft(DraftRequest(body="请提货", sender="customer", subject="pickup --- 60114338678",
                           facts={"BOL": "60114338678", "pickup_address": "88 Harbor Blvd",
                                  "contact_name": "Grace Liu", "contact_phone": "562-555-0199"},
                           source_text=src, issue_override="pickup"), FakeLlmClient())
    assert "[[MISSING: customer_request]]" not in r.draft_body
    assert "{customer_request}" not in r.draft_body
    assert find_placeholders(r.draft_body) == []
    # the base statement appears exactly once (no duplicate)
    assert r.draft_body.count("has not been picked up yet") == 1
