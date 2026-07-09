---
title: Template System
type: concept
area: drafting
updated: 2026-07-09
status: mature
affects:
  - templates/**
references:
  - concepts/drafting/issue-taxonomy.md
---

# Template System

One template per [issue type](issue-taxonomy.md), living in `templates/<issue-type>.md`.
This is deliverable **A** (the editable skeleton) and the anchor for deliverable **B**
(the LLM-generated draft). All 9 slugs from `issue-taxonomy.md` — `pickup`,
`shipment-status`, `pro-lookup`, `pod-request`, `cancellation`, `reconsignment`,
`delivery-window`, `damage`, `return-reason` — have a template file; `tests/test_templates.py`
asserts this stays true against `scripts/corpus_report.py`'s live slug set (no
`delivery-access.md`: that category folded into `damage`/`pickup`, see issue-taxonomy.md).

## Each template file contains (four sections, always in this order)

1. **`## Skeleton`** — the English email body with `{slot}` placeholders. Always English —
   it is sent to the broker — even though the surrounding prose/comments in the template
   file may be Chinese (author-facing notes on when/why to use it).
2. **`## Slots`** — each slot's meaning and where it is sourced (thread vs. WeChat message),
   one bullet per slot, in the order they appear in the skeleton.
3. **`## Tone`** — one or two sentences: concise, professional, broker-facing; lead with
   BOL/PRO; never invent facts.
4. **`## Examples`** — 1–2 references to real `LTL-mail/*.eml` filenames (or the parsed
   `cases/<BOL>/thread.md`) showing the template in use, with a short real quote from the
   broker's reply.

## Slot vocabulary (final)

Slots shared across every template:

- `{broker_contact}` — the broker contact's first name, taken from the signature of their
  most recent reply in the thread. Falls back to `"team"` when no name is on file.
- `{BOL}` — the case's BOL number. Always required; sourced from the case folder name /
  thread header.
- `{pro_clause}` — `" (PRO# {pro})"` when a PRO# is known, else an empty string (do not
  print a placeholder PRO#).
- `{customer_request}` — the customer's WeChat ask, translated to English and condensed to
  one sentence by the drafting skill. Empty string when there is nothing beyond the base
  ask already covered by the skeleton.
- `{shipper_signoff}` — fixed, never varies per case (see below).

Issue-specific slots (sourced from the thread or the WeChat message, never invented):

- `pickup`: `{pickup_address}`, `{contact_name}`, `{contact_phone}`.
- `shipment-status`: `{last_known_status}`.
- `pro-lookup`: none beyond the shared set (shortest template).
- `pod-request`: `{delivery_date_clause}` (a full sentence, empty when the delivery date
  is unknown — never guess a date).
- `cancellation`: `{cancel_reason}`.
- `reconsignment`: `{new_address}` (copied verbatim, never translated/normalized),
  `{contact_name}`, `{contact_phone}`.
- `delivery-window`: `{requested_window}`, `{receiver_contact}`.
- `damage`: `{damage_desc}`, `{customer_request}` (used for the follow-up ask, e.g. a
  specific delivery date or alternate-truck request).
- `return-reason`: `{return_reason}` (optional context/dispute sentence).

Any required slot missing from the thread renders as `[[MISSING: …]]` in the draft rather
than being guessed — the reviewer fills it in before sending.

## `{shipper_signoff}` (fixed, verbatim)

Sourced from Justnano's real signature appearing in every `cases/<BOL>/thread.md` (e.g.
`cases/60114338678/thread.md`, Turn 1). The skill inserts this exact block, unchanged,
for every draft:

```
Best Regards

Hughson Huang
President

Justnano INC
Add: 14425 Yorba Ave, Chino CA 91710
Mobile: +1 (626)-688-8030
Office: +1 (626)-600-4211
hs@justnanoinc.com | www.justnanoinc.com
```

## Drafting contract (used by the skill)

The skill fills known slots deterministically, then lets the model translate the Chinese
customer request and smooth the prose — but it must not invent facts (addresses, dates,
prices) absent from the thread or WeChat message. Missing required slot → the draft marks
it `[[MISSING: …]]` for the reviewer rather than guessing.

## Convention: one template per issue slug, four sections

Every `templates/<slug>.md` follows the same four-section shape (`## Skeleton` / `## Slots`
/ `## Tone` / `## Examples`) so the drafting skill and `tests/test_templates.py` can treat
all 9 files identically — no per-template special-casing. When `issue-taxonomy.md` gains a
new slug (same-task rule), add `templates/<new-slug>.md` with the same four sections in the
same task; the test will otherwise fail on the next corpus scan.
