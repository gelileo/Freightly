---
title: EML Parsing
type: concept
area: drafting
updated: 2026-07-09
status: mature
affects:
  - scripts/parse_eml.py
load_bearing: true
---

# EML Parsing

Deterministic decoding of raw `.eml` into a clean, chronological thread. Kept as code
(`scripts/parse_eml.py`), not model work, because MIME decoding must be exact.

## Responsibilities

1. Parse MIME; decode `base64` (text/plain) and `quoted-printable` (text/html) bodies.
2. Prefer the `text/plain` part; fall back to stripped HTML. Discard inline images
   (signature logos — in the sample, 12 repeating PNGs made up most of the 165 KB).
3. Split the quoted history into individual turns, each with sender, timestamp, and body.
   **Two quoting formats appear and both must be handled** (see below).
4. Extract `BOL` and `PRO#` numbers and the involved parties.
5. Dedupe thread snapshots: `Re_ … 60114662390(1..8).eml` are one growing thread — keep
   the most complete.

## Quoting formats (measured across the 71-file corpus, 2026-07-09)

| Format | Turn marker (regex, multiline) | Count |
| --- | --- | --- |
| **Front / Apple-style** (dominant) | `^On .+ wrote:\s*$` | 46 files only + 25 mixed |
| **Outlook / Foxmail-style** | `^From:\s` block with `Sent:/To:/Subject:` | 0 files only + 25 mixed |

- `On-wrote only`: 46 · `both formats in one thread`: 25 · `From-block only`: 0.
- The parser must recognize **both markers** and split on whichever appears; deeper history
  in the 25 "mixed" threads switches from Front to Outlook forwards.

## Known corpus quirks

- Chinese subjects/bodies appear (`回复：` = "Reply"); preserve UTF-8.
- Many emails are sent via **Front** (shared inbox): body ends with `[Sent from Front]`
  and a signature block with `[image]<url>` / `[instagram]<url>` links to strip.
- The broker side is often the shared mailbox `ltlwest@priority1.com` (LTL West), signed by
  individual analysts (e.g. Isabella Guerrero, Laura Posada) — capture the human name.
- Timestamps come in mixed formats/timezones (e.g. `On May 21, 2026 at 9:21 AM GMT-5`).
- Multi-BOL subjects → emit one case per BOL.

## To do (implementation)

- Output shape: `cases/<BOL>/thread.md` via `render_thread_md`; fixtures in `tests/`.
