---
title: Customer Web + Intake Form Engine
type: concept
area: app
updated: 2026-07-11
status: mature
affects:
  - web/customer/index.html
  - app/forms.py
  - app/api.py
references:
  - concepts/app/api.md
  - concepts/app/agent-console.md
  - concepts/drafting/template-system.md
---

# Customer Web + Intake Form Engine

Slice 7 (second frontend): a dependency-free customer web app + a schema-driven **intake form
engine**. The customer starts a case via a **category-dependent form** and sees their cases as
friendly **Chinese status** — never the internal English drafts.

## Form engine (`app/forms.py`)

`FORM_SCHEMAS[slug] = [Field…]`, `Field = {name, label_zh, label_en, type, required}`. Field
`name`s **are template slot names** (pickup→`pickup_address/contact_name/contact_phone`,
delivery-window→`requested_window/receiver_contact`, reconsignment→`new_address/…`, damage→
`damage_desc`, …), so intake collects exactly what the drafting engine fills. `issue_types()`
returns the customer-facing types + labels + schemas. Single source of truth; adding a type is
a data change here — no frontend redeploy. (Per-agent overrides in the multi-tenant build.)

## Endpoints (`app/api.py`)

- `GET /issue-types` → `forms.issue_types()` (auth required).
- `GET /engagements` → the caller's **active** engagements (as a customer-org member), each with
  `agent_name` and that agent's `broker_accounts` (id + broker name) — scoped; an unrelated user
  gets `[]`.
- `POST /cases` gains optional **`fields`** (dict) → `open_customer_case(fields=…)`, which merges
  them into the draft `facts` (fill slots) and `source_text` (validator keeps them). Verified:
  a `requested_window` value flows into the drafted broker email.

## Customer app (`web/customer/index.html`, served at `/customer`)

Chinese-primary, bilingual. Login (`X-User-Id`). **My cases:** `GET /cases` → rows with a
friendly Chinese status (`SENT_TO_BROKER`→"已转交承运商", `PENDING_APPROVAL`→"代理审核中", …) —
**no English message bodies**. **New case:** pick agent (`/engagements`) → broker → issue type
(`/issue-types` → dynamic fields render) → BOL + note → `POST /cases {…, fields}`. XSS-escaped.

## Verified (Playwright, real browser)

Log in as a customer → New case → agent/broker/issue selects populate → choose Delivery window
(fields switch to requested_window) → fill + BOL → Submit → the case appears under My Cases as
"代理审核中"; the drafted broker email contains the submitted window. Served-HTML smoke:
`tests/test_console.py`; form/endpoint tests: `tests/test_forms.py`, `tests/test_api.py`.

## Deferred / notes

- **Customer-facing ZH updates are now built** (Slice 8, see `concepts/drafting/summarize.md`):
  clicking a case shows agent-approved Chinese updates (`channel=app, lang=zh, status=posted`) —
  a broker reply is summarized to Chinese, approval-gated, then displayed. The customer app still
  never shows internal English drafts.
- WeChat Mini Program (same API) is a separate slice needing the WeChat toolchain.

## Login (updated 2026-07-12)

The customer app now logs in with **email + password** (`POST /auth/login` → session token, `Authorization: Bearer`), same as the agent console; 401 auto-logs-out. The customer's password is provisioned at onboarding (`onboard_customer` sets it or returns a `temp_password`). Replaces the earlier `X-User-Id` login. See `concepts/app/identity-model.md` → Email/password login.

**Customer-only gate.** Symmetric to the agent console: login/reload check the identity payload's `is_customer` flag and refuse a non-customer session (e.g. an agent account, which has no customer cases) with "Not a customer account — use a customer login". Reload verifies via `GET /auth/me`. UX gate only; access is enforced server-side. See `identity-model.md` → Console identity gate.
