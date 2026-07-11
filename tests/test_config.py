import os

from app import config
from engine.llm import FakeLlmClient
from app.transport import FakeTransport


def test_factories_default_to_fakes(monkeypatch):
    # With no credentials in the environment, the factories return the deterministic fakes
    # (the real Gemini/Gmail branches are import-guarded and never exercised in CI).
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GMAIL_TOKEN_FILE", raising=False)
    assert isinstance(config.make_llm(), FakeLlmClient)
    assert isinstance(config.make_transport(), FakeTransport)
