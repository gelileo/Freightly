"""Anti-fabrication validator: factual slot values must be traceable to the source text.
Untraceable factual values are rewritten to [[MISSING: key]] rather than trusted."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from engine.llm import LlmDraft

# Placeholders that must NEVER reach a broker: the anti-fabrication marker `[[MISSING: …]]`
# (any `[[…]]`), and unfilled template slots like `{pickup_address}`.
_PLACEHOLDER_RE = re.compile(r"\[\[[^\]]*\]\]|\{[A-Za-z][\w-]*\}")


def find_placeholders(text: str) -> list[str]:
    """Return every unfilled placeholder token in `text` (empty list if the draft is clean).
    Used as the send-time guardrail so a draft with missing facts / unfilled slots cannot be
    sent to a broker."""
    return _PLACEHOLDER_RE.findall(text or "")

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
    warnings: list[str] = field(default_factory=list)


def validate_draft(raw: LlmDraft, *, source_text: str) -> Validated:
    body = raw.body
    missing = list(raw.missing)
    rejected: list[str] = []
    warnings: list[str] = []
    for key, val in raw.filled_slots.items():
        if key in FACTUAL_SLOTS and val and val not in (source_text or ""):
            rejected.append(key)
            missing.append(key)
            new_body = body.replace(val, f"[[MISSING: {key}]]")
            if new_body == body:
                warnings.append(
                    f"unredacted factual slot {key!r}: value not found verbatim in draft body — manual review required"
                )
            body = new_body
    return Validated(body=body, missing=missing, rejected=rejected, warnings=warnings)
