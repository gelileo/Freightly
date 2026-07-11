---
title: Summarize→ZH (customer updates)
type: concept
area: drafting
updated: 2026-07-11
status: mature
affects:
  - engine/llm.py
  - engine/drafting.py
  - app/router.py
references:
  - concepts/drafting/drafting-engine.md
  - concepts/app/case-workflow.md
  - concepts/app/customer-web.md
---

# Summarize→ZH (customer updates)

Slice 8: turns a broker's English reply into a faithful **Chinese** customer update. Closes the
previously-deferred "customer-facing ZH posting" gap.

## Capability (`engine/llm.py`)

`LlmClient.summarize(*, text, target_lang, context="") -> str` — a distinct LLM operation from
`generate` (which fills templates). `FakeLlmClient.summarize` is deterministic
(`"[summary->{lang}] " + first line`) for tests; `GeminiLlmClient.summarize` prompts Gemini to
produce a short, **faithful** message (no invented facts) and returns plain text.
`engine.drafting.summarize_for_customer(broker_text, llm, target_lang="zh")` is the thin wrapper
(faithful-relay instruction).

## Wiring (`app/router.py`)

On a **matched-thread broker reply**, `ingest_broker_email` appends the `received` broker message
and creates a **customer-facing message** (`party=agent, channel=app, lang=zh,
status=pending_approval`) holding the summary, then advances the case to `PENDING_APPROVAL`.
(Broker-*initiated* new cases still draft an English broker reply.)

## Approval gate & display

The ZH summary is `pending_approval` — the agent approves (or edits/rejects) it in the console;
approving an app-channel message posts it (`POSTED_TO_CUSTOMER`). The **customer app**
(`/customer`) shows only `channel=app, lang=zh, status=posted` messages as the update feed —
never the internal English drafts. So the customer sees only agent-approved Chinese updates.

## Verified live

Real Gemini summarized an out-of-route-charge broker email into Chinese (kept the redirect
address and the $55.56 fee), the agent approved it, and the **customer app displayed the Chinese
update** — confirmed end-to-end in a real browser. Fakes keep CI hermetic
(`tests/test_engine_llm.py`, `tests/test_router.py`).

## Notes / follow-ups

Summaries are faithful-instructed and human-gated (edit/reject in the console) — the gate is the
backstop, as summaries aren't run through the factual-slot validator. A future refinement could
add light fact-checking of amounts/dates in the summary against the source.
