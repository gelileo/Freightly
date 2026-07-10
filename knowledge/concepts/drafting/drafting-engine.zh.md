---
title: Drafting Engine
type: concept
area: drafting
updated: 2026-07-10
status: mature
affects:
  - engine/**
references:
  - concepts/drafting/platform-architecture.md
  - concepts/drafting/issue-taxonomy.md
  - concepts/drafting/template-system.md
load_bearing: true
---

# 起草引擎(Drafting Engine)

English version: [drafting-engine.md](drafting-engine.md).

## 目的

`engine/` 是一个无头(headless)、依赖注入的 Python 包,把一封已解析的 `.eml`(或一条粘贴进来的
消息)转换成一份**经过校验的草稿**——不发起任何网络调用,除读取 `templates/*.md` 外不做任何文件
I/O,也没有任何 UI。它存在的意义是:此前只能通过 `.claude/skills/draft-broker-email` 这个 skill
才能触达的起草逻辑,现在可以被直接调用、并以确定性方式测试——未来后端服务(见下方"与 app spec 的
关系")真正要调用的,就是这同一条代码路径。

它是一层纯粹的编排(orchestration):不重新实现 triage、issue 分类或模板系统。它原样导入
`scripts/triage.py` 的 `triage()` 和 `scripts/corpus_report.py` 的 `classify_issue()`,并读取
skill 所用的同一批 `templates/<slug>.md` 骨架。真正新增的代码只有三块:LLM 边界(一个 port + 两个
适配器)、反捏造校验器,以及把这一切串起来的胶水函数 `draft()`。

## 组成部分

- **`engine/llm.py`** —— LLM 边界。
  - `LlmDraft` —— dataclass:`lang: str`、`body: str`、`filled_slots: dict[str, str]`、
    `missing: list[str]`。每个 `LlmClient` 实现都返回这一统一形状。
  - `LlmClient` —— 一个只有一个方法的 `Protocol`:`generate(*, system, template, facts,
    source_text, target_lang) -> LlmDraft`。下面的 `draft()` 只依赖这个 Protocol,从不依赖具体
    客户端,所以测试永远不会触网。
  - `FakeLlmClient` —— 全部 engine 测试使用的确定性桩(stub)。它对 `facts` 做简单的 `{slot}`
    替换(正则 `\{(\w+)\}`);任何在 `facts` 里找不到对应值的槽位,在正文里变成
    `[[MISSING: slot]]` 并被加入 `missing`。它不做真实翻译——只提供恰好足够的行为,让编排与校验
    逻辑可以在没有 LLM 调用的情况下被验证。
  - `GeminiLlmClient` —— 真实适配器(`gemini-2.5-flash`,经由 `google-genai` SDK)。需要
    `GEMINI_API_KEY`;构造的 prompt 会重申反捏造指令("仅使用这些事实来填充 factual 槽位……未知的
    factual 槽位留空写成 `[[MISSING: key]]`"),要求返回结构化 JSON
    (`{"lang","body","filled_slots","missing"}`),再映射为 `LlmDraft`。只有
    `tests/test_gemini_client.py` 会跑到它,该测试用
    `@pytest.mark.skipif(not os.environ.get("GEMINI_API_KEY"), ...)` 标记——它是整个测试套件里
    默认被跳过的那一个(32 passed, 1 skipped),只有存在真实 key 时才会真正执行。

- **`engine/validate.py`** —— 反捏造闸门。见下方"反捏造:`FACTUAL_SLOTS` 与 `warnings` 失败必现
  (fail-loud)机制"。

- **`engine/knowledge.py`** —— `load_template(slug)` 读取 `templates/<slug>.md`,返回其
  `## Skeleton` 标题下的正文(正则提取,遇到下一个 `## ` 停止)。这一层刻意做得很薄:本切片直接从
  磁盘读模板,和 skill 现有做法完全一致。app spec 里描述的、带版本、支持按 agent 覆盖的
  Knowledge service(§8,"Phase 0")是后续独立的一块工作——这个模块是它未来要替换掉的占位实现。

- **`engine/drafting.py`** —— 编排器。见下方"`draft()` 流水线"。

## `draft()` 流水线

`draft(req: DraftRequest, llm: LlmClient) -> DraftResult` 按顺序执行六个阶段:

```
triage(分流) → classify(分类) → template(选模板) → fill(填槽/LLM) → validate(校验)
```

1. **Triage(分流)** —— `scripts/triage.py` 的 `triage(req.body, req.sender)` 返回
   `"skip" | "billing-dispute" | "shipment"` 三者之一。
   - `"skip"` 立即短路返回:`DraftResult(triage="skip", issue="", template_slug="",
     draft_lang="", draft_body="")`——不加载模板、不发起 LLM 调用、不写任何东西。这与 skill 的
     规则一致:非可执行的邮件永远不会得到 case 文件夹或草稿。
2. **Classify(分类)**(仅对 `"billing-dispute"` / `"shipment"` 执行):
   - `"billing-dispute"` 将 `issue` 和模板 slug 都直接固定为 `"billing-dispute"`——triage 本身
     已经决定了类别,不再有单独的分类子步骤(与 `platform-architecture.md` 描述的 v2 流程一致)。
   - `"shipment"` 调用 `scripts/corpus_report.py` 的 `classify_issue(req.subject)`。如果它返回
     `"uncategorized"`,引擎会退回到 `"pickup"` 模板 slug 作为安全默认值,以保证流水线永远不会
     卡死——代码注释明确写出这是刻意的折衷("安全默认值;人工可纠正"),而不是断言这封邮件真的是
     在讲 pickup。现实中 `classify_issue` 无法细分的主题行,正是下方回归测试量出来的
     `unknown_shipment` 那一桶(535 里的 203)。
3. **Template(选模板)** —— `load_template(slug)`(`engine/knowledge.py`)读取选中的
   `templates/<slug>.md` 骨架。
4. **Fill(填槽/LLM)** —— `llm.generate(system="", template=template, facts=req.facts,
   source_text=req.source_text, target_lang=req.target_lang)` 产出原始的 `LlmDraft`。
   `req.facts` 携带调用方提供的确定性数值(BOL、PRO、地址等)——引擎从不要求 LLM 去"发明"这些
   值,只要求它去"使用"这些值。
5. **Validate(校验)** —— `validate_draft(raw, source_text=req.source_text)`(见下文)检查 LLM
   声称已填的每一个 factual 槽位是否能在原文里找到,把找不到的重写为 `[[MISSING: key]]`。
6. **结果** —— `DraftResult(triage=t, issue=issue, template_slug=slug,
   draft_lang=raw.lang, draft_body=v.body, missing=v.missing,
   rejected_slots=v.rejected, warnings=v.warnings)`。

`DraftRequest` 字段:`body, sender, subject, facts: dict[str,str] = {}, source_text: str
= "", target_lang: str = "en"`。

**失败必现(fail-loud)信号已传达给调用方:** `DraftResult` 携带一个 `warnings: list[str] = []`
字段,来自 `Validated.warnings`(见下文)。`draft()` 的调用方不再需要直接调用 `validate_draft()`
才能看到这条失败必现警告——它现在是返回值的一部分,可以直接在审批 UX(例如 agent 控制台)里展示,
而不只是停留在一行日志里。`tests/test_engine_drafting.py::test_draft_surfaces_validator_warnings`
用一个桩 LLM 断言了这条传递路径:该桩把某个 factual 值重新格式化,使其不再是草稿正文的逐字子串
(模拟真实 LLM 的格式漂移),从而强制走 `warnings` 路径而不是 `rejected`/脱敏路径。

## 反捏造:`FACTUAL_SLOTS` 与 `warnings` 失败必现(fail-loud)机制

这个引擎强制执行的最重要的不变量(沿袭自 `platform-architecture.md` 里"人工复核"这一惯例,现在
把它变成了机械化的强制规则)是:**绝不信任 LLM 陈述一个在原文里无法验证存在的事实。**

`engine/validate.py` 定义:

```python
FACTUAL_SLOTS: set[str] = {
    "BOL", "PRO", "pro", "pickup_address", "new_address", "contact_phone",
    "delivery_date", "charge_ref",
}
```

`validate_draft(raw: LlmDraft, *, source_text: str) -> Validated` 遍历
`raw.filled_slots`。对于每一个 key 在 `FACTUAL_SLOTS` 里的槽位,如果 LLM 声称的值不是
`source_text` 的逐字子串,就会被**拒绝**:

- 该 key 会同时被加入 `rejected` 和 `missing`;
- 草稿正文里该捏造值的每一处出现都会被替换为 `[[MISSING: key]]`。

不在 `FACTUAL_SLOTS` 里的槽位(比如 `customer_request`——这是语言表达,不是事实)从不受此约束;
只有对可核实的真实世界事实的陈述才会被检查。

**`warnings` 失败必现(fail-loud)机制。** 用字符串替换来做"脱敏"有一种失败模式:如果 LLM 在
`filled_slots` 里报告的捏造值,实际上并没有逐字出现在草稿 `body` 里(比如它在正文中把
"99999999999" 写成了不同的格式),那么 `body.replace(val, ...)` 就是一次空操作——返回的 body
不会有任何变化,仍然包含一个无法溯源的事实,却没有任何 `[[MISSING]]` 标记去标出它。此时如果
"悄悄地"返回这份 body,会比什么都不做更糟——因为它看起来像是干净通过了。所以 `validate_draft` 会
在替换尝试之后显式检查 `new_body == body`;如果什么都没变,它会往 `Validated.warnings` 里追加一
条消息(例如 `"unredacted factual slot 'BOL': value not found verbatim in draft body —
manual review required"`),而不是悄悄地"成功"。这条规则可以概括为:**一个无法被脱敏(redact)
的、无法溯源的事实性数值,必须产生一条警告,绝不能悄悄地视为成功。**

`Validated` 字段:`body: str, missing: list[str] = [], rejected: list[str] = [],
warnings: list[str] = []`。

## 原样复用 `scripts/`

`engine/drafting.py` 直接导入 `scripts.triage.triage` 和
`scripts.corpus_report.classify_issue`——没有包一层,没有重新实现,行为完全不变。这是刻意的:
triage/分类规则及其在全语料上已实测验证过的行为,是这个系统里承重(load-bearing)、已经被验证过的
那一部分(`concepts/drafting/issue-taxonomy.md`);引擎的职责只是把它们串在一个干净的函数签名后面。
未来任何对 triage/分类规则的改动,都会自动流入 `draft()`,不需要改这里的代码。

## 语料回归测试(regression harness)

`tests/test_corpus_regression.py` 是这个引擎的真值锁(ground-truth lock),它把合并后的全部
922 个文件(`LTL-mail/` + `LTL-mail-2/`)重放一遍,跑 `scripts/triage_report.py` 的
`triage_report()`:

```python
def test_triage_distribution_locked():
    r = triage_report()
    assert r["counts"] == {"skip": 327, "billing-dispute": 60, "shipment": 535}
    assert len(r["unknown_shipment"]) == 203
```

这些数字与 `issue-taxonomy.md` 的"v2 triage 分布"一节里记录的真实实测分布完全一致——写这条测试
的目的是:未来任何一次对 `scripts/triage.py` 规则的改动,只要改变了全语料分布,就会被立刻发现,
而不是等到生产流量里才被发现。922 这个总数 = 71(`LTL-mail/`)+ 851(`LTL-mail-2/`)。

同一个文件里还有 `test_engine_replays_known_cases()`,它把三份具有代表性的真实 `.eml` 文件端到端
地跑过 `draft()`(而不只是 `triage()`),并断言每一份的 `DraftResult.triage` 符合预期:

| 文件 | 期望的 `triage` |
| --- | --- |
| `LTL-mail-2/FFBA BOL# 60112079078.eml` | `billing-dispute` |
| `LTL-mail-2/10% Off Freight Promo LTL, Truckload And Expedited.eml` | `skip` |
| `LTL-mail/Re_ pickup --- 60114338678.eml` | `shipment` |

锁定的分布断言加上这三个重放用例,合在一起就是 app spec(§10,Phase 1)所说的"headless drafting
backend uniquely validated against ground truth by replaying the 922 historical emails"
所指的那套回归测试。

## 与 app spec 的关系

这个引擎是 `docs/superpowers/specs/2026-07-10-broker-app-system-design.md`(及其 `.zh.md`
对应版本)的**第一块建成的切片(first built slice)**。该 spec 的 §8("起草引擎内部")描述的是
同样形状的流水线——`TRIAGE → CLASSIFY → SELECT template → FILL → GENERATE → VALIDATE →
PERSIST`——作为一个后端服务;`engine/drafting.py` 的 `draft()` 今天实现了到 `VALIDATE` 为止的
一切,是无头的,还没有 `PERSIST` 这一步(目前没有 case 存储、没有 `pending_approval` 状态、也没有
agent 控制台——见下方"本切片范围之外")。spec 的 §12("从 `hs` 复用什么")明确指出
`scripts/triage.py` 和 `scripts/corpus_report.py` 会被直接复用;这个引擎正是把那份复用真正接线成
一个可导入、可测试的函数的地方,而不再只能通过 `draft-broker-email` skill 的手工流程去触达。

## 测试策略

`python3 -m pytest -q` → 33 passed, 1 skipped(那个被保护的、需要真实 Gemini 的测试,没有
`GEMINI_API_KEY` 时会被跳过)。覆盖 `engine/` 的测试文件:

- `tests/test_engine_llm.py` —— `FakeLlmClient` 的填槽/`[[MISSING]]` 行为。
- `tests/test_engine_validate.py` —— 上面描述的五种反捏造/警告场景。
- `tests/test_engine_drafting.py` —— `draft()` 的三条分流分支(skip / billing / shipment),
  用 `FakeLlmClient`。
- `tests/test_corpus_regression.py` —— 锁定的全语料分布,以及三个用例通过 `draft()` 的重放。
- `tests/test_gemini_client.py` —— 受保护的、真实联网的 `GeminiLlmClient` 集成测试。

## 本切片范围之外(Out of scope)

以下内容延后到 app spec 的后续阶段,今天的 `engine/` 里不包含:

- 持久化(没有 `Case`/`Message` 数据库表;`DraftResult` 只是一个内存值)。
- 身份与关系模型(users、orgs、engagements、broker accounts)。
- 邮件传输层(通过真实邮箱收发)。
- Agent 控制台(审批队列、复核 UX)。
- 带版本、支持按 agent 覆盖的 Knowledge service(`engine/knowledge.py` 是它未来要替换掉的、
  读磁盘的占位实现)。
