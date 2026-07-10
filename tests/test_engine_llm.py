from engine.llm import FakeLlmClient, LlmDraft


def test_fake_llm_fills_known_slots_and_marks_missing():
    llm = FakeLlmClient()
    out = llm.generate(
        system="", template="BOL {BOL}, contact {contact_phone}.",
        facts={"BOL": "60114821897"}, source_text="", target_lang="en",
    )
    assert isinstance(out, LlmDraft)
    assert out.body == "BOL 60114821897, contact [[MISSING: contact_phone]]."
    assert out.filled_slots == {"BOL": "60114821897"}
    assert out.missing == ["contact_phone"]
