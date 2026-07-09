---
title: Template System
type: concept
area: drafting
updated: 2026-07-09
status: thin
affects:
  - templates/**
references:
  - concepts/drafting/issue-taxonomy.md
---

# Template System

One template per [issue type](issue-taxonomy.md), living in `templates/<issue-type>.md`.
This is deliverable **A** (the editable skeleton) and the anchor for deliverable **B**
(the LLM-generated draft).

## Each template file contains

1. **Skeleton** — the English email with `{slot}` placeholders.
2. **Slot list** — each slot's meaning and where it is sourced (thread vs. WeChat message).
   Common slots: `{BOL}`, `{PRO}`, `{pickup_address}`, `{contact_name}`, `{contact_phone}`,
   `{contact_email}`, `{delivery_date}`, `{customer_request}`.
3. **Tone / structure notes** — concise, professional, broker-facing; lead with BOL/PRO.
4. **Worked examples** — 2–3 references to real `LTL-mail/` threads showing the template
   in use.

## Drafting contract (used by the skill)

The skill fills known slots deterministically, then lets the model translate the Chinese
customer request and smooth the prose — but it must not invent facts (addresses, dates,
prices) absent from the thread or WeChat message. Missing required slot → the draft marks
it `[[MISSING: …]]` for the reviewer rather than guessing.

## To do (implementation)

- Author the first templates for the highest-frequency issue types in the corpus.
- Finalize the slot vocabulary once the parser output shape is fixed.
