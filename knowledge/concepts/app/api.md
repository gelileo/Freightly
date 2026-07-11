---
title: HTTP API
type: concept
area: app
updated: 2026-07-10
status: mature
affects:
  - app/api.py
  - app/server.py
references:
  - concepts/app/case-workflow.md
  - concepts/app/identity-model.md
---

# HTTP API

Slice 4: a JSON HTTP API over the headless backend. Dependency-free (stdlib `http.server`).
The tested surface is the **pure `dispatch(req, *, conn, llm, webhook_secret) -> Response`**
function in `app/api.py`; `app/server.py` is a thin `ThreadingHTTPServer` shell that translates
HTTP ↔ `Request`/`Response` and owns the socket (one fresh sqlite connection per request —
sqlite connections aren't thread-shareable).

## Auth boundary

- **User routes** trust an upstream-authenticated **`X-User-Id`** header. Real WeChat/OAuth
  login happens at the gateway/frontend; the API mints no sessions. Missing header → **401**.
  Every user route then enforces `app.access` (→ **403** on denial).
- **`POST /inbound`** (mail-transport webhook) authenticates with a shared **`X-Webhook-Secret`**
  (constant-time compare); no user context. Missing/wrong → **401**.

## Endpoints

| Method + path | Body → result | Access |
| --- | --- | --- |
| `POST /cases` | `{engagement_id, broker_account_id, bol, pro, issue_type, wechat_text}` → 201 `{case, messages}` | member of the engagement's customer OR agent org |
| `GET /cases` | → `{cases:[…]}` (access-filtered) | any authenticated user |
| `GET /cases/{id}` | → `{case, messages}` | `user_may_access_case` |
| `GET /cases/{id}/audit` | → `{audit:[…]}` | `user_may_access_case` |
| `POST /cases/{id}/messages/{mid}/approve` | → `{message, case}` | member of case's **agent** org |
| `POST /cases/{id}/messages/{mid}/edit` | `{body}` → `{message, case}` | agent-org member |
| `POST /cases/{id}/messages/{mid}/reject` | → `{message, case}` | agent-org member |
| `POST /inbound` | `{eml, to_mailbox, thread_id?}` → `{case_id}` or `{skipped:true}` | webhook secret |

## Status-code mapping

200/201 ok · 400 bad input (inactive engagement, unknown/unreadable mailbox or eml, **non-object
JSON body**) · 401 unauthenticated · 403 forbidden (access) · 404 not found · **409** illegal
domain action (approve a non-pending message, illegal case transition — mapped from the domain
`ValueError`). `dispatch` rejects non-`dict` bodies with 400; `_inbound` maps
`ValueError/KeyError/TypeError/OSError` (bad eml path etc.) to 400; the `server.py` shell wraps
`dispatch` so any unexpected error is a **controlled 500** (`{"error":"internal error"}`, no
stack leak) rather than a dead request thread.

## Invariants preserved

- **Approval is still the only send/post path** — the API just calls `cases.approve_message`
  etc.; no endpoint writes `sent`/`posted` directly.
- **Only the case's agent org** can approve/edit/reject (a customer-org member gets 403).
- **`skip` inbound creates nothing** (returns `{skipped:true}`).
- Cross-org isolation holds end to end (tested in `tests/test_api.py`).

## Not here / next

Real login (WeChat mini-program / OAuth), rate limiting, TLS termination, and pagination live
at the gateway / a later slice. Frontends (agent console, customer app) consume this API.
