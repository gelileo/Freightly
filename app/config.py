"""Factories that pick the real Gemini / Gmail adapters when credentials are present, else the
deterministic fakes. Keeps CI/tests hermetic (env unset → fakes) while letting production wire
the real services via environment."""
from __future__ import annotations

import os


def make_llm():
    if os.environ.get("GEMINI_API_KEY"):
        from engine.llm import GeminiLlmClient
        return GeminiLlmClient()
    from engine.llm import FakeLlmClient
    return FakeLlmClient()


def make_transport():
    token_file = os.environ.get("GMAIL_TOKEN_FILE")
    if token_file:
        from google.oauth2.credentials import Credentials  # deferred
        from app.transport import GmailTransport
        creds = Credentials.from_authorized_user_file(token_file)
        return GmailTransport(credentials=creds)
    from app.transport import FakeTransport
    return FakeTransport()
