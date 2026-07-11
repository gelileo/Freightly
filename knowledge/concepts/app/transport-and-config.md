---
title: Mail Transport + Config (real Gemini + Gmail wiring)
type: concept
area: app
updated: 2026-07-10
status: mature
affects:
  - app/transport.py
  - app/config.py
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

## Send-on-approval (the only outbound send path)

`app/api._approve_and_maybe_send` (called only by the approve handler):
- app-channel (customer) approvals do **not** send.
- email (broker-facing) approvals: resolve `from_addr` = broker-account `mailbox` (agent's
  connected mailbox), `to` = broker-account `broker_email` (the broker's address; a new
  nullable column distinct from the routing `mailbox`). Validate the transition, then
  `transport.send(...)` → mark sent (`cases.approve_message`) → stamp `messages.mail_message_id`
  and (if unset) `cases.mail_thread_id` → advance the case to **AWAITING_BROKER**.
- Missing recipient/**sending mailbox**/transport or illegal transition → `ValueError` → **409**,
  nothing sent, message stays `pending_approval`.
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

- `make_llm()` → `GeminiLlmClient` when `GEMINI_API_KEY` is set, else `FakeLlmClient`.
- `make_transport()` → `GmailTransport` (loading OAuth creds from `GMAIL_TOKEN_FILE`) when set,
  else `FakeTransport`.
- `server.serve()` builds both from config (still injectable for tests). Env unset → fakes.

## Inbound (real Gmail) — how it connects

The `POST /inbound` webhook already accepts a raw `.eml` + `to_mailbox`. A production Gmail
integration watches the agent mailbox (Gmail `watch`/push or poll), fetches the raw RFC-822
message, and POSTs it to `/inbound` with the connected mailbox as `to_mailbox` (and, once
`parse_eml` exposes Message-ID/References, the derived `thread_id`). Until header-derivation
lands, outbound-established `mail_thread_id` is the threading key.

## Deferred / notes
- Real Gemini and Gmail calls are unverified in CI (no creds) — mechanism proven with fakes;
  a guarded construction test covers the import boundary.
- `parse_eml` still doesn't expose Message-ID/References (header-derived inbound threading
  remains a follow-up).
- Recipient modeling is minimal (`broker_email` per broker account); per-contact routing and
  send-failure retry/idempotency are follow-ups.
