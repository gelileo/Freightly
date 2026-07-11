---
title: Platform Architecture
type: concept
area: drafting
updated: 2026-07-09
status: mature
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

1. **Raw corpus** — **as built (v2): two read-only directories**, `LTL-mail/*.eml`
   (71 files, the original adoption corpus) **and** `LTL-mail-2/*.eml` (851 files,
   Justnano's full broker inbox — statements, FFBA/billing disputes, drayage,
   sales/promo, meetings/auto-replies, plus the shipment-issue mail already covered by
   `LTL-mail/`). `scripts/corpus.py`'s `list_corpus()`/`merged_best()` treat both
   directories as one merged, deduped corpus (922 files total). Multiple `(1)(2)(3)…`
   files per BOL are usually snapshots of the same thread growing over time, now scattered
   across **either** directory. **Caveat: ~24/141 BOLs host two DISTINCT threads under one
   BOL** (a shipment thread + a separate billing/FFBA thread); `merged_best()` keeps only the
   largest and silently drops the other — parse the specific referenced `.eml` when you need
   a particular topic. See [eml-parsing](eml-parsing.md).
2. **Parser** — `scripts/parse_eml.py`. Deterministic. Decodes MIME (base64 /
   quoted-printable), strips signatures/logos, splits quoted history into chronological
   turns, dedupes thread snapshots, extracts BOL/PRO and parties. See
   [eml-parsing](eml-parsing.md).
3. **Corpus merge** — `scripts/corpus.py` (**v2, built**). `list_corpus(dirs=("LTL-mail",
   "LTL-mail-2"))` globs `*.eml` from both directories; `merged_best(dirs)` wraps
   `parse_eml.dedupe_snapshots()` over that combined file list, so the largest snapshot
   per BOL is picked **across both directories**, not just within one. This is what the
   skill's step 1 (locate case) calls to choose which `.eml` to parse.
4. **Triage front door** — `scripts/triage.py` (**v2, built**). `triage(body, sender) ->
   "skip" | "billing-dispute" | "shipment"` runs on the newest turn's body/sender
   **before** issue/response classification. Governed by
   [issue-taxonomy](issue-taxonomy.md) → "v2: `triage` 前置维度". `skip` mail never
   gets a case folder or draft; `billing-dispute` fixes the template to
   `templates/billing-dispute.md` and skips issue-type classification; `shipment` is the
   unchanged v1 two-dimension flow. `scripts/triage_report.py` runs `triage` over the
   full merged corpus and reports the bucket distribution (see "v2 triage 分布" in
   issue-taxonomy.md: 922 files → skip 327 / billing-dispute 60 / shipment 535).
5. **Case store** — `cases/<BOL>/thread.md` (parsed, deduped, chronological) and
   `cases/<BOL>/drafts/` (generated drafts awaiting review). `skip`-triaged mail
   produces neither.
6. **Taxonomy** — two dimensions, emergent and curated, for `shipment` and
   `billing-dispute` mail only: [issue-taxonomy](issue-taxonomy.md) (what the customer
   /broker wants — 10 shipment slugs + `billing-dispute`) ×
   [response-taxonomy](response-taxonomy.md) (how the broker replied — 6 slugs, reused
   as-is for billing-dispute). `triage`'s `skip` bucket sits **outside** this
   two-dimension model entirely (it is a front-door gate, not a third issue slug).
7. **Templates** — `templates/<issue-type>.md`: fill-in-blank skeleton + slot list +
   tone notes + linked real examples. 10 shipment templates + `templates/billing-dispute.md`
   (11 files total). See [template-system](template-system.md).
8. **Drafting skill** — `.claude/skills/draft-broker-email/SKILL.md`. Orchestrates the
   v2 flow: locate/snapshot-select (via `corpus.py`) → triage (skip/billing-dispute/
   shipment) → [for billing-dispute/shipment] classify → select template → fill slots →
   write draft → stop.

## Case model

- **Case key = BOL number.**
- **As built (current behavior):** the CLI parses **one `.eml` at a time** and writes to the
  **primary BOL only** (`parsed.bol[0]`) at `cases/<BOL>/thread.md`, overwriting on re-run.
- **Known limitations (not yet wired into the CLI):**
  - A subject naming several BOLs (`60114838856, 60114838936`) does **not** fan out into
    multiple case folders — only the first BOL gets a folder.
  - `dedupe_snapshots()` exists as a library function (picks the largest snapshot per BOL)
    but the CLI does not call it to auto-select the fullest of the `(1)(2)(3)` snapshots;
    the caller chooses which file to parse. See [eml-parsing](eml-parsing.md).

## Data flow (the drafting flow, v2 — built)

```
raw .eml (either LTL-mail/ or LTL-mail-2/)
        │
        ▼  merged_best() picks the largest snapshot per BOL, across both dirs
cases/<BOL>/thread.md
        │
        ▼  triage(body, sender)
   ┌────┴─────────────┬──────────────────┐
   ▼                  ▼                  ▼
 "skip"        "billing-dispute"      "shipment"
   │                  │                  │
   ▼                  │                  ▼
STOP — no case/       │        classify issue-type × response-type
draft written         │        (scripts/corpus_report.py / issue-taxonomy.md)
                       │                  │
                       ▼                  ▼
           classify response-type   select templates/<issue-type>.md
           only (issue-type fixed          │
           to templates/billing-           │
           dispute.md by triage)           │
                       │                  │
                       └────────┬─────────┘
                                ▼
              live WeChat msg (Chinese, pasted, may be empty for
              broker-initiated billing-dispute notices) ──┐
                                ▼                          │
                 extract slot values from thread ◀─────────┘
                                ▼
                 generate English draft (translate Chinese), anchored on template
                                ▼
                     write cases/<BOL>/drafts/<n>.md  ──▶  STOP for human review
```

See [issue-to-template-flow](../connections/issue-to-template-flow.md) for the
classification-to-draft detail on the `billing-dispute`/`shipment` branches, and
[issue-taxonomy](issue-taxonomy.md) → "v2: `triage` 前置维度" for the `skip` gate.

## Deliverables A and B (both required)

- **A — fill-in-blank templates**: canonical skeleton per issue type, the editable artifact.
- **B — LLM-drafted, template-guided**: the skill reads the skeleton + examples and
  produces a polished draft, translating the customer's Chinese, always pausing for review.

## Error handling / edge cases

- Unparseable or encrypted `.eml` → skip with a logged reason; never fabricate a thread.
- Issue or response that fits no existing category → the same-task rule requires adding it
  to the taxonomy article before drafting (capture first).
- Multi-BOL threads → intended as one case per BOL; **currently only the primary BOL gets a
  case folder** (see Case model → Known limitations). The draft should still reference all
  relevant BOLs in its body.
- Non-actionable mail (`triage == "skip"`) → never gets a case folder or a draft; the skill
  states the reason and stops at the triage step. See "v2: `triage` 前置维度" below.
- `shipment` mail whose subject `classify_issue()` can't sub-route (`unknown_shipment`,
  203/535 in the current corpus) → the skill falls back to human judgment against
  `issue-taxonomy.md`'s definitions (per SKILL.md step 4); this is a known, deferred gap in
  subject-based sub-classification, not a triage defect (triage itself correctly bucketed
  the mail as `shipment`).

## Testing strategy

- Parser: unit tests over a few sanitized corpus fixtures (known BOL, known turn count,
  known parties) — deterministic, so assertable.
- Taxonomy/templates: validated by re-running classification over labeled corpus examples
  and checking the chosen category/template matches the recorded example.
- Corpus merge: `tests/test_corpus.py` asserts `merged_best()` picks the right file across
  both directories for a known cross-directory BOL.
- Triage: `tests/test_triage.py` asserts `triage()` on labeled real bodies/senders;
  `tests/test_triage_report.py` asserts the full-corpus bucket counts sum to 922 and
  `billing-dispute` clears a minimum threshold.
- End-to-end (this article's own validation, 2026-07-09): ran `/draft-broker-email`
  end-to-end for both non-skip and skip cases — see "v2 (built)" below.

## v2 (built, 2026-07-09) — triage front door + merged corpus + billing-dispute

Triggered by the `LTL-mail-2/` corpus (851 files = Justnano's full broker inbox). This is
now the **as-built current state** (superseding the earlier "Planned v2" note in this
article's history — see `knowledge/log.md` for the compile trail).

- **Scope expanded** from shipment-issue drafting to also cover **billing / FFBA disputes**
  (Priority1 statements + Free Freight Bill Audit pricing-variance / extra-charge disputes).
  Drayage/container mail and broker marketing/sales prospecting stay **out of scope** and
  are folded into the `skip` bucket rather than given their own issue category; non-actionable
  mail generally (promo, statement noise, meetings, auto-replies, forwarded invoice
  boilerplate) also resolves to `skip` so nothing is drafted for it.
- **Corpus = both `LTL-mail/` + `LTL-mail-2/`, merged.** `scripts/corpus.py`'s
  `list_corpus()`/`merged_best()` (built) glob both directories and dedupe snapshots by BOL
  across them — the caller (the skill, step 1) no longer has to reason about which directory
  a BOL's fullest snapshot lives in. Verified end-to-end: BOL `60112079078`'s only snapshot
  lives in `LTL-mail-2/`; `merged_best()` returns it correctly (see Task 6 draft evidence,
  `cases/60112079078/drafts/1.md`).
- **Classification front door is body-based.** `scripts/triage.py`'s `triage(body, sender)`
  runs on the parsed newest-turn body before any issue/response classification, replacing
  what would otherwise still be a subject-only-first pass (subject-only alone hit 71%
  uncategorized on `LTL-mail-2` because many shipment threads carry bare-BOL / `BOL# …`
  subjects with no keyword). Full-corpus distribution (922 files, `scripts/triage_report.py`):
  `skip` 327 (35.5%), `billing-dispute` 60 (6.5%), `shipment` 535 (58.0%). Within `shipment`,
  203 files (`unknown_shipment`) still need body-level issue sub-classification beyond what
  `classify_issue()`'s subject rules cover — documented as a deferred gap, not a defect
  (see Error handling / edge cases above and `issue-taxonomy.md`'s "v2 triage 分布").
- **End-to-end validated (Task 6):** (A) `LTL-mail-2/FFBA BOL# 60112079078.eml` →
  `triage() == "billing-dispute"` → drafted via `templates/billing-dispute.md`,
  `accepted` response branch → `cases/60112079078/drafts/1.md` (unsent, no invented
  amounts, one flagged parser gap — see `eml-parsing.md`). (B)
  `LTL-mail-2/10% Off Freight Promo LTL, Truckload And Expedited.eml` →
  `triage() == "skip"` → confirmed the skill stops with no case/draft written (see
  `cases/_skip-demo.md`).

## Out of scope (YAGNI)

- Sending email / mailbox integration.
- Auto-ingesting WeChat (messages are pasted at draft time).
- Git hooks and CI drift-check. (The folder is now a git repo — initialized during
  implementation — so these *could* be added later, but living-doc's hook/Action layer was
  intentionally not installed.)

## Live mail loop (2026-07-11)

The inbound→draft→approve→send loop now runs against the real shipper mailbox
(`hs@justnanoinc.com`, Alibaba Enterprise Mail): the **IMAP poller** (`app/inbound.py`) pulls new
broker replies (UID-watermarked, read-only — never touches the human mailbox's flags), matches
them to the originating case by header-derived thread id, and produces an approval-gated ZH
customer update; **`AlibabaSmtpTransport`** sends the agent-approved English broker email. Both
verified live (login/read-only only); a real outbound send remains an explicitly-confirmed step.
See `concepts/app/transport-and-config.md`.
