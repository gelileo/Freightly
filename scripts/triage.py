"""Body-based front-door triage: skip / billing-dispute / shipment.

Governed by knowledge/concepts/drafting/issue-taxonomy.md (v2). Rules are ordered:
skip (non-actionable) first, then billing, else shipment.
"""
from __future__ import annotations

import re

# Non-actionable: broker marketing/sales, statements, drayage, auto-replies, meetings.
_SKIP_SENDER = re.compile(r"noreply@priority1", re.IGNORECASE)
_SKIP_BODY = re.compile(
    r"promotion|10% discount|new shippers|shipments going out this week|"
    r"kick off (the|a great|october)|containers you have coming in from the port|"
    r"quote for you|out of office|automatic reply|calendar invitation|has invited you",
    re.IGNORECASE,
)

# Billing disputes (real money): FFBA audit variances, extra/accessorial charges.
_BILLING = re.compile(
    r"free freight bill audit|pricing variance|additional charge|out of route|"
    r"accessorial charge|reweigh|reclass",
    re.IGNORECASE,
)


def triage(body: str, sender: str) -> str:
    body = body or ""
    sender = sender or ""
    if _SKIP_SENDER.search(sender) or _SKIP_BODY.search(body):
        return "skip"
    if _BILLING.search(body):
        return "billing-dispute"
    return "shipment"
