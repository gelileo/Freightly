# Knowledge Base Index

Grouped by subject area. Each article is a standalone reference. Connections at the bottom analyze how multiple concepts interact.

## Drafting system (this repo)

| Article | Summary | Updated |
| --- | --- | --- |
| [platform-architecture](concepts/drafting/platform-architecture.md) | Design: folders, data flow, case model, review gate — v2 built (triage front door, merged corpus, billing-dispute) | 2026-07-09 |
| [issue-taxonomy](concepts/drafting/issue-taxonomy.md) | Customer issue categories (10 shipment slugs + `billing-dispute`, 11 total) + v2 `triage` front-door dimension (skip/billing-dispute/shipment) and its measured 922-file distribution | 2026-07-09 |
| [response-taxonomy](concepts/drafting/response-taxonomy.md) | Broker response categories (6 slugs, reused as-is for billing-dispute) | 2026-07-09 |
| [eml-parsing](concepts/drafting/eml-parsing.md) | How raw `.eml` threads are decoded, deduped, split into turns; now spans `LTL-mail/` + `LTL-mail-2/` via `scripts/corpus.py` | 2026-07-09 |
| [summarize](concepts/drafting/summarize.md) | Summarize a broker reply → faithful Chinese customer update (LlmClient.summarize; agent-approved, shown in customer app) (Slice 8) | 2026-07-11 |
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

## App backend (multi-sided platform, headless)

| Article | Summary | Updated |
| --- | --- | --- |
| [identity-model](concepts/app/identity-model.md) | Orgs/users/memberships/engagements/brokers + relationship-scoped access (Slice 2) | 2026-07-10 |
| [case-workflow](concepts/app/case-workflow.md) | Case/message/audit + guarded state machine + inbound router + approval gate (Slice 3) | 2026-07-10 |
| [headless-backend](concepts/app/headless-backend.md) | End-to-end headless loop overview + built/deferred | 2026-07-10 |
| [api](concepts/app/api.md) | JSON HTTP API (dispatch + http.server shell), auth boundary, endpoints (Slice 4) | 2026-07-10 |
| [transport-and-config](concepts/app/transport-and-config.md) | MailTransport port + Fake/Gmail, send-on-approval + thread continuity, Gemini/Gmail config factory (Slice 5) | 2026-07-10 |
| [agent-console](concepts/app/agent-console.md) | Dependency-free HTML+JS agent console (thin API client), served by stdlib server (Slice 6) | 2026-07-11 |
| [customer-web](concepts/app/customer-web.md) | Customer web + schema-driven intake form engine (issue-types/engagements endpoints, dynamic forms) (Slice 7) | 2026-07-11 |
| [wechat-miniprogram](concepts/app/wechat-miniprogram.md) | WeChat Mini Program as the customer frontend — dual-thread architecture, ecosystem/networking constraints, `wx.login`→`code2Session`→openid/unionid auth. **Backend auth adapter built** (`app/wechat.py`, `app/auth.py`); Mini Program views still deferred | 2026-07-11 |
| [wechat-miniprogram.zh](concepts/app/wechat-miniprogram.zh.md) | 中文版:微信小程序作为客户前端——双线程架构、生态/网络约束、`wx.login`→`code2Session`→openid/unionid 鉴权。**后端鉴权适配器已构建**;视图仍暂缓 | 2026-07-11 |

## Code modules (governed by the articles above, not separately indexed)

| Module | Governing article(s) |
| --- | --- |
| `app/db.py`, `app/models.py`, `app/repo.py`, `app/access.py` | identity-model.md, case-workflow.md |
| `app/cases.py` (state machine, audit, approval), `app/router.py` (intake + inbound) | case-workflow.md |
| `app/api.py` (`dispatch`), `app/server.py` (http.server shell) | api.md, transport-and-config.md |
| `app/wechat.py` (`WeChatClient`, Fake/Real), `app/auth.py` (login/session/invite/bind) | wechat-miniprogram.md, identity-model.md |
| `app/transport.py` (MailTransport, FakeTransport, GmailTransport), `app/config.py` (make_llm/make_transport) | transport-and-config.md |
| `web/agent/index.html` (agent console), `app/server.py` static-serve route | agent-console.md |
| `web/customer/index.html` (customer app), `app/forms.py` (form engine) | customer-web.md |
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
