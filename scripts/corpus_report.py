"""Classify the LTL-mail corpus by issue type from the subject line.

Governed by knowledge/concepts/drafting/issue-taxonomy.md — keep the RULES in
sync with that article (same-task rule).
"""
from __future__ import annotations

from pathlib import Path
import re

# Ordered: first matching pattern wins. Patterns match the subject case-insensitively.
RULES: list[tuple[str, str]] = [
    (r"return reason", "return-reason"),
    (r"crate damaged|damage", "damage"),
    # delivery-access: equipment/size/road access failure. Keywords chosen NOT to collide
    # with any subject in the 71-file corpus (which never says liftgate/bobtail/etc.); this
    # category is normally body-driven, so classify_issue rarely fires it — see issue-taxonomy.md.
    (r"liftgate|bobtail|won'?t fit|will not fit|too big|too narrow|oversiz", "delivery-access"),
    (r"delivery window", "delivery-window"),
    (r"shipment status|statue", "shipment-status"),  # 'Statue' is a corpus typo for Status
    (r"\bpod\b", "pod-request"),
    (r"cancel", "cancellation"),
    (r"pickup|pick up", "pickup"),
    (r"pro#|\bpro\b", "pro-lookup"),
    # Bare-BOL subject, no keyword at all (e.g. "Re: 60113972680(1)"). Corpus
    # example: BOL 60113972680 — thread body asks to reconsign the shipment to
    # a new delivery address. Kept last so real keyword matches win first.
    (r"^re:\s*\d{6,}(\(\d+\))?$", "reconsignment"),
]


def classify_issue(subject: str) -> str:
    s = subject.lower()
    # strip Chinese reply prefix 回复 and Re: noise before matching
    s = s.replace("回复", " ")
    for pattern, slug in RULES:
        if re.search(pattern, s):
            return slug
    return "uncategorized"


def corpus_report(corpus_dir: "str | Path") -> dict:
    corpus_dir = Path(corpus_dir)
    by_issue: dict[str, list[str]] = {}
    unknown: list[str] = []
    for p in sorted(corpus_dir.glob("*.eml")):
        # subject sits in the filename for this corpus (Re_ <subject>.eml),
        # normalize back to a subject-ish string
        subject = p.stem.replace("Re_", "Re:").replace("_", " ")
        slug = classify_issue(subject)
        bols = re.findall(r"\b60\d{9}\b", p.name)
        if slug == "uncategorized":
            unknown.append(subject)
        else:
            by_issue.setdefault(slug, []).extend(bols)
    return {"by_issue": by_issue, "unknown": unknown}
