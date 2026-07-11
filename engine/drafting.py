"""Headless drafting orchestrator: triage → classify → template → fill → LLM → validate.
Reuses scripts/ unchanged; depends on the LlmClient port so it is testable without network."""
from __future__ import annotations

from dataclasses import dataclass, field

from scripts.triage import triage
from scripts.corpus_report import classify_issue
from engine.knowledge import SHIPPER_SIGNOFF, TEMPLATES_DIR, load_template
from engine.llm import LlmClient
from engine.validate import validate_draft


@dataclass
class DraftRequest:
    body: str
    sender: str
    subject: str
    facts: dict[str, str] = field(default_factory=dict)
    source_text: str = ""
    target_lang: str = "en"
    issue_override: str | None = None  # when the issue type is known (customer picked it),
    #                                    honor it instead of re-classifying from the subject


@dataclass
class DraftResult:
    triage: str
    issue: str
    template_slug: str
    draft_lang: str
    draft_body: str
    missing: list[str] = field(default_factory=list)
    rejected_slots: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def draft(req: DraftRequest, llm: LlmClient) -> DraftResult:
    t = triage(req.body, req.sender)
    if t == "skip":
        return DraftResult(triage="skip", issue="", template_slug="",
                           draft_lang="", draft_body="")
    if t == "billing-dispute":
        issue = "billing-dispute"
        slug = "billing-dispute"
    elif req.issue_override:  # customer-declared issue type — honor it
        issue = slug = req.issue_override
    else:  # shipment — classify from the subject
        issue = classify_issue(req.subject)
        slug = issue if issue != "uncategorized" else "pickup"  # safe default; agent can correct
    if not (TEMPLATES_DIR / f"{slug}.md").exists():  # unknown slug (e.g. "other") → safe default
        slug = "pickup"
    template = load_template(slug)
    raw = llm.generate(system="", template=template, facts=req.facts,
                       source_text=req.source_text, target_lang=req.target_lang)
    v = validate_draft(raw, source_text=req.source_text)
    # Deterministically inject the fixed shipper signoff — never trust the LLM for it.
    body = v.body.replace("[[MISSING: shipper_signoff]]", SHIPPER_SIGNOFF) \
                 .replace("{shipper_signoff}", SHIPPER_SIGNOFF)
    missing = [x for x in v.missing if x != "shipper_signoff"]
    return DraftResult(triage=t, issue=issue, template_slug=slug, draft_lang=raw.lang,
                       draft_body=body, missing=missing, rejected_slots=v.rejected,
                       warnings=v.warnings)
