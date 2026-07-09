# Build Log

Append-only chronological log of significant changes to this project. Each entry records what changed, why, and which articles were touched. Read sequentially, this log tells the story of the project's decisions.

## [2026-07-09] compile | adopt living-doc + capture design

- Adopted the living-doc methodology (greenfield template, applied manually) as the
  documentation substrate. Git hooks and CI drift-check intentionally omitted (not a git repo).
- Added `CLAUDE.md` with the same-task rule and article-mapping table, customized for the
  broker-email drafting assistant.
- Wrote the approved design as `concepts/drafting/platform-architecture.md`.
- Captured thin, capture-first stubs for the known surface area: `issue-taxonomy`,
  `response-taxonomy`, `eml-parsing`, `template-system`, `parties-and-roles`, and the
  `issue-to-template-flow` connection. Taxonomy seeds were read from the 71-file `LTL-mail/`
  corpus subject lines; category definitions and template bodies remain to be filled during
  implementation.

## [2026-07-09] discovery | two quoting formats in corpus

- Real-data pass over all 71 `LTL-mail/*.eml`: the dominant quoting format is Front's
  `^On … wrote:$` (46 files only, 25 mixed with Outlook `From:` blocks, 0 Outlook-only).
  The original `hs.eml` sample was Foxmail/Outlook-style and misled the first draft of the
  parsing article. Updated `concepts/drafting/eml-parsing.md` to require handling BOTH
  formats and to note Front signatures + the shared `ltlwest@priority1.com` mailbox.
- Deleted the stray root `hs.eml` (duplicate of a `60114821897` thread already in `LTL-mail/`).
