---
title: Agent Console (frontend)
type: concept
area: app
updated: 2026-07-11
status: mature
affects:
  - web/agent/index.html
  - app/server.py
references:
  - concepts/app/api.md
  - concepts/app/case-workflow.md
---

# Agent Console

Slice 6 (first frontend): a dependency-free, self-contained **HTML + vanilla-JS** page the
operator uses to run the approval workflow. No framework, no build step. It is a **thin API
client** — every rule (auth, access, the approval gate, state machine) is enforced server-side;
the console only calls the JSON API.

## Serving

`app/server.py` serves `web/agent/index.html` at `GET /` (and `/console`, `/index.html`);
`/favicon.ico` → 204; every other path falls through to the JSON `dispatch`. So `GET /` returns
HTML while `GET /cases` returns JSON — no route clash. `serve()` defaults `static_dir` to
`web/agent/`.

## What it does

- **Login bar** — an operator user-id (stored in `localStorage`), sent as `X-User-Id` on every
  request. (Real deployment: a gateway performs WeChat/OAuth login and injects this header; the
  console's field is a dev/stand-in.)
- **Case list** — `GET /cases` → rows (BOL, issue type, status pill, origin).
- **Case detail** — `GET /cases/{id}` → the message thread + the `pending_approval` draft in an
  editable `<textarea>` (with `[[MISSING: …]]` visible), plus `GET /cases/{id}/audit`.
- **Actions** — Approve & send (`edit` the current text, then `approve`), Save edit (`edit`),
  Reject (`reject`); API errors (401/403/409) shown inline; the case refreshes after each.

## Safety

- **No backend bypass:** the console never mutates state except through the API; approval
  remains the only send/post path.
- **XSS:** all server data is HTML-escaped (`esc()`) before insertion; `[[MISSING]]` markers are
  rendered as text.
- Auth is `X-User-Id` only (documented as gateway-provided in production).

## Verified

End-to-end in a real browser (Playwright): log in as the agent operator → see a seeded case →
open it → **Approve & send** → the message becomes `sent` and the case advances to
`AWAITING_BROKER` in the UI. Plus a served-HTML smoke test (`tests/test_console.py`).

## Not here / next

Real login/session, customer-facing frontends (WeChat Mini Program + responsive web — separate
toolchains), pagination, and richer case filtering are later slices.

## Login (updated 2026-07-12)

The console now logs in with **email + password** (`POST /auth/login` → session token) and sends `Authorization: Bearer <token>` on every call; on 401 it clears the token and returns to the login prompt. Passwords are provisioned out-of-band (`scripts/set_agent_password.py`, or `seed_demo.py` for the demo operator). Replaces the earlier type-any `X-User-Id` login. See `concepts/app/identity-model.md` → Email/password login.

**Agent-only gate.** Login/reload check the identity payload's `is_agent` flag and **refuse a non-agent session** (e.g. a customer account) with "Not an agent account — use an agent login", instead of silently showing empty, draft-less cases (broker drafts are withheld from customer sessions server-side). On reload the console calls `GET /auth/me` to verify identity and show the real "as &lt;name&gt;" (fixes an earlier "as true" placeholder). See `identity-model.md` → Console identity gate.

## Provisioning panels (2026-07-12)

The console's left column has three agent-only provisioning panels: **Onboard customer** (`POST /onboard-customer` → customer org + active engagement + login), **Add operator** (`POST /agents` → another agent operator/admin in this org; **admin-only**), and **Brokers** (`GET /brokers` list; `POST /brokers` add; `POST /brokers/{account_id}` edit recipient — create/edit are **admin-only**). Onboard/Add-operator accept an optional password and show the generated temp password. The Brokers panel lists each broker with an inline-editable recipient address (the `to` used when an approved broker email is sent — see `transport-and-config.md`) and an add form (name + recipient + optional sending mailbox); a mailbox already claimed by another agent org is rejected (400). The admin gate for `/agents` and `/brokers` is the shared `api._require_agent_admin` helper; listing brokers is open to any agent-org member.
