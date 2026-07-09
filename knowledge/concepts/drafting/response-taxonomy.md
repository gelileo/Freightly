---
title: Broker Response Taxonomy
type: concept
area: drafting
updated: 2026-07-09
status: thin
references:
  - concepts/drafting/issue-taxonomy.md
  - connections/issue-to-template-flow.md
---

# Broker Response Taxonomy

How the broker (Priority-1, relaying the carrier) replies. The second classification
dimension; combined with the [issue type](issue-taxonomy.md) it selects the reply template.

## Seed categories (definitions TBD in implementation)

| Slug | Meaning |
| --- | --- |
| `accepted` | Broker/carrier will do what was asked |
| `declined` | Cannot do it (e.g. no equipment fits, route inaccessible) |
| `offered-alternative` | Proposes another option (terminal pickup, different truck, reschedule) |
| `needs-info` | Requests more detail before proceeding (dims, contact, address, PRO) |
| `quoted-cost-eta` | Provides a price, fee, or delivery date/window |
| `confirmed-completed` | Reports the action done (picked up, delivered, POD attached) |

## To do (implementation)

- Validate against the corpus; the oversized-crate thread (`hs.eml`) walks
  `declined → offered-alternative` before resolution, a useful test case.
- Define precedence when a single broker email mixes signals (e.g. `needs-info` +
  `offered-alternative`).
