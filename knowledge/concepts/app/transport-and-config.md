---
title: Mail Transport + Config (real Gemini + Gmail wiring)
type: concept
area: app
updated: 2026-07-10
status: mature
affects:
  - app/transport.py
  - app/config.py
  - app/inbound.py
references:
  - concepts/app/case-workflow.md
  - concepts/app/api.md
  - concepts/drafting/drafting-engine.md
---

# Mail Transport + Config

Slice 5: wires the real **Gemini** LLM and a **Gmail** mail transport behind ports/config, and
makes agent approval actually **send**. Same port pattern as `engine.llm`: the app depends on a
`MailTransport` Protocol; tests use `FakeTransport`; the real `GmailTransport` is credential-
guarded and never imported/hit without creds (CI stays hermetic).

## `app/transport.py`

- `SentRef(message_id, thread_id)`.
- `MailTransport.send(*, from_addr, to, subject, body, thread_id=None, in_reply_to=None) -> SentRef`.
- `FakeTransport` — records `.sent`; deterministic ids; preserves a passed `thread_id` (a reply
  keeps its thread).
- `GmailTransport` — real adapter (`google-api-python-client` + OAuth `Credentials`). Builds an
  RFC-822 `EmailMessage` with `In-Reply-To`/`References` for threading, calls
  `users().messages().send()`, returns the Gmail message + thread ids. **Deferred imports**, so
  `import app.transport` and even constructing `GmailTransport` work without the library.
- `AlibabaSmtpTransport` — real adapter for **Alibaba Enterprise Mail** (`hs@example.com`)
  over **SMTP-SSL** using the **16-digit third-party client password** (stdlib `smtplib`, zero
  deps). Sets a generated `Message-ID` + `In-Reply-To`/`References`; returns
  `SentRef(message_id, thread_id=References-root)`. **`from_addr` is locked** to the authenticated
  mailbox (raises `ValueError` otherwise — Alibaba/Gmail both reject a foreign From). The SMTP
  client is an **injectable `smtp_factory`** (default `smtplib.SMTP_SSL`) so tests use a `FakeSmtp`
  (no network). Live SMTP login verified 2026-07-11 (`smtp.qiye.aliyun.com:465`).

## Send-on-approval (the only outbound send path)

`app/api._approve_and_maybe_send` (called only by the approve handler):
- app-channel (customer) approvals do **not** send.
- email (broker-facing) approvals: resolve `from_addr` = broker-account `mailbox` (agent's
  connected mailbox), `to` = broker-account `broker_email` (the broker's address; a new
  nullable column distinct from the routing `mailbox`). This `broker_email` is set when the
  account is created (via `seed_demo.py` seeding, or the admin **`POST /brokers`** route) and can
  be corrected later via **`POST /brokers/{account_id}`** — an agent **admin** manages brokers
  from the console's Brokers panel (see `agent-console.md`); it is not read from an env var at
  send time. Validate the transition, then
  `transport.send(...)` → mark sent (`cases.approve_message`) → stamp `messages.mail_message_id`
  and (if unset) `cases.mail_thread_id` → advance the case to **AWAITING_BROKER**.
- Missing recipient/**sending mailbox**/transport or illegal transition → `ValueError` → **409**,
  nothing sent, message stays `pending_approval`.
- **Placeholder guardrail:** before any network send, the body is scanned with
  `engine.validate.find_placeholders` — if it still contains an anti-fabrication marker
  (`[[MISSING: …]]`) or an unfilled template slot (`{…}`), the send is refused (`ValueError` →
  **409**, nothing sent). An agent must **edit** the draft to fill/remove the placeholder first.
  This makes the anti-fabrication `[[MISSING]]` markers load-bearing at the last gate, not just
  advisory in the console. Optional clauses (e.g. `{pro_clause}` when a shipment has no PRO) are
  pre-filled to an empty string in `draft()`, so a legitimate no-PRO shipment is **not** blocked.
- **Atomicity:** the network send happens first (if it raises, nothing is written — message
  stays `pending_approval`, verified by `test_send_failure_leaves_state_untouched`); all
  post-send bookkeeping (message→sent, `SENT_TO_BROKER`→`AWAITING_BROKER` transitions, mail-id +
  thread-id stamps) runs in **one transaction** with rollback-on-error, so a crash can't strand
  the case mid-way. Unexpected send failures are logged server-side (traceback) and returned as
  a controlled 500.

**Thread continuity (tested):** the send stamps `case.mail_thread_id`; a broker reply ingested
with that `thread_id` matches the same case (→ REPLY_DRAFTED → new draft), closing the
outbound→inbound loop with no new case.

## `app/config.py`

- `load_env()` — dependency-free `.env` loader (KEY=VALUE → `os.environ`, **real env wins** via
  `setdefault`; `.env` is gitignored). Called by both factories so keys in `.env` are picked up.
- `make_llm()` → `GeminiLlmClient` when `GEMINI_API_KEY` is set (incl. from `.env`), else `FakeLlmClient`.
- `make_transport()` precedence: **`AlibabaSmtpTransport`** (when `SMTP_PASSWORD` set;
  `SMTP_ADDRESS` default `hs@example.com`, `SMTP_HOST`/`SMTP_PORT` default
  `smtp.qiye.aliyun.com`/`465`) → `GmailTransport` (`GMAIL_TOKEN_FILE`) → `FakeTransport`.
- `make_imap_config()` → `{host,port,address,password}` for the inbound poller
  (`IMAP_HOST`/`IMAP_PORT` default `imap.qiye.aliyun.com`/`993`).
- `server.serve()` builds both from config (still injectable for tests). Env/`.env` unset → fakes.

### Real Gemini — verified live (2026-07-10)

`GeminiLlmClient.MODEL = "gemini-flash-latest"` (a stable alias; `gemini-2.5-flash` is retired
for new accounts). Verified end-to-end with a real key from `.env`: a Chinese WeChat request
(`请尽快安排提货…`) drafted to English (`"…please arrange for pickup as soon as possible."`),
and `config.make_llm()` auto-selected `GeminiLlmClient`. `google-genai` is **not** a system dep
(CI/tests use the fake); install it in a venv for real use:
```
python3 -m venv .venv && .venv/bin/pip install google-genai   # .venv is gitignored
```

## Inbound — IMAP poller (`app/inbound.py`, built)

`poll_once(conn, imap, *, mailbox_addr, llm)` pulls broker replies from the Alibaba mailbox and
feeds `router.ingest_broker_email` — no webhook required:

- **UID high-water mark** persisted in `imap_state(mailbox, last_uid, uidvalidity)`. Only messages
  with `UID > last_uid` are processed. **First run** (or on `UIDVALIDITY` change) **seeds `last_uid`
  to the current max UID**, so the existing backlog (measured **1,655 unread / 4,686 total** on the
  live box) is skipped, not ingested.
- **Read-only + `BODY.PEEK[]`** — the poller **never changes flags** on the shared human mailbox.
- **Header-derived threading (now built):** `parse_eml_bytes` exposes `Message-ID`/`In-Reply-To`/
  `References`; the poller derives `thread_id` from the References root (= the `Message-ID` we set
  on send), so a broker reply matches the case whose `mail_thread_id` we stamped → summarize→ZH.
- **Idempotent:** the watermark advances only after a successful ingest, and a message whose
  `Message-ID` is already stored (`messages.mail_message_id`) is skipped.
- `ImapClient` (real `imaplib.IMAP4_SSL`, read-only) + `run_poller(interval, once)` loop +
  `python -m app.inbound` CLI. Polling, not IMAP IDLE. Live IMAP read-only login verified
  2026-07-11 (`imap.qiye.aliyun.com:993`).

## Deferred / notes
- **No real send in build/tests** — all hermetic (`FakeSmtp`/`FakeImap`); guarded live tests only
  log in (SMTP) / read-only select (IMAP). A live outbound send is a separate, explicitly-confirmed
  step.
- Gmail path retained but Alibaba is the live provider. Real Gemini verified separately (2026-07-10).
- Recipient modeling is minimal (`broker_email` per broker account); per-contact routing and
  SMTP/IMAP retry/backoff are follow-ups (a transient poll error simply retries next cycle).
- **Known low-risk limitations** (from the final review): a broker email with **no `Message-ID`**
  has no secondary dedup key, so a crash in the tiny window between ingest-commit and
  watermark-commit could duplicate it (real mail carries a Message-ID); a reply carrying only
  `In-Reply-To` to a non-root message (no `References`) could spawn a new case instead of matching;
  and dedup is not mailbox-scoped (harmless for the single-mailbox deployment). The primary
  idempotency is the UID watermark; the `Message-ID` check is the secondary guard.
