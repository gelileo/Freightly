---
title: Drafting Engine
type: concept
area: drafting
updated: 2026-07-10
status: mature
affects:
  - engine/**
references:
  - concepts/drafting/platform-architecture.md
  - concepts/drafting/issue-taxonomy.md
  - concepts/drafting/template-system.md
load_bearing: true
---

# Drafting Engine

中文版: [drafting-engine.zh.md](drafting-engine.zh.md).

## Purpose

`engine/` is a headless, dependency-injected Python package that turns a parsed `.eml`
(or a pasted message) into a validated draft, without any network call, any file I/O
beyond reading `templates/*.md`, or any UI. It exists so the drafting logic that was
previously only reachable through the `.claude/skills/draft-broker-email` skill can be
called directly and tested deterministically — the same code path a future backend
service (see "Relation to the app spec" below) will call for real.

It is a pure orchestration layer: it does not reimplement triage, issue classification,
or templates. It imports `scripts/triage.py`'s `triage()` and
`scripts/corpus_report.py`'s `classify_issue()` unchanged, and reads the same
`templates/<slug>.md` skeletons the skill uses. The only new code is the LLM boundary
(a port + two adapters), the anti-fabrication validator, and the glue function `draft()`
that sequences all of it.

## Components

- **`engine/llm.py`** — the LLM boundary.
  - `LlmDraft` — dataclass: `lang: str`, `body: str`, `filled_slots: dict[str, str]`,
    `missing: list[str]`. The uniform shape every `LlmClient` implementation returns.
  - `LlmClient` — a `Protocol` with one method, `generate(*, system, template, facts,
    source_text, target_lang) -> LlmDraft`. `draft()` (below) depends only on this
    Protocol, never on a concrete client, so tests never touch the network.
  - `FakeLlmClient` — deterministic stub used by all engine tests. It does simple
    `{slot}` substitution from `facts` (regex `\{(\w+)\}`); any slot with no matching
    fact becomes `[[MISSING: slot]]` in the body and is added to `missing`. It performs
    no real translation — just enough behavior to exercise the orchestration and
    validation logic without an LLM call.
  - `GeminiLlmClient` — the real adapter (`gemini-2.5-flash`, via the `google-genai`
    SDK). Requires `GEMINI_API_KEY`; builds a prompt that repeats the anti-fabrication
    instruction ("use ONLY these facts for factual slots… leave unknown factual slots as
    `[[MISSING: key]]`"), requests structured JSON
    (`{"lang","body","filled_slots","missing"}`), and maps the response onto `LlmDraft`.
    Exercised only by `tests/test_gemini_client.py`, which is
    `@pytest.mark.skipif(not os.environ.get("GEMINI_API_KEY"), ...)` — it is the one test
    in the suite that is skipped by default (32 passed, 1 skipped) and only runs with a
    real key present.

- **`engine/validate.py`** — the anti-fabrication gate. See "Anti-fabrication" below.

- **`engine/knowledge.py`** — `load_template(slug)` reads `templates/<slug>.md` and
  returns the text under its `## Skeleton` heading (regex-extracted, stops at the next
  `## `). Deliberately thin: this slice reads templates straight off disk exactly like
  the skill already does. The versioned, per-agent-override Knowledge service described
  in the app spec (§8, "Phase 0") is a later, separate piece of work — this module is
  the placeholder it will eventually replace.

- **`engine/drafting.py`** — the orchestrator. See "The `draft()` pipeline" below.

## The `draft()` pipeline

`draft(req: DraftRequest, llm: LlmClient) -> DraftResult` runs six stages in order:

```
triage → classify → template → fill (LLM) → validate
```

1. **Triage** — `triage(req.body, req.sender)` from `scripts/triage.py` returns one of
   `"skip" | "billing-dispute" | "shipment"`.
   - `"skip"` short-circuits immediately: `DraftResult(triage="skip", issue="",
     template_slug="", draft_lang="", draft_body="")` — no template is loaded, no LLM
     call is made, nothing is written. This mirrors the skill's rule that non-actionable
     mail never gets a case folder or a draft.
2. **Classify** (only for `"billing-dispute"` / `"shipment"`):
   - `"billing-dispute"` fixes both `issue` and the template slug to
     `"billing-dispute"` — triage itself has already decided the category, so there is
     no separate classification sub-step (matches `platform-architecture.md`'s v2 flow).
   - `"shipment"` calls `classify_issue(req.subject)` from `scripts/corpus_report.py`. If
     it returns `"uncategorized"` the engine falls back to the `"pickup"` template slug
     as a safe default so the pipeline never dead-ends — the code comment calls this out
     explicitly ("safe default; agent can correct") since it is a deliberate compromise,
     not a claim that the mail is actually about pickup. Real-world subjects that
     `classify_issue` can't sub-route are exactly the `unknown_shipment` bucket measured
     by the regression harness below (203/535).
3. **Template** — `load_template(slug)` (`engine/knowledge.py`) reads the chosen
   `templates/<slug>.md` skeleton.
4. **Fill (LLM)** — `llm.generate(system="", template=template, facts=req.facts,
   source_text=req.source_text, target_lang=req.target_lang)` produces a raw `LlmDraft`.
   `req.facts` carries the deterministic, caller-supplied values (BOL, PRO, addresses,
   etc.) — the engine never asks the LLM to invent these; it asks it to *use* them.
5. **Validate** — `validate_draft(raw, source_text=req.source_text)` (see below) checks
   every factual slot the LLM claims to have filled against the source text and rewrites
   untraceable ones to `[[MISSING: key]]`.
6. **Result** — `DraftResult(triage=t, issue=issue, template_slug=slug,
   draft_lang=raw.lang, draft_body=v.body, missing=v.missing,
   rejected_slots=v.rejected, warnings=v.warnings)`.

`DraftRequest` fields: `body, sender, subject, facts: dict[str,str] = {}, source_text:
str = "", target_lang: str = "en"`.

**Fail-loud signal reaches callers:** `DraftResult` carries a `warnings: list[str] = []`
field, populated from `Validated.warnings` (see below). A caller of `draft()` no longer
needs to call `validate_draft()` directly to see the fail-loud warning — it is part of
the return value, ready to be surfaced in an approval UX (e.g. the agent console) rather
than only living in a log line. `tests/test_engine_drafting.py::test_draft_surfaces_validator_warnings`
asserts this propagation using a stub LLM that reformats a factual value so it isn't a
verbatim substring of the draft body (simulating real-LLM formatting drift), forcing the
`warnings` path rather than the `rejected`/redaction path.

## Anti-fabrication: `FACTUAL_SLOTS` and the `warnings` fail-loud mechanism

The single most important invariant this engine enforces (carried from the human-review
convention in `platform-architecture.md`, now made mechanical): **the LLM is never
trusted to state a fact that isn't verifiably present in the source text.**

`engine/validate.py` defines:

```python
FACTUAL_SLOTS: set[str] = {
    "BOL", "PRO", "pro", "pickup_address", "new_address", "contact_phone",
    "delivery_date", "charge_ref",
}
```

`validate_draft(raw: LlmDraft, *, source_text: str) -> Validated` walks
`raw.filled_slots`. For every slot whose key is in `FACTUAL_SLOTS`, if the value the LLM
claims is not a verbatim substring of `source_text`, it is **rejected**:

- the key is appended to both `rejected` and `missing`,
- every occurrence of the fabricated value in the draft body is replaced with
  `[[MISSING: key]]`.

Slots outside `FACTUAL_SLOTS` (e.g. `customer_request` — language, not a fact) are never
policed this way; only claims about identifiable real-world facts are checked.

**The `warnings` fail-loud mechanism.** Redaction by string-replace has one failure mode:
if the fabricated value the LLM reported in `filled_slots` isn't actually present
verbatim in the draft `body` (e.g. it reformatted "99999999999" differently in the
prose), `body.replace(val, ...)` is a no-op — the body is returned unchanged, still
containing an untraceable fact, but with no `[[MISSING]]` marker to flag it. Silently
returning that body would be worse than doing nothing: it looks like a clean pass. So
`validate_draft` explicitly checks `new_body == body` after the replace attempt; if
nothing changed, it appends a message to `Validated.warnings` (e.g. `"unredacted factual
slot 'BOL': value not found verbatim in draft body — manual review required"`) instead
of silently succeeding. The rule, stated generally: **an untraceable factual value that
cannot be redacted must produce a warning, never a silent success.**

`Validated` fields: `body: str, missing: list[str] = [], rejected: list[str] = [],
warnings: list[str] = []`.

## Reuses `scripts/` unchanged

`engine/drafting.py` imports `scripts.triage.triage` and
`scripts.corpus_report.classify_issue` directly — no wrapper, no re-implementation, no
behavior change. This is deliberate: the triage/classification rules and their measured
corpus-wide behavior are the load-bearing, already-validated part of the system
(`concepts/drafting/issue-taxonomy.md`); the engine's job is only to sequence them behind
a clean function signature. Any future change to triage/classification rules
automatically flows through to `draft()` without a code change here.

## Corpus regression harness

`tests/test_corpus_regression.py` is the ground-truth lock for this engine, replaying
the full merged 922-file corpus (`LTL-mail/` + `LTL-mail-2/`) through
`scripts/triage_report.py`'s `triage_report()`:

```python
def test_triage_distribution_locked():
    r = triage_report()
    assert r["counts"] == {"skip": 327, "billing-dispute": 60, "shipment": 535}
    assert len(r["unknown_shipment"]) == 203
```

These numbers are the same real, measured distribution recorded in
`issue-taxonomy.md`'s "v2 triage 分布" section — this test exists so any future change
to `scripts/triage.py`'s rules that shifts the corpus-wide distribution is caught
immediately, rather than discovered later against production traffic. The 922-file
total is 71 (`LTL-mail/`) + 851 (`LTL-mail-2/`).

The same file also has `test_engine_replays_known_cases()`, which runs three
representative real `.eml` files end to end through `draft()` (not just `triage()`) and
asserts the expected `DraftResult.triage` for each:

| File | Expected `triage` |
| --- | --- |
| `LTL-mail-2/FFBA BOL# 60112079078.eml` | `billing-dispute` |
| `LTL-mail-2/10% Off Freight Promo LTL, Truckload And Expedited.eml` | `skip` |
| `LTL-mail/Re_ pickup --- 60114338678.eml` | `shipment` |

Together, the locked distribution assertion and the three replayed cases are the
regression harness the app spec (§10, Phase 1) refers to when it says the headless
drafting backend is "uniquely validated against ground truth by replaying the 922
historical emails."

## Relation to the app spec

This engine is **the first built slice** of
`docs/superpowers/specs/2026-07-10-broker-app-system-design.md` (and its
`.zh.md` twin). That spec's §8 ("Drafting engine internals") describes the same
pipeline shape — `TRIAGE → CLASSIFY → SELECT template → FILL → GENERATE → VALIDATE →
PERSIST` — as a backend service; `engine/drafting.py`'s `draft()` implements everything
up to `VALIDATE` today, headless and without the `PERSIST` step (there is no case store,
no `pending_approval` state, no agent console yet — see "Out of scope" below). The spec's
§12 ("Reuse from `hs`") explicitly names `scripts/triage.py` and
`scripts/corpus_report.py` as directly reused; this engine is where that reuse is wired
into an importable, testable function rather than only being reachable through the
`draft-broker-email` skill's manual flow.

## Testing strategy

`python3 -m pytest -q` → 33 passed, 1 skipped (the guarded live-Gemini test, skipped
without `GEMINI_API_KEY`). Test files covering `engine/`:

- `tests/test_engine_llm.py` — `FakeLlmClient` slot-fill/`[[MISSING]]` behavior.
- `tests/test_engine_validate.py` — the five anti-fabrication/warning cases described
  above.
- `tests/test_engine_drafting.py` — `draft()`'s three routing branches (skip / billing /
  shipment) with `FakeLlmClient`.
- `tests/test_corpus_regression.py` — the locked corpus-wide distribution and the
  three-case replay through `draft()`.
- `tests/test_gemini_client.py` — guarded, real-network integration test for
  `GeminiLlmClient`.

## Out of scope (this slice)

Deferred to later phases of the app spec, not part of `engine/` today:

- Persistence (no `Case`/`Message` DB tables; `DraftResult` is an in-memory value).
- Identity & relationship model (users, orgs, engagements, broker accounts).
- Mail transport (sending/receiving over a real mailbox).
- The agent console (approval queue, review UX).
- The versioned, per-agent-override Knowledge service (`engine/knowledge.py` is the
  disk-reading placeholder it will replace).
