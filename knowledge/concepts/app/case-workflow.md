---
title: Case Workflow (state machine, audit, inbound router)
type: concept
area: app
updated: 2026-07-10
status: mature
affects:
  - app/cases.py
  - app/router.py
references:
  - concepts/app/identity-model.md
  - concepts/drafting/drafting-engine.md
---

# Case Workflow

Slice 3 of the app: the workflow spine that turns identity (Slice 2) + the drafting engine
into a case lifecycle. Dependency-free (stdlib sqlite3), headless. Nothing sends/posts without
an agent approval; `triage=skip` inbound creates nothing.

## Entities (schema in `app/db.py`)

- **cases** — `agent_org_id` (always known), `customer_org_id` (**nullable** — broker-initiated
  cases start unattributed), `broker_account_id`, `shipment_bol/pro`, `origin(customer|broker)`,
  `issue_type`, `status`, `mail_thread_id`.
- **messages** — `party`, `channel(app|email)`, `lang(zh|en)`, `body`, `status`
  (`draft|pending_approval|approved|sent|posted|received`), `classification` (JSON).
- **audit_log** — one row per transition/action (`actor, action, from_status, to_status`),
  ordered by `rowid` (monotonic; `CURRENT_TIMESTAMP` is too coarse to order within a test).

## State machine (`app/cases.py`)

`transition(conn, case_id, to_status, actor)` validates against `ALLOWED` and writes an audit
row; an illegal transition raises `ValueError` and writes **no** audit. Map:
```
NEW→DRAFTING; DRAFTING→PENDING_APPROVAL;
PENDING_APPROVAL→{SENT_TO_BROKER, POSTED_TO_CUSTOMER, DRAFTING, RESOLVED};
SENT_TO_BROKER→{AWAITING_BROKER, RESOLVED}; POSTED_TO_CUSTOMER→{AWAITING_BROKER, RESOLVED};
AWAITING_BROKER→{REPLY_DRAFTED, RESOLVED}; REPLY_DRAFTED→PENDING_APPROVAL;
RESOLVED→CLOSED
```

## Approval gate

`approve_message` is the **only** function that moves a message to `sent` (email → case
`SENT_TO_BROKER`) or `posted` (app → `POSTED_TO_CUSTOMER`). `edit_message` (pending_approval
only, audited) and `reject_message` (→ draft, case → DRAFTING) round out the review actions.
Approving a non-pending message raises.

## Inbound router + intake (`app/router.py`)

- `open_customer_case(...)` — requires an ACTIVE engagement; creates a customer-origin case,
  drafts an EN broker email via `engine.draft` (ZH WeChat text → EN), stores it
  `pending_approval`, case → PENDING_APPROVAL.
- `ingest_broker_email(..., to_mailbox, ...)` — parse via `scripts.parse_eml`; `triage`:
  `skip` → return None, create nothing; matches an existing case by `mail_thread_id` → append
  a `received` broker message + draft a reply; else create a broker-origin (unattributed) case
  + draft. The owning agent is resolved from `to_mailbox` via `repo.agent_for_mailbox` (raises
  if the mailbox is unknown). **Limitation:** `thread_id` is currently **caller-supplied**;
  deriving it from the email's `Message-ID`/`References`/`In-Reply-To` headers is deferred
  (`scripts.parse_eml.ParsedEmail` does not yet expose those headers). Until that lands, real
  inbound integration must supply `thread_id`, or every broker email creates a new case.

## Relationship-scoped case access

`app/access.user_may_access_case` — a member of the case's agent org always; a member of its
customer org only when an ACTIVE engagement links them (revoking the engagement removes the
customer's access but not the agent's). Isolation-tested.

## Transactional safety & audit

The approval actions (`approve_message`/`reject_message`) **validate the case transition
before mutating the message**, then apply both writes under a single `commit()` with
`rollback()` on any error — so a failed action leaves nothing changed (no half-applied message
flip, no missing audit). `edit_message` preserves the prior body in the audit `detail` column.
`audit_trail` is ordered by `rowid`.

## Scope note / deferred

Drafts here are **broker-facing English** (the engine's competency). **Customer-facing Chinese
posting** — summarizing a broker reply back into a ZH customer message — needs a dedicated
engine `summarize→ZH` capability and the customer app, and is deferred to a later slice.
Broker-initiated **customer attribution** (linking a case to the right CustomerOrg by BOL) is
also deferred (cases start unattributed; the spec flags this as an open question).
