---
title: Customer Issue Taxonomy
type: concept
area: drafting
updated: 2026-07-09
status: thin
references:
  - concepts/drafting/response-taxonomy.md
  - connections/issue-to-template-flow.md
---

# Customer Issue Taxonomy

The customer's *ask*, as relayed to the broker. Emergent and curated: every new `.eml`
that reveals a category not listed here must add it (same-task rule).

## Seed categories (read from `LTL-mail/` subject lines; definitions TBD in implementation)

| Slug | Trigger (customer wants…) | Corpus example |
| --- | --- | --- |
| `pickup` | Arrange / confirm / chase a pickup | `Re_ pickup --- 60114338678.eml` |
| `delivery-window` | Set or change the delivery appointment | `Re_ Delivery window --- 60114839031.eml` |
| `shipment-status` | Where is it / when will it arrive | `Re_ Shipment status --- 60114476384.eml` |
| `pod-request` | Proof of delivery document | `Re_ POD --- 60114592263.eml` |
| `cancellation` | Cancel a shipment | `Re_ Cancel shipment --- 60114304778.eml` |
| `return-reason` | Explain / obtain a return reason | `Re_ Request for Return Reason --- 60113820374.eml` |
| `damage` | Report damaged freight / urgent redelivery | `Re_ Urgent Delivery Request – Crate Damaged _ 60114821897.eml` |
| `delivery-access` | Site can't take a normal truck (oversized / narrow road) | `hs.eml` (BOL 60114821897) |
| `pro-lookup` | Get / reconcile a PRO number | `Re_ Pro# ---- 60114662390.eml` |

## To do (implementation)

- Write a one-paragraph definition + disambiguation for each slug.
- Confirm slugs against a full pass over all 71 corpus files; merge/split as the data shows.
- Note which issue types commonly co-occur (e.g. `delivery-access` → `pickup` after the
  customer agrees to terminal pickup).
