---
title: Headless Backend Overview
type: connection
area: app
updated: 2026-07-10
status: mature
references:
  - concepts/app/identity-model.md
  - concepts/app/case-workflow.md
  - concepts/drafting/drafting-engine.md
---

# Headless Backend Overview

The app's backend, built and tested with **no UI, no network, no third-party deps** (stdlib
sqlite3 + the stdlib drafting engine; Gemini behind a guarded port). It turns the drafting
brain (`engine/`) + identity (`app/` Slice 2) + case workflow (`app/` Slice 3) into a complete,
approval-gated case pipeline.

## The loop (proven end-to-end in `tests/test_e2e_headless.py`)

```
identity: org(customer) --active engagement--> org(agent) --broker account(mailbox)--> broker
                                   │
  ┌───────────────── customer intake ─────────┼──────────── broker email in ───────────┐
  open_customer_case(engagement, …, wechat)   │   ingest_broker_email(eml, to_mailbox)
        │                                      │        │ parse_eml → triage
        │ engine.draft (ZH→EN broker email)    │        ├─ skip → nothing
        ▼                                      │        ├─ match thread → reply draft
  Case(customer) → PENDING_APPROVAL            │        └─ new → Case(broker) → draft
        │                                      │                    │
        └──────────────► pending_approval message ◄────────────────┘
                                   │
                    agent reviews (edit / reject / approve)  ← the gate
                                   │  approve_message  (ONLY path to sent/posted)
                                   ▼
                    message sent/posted · case advances · audit row
```

## Guarantees (all tested)

- **Approval gate:** a message reaches `sent`/`posted` only via `approve_message`; the action
  validates the case transition before mutating and rolls back on error (no silent flips).
- **`skip` inbound creates nothing** (no case, no message).
- **Relationship-scoped access:** cases visible only to their agent-org members and (via an
  active engagement) customer-org members; cross-org isolation tested.
- **Full audit trail** with edit history (prior body) and ordered transitions.

## Built vs. deferred (the "headless phase")

Built: engine, identity/relationship, case core + state machine + audit, inbound router +
customer intake, approval gate, access scoping, end-to-end integration test.

Deferred (documented in the slice articles + spec §11, backstopped by the human-approval gate):
- **Customer-facing ZH posting** — summarizing a broker reply into a Chinese customer message
  (needs an engine `summarize→ZH` capability + the customer app).
- **Header-derived threading** — `thread_id` is caller-supplied; deriving it from
  Message-ID/References needs `parse_eml` to expose those headers.
- **Broker-initiated customer attribution** — linking an unattributed broker case to a
  CustomerOrg by BOL.
- **Knowledge-service versioning / per-agent template overrides** (Phase 0) — the engine reads
  templates directly for now.
- **API server + agent/customer frontends** — the non-headless phase.
