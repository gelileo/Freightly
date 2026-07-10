from engine.llm import LlmDraft
from engine.validate import validate_draft


def test_untraceable_factual_slot_is_rejected():
    # model invented a BOL not present in the source → must be rejected to [[MISSING]]
    raw = LlmDraft(lang="en", body="Regarding BOL 99999999999.",
                   filled_slots={"BOL": "99999999999"}, missing=[])
    v = validate_draft(raw, source_text="the real shipment is 60114821897")
    assert "99999999999" not in v.body
    assert "[[MISSING: BOL]]" in v.body
    assert v.rejected == ["BOL"] and "BOL" in v.missing


def test_traceable_factual_slot_is_kept():
    raw = LlmDraft(lang="en", body="Regarding BOL 60114821897.",
                   filled_slots={"BOL": "60114821897"}, missing=[])
    v = validate_draft(raw, source_text="BOL 60114821897 PRO# 72406971")
    assert v.body == "Regarding BOL 60114821897." and v.rejected == []


def test_non_factual_slot_not_policed():
    # customer_request is language, not a fact — not required to be a source substring
    raw = LlmDraft(lang="en", body="Note: please expedite.",
                   filled_slots={"customer_request": "please expedite"}, missing=[])
    v = validate_draft(raw, source_text="")
    assert v.rejected == []
