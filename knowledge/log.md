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

## [2026-07-09] compile | corpus-wide triage report + matured v2 distribution (task 4)

- TDD: wrote `tests/test_triage_report.py` (asserts `sum(counts) == 922`, the three bucket
  keys present, `billing-dispute >= 20`, `unknown_shipment` is a list); confirmed it FAILed
  (`ModuleNotFoundError: No module named 'scripts.triage_report'`), then added
  `scripts/triage_report.py` (`triage_report(dirs=CORPUS_DIRS)` — runs `parse_eml` + `triage`
  over every file in the merged 922-file corpus, flags `shipment`-bucketed mail that
  `classify_issue(subject)` still can't sub-route as `unknown_shipment`) and confirmed PASS.
- Ran the report and read real body samples across all three buckets plus `unknown_shipment`;
  found and fixed three genuine mis-classifications in `scripts/triage.py`'s `_SKIP_BODY`
  (all verified corpus-wide for zero collateral before landing):
  1. A 23-snapshot drayage rate-quote thread ("Drayage moves --- 40HQ from Phoenix Terminal
     to Tempe, AZ") asks "Please advise: Drayage cost / Free time at terminal / Any
     additional charges" — the literal "additional charge(s)" was tripping `_BILLING`,
     misrouting a plain quote request into `billing-dispute`. Drayage is out of v2 scope
     (`skip`) per the existing "decision | v2 scope" log entry. Added
     `drayage cost|free time at terminal`.
  2. 7 standalone Priority1 sales-rep outreach emails ("Priority1 Business.eml", "Let's Kick
     Off ... .eml", etc. — "earn your business", "quote your upcoming shipments",
     "competitive pricing") were landing in `shipment` because they didn't hit any existing
     promo keyword. Added `earn (your|more) business|earn the right to move|quote (them|your
     upcoming|more shipments|them out for you)|competitive (pricing|rates)`; manually
     confirmed each hit is a standalone outreach email, not a reply thread that would get
     silently skipped via a quoted-history false positive.
  3. 18 automated invoice-notification emails ("JUSTNANO INC-(298296-P1) Priority1 Invoice
     ....eml") are the same "Dear Customer, Attached are your invoice(s) ... log in to view
     all invoices ... 2.5% surcharge" boilerplate as the `noreply@priority1.com`-sent
     statements already caught by `_SKIP_SENDER`, but forwarded/cc'd through a human mailbox
     (Kaylin Shaw / Melody Sparks) so the sender check missed them. Added the three
     boilerplate phrases; verified across all 248 "Priority1 Invoice" files in the corpus
     (230 already `skip`, these 18 now join them, zero collateral into `billing-dispute` or
     other `shipment` files).
- Real distribution after refinement (922 files total): `skip` 327, `billing-dispute` 60,
  `shipment` 535; `unknown_shipment` (shipment mail whose subject `classify_issue` still
  can't sub-route — expected, deferred to body-level sub-classification) 203. Before the
  three fixes: `skip` 279, `billing-dispute` 83, `shipment` 560, `unknown_shipment` 228.
  `billing-dispute >= 20` holds comfortably (60), no threshold adjustment needed.
- Matured `concepts/drafting/issue-taxonomy.md`: added "## v2 triage 分布(实测 2026-07-09)"
  with the real counts table and a full writeup of the three `_SKIP_BODY` refinements
  (with the exact real-body quotes that justified each) and the before/after comparison.
- Full suite green: `python3 -m pytest -q` → 21 passed.
- Files: `scripts/triage_report.py`, `tests/test_triage_report.py`, `scripts/triage.py`,
  `knowledge/concepts/drafting/issue-taxonomy.md`, `knowledge/log.md`.

## [2026-07-09] compile | v2 skill flow (triage: skip/billing/shipment) + freight terms (task 5)

- Upgraded `.claude/skills/draft-broker-email/SKILL.md` to the v2 body-based triage flow:
  inserted a front-door **TRIAGE** step (new step 2, after locate-case+snapshot, before the
  issue×response classification) that calls `scripts/triage.py`'s `triage(body, sender)`:
  `skip` → tell the user it's non-actionable and stop, never drafting/never writing
  `cases/<BOL>/drafts/`; `billing-dispute` → issue type is fixed to
  `templates/billing-dispute.md` by triage itself (skip the issue-type sub-step), still
  classify broker response type per `response-taxonomy.md`, then continue through
  fill-slots/save/stop; `shipment` → unchanged v1 two-dimension (issue×response)
  classification and templates. Step 1 (locate case) now points at `scripts/corpus.py`'s
  `merged_best()` (wraps `parse_eml.dedupe_snapshots`, merges across **both**
  `LTL-mail/` + `LTL-mail-2/`) as the preferred way to pick the fullest snapshot. Renumbered
  the remaining steps (3–8) and added two constraints: `triage == skip` mail never reaches
  `issue-to-template-flow.md`'s matrix, and `triage.py` misclassifications get the same
  same-task update-and-log treatment as issue/response taxonomy gaps.
- Matured `knowledge/connections/issue-to-template-flow.md`: added a one-line v2 scope note
  under `## Rule` (the matrix only applies to `billing-dispute`/`shipment`; `skip` mail never
  enters it, having already terminated in `SKILL.md` step 2), and a new
  `### billing-dispute (模板: templates/billing-dispute.md)` section with three real-quote-
  grounded branches: `accepted` ("Priority1 CAN dispute these charges on your behalf within 2
  BUSINESS DAYS", `LTL-mail-2/FFBA BOL# 60112079078.eml`) → thank + ask them to proceed and
  report back; `needs-info` ("please provide packing slip and spec sheet to dispute",
  `LTL-mail-2/Priority1 Variance Update for Shipment 60111754054.eml`; also
  `LTL-mail-2/Variance for BOL 60114679882.eml`) → supply the requested info, honestly noting
  the corpus asks for *supporting documents* rather than the originally-assumed
  reference/date; `declined` (no real reply-to-our-dispute quote exists yet in the corpus —
  all 7 FFBA/variance emails found are broker-initiated first notices — so this branch is
  marked inferred, analogous to `return-reason`'s `declined`) → restate the charge, request
  carrier support docs + ask the dispute path, don't concede. `status: mature` kept.
- Matured `knowledge/concepts/freight/parties-and-roles.md`: added freight terms **FFBA**
  (Free Freight Bill Audit — Priority1's post-shipment audit that can add a pricing variance),
  **out-of-route charge**, **accessorial**, **reweigh/reclass**, **PO#** (receiver's purchase
  order number needed to schedule an appointment delivery — real quote from
  `LTL-mail-2/60112049235.eml`), and **drayage** (container short-haul — out of v2 scope,
  `triage.py` special-cases it to `skip` even though its body literally contains "additional
  charge(s)"), each grounded in a real `LTL-mail-2/` quote. Added new parties to the chain
  table: **Ashton Johnson** (Priority1 Account Executive / sales, `Ashton.Johnson@priority1.com`,
  always `triage == skip`), **`NoReply@Priority1.com`** (automated statement sender, matched by
  `_SKIP_SENDER`), and carrier **Warp** (relays an out-of-route charge and a TONU fee via
  broker Will Jerry). Added a new "v2 additions (`LTL-mail-2/`, 2026-07-09)" section rather
  than editing the pre-existing "Confirmed across the corpus" section, since that section is
  explicitly scoped to the 71-file `LTL-mail/` verification and stating "one carrier named so
  far: AAA Cooper" is still accurate for that scope. `status: mature` kept on both articles.
- Doc-only task, no code/tests changed. Full suite green: `python3 -m pytest -q` → 21 passed
  (unchanged from before this task).
- Files: `.claude/skills/draft-broker-email/SKILL.md`,
  `knowledge/connections/issue-to-template-flow.md`,
  `knowledge/concepts/freight/parties-and-roles.md`, `knowledge/log.md`.

## [2026-07-09] compile | v2 end-to-end validation + doc maturation (task 6, final)

- Full suite green before and after this task: `python3 -m pytest -q` → 21 passed
  (unchanged; doc/demo-only task, no test files touched).
- **End-to-end A (billing-dispute draft):** `LTL-mail-2/FFBA BOL# 60112079078.eml` →
  `scripts/corpus.py`'s `merged_best()` confirms it's the only/largest snapshot for BOL
  `60112079078` → parsed to `cases/60112079078/thread.md` →
  `triage(body, sender) == "billing-dispute"` (real sender `Jalen.Turner@priority1.com`,
  body hits `_BILLING` on "Free Freight Bill Audit"/"pricing variance"/"additional
  charge(s)") → response type `accepted` (real quote: "Priority1 CAN dispute these
  charges on your behalf within 2 BUSINESS DAYS…" — this is in fact the corpus example
  `issue-to-template-flow.md`'s `billing-dispute` → `accepted` branch already cites) →
  drafted via `templates/billing-dispute.md`, written to `cases/60112079078/drafts/1.md`.
  Slots grounded in the real thread table (Carrier "Frontline Freight(FCSY)", Customer
  Quote $545.63, Updated Charge $52.29, reweigh/reclass note) — no invented dollar
  amounts, no `[[MISSING]]` needed, unsent (per skill step 8). `cases/` is gitignored
  (local demo output, not committed).
- **Found during A (documented, not fixed — out of this task's file scope):**
  `extract_ids()`'s PRO regex requires "PRO" adjacent to its digits, so it misses PRO
  numbers rendered in HTML `<table>` layouts (header row and data row separated once
  HTML is stripped to text) — `parsed.pro` came back `[]` for BOL 60112079078 even though
  the real PRO (`3100034`) is present in the body/raw HTML. Manually verified against the
  raw HTML table cell order before using it in the draft (real data, not invented).
  Documented as a "Known corpus quirk" in `eml-parsing.md`.
- **End-to-end B (skip confirmation):** `LTL-mail-2/10% Off Freight Promo LTL, Truckload
  And Expedited.eml` (sender `Ashton.Johnson@priority1.com`, a Priority1 sales/account
  role already documented as always-`skip` in `parties-and-roles.md`) →
  `triage(body, sender) == "skip"` (hits `_SKIP_BODY` on "promotion"/"10% discount"/"new
  shippers"). Confirmed the skill stops at step 2: no `cases/<BOL>/` folder created (the
  mail has no BOL at all), no draft written, no email produced. Recorded as
  `cases/_skip-demo.md` (gitignored, local evidence).
- **Doc maturation ("Planned v2" → built):** `platform-architecture.md` — replaced
  "## Planned v2 (NOT yet built)" with "## v2 (built, 2026-07-09)"; rewrote the
  `Components` list (corpus merge, triage front door added as first-class components,
  template count 10+1), the `Data flow` diagram (now shows the triage branch point), and
  `Error handling`/`Testing strategy` sections to reflect the built triage/merge/
  billing-dispute machinery instead of describing it as a future plan. `eml-parsing.md` —
  added a "Corpus scope (v2, built)" section describing the two-directory merge via
  `scripts/corpus.py`, plus the PRO-extraction-gap quirk found above. `template-system.md`
  — added `billing-dispute` to the slot vocabulary and the template count/convention
  section (11 templates total: 10 shipment + 1 triage-driven billing-dispute; noted it is
  NOT in `corpus_report()`'s subject-slug set and is covered by its own test instead of
  `tests/test_templates.py`'s corpus-based assertion). All three kept `status: mature`,
  `updated: 2026-07-09`.
- **Two Minor fixes (same-task cleanup, per review):**
  1. `issue-taxonomy.md`: corrected the category-count header from "10 类" (which
     undercounted — the table lists 10 shipment slugs + `billing-dispute` = 11) to
     "10 运输类 + `billing-dispute`,合计 11 类".
  2. `SKILL.md`: fixed a real drift bug — step 2's `billing-dispute` bullet had stale step
     numbers ("第 5–7 步" for 填槽/落盘/停下, which are actually steps 6/7/8 after the v2
     TRIAGE step was inserted) and duplicated step 4/5's response-type-classification and
     template-branch-selection mechanics inline, creating ambiguity about whether that
     work happens at step 2 or step 4/5. Trimmed step 2's bullet to state only what's
     skipped (issue-type sub-step) versus kept, with correct step references; step 4's
     `broker response type` bullet is now the single place describing the classification
     mechanics (explicitly applying to both `shipment` and `billing-dispute`); step 5
     references "the response type determined in step 4" instead of restating it. Also
     corrected the stale "10 个 issue slug" count in `## 约束` to "10 个运输类 + …
     合计 11 个" to match issue-taxonomy.md.
- **Anti-drift check:** every `knowledge/concepts/**` and `knowledge/connections/**`
  article's frontmatter is `status: mature`, `updated: 2026-07-09` (verified by grepping
  all files). Matured `knowledge/index.md`: refreshed each article's summary line to
  mention its v2 content and added a new "Code modules" table pointing
  `scripts/corpus.py` / `scripts/triage.py` / `scripts/triage_report.py` /
  `templates/billing-dispute.md` / `SKILL.md` at their governing articles (`index.md` and
  `log.md` themselves carry no frontmatter by design — they are the index/log, not
  concept articles).
- Files touched: `knowledge/concepts/drafting/platform-architecture.md`,
  `knowledge/concepts/drafting/eml-parsing.md`,
  `knowledge/concepts/drafting/template-system.md`,
  `knowledge/concepts/drafting/issue-taxonomy.md`, `knowledge/index.md`,
  `.claude/skills/draft-broker-email/SKILL.md`, `knowledge/log.md`. Also produced (not
  committed, gitignored): `cases/60112079078/thread.md`,
  `cases/60112079078/drafts/1.md`, `cases/_skip-demo.md`.

## [2026-07-09] compile | final whole-branch review fixes (v2)

- Final review (opus) found an Important issue: `merged_best()`/`dedupe_snapshots` keys on BOL
  alone and returns one file, but ~24/141 BOLs host TWO distinct threads (a shipment thread +
  a separate billing/FFBA thread, e.g. 60114592263, 60112135944) — so it silently drops the
  other-topic thread, and the matured docs asserted a false "same-thread snapshots" model.
- Applied cheap guardrails: corrected `dedupe_snapshots` docstring, `eml-parsing.md`,
  `platform-architecture.md` to document the two-threads-per-BOL caveat; added a ⚠️ warning to
  `SKILL.md` step 1 (parse the specific referenced .eml for a named topic, esp. billing; don't
  blindly trust merged_best). Fixed the Minor billing `accepted`-branch wording (drop the
  already-answered "can Priority1 dispute" clause).
- DEFERRED (needs a design decision): the real fix — dedupe keyed on (BOL + subject-family) or
  merged_best returning all distinct threads per BOL. Tracked for a follow-up.
- Triage of other recorded minors: whole-body triage kept (load-bearing for drayage; zero real
  shipment issue skipped); PRO-in-HTML-table gap deferred (fails safe to [[MISSING]]).
- 21 tests green. Files: `scripts/parse_eml.py`, `knowledge/concepts/drafting/eml-parsing.md`,
  `knowledge/concepts/drafting/platform-architecture.md`,
  `.claude/skills/draft-broker-email/SKILL.md`,
  `knowledge/connections/issue-to-template-flow.md`, `knowledge/log.md`.

## [2026-07-09] decision | merged_best redesign CLOSED (won't-fix)

Reconsidered the deferred `merged_best()` subject-family redesign against how the corpus is
actually used, and closed it as **won't-fix**. Reasoning:

- **Classification & template-building iterate ALL files, not `merged_best()`.** `corpus_report.py`
  uses `glob("*.eml")` and `triage_report.py` uses `list_corpus()` — every file (both the
  shipment thread and the billing thread of a shared BOL) is classified independently. The
  two-threads-per-BOL behavior does not affect taxonomy/triage/template derivation at all.
- **`merged_best()` is used only at runtime** (`SKILL.md` step 1) as a convenience to auto-locate
  an archived thread by BOL, plus one unit test. In live use the input is the actual incoming
  `.eml`/pasted message being replied to — not an archive lookup — so the mis-pick can't silently
  drop a real reply. The existing SKILL.md step-1 ⚠️ guardrail (parse the specific referenced
  `.eml` for a named topic, especially billing) fully covers the residual convenience case.
- Net: the redesign would add dedupe complexity for no build-time benefit and a runtime benefit
  the guardrail already provides. The documented caveats in `eml-parsing.md` /
  `platform-architecture.md` and the SKILL.md guardrail remain (they are accurate and useful);
  only the code redesign is closed.

## [2026-07-10] compile | engine/ build (tasks 1-6) + drafting-engine knowledge article (EN+ZH)

- Built the headless `engine/` package described in
  `docs/superpowers/specs/2026-07-10-broker-app-system-design.md` §8/§12 (Phase 0/1
  slice), across six tasks, reusing `scripts/` unchanged throughout:
  1. **`engine/llm.py`** — `LlmDraft` dataclass, `LlmClient` Protocol, `FakeLlmClient`
     (deterministic `{slot}` substitution stub).
  2. **`engine/drafting.py`** — `DraftRequest`/`DraftResult` + `draft()` orchestrator:
     triage (`scripts/triage.py`) → classify (`scripts/corpus_report.py`, `shipment`
     only; `billing-dispute` fixes template by triage itself; `skip` short-circuits) →
     `load_template` → LLM fill → validate.
  3. **`engine/validate.py`** — anti-fabrication `validate_draft`/`FACTUAL_SLOTS`
     (`BOL, PRO, pro, pickup_address, new_address, contact_phone, delivery_date,
     charge_ref`); untraceable factual values are redacted to `[[MISSING: key]]`; a
     follow-up fix added `Validated.warnings` so an untraceable value that can't even
     be found verbatim in the draft body (redact is a no-op) produces a warning instead
     of a silent pass.
  4. **`tests/test_corpus_regression.py`** — locks the real, measured triage
     distribution over the merged 922-file corpus: `{skip: 327, billing-dispute: 60,
     shipment: 535}`, `unknown_shipment: 203`; plus a three-case end-to-end replay
     through `draft()` (billing-dispute / skip / shipment).
  5. **`engine/llm.py`: `GeminiLlmClient`** — real adapter (`gemini-2.5-flash`,
     `google-genai`), structured-JSON prompt repeating the anti-fabrication
     instruction; guarded by `tests/test_gemini_client.py`
     (`skipif no GEMINI_API_KEY` — the one skipped test in the suite).
  6. **This task** — added `knowledge/concepts/drafting/drafting-engine.md` (EN) and
     `drafting-engine.zh.md` (ZH), per the dual-language rule for design/plan/knowledge
     docs. Content: the `engine/` package (port + Fake/Gemini clients), the six-stage
     `draft()` pipeline, the `FACTUAL_SLOTS` anti-fabrication rule and the `warnings`
     fail-loud mechanism (documented explicitly as "untraceable factual value that
     can't be redacted → warning, never silent success"), that it reuses `scripts/`
     unchanged, the locked corpus-regression distribution, and that this is the first
     built slice of `docs/superpowers/specs/2026-07-10-broker-app-system-design.md`.
     Also honestly documented one open gap found while writing the article:
     `DraftResult` does not yet expose `Validated.warnings` to callers of `draft()` —
     no test currently asserts it — flagged as a follow-up before the engine is wired
     into the app-spec backend (a warning must reach the agent console, not just a log
     line).
- Frontmatter for both new articles validated against
  `schemas/article-frontmatter.schema.json` (required fields present; `type: concept`;
  `status: mature`; `updated: 2026-07-10`; no keys outside the schema's allowed set) via
  a scratch validator script (no `jsonschema`/`pyyaml` installed in this environment).
- Updated `knowledge/index.md`: added both articles to the "Drafting system" table, and
  added `engine/llm.py` / `engine/validate.py` / `engine/knowledge.py` /
  `engine/drafting.py` to the "Code modules" table, each pointing at
  `drafting-engine.md`.
- Full suite green: `python3 -m pytest -q` → 32 passed, 1 skipped (Gemini, no API key
  in this environment) — unchanged by this doc-only task.
- Files touched: `knowledge/concepts/drafting/drafting-engine.md`,
  `knowledge/concepts/drafting/drafting-engine.zh.md`, `knowledge/index.md`,
  `knowledge/log.md`.

## [2026-07-10] compile | DraftResult surfaces Validated.warnings

- Closed the known gap: `engine/drafting.py`'s `DraftResult` gained a `warnings:
  list[str] = []` field, and `draft()` now passes `warnings=v.warnings` through, so the
  anti-fabrication fail-loud signal reaches callers instead of being dropped. Added
  `test_draft_surfaces_validator_warnings` (`tests/test_engine_drafting.py`) using a
  stub LLM that reformats a factual value to simulate real-LLM drift, proving the
  `warnings` path (not just `rejected`) propagates. Updated both
  `drafting-engine.md`/`drafting-engine.zh.md` known-gap notes accordingly. Full suite:
  `python3 -m pytest -q` → 33 passed, 1 skipped.

## [2026-07-10] review | drafting-engine final whole-branch review

- Final review (opus): no Critical; mergeable as-is for the headless slice (no auto-send,
  human-approval gate downstream, scripts/ provably unchanged, 33 tests + 1 skipped, real
  regression values locked).
- One Important (documented, deferred to before the live Gemini path): validate_draft is
  filled_slots-scoped — a fact the LLM writes into prose without reporting it bypasses the
  gate. Corrected both drafting-engine articles to stop overstating the invariant as fully
  "mechanical" and to record the follow-ups.
- Follow-ups BEFORE GeminiLlmClient is wired into a real drafting path: (1) prose scan for
  BOL/PRO shapes in body absent from source_text → warning; (2) token-boundary matching
  (substring false-positive: a fabricated value that is a substring of a real one is currently
  accepted); (3) GeminiLlmClient JSON-decode/empty-response hardening; (4) FakeLlmClient
  empty-string/dup-missing polish; (5) load_template missing-file + skeleton-last-section guard.
- Files: `knowledge/concepts/drafting/drafting-engine.md` + `.zh.md`, `knowledge/log.md`.

## [2026-07-10] compile | domain identity/relationship core (app Slice 2)

- New `app/` backend package (stdlib sqlite3, dependency-free): `db.py` (schema+connection),
  `models.py` (dataclasses), `repo.py` (orgs/users/memberships/engagements/brokers/broker-accounts),
  `access.py` (relationship-scoped access).
- Multi-sided identity per the app spec: typed orgs (customer|agent), invite/approve engagements
  (customer↔agent), agent broker-accounts (agent↔broker) with mailbox → `agent_for_mailbox()`.
- Relationship-scoped access with cross-engagement isolation tests (the security boundary).
- 11 new tests; full suite green. EN-only doc (headless-phase directive):
  `knowledge/concepts/app/identity-model.md`. Cases/state-machine/inbound-router = Slice 3.

## [2026-07-10] compile | case core + state machine + inbound router (app Slice 3)

- `app/cases.py`: cases/messages/audit_log; guarded `transition()` (illegal → ValueError, no
  audit); `approve_message` is the ONLY path to sent/posted; edit/reject; `audit_trail`
  ordered by rowid (CURRENT_TIMESTAMP too coarse).
- `app/router.py`: `open_customer_case` (active engagement → EN broker draft, pending_approval)
  and `ingest_broker_email` (parse→triage: skip creates nothing / match-by-thread / new
  unattributed broker case; agent resolved via `agent_for_mailbox`, unknown mailbox raises).
- `app/access.user_may_access_case` (agent-org member always; customer only via active
  engagement) — isolation-tested.
- 12 new tests; full suite green. EN doc `knowledge/concepts/app/case-workflow.md`.
- Deferred: customer-facing ZH posting (needs engine summarize→ZH), broker-initiated customer
  attribution by BOL.

## [2026-07-10] fix | case-core review findings (Slice 3)

- CRITICAL fixed: approval actions (approve/reject) now validate the case transition BEFORE
  mutating the message, and wrap both writes in one commit with rollback-on-error — a failed
  action no longer silently flips a message to sent/posted with no audit.
- Router: matched-thread branch returns a FRESH Case (was stale); new-case branch adds the
  pending draft BEFORE transitioning to PENDING_APPROVAL.
- edit_message now preserves the prior body in a new audit `detail` column.
- Tests added: atomic-failed-approve regression, matched-thread reply path, edit-records-prior-body,
  full lifecycle → CLOSED. Doc flags thread_id as caller-supplied (header derivation deferred).

## [2026-07-10] compile | headless backend capstone (end-to-end)

- `tests/test_e2e_headless.py`: full loop on real corpus data — identity setup → ingest a real
  FFBA broker email → broker-initiated case + pending draft → agent approves → sent + audit;
  plus customer-initiated pickup → edit → approve. Deterministic (FakeLlmClient).
- `knowledge/concepts/app/headless-backend.md`: overview tying engine + identity + case core,
  the guarantees, and the built-vs-deferred list. Headless backend core is functionally complete.

## [2026-07-10] compile | JSON HTTP API server (app Slice 4)

- `app/api.py`: pure `dispatch(req, *, conn, llm, webhook_secret) -> Response` (routing, auth,
  access, JSON) — the tested surface. Endpoints: POST /cases, GET /cases, GET /cases/{id},
  GET /cases/{id}/audit, POST /cases/{id}/messages/{mid}/{approve,edit,reject}, POST /inbound.
- Auth boundary: user routes require `X-User-Id` (upstream-authenticated) + enforce app.access;
  /inbound uses `X-Webhook-Secret` (constant-time). Domain ValueError → 409; access → 403.
- `app/server.py`: thin stdlib ThreadingHTTPServer shell (fresh conn per request).
- 7 tests (6 dispatch + 1 live-socket smoke); full suite 72 passed, 1 skipped. Doc:
  `knowledge/concepts/app/api.md`. Approval remains the only send/post path.

## [2026-07-10] fix | API robustness (malformed-request crash paths)

- Review Critical fixed: authenticated malformed requests no longer crash. `dispatch` rejects
  non-object JSON bodies with 400; `_inbound` catches TypeError/OSError (bad/missing/unreadable
  eml path) → 400; `server.py` wraps `dispatch` in try/except → controlled 500 (no stack leak,
  no dead thread). +1 regression test (test_malformed_requests_are_400_not_crashes). 73 passed.

## [2026-07-10] compile | real Gemini + Gmail transport wiring (app Slice 5)

- `app/transport.py`: MailTransport port + FakeTransport (tested) + guarded GmailTransport
  (deferred google imports; RFC-822 + In-Reply-To/References threading).
- Send-on-approval: `app/api._approve_and_maybe_send` sends a broker email via the transport
  on approval, stamps `messages.mail_message_id` + `cases.mail_thread_id`, advances to
  AWAITING_BROKER. Missing recipient/transport/illegal → 409, nothing sent. Thread continuity
  proven: reply on that thread matches the same case.
- Added `broker_accounts.broker_email` (broker's TO address; distinct from routing `mailbox`).
- `app/config.py`: make_llm()/make_transport() select real Gemini/Gmail when GEMINI_API_KEY /
  GMAIL_TOKEN_FILE set, else fakes; server.serve() builds from config. Env unset → fakes.
- +7 tests; full suite 79 passed, 1 skipped. Doc: knowledge/concepts/app/transport-and-config.md.

## [2026-07-10] fix | Slice 5 review fast-follows (send-path atomicity + logging)

- Made send-on-approval bookkeeping atomic: send first (raise → nothing written), then
  message→sent + SENT_TO_BROKER→AWAITING_BROKER + mail/thread stamps in ONE transaction w/
  rollback (no more 3-commit stranding window). Guarded empty from_addr (→409). server.py logs
  the traceback before a controlled 500. +1 regression test (send-failure-leaves-state-untouched).
  80 passed, 1 skipped. (Deferred: retry/backoff, in_reply_to capture, real-creds Gmail test.)

## [2026-07-10] wire | real Gemini verified live + .env loading

- Added dependency-free `config.load_env()` (.env → os.environ, real env wins; `.env` gitignored).
- `GeminiLlmClient.MODEL` → `gemini-flash-latest` (stable alias; `gemini-2.5-flash` retired for
  new accounts). VERIFIED LIVE with the real key: ZH WeChat request → EN broker clause; and
  `config.make_llm()` auto-selects Gemini when the key is present.
- `google-genai` is not a system/CI dependency (fakes cover tests); use a gitignored `.venv`
  for real runs. Full suite stays hermetic on system python: 81 passed, 1 skipped.
- Secret hygiene: `.env` and `.venv` added to `.gitignore`; neither tracked/staged.

## [2026-07-10] fix | real-Gemini live-run findings (drafting quality)

Running the full stack against REAL Gemini (not the fake) surfaced 3 correctness bugs the
FakeLlmClient masked; all fixed + tested:
- **Wrong template:** customer-declared issue type was thrown away — open_customer_case
  synthesized a "delivery-window --- …" subject that classify_issue (matches "delivery window",
  space) couldn't map, falling back to pickup. Added `DraftRequest.issue_override`; the customer
  path now honors the picked type. Unknown/`other` slug → safe pickup fallback (template-exists guard).
- **BOL dropped as [[MISSING]]:** trusted structured facts (BOL/PRO from the form) weren't in
  source_text, so the anti-fabrication validator rejected them. open_customer_case now folds
  facts into source_text.
- **Broken signoff:** `{shipper_signoff}` was left to the LLM (→ [[MISSING]]). Now injected
  deterministically from `engine.knowledge.SHIPPER_SIGNOFF` (single-agent default; per-agent
  override later).
- Verified live: ZH ("6号中午前直送，不用预约") → EN delivery-window draft, BOL+PRO filled,
  signoff present. 85 passed, 1 skipped.

FOLLOW-UP (logged, human-gate covers it): Gemini sometimes derives the greeting from the
customer's informal address to the AGENT ("老黄" → "Hi Lao Huang") instead of the broker
contact/"team". Needs a prompt refinement + broker-contact resolution (default "team" when unknown).

## [2026-07-10] fix | broker-contact greeting hallucination (resolved)

- Root cause: `{broker_contact}` was an unconstrained slot the LLM filled from the customer's
  text (e.g. "老黄" → "Hi Lao Huang"). Fix: pre-substitute `{broker_contact}` server-side in
  `draft()` BEFORE the LLM (resolved name, default "team"), + a `_SYSTEM` prompt telling the
  model not to change the greeting or invent names. Router may pass a resolved name via
  facts["broker_contact"] (future broker-contact resolution); default "team" for now.
- Verified live: same input now greets "Hi team,". +2 tests. 87 passed, 1 skipped.
- (drafting-engine.zh.md not updated — headless-phase EN-only per directive.)

## [2026-07-11] compile | agent console (frontend Slice 6)

- First frontend: `web/agent/index.html` — dependency-free self-contained HTML + vanilla JS
  (bilingual), a thin client over the JSON API (login via X-User-Id, case list/detail, editable
  pending draft, approve/edit/reject, audit). `app/server.py` serves it at GET / (favicon→204;
  other paths → JSON dispatch). All rules stay server-side; data HTML-escaped (XSS-safe).
- VERIFIED in a real browser (Playwright): op logs in → opens seeded case → Approve & send →
  message 'sent', case → AWAITING_BROKER in the UI. + served-HTML smoke (tests/test_console.py).
  88 passed, 1 skipped. Dual-language doc: knowledge/concepts/app/agent-console.md (+ .zh.md).
- Next frontends (customer WeChat Mini Program + responsive web) need their own toolchains.

## [2026-07-11] fix | agent-console review findings (XSS hardening + classification surface)

- esc() now escapes quotes too; applied to all attribute/JS-string interpolations (onclick IDs)
  — closes a latent stored-XSS pattern (inert today since IDs are uuids).
- Surfaced the pending draft's classification (triage/issue/template) + a highlighted Missing
  list + warnings panel (from message.classification) — the plan's requirement; removed the dead
  markMissing() (a textarea can't render HTML). Browser-verified the panel renders.
- Empty-draft guard: approve/edit abort with "draft is empty" instead of sending a blank email.
- 88 passed, 1 skipped.

## [2026-07-11] compile | customer web + intake form engine (frontend Slice 7)

- `app/forms.py`: schema-driven intake form engine (FORM_SCHEMAS per issue slug; field names ==
  template slots; issue_types()). Single source of truth; adding a type is a data change.
- API: GET /issue-types, GET /engagements (customer's active engagements + agent's brokers,
  scoped), POST /cases gains optional `fields` → open_customer_case(fields=) merges into
  facts+source_text (field flows into the draft).
- `web/customer/index.html` served at /customer (server generalized to a web_root + route map,
  agent console stays at /): login, My cases (friendly Chinese status, no English bodies),
  New case (agent/broker/issue selects → dynamic category fields → submit). XSS-escaped.
- VERIFIED in a real browser (Playwright): customer logs in → New case → Delivery window →
  fill requested_window + BOL → submit → case shows as "代理审核中"; drafted broker email
  contains the submitted window. 93 passed, 1 skipped. Dual-language doc: customer-web.md(+.zh).
- Deferred: customer-facing ZH summaries (engine summarize→ZH); WeChat Mini Program.

## [2026-07-11] fix | customer-web review findings (fields forgery + cross-agent broker)

- CRITICAL fixed: `fields` are now whitelisted to the chosen issue type's FORM_SCHEMAS field
  names in open_customer_case — a client can no longer override the trusted BOL/PRO (never in a
  schema) or inject off-schema factual slots (charge_ref, …) that would tautologically pass the
  anti-fabrication validator. Legit schema fields (customer's own request details) still flow.
- Important fixed: open_customer_case validates broker_account_id belongs to the engagement's
  agent org (was a cross-agent leak, now reachable via GET /engagements) → 400 otherwise.
- Important fixed: added ISSUE_LABELS["pro-lookup"] so the customer menu offers it.
- Minor: dropped double-esc() on customer textContent error assignments.
- +2 regression tests (forged fields dropped; cross-agent broker rejected). 95 passed, 1 skipped.

## [2026-07-11] compile | engine summarize→ZH + customer ZH updates (Slice 8)

- `LlmClient.summarize(text,target_lang,context)` added to the port (Fake deterministic; Gemini
  real, faithful plain-text). `engine.drafting.summarize_for_customer`.
- `app/router.ingest_broker_email`: matched-thread broker reply now creates a customer-facing
  ZH message (channel=app, lang=zh, pending_approval) via summarize + advances to
  PENDING_APPROVAL. Agent approves → POSTED_TO_CUSTOMER.
- Customer app: clickable case → shows posted app/zh updates (never English drafts).
- VERIFIED LIVE (real Gemini): out-of-route broker email → faithful ZH summary (kept address +
  $55.56 fee) → agent-approved → shown in the customer app (browser-confirmed). 97 passed, 1 skipped.
- Docs: knowledge/concepts/drafting/summarize.md (+ .zh); customer-web deferred note → built.

## 2026-07-11 — Slice 8 review fix: server-side customer message filtering
- Review (sonnet) flagged: "customer only sees approved ZH" was frontend-only; GET /cases
  returned raw internal English broker mail to any customer caller.
- Fix: `app/api._get_case`/`_create_case` now compute an `agent_view` role check; `_messages`
  withholds all but `channel=app, lang=zh, status=posted` from customer-side callers. The API
  never emits internal English drafts / received broker mail to the customer.
- Added guarded live-Gemini `summarize` test + server-side-filter regression test.
- summarize.md/.zh + router docstring corrected to state server-side enforcement.
- Merged feat/summarize-zh → main (--no-ff, aa7908b). 98 passed, 2 skipped.

## 2026-07-11 — New article: WeChat Mini Program frontend + auth (thin, reference)
- Added `concepts/app/wechat-miniprogram.md` (+ `.zh`): captures the Mini Program as the
  future customer frontend BEFORE building it — dual-thread (render/logic + WeixinJSBridge)
  architecture, ecosystem (accounts/review/distribution), networking allowlist constraint
  (collides with US data residency), Subscription Messages for push, and the load-bearing
  `wx.login → code2Session → openid/unionid` auth flow that fills the deferred "real WeChat
  login is a gateway concern" (api.md). status=thin, load_bearing=true (auth).
- Indexed under "App backend"; added a row to CLAUDE.md article-mapping table.
- Capture-first: documents a not-yet-built frontend so the auth adapter is designed against
  reality; no code changed.
