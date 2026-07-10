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


class GeminiLlmClient:
    """Real adapter. Requires `google-genai` and GEMINI_API_KEY. Requests structured JSON
    and maps it to LlmDraft. Deterministic-first: factual slots in `facts` are passed through
    and the model is instructed to use ONLY those for facts (validator enforces anyway)."""

    MODEL = "gemini-2.5-flash"

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
