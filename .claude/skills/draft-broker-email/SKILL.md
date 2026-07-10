---
name: draft-broker-email
description: Use when the shipper (Justnano) needs to draft an English email to the freight broker (Priority-1) about a shipment issue or billing dispute. Parses the .eml thread, first triages it into skip/billing-dispute/shipment, then (for the latter two) classifies issue×response and drafts from templates for human review. Never sends.
---

# Draft Broker Email

## 何时使用

客户经微信(中文)提出某个 BOL 的问题,需要给经纪人 Priority-1 发英文邮件时。也覆盖 Priority1
自己发来的 FFBA/计费差异通知(billing-dispute)——不只是客户主动发起的货运诉求。

## 流程(必须逐步执行)

1. **定位 case**:向用户确认 BOL,或从给定 `.eml` 解析。运行
   `python3 scripts/parse_eml.py "<file.eml>"` 生成 `cases/<BOL>/thread.md`;读它。
   若 `cases/<BOL>/thread.md` 已存在(之前已解析过),直接读取,无需重新解析。
   **快照选择(重要,v2 起语料分布在两个目录):** 同一 BOL 常有多份快照文件
   (`…(1)…(8).eml`),它们是同一线程的不同增长阶段,分散在 `LTL-mail/` 与 `LTL-mail-2/`
   两个目录里;`parse_eml.py` 每次运行会**覆盖** `thread.md`。务必解析**体积最大/最新**的
   那份,否则 thread 会漏掉 broker 最新的回复,导致后续分类基于过时线程。优先用
   `scripts/corpus.py` 的 `merged_best()`(内部调用 `scripts/parse_eml.py` 的
   `dedupe_snapshots`,已跨 `LTL-mail/` + `LTL-mail-2/` 两个目录合并同一 BOL 的全部快照)
   选出该 BOL 体积最大的那份来解析。
   **⚠️ 关键警告(一个 BOL 可能有两个不同话题的线程):** 合并语料里约 24/141 个 BOL
   同时挂着**一条运输线程**和**一条独立的账单/FFBA 线程**(如 `60114592263`:POD 运输线程 +
   "$500–$700 改送费"账单线程)。`merged_best()` 只按 BOL 取体积最大的那一份,会**悄悄丢弃
   另一话题的线程**。因此当用户/broker 指名的是某个具体话题(尤其账单)时,**直接解析他引用
   的那封 `.eml`**,不要盲目采用 `merged_best()`——否则可能把账单争议误当运输线程、triage 成
   `shipment`,把真正要回的账单邮件漏掉。
2. **TRIAGE(前置分流,v2 新增)**:取 thread 中最新一封来信的正文与发件人,调用
   `scripts/triage.py` 的 `triage(body, sender)`——治理文档是
   `knowledge/concepts/drafting/issue-taxonomy.md` 的 "v2:`triage` 前置维度" 一节,
   结果分三支:
   - **`skip`** —— 非可执行邮件(broker 的营销推广/月结 statement/drayage 报价询价/
     会议邀请/out-of-office 自动回复等)。明确告知用户"这是不可执行邮件,不起草",
     **流程到此结束**,不进入下面任何步骤,不写 `cases/<BOL>/drafts/`。
   - **`billing-dispute`** —— 经纪人/承运商提出的额外收费或计费差异(FFBA pricing
     variance、out-of-route、reweigh/reclass、accessorial 等)。issue type 已由 triage
     直接固定为 `billing-dispute`(模板固定为 `templates/billing-dispute.md`),**跳过**
     下面第 4 步里的 issue-type 判定(只做该步的 response-type 判定,机制与 `shipment`
     分支相同,不重复展开——见第 4 步);其余步骤(第 3/4/5/6/7/8 步)照常进行,选模板
     环节固定为 `templates/billing-dispute.md`,分支挑选按
     `knowledge/connections/issue-to-template-flow.md` 的 `billing-dispute` 小节(见
     第 5 步)。
   - **`shipment`** —— 其余货运类诉求,继续走第 3 步起完整的 v1 两维(issue×response)
     分类流程与对应模板。
3. **粘贴客户诉求**:请用户粘贴该问题的微信中文原文(若有)。`billing-dispute` 分支下,
   若无客户诉求(如 broker 主动发来的 FFBA 通知),该步可为空,`{dispute_basis}` 留空。
4. **分类(response-type 判定对 `shipment`/`billing-dispute` 两分支都适用;issue-type
   判定仅 `shipment` 分支需要,`billing-dispute` 分支已在第 2 步固定,跳过下面第一条)**:
   - issue type(仅 `shipment` 分支):用 `scripts/corpus_report.py` 的 `classify_issue`
     (按邮件主题匹配),或按 `knowledge/concepts/drafting/issue-taxonomy.md` 的定义
     人工判断。
   - broker response type(`shipment`/`billing-dispute` 两分支都要做,判定方法相同):
     读 thread 中最新一轮 broker 邮件,按
     `knowledge/concepts/drafting/response-taxonomy.md` 的判定优先级(先看
     `confirmed-completed` → `declined` → `needs-info` → `offered-alternative` →
     否则 `accepted`)分类。
   若两者中任一维度都没有匹配的现有类别 → 按 same-task 规则先更新对应分类文章
   (`issue-taxonomy.md` 或 `response-taxonomy.md`),记录真实依据(引文/出处),
   再继续起草。不要先起草、之后"回头补文档"。
5. **选模板**:打开 `templates/<issue-type>.md`(`billing-dispute` 分支固定为
   `templates/billing-dispute.md`),读其四个小节(`## Skeleton` / `## Slots` /
   `## Tone` / `## Examples`)。按第 4 步判定的 broker response type 选用其分支/措辞
   ——具体矩阵见 `knowledge/connections/issue-to-template-flow.md`(已成熟,列出
   `needs-info`/`declined`/`accepted`/`offered-alternative` 在各高频 issue 下、以及
   `billing-dispute` 下的措辞差异)。若 response type 判定含糊,按该文档的默认原则:
   偏向 `needs-info` 措辞(问询/澄清,不过度承诺)。
6. **填槽**:
   - `{BOL}`、`{pro_clause}`、地址、联系人等结构化槽位从 `thread.md` 确定性提取填入。
   - `{customer_request}`(及各模板专属的诉求类槽,如 `{cancel_reason}`、
     `{requested_window}`、`{damage_desc}`、`{return_reason}`、`{dispute_basis}`)由本轮
     客户微信中文诉求翻译为英文,压缩为一句话;若客户没有额外诉求,该槽留空(按模板
     Slots 小节的说明)。
   - **不得臆造**地址、日期、费用、联系方式等事实性内容——thread 与微信原文都没有
     的,填 `[[MISSING: 描述缺什么]]`,交给人工审核补全,不猜测。
   - `{new_address}` 一类的地址槽必须原文照抄,不翻译、不规范化改写。
   - `{shipper_signoff}` 固定使用 `template-system.md` 里记录的 Justnano 签名全文。
7. **落盘**:写 `cases/<BOL>/drafts/<递增序号>.md`(序号从 1 开始,若目录已有草稿,
   取现有最大序号 + 1),内容包含三部分:
   - 分类结果(triage 结果;`shipment` 分支还需 issue type、response type,及判定依据
     的简短引文/理由;`billing-dispute` 分支只需 response type 及依据)。
   - 所选模板(`templates/<issue-type>.md` 的路径,及采用的分支/措辞)。
   - 最终英文草稿全文(可直接复制发送的完整邮件正文)。
8. **停下**:向用户展示草稿文件路径与正文,明确说明"此邮件尚未发送,请人工审核后再发送"。
   绝不代为发送邮件,也不建议使用邮件客户端自动发送。

## 约束

- 模板骨架永远是英文(发给经纪人看);客户的中文诉求经翻译后才能填入槽位。
- 每次遇到新的 issue 类别或 broker response 类别(现有 10 个运输类 issue slug +
  `billing-dispute`,合计 11 个 / 6 个 response slug 都覆盖不了),必须在同一任务内更新
  `knowledge/concepts/drafting/issue-taxonomy.md` 或 `response-taxonomy.md`,
  并在 `knowledge/log.md` 追加记录(same-task 规则,参见 `CLAUDE.md`)。
- 同理,`triage(body, sender)` 的三桶判定(`skip`/`billing-dispute`/`shipment`)出现
  误判或新的不可执行邮件模式时,同一任务内更新 `scripts/triage.py` 与
  `issue-taxonomy.md` 的 "v2:`triage` 前置维度" 一节,并记 `log.md`。
- 永远不臆造事实性槽位(地址/日期/费用/联系方式);缺失一律 `[[MISSING: …]]`。
- 永远不自动发送邮件;每次起草流程都必须在最后一步(第 8 步)停下等待人工审核。
- `triage == skip` 的邮件不写草稿、不落盘、不进入 `knowledge/connections/issue-to-template-flow.md`
  的任何矩阵分支。
