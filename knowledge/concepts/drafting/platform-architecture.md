---
title: Platform Architecture
type: concept
area: drafting
updated: 2026-07-09
status: thin
affects:
  - scripts/**
  - templates/**
  - .claude/skills/draft-broker-email/**
references:
  - concepts/drafting/issue-taxonomy.md
  - concepts/drafting/response-taxonomy.md
  - concepts/drafting/eml-parsing.md
  - concepts/drafting/template-system.md
  - concepts/freight/parties-and-roles.md
  - connections/issue-to-template-flow.md
load_bearing: true
---

# Platform Architecture

## Purpose

Help **Justnano (the shipper)** answer its **freight broker (Priority-1)** about shipment
issues that end **customers** raise over WeChat in Chinese. The system categorizes each
customer issue and each broker response, then drafts a polished English email to the
broker from a per-category template. **Every draft is written to disk for human review
before sending; nothing is sent automatically.**

See [parties-and-roles](../freight/parties-and-roles.md) for the customer → shipper →
broker → carrier chain.

## Why this shape

- **Markdown knowledge + thin script + a skill.** No servers, no database. The taxonomy
  and templates are human-readable Markdown the user can edit directly; the only code is
  the deterministic `.eml` parser, because email decoding and quoted-history splitting
  must not be left to a language model.
- **Living-doc governed.** The taxonomy and templates ARE living-doc knowledge articles.
  The same-task rule forces them to stay current as the corpus grows, so the skill (which
  reads them as instructions) can't silently drift.
- **Human-in-the-loop.** Volume is low and stakes are real (money, carriers), so a review
  gate is mandatory rather than optional.

## Components

1. **Raw corpus** — `LTL-mail/*.eml` (71 files at adoption). Read-only ground truth.
   Multiple `(1)(2)(3)` files per BOL are snapshots of the same thread growing over time.
2. **Parser** — `scripts/parse_eml.py`. Deterministic. Decodes MIME (base64 /
   quoted-printable), strips signatures/logos, splits quoted history into chronological
   turns, dedupes thread snapshots, extracts BOL/PRO and parties. See
   [eml-parsing](eml-parsing.md).
3. **Case store** — `cases/<BOL>/thread.md` (parsed, deduped, chronological) and
   `cases/<BOL>/drafts/` (generated drafts awaiting review).
4. **Taxonomy** — two dimensions, emergent and curated:
   [issue-taxonomy](issue-taxonomy.md) (what the customer wants) ×
   [response-taxonomy](response-taxonomy.md) (how the broker replied).
5. **Templates** — `templates/<issue-type>.md`: fill-in-blank skeleton + slot list +
   tone notes + linked real examples. See [template-system](template-system.md).
6. **Drafting skill** — `.claude/skills/draft-broker-email/SKILL.md`. Orchestrates the flow.

## Case model

- **Case key = BOL number.** A subject naming several BOLs (`60114838856, 60114838936`)
  belongs to multiple cases; the latest / most complete snapshot is authoritative.
- The parser collapses snapshots per BOL and keeps the fullest thread.

## Data flow (the drafting flow)

```
raw .eml ──parse──▶ cases/<BOL>/thread.md ─┐
live WeChat msg (Chinese, pasted) ─────────┤
                                            ▼
                              classify: issue-type × response-type
                                            ▼
                              select templates/<issue-type>.md
                                            ▼
                      extract slot values from thread + WeChat msg
                                            ▼
                 generate English draft (translate Chinese), anchored on template
                                            ▼
                     write cases/<BOL>/drafts/<timestamp>.md  ──▶  STOP for human review
```

See [issue-to-template-flow](../connections/issue-to-template-flow.md) for the
classification-to-draft detail.

## Deliverables A and B (both required)

- **A — fill-in-blank templates**: canonical skeleton per issue type, the editable artifact.
- **B — LLM-drafted, template-guided**: the skill reads the skeleton + examples and
  produces a polished draft, translating the customer's Chinese, always pausing for review.

## Error handling / edge cases

- Unparseable or encrypted `.eml` → skip with a logged reason; never fabricate a thread.
- Issue or response that fits no existing category → the same-task rule requires adding it
  to the taxonomy article before drafting (capture first).
- Multi-BOL threads → one case per BOL; the draft references all relevant BOLs.

## Testing strategy

- Parser: unit tests over a few sanitized corpus fixtures (known BOL, known turn count,
  known parties) — deterministic, so assertable.
- Taxonomy/templates: validated by re-running classification over labeled corpus examples
  and checking the chosen category/template matches the recorded example.

## Out of scope (YAGNI)

- Sending email / mailbox integration.
- Auto-ingesting WeChat (messages are pasted at draft time).
- Git hooks and CI drift-check (folder is not a git repo).
