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
