---
title: Summarize→ZH(客户更新)
type: concept
area: drafting
updated: 2026-07-11
status: mature
affects:
  - engine/llm.py
  - engine/drafting.py
  - app/router.py
references:
  - concepts/drafting/drafting-engine.md
  - concepts/app/case-workflow.md
  - concepts/app/customer-web.md
---

# Summarize→ZH(客户更新)

Slice 8:把 broker 的英文回复变成忠实的**中文**客户更新。补上此前暂缓的"面向客户的中文张贴"缺口。

## 能力(`engine/llm.py`)

`LlmClient.summarize(*, text, target_lang, context="") -> str` —— 与 `generate`(填模板)不同的
独立 LLM 操作。`FakeLlmClient.summarize` 确定性(`"[summary->{lang}] " + 首行`)供测试;
`GeminiLlmClient.summarize` 提示 Gemini 生成简短、**忠实**的消息(不臆造事实)并返回纯文本。
`engine.drafting.summarize_for_customer(broker_text, llm, target_lang="zh")` 为薄封装(忠实转达指令)。

## 接线(`app/router.py`)

对**命中线程的 broker 回复**,`ingest_broker_email` 追加 `received` broker 消息,并创建一条
**面向客户的消息**(`party=agent, channel=app, lang=zh, status=pending_approval`)含摘要,再把
case 推进到 `PENDING_APPROVAL`。(broker **发起**的新 case 仍起草英文 broker 回复。)

## 审批门与展示

中文摘要为 `pending_approval` —— 代理在控制台批准(或编辑/驳回);批准 app 通道的消息即张贴
(`POSTED_TO_CUSTOMER`)。**过滤在服务端强制**:`GET /cases/{id}` 对客户方调用者只返回
`channel=app, lang=zh, status=posted` 的消息(见 `app/api._get_case`/`_messages`);内部英文草稿
与 broker 原始来邮**不经 API 下发给客户**,而非仅靠前端隐藏。因此客户只看到代理批准的中文更新。

## 实测

真实 Gemini 把一封 out-of-route 收费的 broker 邮件摘要成中文(保留改道地址与 55.56 美元费用),
代理批准后**客户端展示了该中文更新**——在真实浏览器中端到端确认。fake 保持 CI 无依赖
(`tests/test_engine_llm.py`、`tests/test_router.py`)。

## 说明 / 后续

摘要带忠实指令且人工把关(可在控制台编辑/驳回)——人工门为兜底,因为摘要不走事实槽位校验器。
后续可增加对摘要中金额/日期与原文的轻量事实核对。
