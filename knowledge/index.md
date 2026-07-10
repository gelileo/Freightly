# Knowledge Base Index

Grouped by subject area. Each article is a standalone reference. Connections at the bottom analyze how multiple concepts interact.

## Drafting system (this repo)

| Article | Summary | Updated |
| --- | --- | --- |
| [platform-architecture](concepts/drafting/platform-architecture.md) | Design: folders, data flow, case model, review gate — v2 built (triage front door, merged corpus, billing-dispute) | 2026-07-09 |
| [issue-taxonomy](concepts/drafting/issue-taxonomy.md) | Customer issue categories (10 shipment slugs + `billing-dispute`, 11 total) + v2 `triage` front-door dimension (skip/billing-dispute/shipment) and its measured 922-file distribution | 2026-07-09 |
| [response-taxonomy](concepts/drafting/response-taxonomy.md) | Broker response categories (6 slugs, reused as-is for billing-dispute) | 2026-07-09 |
| [eml-parsing](concepts/drafting/eml-parsing.md) | How raw `.eml` threads are decoded, deduped, split into turns; now spans `LTL-mail/` + `LTL-mail-2/` via `scripts/corpus.py` | 2026-07-09 |
| [template-system](concepts/drafting/template-system.md) | Template skeletons, slot conventions, worked examples — 10 shipment templates + `billing-dispute` (11 total) | 2026-07-09 |
| [drafting-engine](concepts/drafting/drafting-engine.md) | The `engine/` package: `LlmClient` port (+Fake/Gemini), `draft()` pipeline (triage→classify→template→fill→LLM→validate), anti-fabrication `FACTUAL_SLOTS` + `warnings` fail-loud rule, reuses `scripts/` unchanged, locked corpus-regression distribution — first built slice of the app spec | 2026-07-10 |
| [drafting-engine.zh](concepts/drafting/drafting-engine.zh.md) | 中文版:`engine/` 包、`draft()` 流水线、反捏造 `FACTUAL_SLOTS` 与 `warnings` 失败必现机制、原样复用 `scripts/`、锁定的语料回归分布 | 2026-07-10 |

## Domain

| Article | Summary | Updated |
| --- | --- | --- |
| [parties-and-roles](concepts/freight/parties-and-roles.md) | Customer / shipper / broker / carrier chain + freight terms, incl. v2 FFBA/billing terms and parties | 2026-07-09 |

## Connections

| Article | Summary | Updated |
| --- | --- | --- |
| [issue-to-template-flow](connections/issue-to-template-flow.md) | How issue×response selects a template and drafts a reply, incl. the `billing-dispute` branch matrix | 2026-07-09 |

## Code modules (governed by the articles above, not separately indexed)

| Module | Governing article(s) |
| --- | --- |
| `scripts/parse_eml.py` | eml-parsing.md |
| `scripts/corpus.py` (`list_corpus`, `merged_best` — merges `LTL-mail/` + `LTL-mail-2/`) | eml-parsing.md, platform-architecture.md |
| `scripts/corpus_report.py` (`classify_issue`, `corpus_report`) | issue-taxonomy.md |
| `scripts/triage.py` (`triage(body, sender) -> skip/billing-dispute/shipment`) | issue-taxonomy.md → "v2: `triage` 前置维度", platform-architecture.md |
| `scripts/triage_report.py` (`triage_report()` — full-corpus bucket distribution) | issue-taxonomy.md → "v2 triage 分布" |
| `templates/billing-dispute.md` | template-system.md, issue-to-template-flow.md |
| `.claude/skills/draft-broker-email/SKILL.md` | platform-architecture.md, all of the above |
| `engine/llm.py` (`LlmDraft`, `LlmClient`, `FakeLlmClient`, `GeminiLlmClient`) | drafting-engine.md |
| `engine/validate.py` (`validate_draft`, `FACTUAL_SLOTS`, `Validated`) | drafting-engine.md |
| `engine/knowledge.py` (`load_template`) | drafting-engine.md |
| `engine/drafting.py` (`DraftRequest`, `DraftResult`, `draft`) | drafting-engine.md |
