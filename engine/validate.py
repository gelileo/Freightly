"""Anti-fabrication validator: factual slot values must be traceable to the source text.
Untraceable factual values are rewritten to [[MISSING: key]] rather than trusted."""
from __future__ import annotations

from dataclasses import dataclass, field

from engine.llm import LlmDraft

# Slots that assert a FACT about the shipment; these must appear in source_text verbatim.
FACTUAL_SLOTS: set[str] = {
    "BOL", "PRO", "pro", "pickup_address", "new_address", "contact_phone",
    "delivery_date", "charge_ref",
}


@dataclass
class Validated:
    body: str
    missing: list[str] = field(default_factory=list)
    rejected: list[str] = field(default_factory=list)


def validate_draft(raw: LlmDraft, *, source_text: str) -> Validated:
    body = raw.body
    missing = list(raw.missing)
    rejected: list[str] = []
    for key, val in raw.filled_slots.items():
        if key in FACTUAL_SLOTS and val and val not in (source_text or ""):
            rejected.append(key)
            missing.append(key)
            body = body.replace(val, f"[[MISSING: {key}]]")
    return Validated(body=body, missing=missing, rejected=rejected)
