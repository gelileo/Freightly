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
3. Split the quoted history into individual turns. **As built, `Turn` = `marker` + `body`**
   — the sender/timestamp are not separate fields; they live unstructured inside the
   `marker` line (e.g. `On May 21, 2026 … hs@justnanoinc.com wrote:`).
   **Two quoting formats appear and both must be handled** (see below).
4. Extract `BOL` and `PRO#` numbers and the involved parties.
5. Dedupe thread snapshots: `Re_ … 60114662390(1..8).eml` are usually one growing thread.
   **As built, `dedupe_snapshots()` provides this (keep the largest file per BOL) as a
   library function; `scripts/corpus.py`'s `merged_best()` now calls it across both dirs,
   and the parse_eml CLI still does not** — the caller chooses which `.eml` to parse.
   **v2 caveat — one BOL can host TWO distinct threads:** in the merged corpus ~24/141 BOLs
   carry both a shipment thread AND a separate billing/FFBA thread under the same BOL number
   (e.g. `60114592263`: a POD thread + a "$500–$700 redelivery charge" billing thread;
   `60112135944`: an FFBA billing file + a small shipment thread). Because `dedupe_snapshots()`
   keys on BOL alone and keeps only the largest file, for those BOLs it **silently drops the
   other-topic thread**. When you need a specific topic, parse the specific `.eml` the
   customer/broker referenced — do not blindly trust `merged_best()`.

## Quoting formats (measured across the 71-file corpus, 2026-07-09)

| Format | Turn marker (regex, multiline) | Count |
| --- | --- | --- |
| **Front / Apple-style** (dominant) | `^On .+ wrote:\s*$` | 46 files only + 25 mixed |
| **Outlook / Foxmail-style** | `^From:\s` block with `Sent:/To:/Subject:` | 0 files only + 25 mixed |

- `On-wrote only`: 46 · `both formats in one thread`: 25 · `From-block only`: 0.
- The parser must recognize **both markers** and split on whichever appears; deeper history
  in the 25 "mixed" threads switches from Front to Outlook forwards.

## Corpus scope (v2, built)

The corpus is no longer just `LTL-mail/`. `scripts/corpus.py` (`list_corpus()` /
`merged_best()`) merges **both** `LTL-mail/` (71 files) **and** `LTL-mail-2/` (851 files,
Justnano's full broker inbox) into one 922-file corpus, deduping same-BOL snapshots
**across** the two directories (not just within one) by delegating to this module's own
`dedupe_snapshots()`. The two directories use different filename conventions (`Re_
<subject>.eml` in `LTL-mail/` vs bare `<subject>.eml` in `LTL-mail-2/`) but both are matched
by the same `60\d{9}` BOL regex in the filename, so grouping works uniformly. `LTL-mail-2`
is a superset of `LTL-mail` by BOL (all 24 old BOLs ⊂ 141 new-corpus BOLs) but both
directories are kept per the v2 scope decision (`knowledge/log.md`, 2026-07-09). Everything
in "Known corpus quirks" and "Quoting formats" below applies uniformly to files in either
directory — `parse_eml()` does not branch on which directory a file came from.

## Known corpus quirks

- Chinese subjects/bodies appear (`回复：` = "Reply"); preserve UTF-8.
- Many emails are sent via **Front** (shared inbox): body ends with `[Sent from Front]`
  and a signature block with `[image]<url>` / `[instagram]<url>` links. **As built, only
  inline image PARTS are discarded (step 2); these textual signature/link artifacts remain
  in `thread.md`** — a known future cleanup. The drafting skill ignores them when filling slots.
- The broker side is often the shared mailbox `ltlwest@priority1.com` (LTL West), signed by
  individual analysts (e.g. Isabella Guerrero, Laura Posada) — capture the human name.
- Timestamps come in mixed formats/timezones (e.g. `On May 21, 2026 at 9:21 AM GMT-5`).
- Multi-BOL subjects → intended one case per BOL, but **as built the CLI writes only the
  primary `bol[0]`** (no fan-out; see `platform-architecture.md` → Case model → Known limitations).
- **PRO# extraction misses HTML-table layouts (found during Task 6 end-to-end validation,
  2026-07-09):** `extract_ids()`'s PRO regex (`PRO#?\s*(\d{6,})`) requires the literal "PRO"
  text to sit directly next to its digits. Several `LTL-mail-2/` FFBA notices render the
  BOL/PRO/Carrier/charge fields as an HTML `<table>` whose header row ("BOL", "PRO", …) and
  data row ("60112079078", "3100034", …) are separated by whitespace/newlines once the HTML
  is stripped to text — `parsed.pro` comes back `[]` even though the PRO number is present in
  `thread.md`'s body text (just not adjacent to the label "PRO"). Confirmed on
  `LTL-mail-2/FFBA BOL# 60112079078.eml` (PRO `3100034`, verified by reading the raw HTML
  `<table>` cell order) — see `cases/60112079078/drafts/1.md` for the worked example. Not
  fixed in this task (out of Task 6's file scope); a future fix would need a
  table-column-aware extractor, not a purely adjacency-based regex.

## To do (implementation)

- Output shape: `cases/<BOL>/thread.md` via `render_thread_md`; fixtures in `tests/`.

## Parse from bytes + threading headers (2026-07-11)

`parse_eml(path)` now delegates to `_from_message(msg)`; a sibling **`parse_eml_bytes(raw)`**
parses raw RFC-822 bytes/str (the IMAP inbound poller has bytes, not a file path).
`_from_message` normalizes line endings to `\n` so a path parse and a bytes parse of the same
message yield identical bodies. `ParsedEmail` gained **`message_id`**, **`in_reply_to`**,
**`references`** (default `""`), enabling **header-derived threading**: the inbound poller derives
a case `thread_id` from the References root / In-Reply-To (= the `Message-ID` set on send). See
`concepts/app/transport-and-config.md` (Inbound poller). `router.ingest_broker_email` accepts raw
bytes (dispatches to `parse_eml_bytes`) and records the incoming `Message-ID` on the stored
`received` broker message (`messages.mail_message_id`) for dedup + provenance.
