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
    r"quote for you|out of office|automatic reply|calendar invitation|has invited you|"
    # drayage rate-quote requests ("please advise: drayage cost / free time at
    # terminal / any additional charges") — corpus-wide sweep found this exact
    # idiom (23-snapshot "Drayage moves --- 40HQ ... Tempe, AZ" thread) tripping
    # _BILLING below via its own "additional charge(s)" phrase; it's a drayage
    # quote ask, not a real dispute, and drayage is out of v2 scope (skip) per
    # the taxonomy's own definition.
    r"drayage cost|free time at terminal|"
    # broker sales-rep prospecting ("earn your business", "quote your upcoming
    # shipments", "competitive pricing/rates") — same genre as the existing
    # promo/discount patterns above, found via corpus-wide sweep on standalone
    # (non-reply-thread) outreach emails from Priority1 territory managers.
    r"earn (your|more) business|earn the right to move|"
    r"quote (them|your upcoming|more shipments|them out for you)|"
    r"competitive (pricing|rates)|"
    # automated invoice notifications forwarded/cc'd through a human Priority1
    # mailbox (Kaylin Shaw / Melody Sparks) instead of noreply@priority1.com —
    # same non-actionable "Dear Customer, Attached are your invoice(s)" boilerplate
    # as the noreply-sent statements _SKIP_SENDER already catches; corpus-wide
    # sweep found 18 such emails escaping to 'shipment' purely because the sender
    # wasn't noreply@.
    r"dear customer, attached are your invoice|log in to view all invoices|"
    r"2\.5% surcharge will apply to all credit card",
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
