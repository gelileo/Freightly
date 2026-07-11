"""Headless drafting orchestrator: triage → classify → template → fill → LLM → validate.
Reuses scripts/ unchanged; depends on the LlmClient port so it is testable without network."""
from __future__ import annotations

from dataclasses import dataclass, field

from scripts.triage import triage
from scripts.corpus_report import classify_issue
from engine.knowledge import SHIPPER_SIGNOFF, TEMPLATES_DIR, load_template
from engine.llm import LlmClient
from engine.validate import validate_draft


_SYSTEM = (
    "You are drafting a concise, professional English email from a freight agent to a freight "
    "broker. Fill each remaining {slot} using the provided facts and by translating the "
    "customer's Chinese request into English. Do NOT change the greeting line and do NOT invent "
    "a recipient name. Never invent BOL/PRO numbers, addresses, dates, or amounts — leave any "
    "unknown factual slot as [[MISSING: key]]."
)


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


def summarize_for_customer(broker_text: str, llm: LlmClient, target_lang: str = "zh") -> str:
    """Relay a broker's reply to the customer as a short, faithful message (default Chinese)."""
    return llm.summarize(text=broker_text, target_lang=target_lang,
                         context="Relay the broker/carrier's answer to the shipping customer.")


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
    # Pre-fill the greeting deterministically so the LLM can't hallucinate a recipient name
    # (e.g. from the customer's informal address to the agent). Default "team" when the broker
    # contact isn't known; the router may pass a resolved name via facts["broker_contact"].
    template = template.replace("{broker_contact}", req.facts.get("broker_contact") or "team")
    raw = llm.generate(system=_SYSTEM, template=template, facts=req.facts,
                       source_text=req.source_text, target_lang=req.target_lang)
    v = validate_draft(raw, source_text=req.source_text)
    # Deterministically inject the fixed shipper signoff — never trust the LLM for it.
    body = v.body.replace("[[MISSING: shipper_signoff]]", SHIPPER_SIGNOFF) \
                 .replace("{shipper_signoff}", SHIPPER_SIGNOFF)
    missing = [x for x in v.missing if x != "shipper_signoff"]
    return DraftResult(triage=t, issue=issue, template_slug=slug, draft_lang=raw.lang,
                       draft_body=body, missing=missing, rejected_slots=v.rejected,
                       warnings=v.warnings)
