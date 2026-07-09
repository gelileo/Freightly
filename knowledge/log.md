# Build Log

Append-only chronological log of significant changes to this project. Each entry records what changed, why, and which articles were touched. Read sequentially, this log tells the story of the project's decisions.

## [2026-07-09] compile | adopt living-doc + capture design

- Adopted the living-doc methodology (greenfield template, applied manually) as the
  documentation substrate. Git hooks and CI drift-check intentionally omitted (not a git repo).
- Added `CLAUDE.md` with the same-task rule and article-mapping table, customized for the
  broker-email drafting assistant.
- Wrote the approved design as `concepts/drafting/platform-architecture.md`.
- Captured thin, capture-first stubs for the known surface area: `issue-taxonomy`,
  `response-taxonomy`, `eml-parsing`, `template-system`, `parties-and-roles`, and the
  `issue-to-template-flow` connection. Taxonomy seeds were read from the 71-file `LTL-mail/`
  corpus subject lines; category definitions and template bodies remain to be filled during
  implementation.

## [2026-07-09] discovery | two quoting formats in corpus

- Real-data pass over all 71 `LTL-mail/*.eml`: the dominant quoting format is Front's
  `^On … wrote:$` (46 files only, 25 mixed with Outlook `From:` blocks, 0 Outlook-only).
  The original `hs.eml` sample was Foxmail/Outlook-style and misled the first draft of the
  parsing article. Updated `concepts/drafting/eml-parsing.md` to require handling BOTH
  formats and to note Front signatures + the shared `ltlwest@priority1.com` mailbox.
- Deleted the stray root `hs.eml` (duplicate of a `60114821897` thread already in `LTL-mail/`).

## [2026-07-09] compile | CLI + write_case renders cases/<BOL>/thread.md

- Added `render_thread_md`, `write_case`, `main`, and the `__main__` CLI guard to
  `scripts/parse_eml.py`; `python3 scripts/parse_eml.py <file.eml> [--out cases]` now writes
  `cases/<BOL>/thread.md` (newest turn first) for humans to read. `cases/` stays out of git
  (see `.gitignore`) — this is CLI output, not source.
- Added the two TDD tests to `tests/test_parse_eml.py` (`render_thread_md`, `write_case`).
- Matured `concepts/drafting/eml-parsing.md`: resolved the "output shape" and "fixtures +
  unit tests" to-do items into a current-state description; `status: thin` → `mature`.
- Files touched: `scripts/parse_eml.py`, `tests/test_parse_eml.py`,
  `knowledge/concepts/drafting/eml-parsing.md`, `knowledge/log.md`.

## [2026-07-09] compile | corpus classifier + matured taxonomy

- Added `scripts/corpus_report.py` (`classify_issue`, `corpus_report`) + `tests/test_taxonomy.py`.
  All 71 `LTL-mail/*.eml` classify with `unknown == []`.
- **New category discovered by the full-corpus pass (same-task rule):** `reconsignment` —
  bare-BOL subjects (e.g. `Re: 60113972680`) whose body asks to reconsign to a new delivery
  address. Added to both `RULES` and `issue-taxonomy.md`.
- Matured `concepts/drafting/issue-taxonomy.md` (9 categories, real BOL counts, example files)
  and `concepts/drafting/response-taxonomy.md` (6 categories, each with a real broker quote
  sampled from generated `cases/<BOL>/thread.md`). Both `status: thin` → `mature`.
- Noted honestly: `quoted-cost-eta` has a real cost example but no hard-ETA example in the
  sampled threads; `delivery-access` folded into `damage`/`pickup` (no standalone subject in
  the 71 files).
- Files touched: `scripts/corpus_report.py`, `tests/test_taxonomy.py`,
  `knowledge/concepts/drafting/issue-taxonomy.md`,
  `knowledge/concepts/drafting/response-taxonomy.md`, `knowledge/log.md`.

## [2026-07-09] compile | broker-email templates per issue type + matured template-system

- Added `templates/<slug>.md` for all 9 issue slugs from `scripts/corpus_report.py`'s live
  scan: `pickup`, `shipment-status`, `pro-lookup`, `pod-request`, `cancellation`,
  `reconsignment`, `delivery-window`, `damage`, `return-reason`. Each has the four required
  sections (`## Skeleton` / `## Slots` / `## Tone` / `## Examples`); skeleton bodies are
  English (sent to the broker), author-facing notes are Chinese. No `delivery-access.md` —
  confirmed via `corpus_report()` that slug is not in the current 9 (folded into
  `damage`/`pickup`, already noted in `issue-taxonomy.md`).
- Grounded every template in a real parsed thread: `pickup` → `cases/60114338678`,
  `shipment-status` → `cases/60114476384` + `cases/60114356900`, `pod-request` →
  `cases/60114592263`, `delivery-window` → `cases/60114839031`, `cancellation` →
  `cases/60114304778`, `damage` → `cases/60114821897`, `return-reason` →
  `cases/60113820374`, `pro-lookup` → `cases/60114662390`, `reconsignment` →
  `cases/60113972680` (customer reconsign to `122 Timberline Dr, Unit 100, Spring Hill,
  TN 37174`; broker `needs-info` reply quoted verbatim).
- Added `tests/test_templates.py` (brief's exact test): asserts every slug from
  `corpus_report("LTL-mail")["by_issue"]` has a `templates/<slug>.md` with all four
  sections. Ran RED (missing `reconsignment.md`) before authoring, GREEN after.
- Matured `knowledge/concepts/drafting/template-system.md`: replaced the "To do
  (implementation)" section with the current state — the fixed `{shipper_signoff}` full
  text (Hughson Huang's real Justnano signature, sourced from `cases/60114338678/thread.md`
  Turn 1), the final per-template slot vocabulary, and the "one template per issue slug,
  four sections" convention. `status: thin` → `mature`.
- Files touched: `templates/pickup.md`, `templates/shipment-status.md`,
  `templates/pro-lookup.md`, `templates/pod-request.md`, `templates/cancellation.md`,
  `templates/reconsignment.md`, `templates/delivery-window.md`, `templates/damage.md`,
  `templates/return-reason.md`, `tests/test_templates.py`,
  `knowledge/concepts/drafting/template-system.md`, `knowledge/log.md`.

## [2026-07-09] compile | draft-broker-email skill + matured issue-to-template-flow

- Added `.claude/skills/draft-broker-email/SKILL.md`: the orchestrating skill. Flow —
  locate/parse case → `cases/<BOL>/thread.md`; ask user to paste the customer's WeChat
  Chinese message; classify issue type (`scripts/corpus_report.py`'s `classify_issue`, or
  `issue-taxonomy.md`) and broker response type (`response-taxonomy.md`'s priority order:
  `confirmed-completed` → `declined` → `needs-info` → `offered-alternative` → else
  `accepted`); if either has no matching category, update the taxonomy article first
  (same-task); select `templates/<issue-type>.md` and its response-branch per
  `issue-to-template-flow.md`; fill slots deterministically, translate the Chinese into
  `{customer_request}` (and issue-specific request slots), never invent facts — missing
  required slot → `[[MISSING: …]]`; write `cases/<BOL>/drafts/<incrementing n>.md`
  containing classification + chosen template + final English draft; stop and show the
  draft path/body, stating it is unsent and awaiting review. Never auto-sends.
- Matured `knowledge/connections/issue-to-template-flow.md`: replaced the "To do
  (implementation)" section with the final issue×response → template-branch matrix,
  covering `pickup`, `shipment-status`, `pod-request`, `delivery-window`, `cancellation`,
  `damage`, `reconsignment` across `needs-info`/`declined`/`accepted`/
  `offered-alternative`, each grounded in a real quote where the corpus has one and
  honestly marked "推断默认" (inferred default) where it doesn't. Default for an ambiguous
  broker response stays `needs-info` framing (ask/clarify, don't over-commit), matching
  `response-taxonomy.md`'s existing guidance. Also fixed a stale reference: the old
  "Two entry points" section cited the deleted `hs.eml` and the retired `delivery-access`
  slug — replaced with the real `damage` example (`cases/60114821897`, `declined` →
  `offered-alternative` → converts to `pickup`), and added an explicit disambiguation note
  that `delivery-access`/`templates/delivery-access.md` do not exist. `status: thin` →
  `mature`.
- Verified: all 9 template slugs from `templates/*.md` match `corpus_report("LTL-mail")`'s
  live slug set (`unknown == []`); full test suite (`python3 -m pytest tests/`, 13 tests)
  still green — no code changed, doc-only task.
- Files touched: `.claude/skills/draft-broker-email/SKILL.md`,
  `knowledge/connections/issue-to-template-flow.md`, `knowledge/log.md`.

## [2026-07-09] compile | issue-to-template-flow review fixes

- Added missing matrix sections for `pro-lookup` and `return-reason` (brief required every issue).
- Corrected the `damage`/60114821897 arc: added an honesty note that it is reconstructed across
  two different email subjects (not one CLI-reproducible thread), and relabeled `declined`/
  `offered-alternative` as customer-relayed (non-broker) per response-taxonomy; only `accepted`
  ("Working on this") is a real broker quote.
- Flagged `quoted-cost-eta` as a known matrix gap.
- Files touched: `knowledge/connections/issue-to-template-flow.md`, `knowledge/log.md`.

## [2026-07-09] compile | end-to-end validation + anti-drift maturation

- End-to-end validated `/draft-broker-email` on BOL 60114821897 (damage / broker `accepted`):
  produced `cases/60114821897/drafts/1.md` with all slots traced to real thread/WeChat data,
  no `[[MISSING]]`, unsent. (`cases/` is gitignored — draft is local demo output.)
- Anti-drift maturation: matured `concepts/drafting/platform-architecture.md` and
  `concepts/freight/parties-and-roles.md` (`thin` → `mature`). Corrected drift in
  platform-architecture: CLI writes primary `bol[0]` only (no multi-BOL fan-out, no auto
  snapshot-collapse — documented as known limitations); draft filename is `<n>` not
  `<timestamp>`; folder is now a git repo. parties-and-roles: recorded the real LTL West
  analysts (Guerrero, Posada, Moore, Dela Cruz, Turner), Front tooling, and the shared
  `ltlwest@priority1.com` mailbox.
- Corrected stale `CLAUDE.md` note (folder is now a git repo).
- All knowledge articles now `status: mature`. Full suite: 13 passed.
- Files touched: `knowledge/concepts/drafting/platform-architecture.md`,
  `knowledge/concepts/freight/parties-and-roles.md`, `CLAUDE.md`, `knowledge/log.md`.

## [2026-07-09] compile | final whole-branch review fixes

- Reconciled `concepts/drafting/eml-parsing.md` (matured) with as-built behavior, per the
  final review: (a) `Turn` = marker + body (no separate sender/timestamp fields); (b)
  `dedupe_snapshots()` is a library function the CLI does not auto-call; (c) Front signature
  text/`[Sent from Front]` artifacts are NOT stripped (only inline image parts discarded);
  (d) multi-BOL subjects write only the primary `bol[0]` (no fan-out).
- Closed the stale-snapshot risk: `SKILL.md` step 1 now instructs picking the largest/most
  recent snapshot (or using `dedupe_snapshots`) before classifying, so response-type isn't
  computed from an out-of-date thread.
- Deferred (documented) Minor items: split_turns over-split on stray "From:" lines (no data
  loss), bol[0] DRY/UNKNOWN-branch, quoted-cost-eta matrix gap, mid-module import placement.
- Files touched: `knowledge/concepts/drafting/eml-parsing.md`,
  `.claude/skills/draft-broker-email/SKILL.md`, `knowledge/log.md`.

## [2026-07-09] taxonomy | re-add delivery-access (same-task rule, live broker msg)

- A live broker message (BOL 60114821897: crate dimensions won't fit liftgate/bobtail →
  free terminal pickup) classified as `uncategorized`; `damage` (no damage) and `pickup`
  (not a pickup request) both misfit. Per the same-task rule (and issue-taxonomy's own note),
  re-added the `delivery-access` issue category.
- Added `templates/delivery-access.md`, a `delivery-access` section in
  `connections/issue-to-template-flow.md`, slots in `template-system.md`, a body-keyword
  RULE in `scripts/corpus_report.py` (liftgate/bobtail/…, chosen NOT to collide with any of
  the 71 corpus subjects — verified: `unknown==[]`, counts unchanged, no `delivery-access`
  key emitted). Category is body/live-message driven, so `corpus_report()` count is 0.
- 13 tests still pass.
- Files: `knowledge/concepts/drafting/issue-taxonomy.md`, `templates/delivery-access.md`,
  `knowledge/connections/issue-to-template-flow.md`,
  `knowledge/concepts/drafting/template-system.md`, `scripts/corpus_report.py`, `knowledge/log.md`.

## [2026-07-09] decision | v2 scope (LTL-mail-2 corpus)

- New corpus `LTL-mail-2/` (851 files) analyzed: it's Justnano's full broker inbox —
  ~330 statements, 36 FFBA billing-audit disputes, ~250+ shipment issues (many bare-BOL /
  `BOL#` subjects), ~25 drayage/container, ~70 sales/promo, plus meetings/auto-replies.
  Superset of `LTL-mail/` by BOL (all 24 old ⊂ 141 new).
- Decisions (user): scope = shipment issues + billing/FFBA disputes (drayage & marketing out,
  non-actionable → skip); corpus = keep BOTH dirs merged; classification → BODY-based
  (subject-only hit 71% uncategorized here).
- Recorded as "Planned v2" in `platform-architecture.md`; next step is a v2 implementation
  plan (writing-plans) then subagent execution. v1 remains as-built until then.
- Files: `knowledge/concepts/drafting/platform-architecture.md`, `knowledge/log.md`.

## [2026-07-09] compile | billing-dispute category + template + taxonomy update (v2 task 3)

- TDD: wrote `tests/test_billing_template.py` (asserts `templates/billing-dispute.md`
  exists with all four sections and the `{charge_ref}`/`{BOL}` slots); confirmed it FAILed
  (no template file), then added `templates/billing-dispute.md` and confirmed it PASSes.
- New template covers FFBA pricing-variance / out-of-route / reweigh-reclass / accessorial
  disputes with a "review-before-invoicing" skeleton (slots `{broker_contact}`/`{charge_ref}`/
  `{BOL}`/`{pro_clause}`/`{dispute_basis}`/`{shipper_signoff}`); never commits to a fabricated
  amount or fault. Examples grounded in real `LTL-mail-2/` quotes: `FFBA BOL# 60112079078.eml`
  ("Free Freight Bill Audit … pricing variance … Priority1 CAN dispute") and
  `BOL 60114409180 _ P-118701-2621.eml` (William Jerry relaying Warp's "out of route charge …
  145b Talmadge Rd, Edison, NJ").
- Matured `concepts/drafting/issue-taxonomy.md`: added the `billing-dispute` row (10th
  category; count `—` since it's sourced from `LTL-mail-2/` body-matching, not the 71-file
  `LTL-mail/` subject-based main table) and a new "`triage` 前置维度" section that makes this
  doc the governing reference for `scripts/triage.py`'s three-way front door (`skip` /
  `billing-dispute` / `shipment`) — `skip` is non-actionable and never drafted;
  `billing-dispute` and `shipment` are both draftable. Added a footnote in 说明与消歧
  documenting why `billing-dispute` sits outside the `LTL-mail/`-derived count.
- Updated `concepts/drafting/response-taxonomy.md`: billing-side broker replies reuse the
  existing 6 response slugs (commonly `needs-info` for supporting docs, `declined` to hold
  the charge, `accepted` to dispute on our behalf) — no new slug added unless the corpus
  later shows a gap.
- Both articles kept `status: mature`, `updated: 2026-07-09`.
- Full suite green: `python3 -m pytest -q` → 20 passed (includes the new billing template
  test and the pre-existing `tests/test_triage.py`).
- Files: `templates/billing-dispute.md`, `tests/test_billing_template.py`,
  `knowledge/concepts/drafting/issue-taxonomy.md`,
  `knowledge/concepts/drafting/response-taxonomy.md`, `knowledge/log.md`.
