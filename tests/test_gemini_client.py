import os
import pytest


@pytest.mark.skipif(not os.environ.get("GEMINI_API_KEY"), reason="no GEMINI_API_KEY; skip live LLM")
def test_gemini_translates_zh_to_en():
    from engine.llm import GeminiLlmClient
    out = GeminiLlmClient().generate(
        system="Translate the customer request into a professional English clause.",
        template="Customer note: {customer_request}",
        facts={"customer_request": "请尽快安排提货"}, source_text="", target_lang="en",
    )
    assert out.lang == "en" and out.body and "MISSING" not in out.body


@pytest.mark.skipif(not os.environ.get("GEMINI_API_KEY"), reason="no GEMINI_API_KEY; skip live LLM")
def test_gemini_summarize_to_zh():
    from engine.llm import GeminiLlmClient
    out = GeminiLlmClient().summarize(
        text="The shipment was delivered on July 6. Proof of delivery is attached.",
        target_lang="zh")
    assert out and isinstance(out, str) and "MISSING" not in out
