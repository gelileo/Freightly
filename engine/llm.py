"""LLM port + a deterministic fake for tests. Real Gemini adapter added in a later task.

The pipeline depends only on the LlmClient Protocol, so tests run without network/cost.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class LlmDraft:
    lang: str
    body: str
    filled_slots: dict[str, str] = field(default_factory=dict)
    missing: list[str] = field(default_factory=list)


class LlmClient(Protocol):
    def generate(self, *, system: str, template: str, facts: dict[str, str],
                 source_text: str, target_lang: str) -> LlmDraft: ...

    def summarize(self, *, text: str, target_lang: str, context: str = "") -> str:
        """Summarize `text` into a short, faithful message in `target_lang` (used to relay a
        broker reply to the customer). Must not invent facts."""
        ...


class FakeLlmClient:
    """Deterministic stub: substitute {slot} from facts; unknown slots → [[MISSING: slot]].
    Does no real translation — enough to test orchestration + validation deterministically."""

    def generate(self, *, system: str, template: str, facts: dict[str, str],
                 source_text: str, target_lang: str) -> LlmDraft:
        filled: dict[str, str] = {}
        missing: list[str] = []

        def repl(m: "re.Match[str]") -> str:
            key = m.group(1)
            val = facts.get(key)
            if val:
                filled[key] = val
                return val
            missing.append(key)
            return f"[[MISSING: {key}]]"

        body = re.sub(r"\{(\w+)\}", repl, template)
        return LlmDraft(lang=target_lang, body=body, filled_slots=filled, missing=missing)

    def summarize(self, *, text: str, target_lang: str, context: str = "") -> str:
        first = next((ln.strip() for ln in (text or "").splitlines() if ln.strip()), "")
        return f"[summary->{target_lang}] {first[:120]}"


class GeminiLlmClient:
    """Real adapter. Requires `google-genai` and GEMINI_API_KEY. Requests structured JSON
    and maps it to LlmDraft. Deterministic-first: factual slots in `facts` are passed through
    and the model is instructed to use ONLY those for facts (validator enforces anyway)."""

    MODEL = "gemini-flash-latest"  # stable alias — survives model retirements (2.5-flash was retired for new accounts)

    def __init__(self, api_key: str | None = None):
        import os
        from google import genai  # google-genai
        self._client = genai.Client(api_key=api_key or os.environ["GEMINI_API_KEY"])

    def generate(self, *, system, template, facts, source_text, target_lang):
        import json
        prompt = (
            f"{system}\nTarget language: {target_lang}.\n"
            f"Template (fill {{slots}}; keep the English skeleton English):\n{template}\n"
            f"Known facts (use ONLY these for factual slots; never invent BOL/PRO/address/"
            f"date/amount — leave unknown factual slots as [[MISSING: key]]):\n{json.dumps(facts, ensure_ascii=False)}\n"
            f"Authoritative source (do not state facts absent here):\n{source_text}\n"
            'Return JSON: {"lang":"..","body":"..","filled_slots":{},"missing":[]}'
        )
        resp = self._client.models.generate_content(
            model=self.MODEL, contents=prompt,
            config={"response_mime_type": "application/json"},
        )
        data = json.loads(resp.text)
        from engine.llm import LlmDraft
        return LlmDraft(lang=data.get("lang", target_lang), body=data.get("body", ""),
                        filled_slots=data.get("filled_slots", {}), missing=data.get("missing", []))

    def summarize(self, *, text, target_lang, context=""):
        prompt = (
            f"Summarize the following freight broker email reply into a short, clear message in "
            f"{target_lang} for the end customer. Be faithful — do NOT invent facts, dates, or "
            f"numbers not present in the text. Output only the message, no preamble.\n"
            + (f"Context: {context}\n" if context else "")
            + f"\nBroker reply:\n{text}"
        )
        resp = self._client.models.generate_content(model=self.MODEL, contents=prompt)
        return (resp.text or "").strip()
