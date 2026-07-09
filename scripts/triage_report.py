"""Run body-based triage over the whole merged corpus and report the distribution.

Drives rule refinement (same-task rule): anything mis-bucketed is fixed in triage.py /
issue-taxonomy.md in THIS task, not deferred.
"""
from __future__ import annotations

from scripts.corpus import CORPUS_DIRS, list_corpus
from scripts.parse_eml import parse_eml
from scripts.corpus_report import classify_issue
from scripts.triage import triage


def triage_report(dirs: tuple[str, ...] = CORPUS_DIRS) -> dict:
    counts: dict[str, int] = {"skip": 0, "billing-dispute": 0, "shipment": 0}
    unknown_shipment: list[str] = []
    for p in list_corpus(dirs):
        parsed = parse_eml(p)
        t = triage(parsed.body, parsed.sender)
        counts[t] = counts.get(t, 0) + 1
        if t == "shipment" and classify_issue(parsed.subject) == "uncategorized":
            unknown_shipment.append(p.name)
    return {"counts": counts, "unknown_shipment": unknown_shipment}
