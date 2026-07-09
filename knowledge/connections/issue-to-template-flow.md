---
title: Issue-to-Template Flow
type: connection
area: drafting
updated: 2026-07-09
status: thin
references:
  - concepts/drafting/issue-taxonomy.md
  - concepts/drafting/response-taxonomy.md
  - concepts/drafting/template-system.md
  - concepts/drafting/platform-architecture.md
---

# Issue-to-Template Flow

How the two classification dimensions combine to pick a template and shape a draft.

## Rule

- **Issue type** (from [issue-taxonomy](../concepts/drafting/issue-taxonomy.md)) selects
  *which* `templates/<issue-type>.md` file to use.
- **Broker response type** (from [response-taxonomy](../concepts/drafting/response-taxonomy.md))
  selects *which branch / framing* inside that template — e.g. the `pickup` template reads
  differently when the last broker email was `needs-info` (supply the missing detail) vs.
  `declined` (relay the customer's next instruction or accept the alternative).

## Two entry points (full loop)

1. **New issue** — no prior broker email; customer's WeChat message drives an *initial*
   outbound email using the issue template's opening branch.
2. **Ongoing thread** — a broker reply exists; classify its response type, then draft the
   *follow-up* branch. The oversized-crate thread (`hs.eml`) is the canonical multi-turn
   example: `delivery-access` issue, broker `declined` → `offered-alternative`, resolved
   by the customer accepting terminal pickup.

## To do (implementation)

- Build the issue×response → template-branch matrix once the template bodies exist.
- Decide default when the response type is ambiguous (lean toward `needs-info` framing:
  ask/clarify rather than over-commit).
