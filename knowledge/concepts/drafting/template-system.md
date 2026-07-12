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
(the LLM-generated draft). The 9 **subject-classifiable** slugs from `issue-taxonomy.md` —
`pickup`, `shipment-status`, `pro-lookup`, `pod-request`, `cancellation`, `reconsignment`,
`delivery-window`, `damage`, `return-reason` — each have a template file, and
`tests/test_templates.py` asserts this stays true against `scripts/corpus_report.py`'s live
slug set. **`delivery-access.md` also exists (10 shipment templates total)** but is driven by
broker **message bodies** (dimensions won't fit liftgate/bobtail → terminal pickup), not by
any subject in the 71-file corpus — so `corpus_report()` never emits it and the corpus-based
test does not require it. It was re-added under the same-task rule (see issue-taxonomy.md).

**v2: `templates/billing-dispute.md` (11 templates total, built).** Unlike the 10 shipment
templates above, `billing-dispute` is **not** selected via `scripts/corpus_report.py`'s
`classify_issue()` (subject-based) at all — it is **triage-driven**: `scripts/triage.py`'s
`triage(body, sender)` classifies the newest turn's **body** and, when it returns
`"billing-dispute"`, the drafting skill fixes the template to `templates/billing-dispute.md`
directly, skipping the issue-type sub-step entirely (see `SKILL.md` step 2/4 and
`issue-taxonomy.md` → "v2: `triage` 前置维度"). It is not in `corpus_report()`'s subject-slug
set and `tests/test_templates.py`'s corpus-based assertion does not (and should not) cover
it; its own test is `tests/test_billing_template.py`. It still follows the same four-section
convention below. `skip` (the third triage bucket) is **not** a template/issue slug at all —
it is a front-door gate that stops the flow before any template is chosen (never drafted).

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
  print a placeholder PRO#). **Pre-filled deterministically by `engine.drafting.draft()`** from
  `facts["PRO"]` (like `{broker_contact}`), *before* the LLM — so a no-PRO shipment renders an
  empty clause, never an `[[MISSING: pro_clause]]` placeholder that the send guardrail would block.
- `{customer_request}` — the customer's WeChat ask, translated to English and condensed to
  one sentence by the drafting skill. Empty string when there is nothing beyond the base
  ask already covered by the skeleton — **enforced**: the `_SYSTEM` prompt tells the model not to
  restate the base issue, and `draft()` strips an unfilled slot (and its blank line) to empty
  rather than emitting a placeholder.
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
- `delivery-access`: `{access_constraint}` (why regular delivery fails), `{proposed_resolution}`
  (the next-step ask — alternate truck / earliest date / cost, and/or terminal-pickup
  confirmation; the customer's final choice stays `[[MISSING]]` until confirmed).
- `billing-dispute` (v2, triage-driven — see above, not part of the 10 shipment slugs):
  `{charge_ref}` (the disputed charge, restated verbatim/factually — e.g. "the FFBA pricing
  variance" — required, `[[MISSING: …]]` if absent), `{dispute_basis}` (our position or the
  broker's ask for supporting docs, one sentence, empty when there is none — **never a
  fabricated dollar amount or fault determination**). Reuses the shared `{broker_contact}`,
  `{BOL}`, `{pro_clause}`, `{shipper_signoff}`; does **not** use `{customer_request}` since
  many billing-dispute threads are broker-initiated notices with no WeChat ask to translate.

Any required slot missing from the thread renders as `[[MISSING: …]]` in the draft rather
than being guessed — the reviewer fills it in before sending.

## `{shipper_signoff}` (fixed, from config)

The signoff is the shipper's real signature (name / title / company / address / phones / email) —
**PII, so it is NOT stored in the repo**. It comes from the `SHIPPER_SIGNOFF` env var (kept in
`.env`, out of git; `\n`-escaped), resolved by `engine.knowledge.shipper_signoff()` and injected
deterministically into every draft. When unset (tests/CI) a neutral placeholder is used:

```
Best Regards

[Shipper Name]
[Title]

[Company]
[Address]
[Phone]
[shipper email] | [website]
```

## Drafting contract (used by the skill)

The skill fills known slots deterministically, then lets the model translate the Chinese
customer request and smooth the prose — but it must not invent facts (addresses, dates,
prices) absent from the thread or WeChat message. Missing required slot → the draft marks
it `[[MISSING: …]]` for the reviewer rather than guessing.

## Convention: one template per issue slug, four sections

Every `templates/<slug>.md` follows the same four-section shape (`## Skeleton` / `## Slots`
/ `## Tone` / `## Examples`) — **11 template files today: 10 shipment-issue slugs
(9 subject-classifiable + `delivery-access`) plus the triage-driven `billing-dispute`.**
`tests/test_templates.py` treats the corpus-classifiable subset identically (no
per-template special-casing) by asserting against `scripts/corpus_report.py`'s live subject
slug set; `delivery-access` and `billing-dispute` are body/triage-driven and are covered by
their own dedicated assertions instead (see issue-taxonomy.md and
`tests/test_billing_template.py`). When `issue-taxonomy.md` gains a new subject-classifiable
slug (same-task rule), add `templates/<new-slug>.md` with the same four sections in the same
task; the test will otherwise fail on the next corpus scan.
