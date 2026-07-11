"""Factories that pick the real Gemini / Gmail adapters when credentials are present, else the
deterministic fakes. Keeps CI/tests hermetic (env unset → fakes) while letting production wire
the real services via environment."""
from __future__ import annotations

import os
from pathlib import Path

_ENV_LOADED = False


def load_env(path: str = ".env") -> None:
    """Dependency-free .env loader: parse KEY=VALUE lines into os.environ WITHOUT overriding
    variables already set in the real environment (real env wins). Idempotent; missing file is
    a no-op. Called by the factories so `GEMINI_API_KEY` / `GMAIL_TOKEN_FILE` in .env are picked
    up automatically."""
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    p = Path(path)
    if p.exists():
        for line in p.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key, val = key.strip(), val.strip().strip('"').strip("'")
            if key:
                os.environ.setdefault(key, val)
    _ENV_LOADED = True


def make_llm():
    load_env()
    if os.environ.get("GEMINI_API_KEY"):
        from engine.llm import GeminiLlmClient
        return GeminiLlmClient()
    from engine.llm import FakeLlmClient
    return FakeLlmClient()


def make_transport():
    load_env()
    token_file = os.environ.get("GMAIL_TOKEN_FILE")
    if token_file:
        from google.oauth2.credentials import Credentials  # deferred
        from app.transport import GmailTransport
        creds = Credentials.from_authorized_user_file(token_file)
        return GmailTransport(credentials=creds)
    from app.transport import FakeTransport
    return FakeTransport()
