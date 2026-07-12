---
title: Deployment (Vercel serverless + Turso)
type: concept
area: app
updated: 2026-07-11
status: thin
load_bearing: true
affects:
  - api/index.py
  - api/poll.py
  - vercel.json
  - requirements.txt
  - app/db.py
references:
  - concepts/app/api.md
  - concepts/app/transport-and-config.md
  - concepts/app/identity-model.md
---

# Deployment (Vercel serverless + Turso)

Staging runs on **Vercel** (static frontends + serverless Python API + Vercel Cron) with
**Turso/libSQL** as the persistent DB. Production (GoDaddy = domain/DNS only, later) and the
WeChat Mini Program are deferred. Spec:
`docs/superpowers/specs/2026-07-11-vercel-serverless-deployment-design.md`.

## Topology

```
 browser ─► Vercel: /            → web/agent/index.html      (static)
                    /customer     → web/customer/index.html   (static)
                    /api/*         → api/index.py  → app.api.dispatch()   (Python function)
                    cron */5m      → api/poll.py   → app.inbound.poll_once (Vercel Cron)
                         │ env: LIBSQL_URL, LIBSQL_AUTH_TOKEN, GEMINI_API_KEY,
                         │      SMTP_ADDRESS, SMTP_PASSWORD, WEBHOOK_SECRET, [CRON_SECRET]
                         ▼
                    Turso (hosted libSQL) — persistent DB over HTTP
```

- **Same origin, no CORS.** Frontends call `/api/...`; `api/index.py` strips `/api` and calls the
  existing pure `dispatch()` (which still sees `/cases`, `/engagements`, …). Frontend base is
  `const API = "/api"` in both `web/*/index.html`.
- **Stateless functions + networked DB.** Each request opens one libSQL connection and closes it;
  `llm`/`transport`/`wechat` are built once per warm instance. Turso is the shared store for the
  API function and the cron poller.

## Local development (no Vercel/Turso needed)

There is **no self-serve signup** — identity is provisioned (the web apps trust an upstream
`X-User-Id`; WeChat users onboard via invite/bind). To run and use the apps locally:

```bash
python3 scripts/seed_demo.py      # creates demo accounts in ./hs.db (idempotent)
python3 scripts/serve_local.py    # serves / (agent) + /customer + /api on http://127.0.0.1:8000
```

- `serve_local.py` runs `app.server` against a **persistent sqlite file** (`HS_DB`, default
  `hs.db`), serving the static frontends and the API. Frontends call `/api/*`; the server strips
  the prefix (same routing as Vercel). Defaults to **FAKE** llm/transport/wechat (no external
  calls, approving an email does NOT send); `USE_REAL_SERVICES=1` wires the real ones from `.env`.
- `seed_demo.py` creates an agent org (`Justnano`, operator **`op`**), a customer org
  (`Acme Shipping`, member **`uc`**), an active engagement, and a broker account. **Log in by
  typing the `X-User-Id`:** agent console → `op`, customer app → `uc`. New customers are added from the **agent console's "Onboard customer" panel**
  (`POST /onboard-customer` → customer org + active engagement + a web-login id), or by extending the seed.

## DB backend (`app/db.py`)

`connect()` returns a **libSQL** connection when `LIBSQL_URL` is set (Vercel), else stdlib
`sqlite3` (local/tests). `_LibsqlConnection` adapts libsql-client (HTTP) to the app's stateful
sqlite3-style surface — `execute`/`commit`/`rollback`/`executescript`, cursors with
`fetchone`/`fetchall`/iteration/`rowcount`, `row["col"]` rows, and constraint errors normalized to
`sqlite3.IntegrityError` — so `repo`/`cases`/`auth`/`inbound` are unchanged. Validated end-to-end
via `scripts/verify_libsql.py` against a local `file:` DB. The stdlib-sqlite test suite remains the
correctness baseline (libsql-client's sync-over-async client stalls pytest teardown, so it is not
in the suite).

## Runbook (operator steps — not automatable from the repo)

```bash
# 1. Turso DB + schema
turso db create hs-staging
turso db show hs-staging --url          # → LIBSQL_URL
turso db tokens create hs-staging       # → LIBSQL_AUTH_TOKEN
python3 scripts/export_schema.py        # → schema.sql (in sync with app.db._SCHEMA)
turso db shell hs-staging < schema.sql  # load the schema

# 2. Vercel project + env (Production/Preview scopes)
vercel link
vercel env add LIBSQL_URL
vercel env add LIBSQL_AUTH_TOKEN
vercel env add GEMINI_API_KEY
vercel env add SMTP_ADDRESS             # hs@justnanoinc.com
vercel env add SMTP_PASSWORD            # 16-digit Alibaba app password
vercel env add WEBHOOK_SECRET           # for POST /api/inbound
# optional: CRON_SECRET (guards /api/poll), IMAP_HOST/PORT (default qiye.aliyun.com:993)

# 3. Deploy + verify
vercel deploy
#   <url>/          → agent console   ;  <url>/customer → customer app
#   seed a demo org/engagement/broker (a one-off script or /api/inbound), log in, click through
```

## Verified locally / verified on deploy

- **Local:** stdlib suite green (133 passed); `scripts/verify_libsql.py` ALL PASS against a
  `file:` libSQL DB; `_strip_api`, `vercel.json` routing, and `schema.sql`-in-sync tests pass.
- **On your deploy (together):** live apps — login (`X-User-Id` for the web apps), list/open cases,
  draft, approve; then the cron poll picks up broker replies.

## Deferred

- Production host + GoDaddy DNS → the chosen host (one deployment model).
- Per-request libSQL client creation is fine at low volume; connection reuse/pooling is a
  perf follow-up. SQLite→Postgres remains a further option (repo layer already isolated).
- WeChat Mini Program (its API base just points at the Vercel domain later).
- `X-User-Id` production lock-down at the gateway (see `api.md`) before any public prod exposure.
