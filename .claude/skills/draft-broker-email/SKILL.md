---
name: draft-broker-email
description: Use when the shipper (Justnano) needs to draft an English email to the freight broker (Priority-1) about a shipment issue. Parses the .eml thread, classifies issue×response, and drafts from templates for human review. Never sends.
---

# Draft Broker Email

## 何时使用

客户经微信(中文)提出某个 BOL 的问题,需要给经纪人 Priority-1 发英文邮件时。

## 流程(必须逐步执行)

1. **定位 case**:向用户确认 BOL,或从给定 `.eml` 解析。运行
   `python3 scripts/parse_eml.py "<file.eml>"` 生成 `cases/<BOL>/thread.md`;读它。
   若 `cases/<BOL>/thread.md` 已存在(之前已解析过),直接读取,无需重新解析。
2. **粘贴客户诉求**:请用户粘贴该问题的微信中文原文(若有)。
3. **分类(两维)**:
   - issue type:用 `scripts/corpus_report.py` 的 `classify_issue`(按邮件主题匹配),
     或按 `knowledge/concepts/drafting/issue-taxonomy.md` 的定义人工判断。
   - broker response type:读 thread 中最新一轮 broker 邮件,按
     `knowledge/concepts/drafting/response-taxonomy.md` 的判定优先级(先看
     `confirmed-completed` → `declined` → `needs-info` → `offered-alternative` →
     否则 `accepted`)分类。
   若两者中任一维度都没有匹配的现有类别 → 按 same-task 规则先更新对应分类文章
   (`issue-taxonomy.md` 或 `response-taxonomy.md`),记录真实依据(引文/出处),
   再继续起草。不要先起草、之后"回头补文档"。
4. **选模板**:打开 `templates/<issue-type>.md`,读其四个小节(`## Skeleton` /
   `## Slots` / `## Tone` / `## Examples`)。按 broker response type 选用其分支/措辞
   ——具体矩阵见 `knowledge/connections/issue-to-template-flow.md`(已成熟,列出
   `needs-info`/`declined`/`accepted`/`offered-alternative` 在各高频 issue 下的措辞差异)。
   若 response type 判定含糊,按该文档的默认原则:偏向 `needs-info` 措辞(问询/澄清,
   不过度承诺)。
5. **填槽**:
   - `{BOL}`、`{pro_clause}`、地址、联系人等结构化槽位从 `thread.md` 确定性提取填入。
   - `{customer_request}`(及各模板专属的诉求类槽,如 `{cancel_reason}`、
     `{requested_window}`、`{damage_desc}`、`{return_reason}`)由本轮客户微信中文诉求
     翻译为英文,压缩为一句话;若客户没有额外诉求,该槽留空(按模板 Slots 小节的说明)。
   - **不得臆造**地址、日期、费用、联系方式等事实性内容——thread 与微信原文都没有
     的,填 `[[MISSING: 描述缺什么]]`,交给人工审核补全,不猜测。
   - `{new_address}` 一类的地址槽必须原文照抄,不翻译、不规范化改写。
   - `{shipper_signoff}` 固定使用 `template-system.md` 里记录的 Justnano 签名全文。
6. **落盘**:写 `cases/<BOL>/drafts/<递增序号>.md`(序号从 1 开始,若目录已有草稿,
   取现有最大序号 + 1),内容包含三部分:
   - 分类结果(issue type、response type,及判定依据的简短引文/理由)。
   - 所选模板(`templates/<issue-type>.md` 的路径,及采用的分支/措辞)。
   - 最终英文草稿全文(可直接复制发送的完整邮件正文)。
7. **停下**:向用户展示草稿文件路径与正文,明确说明"此邮件尚未发送,请人工审核后再发送"。
   绝不代为发送邮件,也不建议使用邮件客户端自动发送。

## 约束

- 模板骨架永远是英文(发给经纪人看);客户的中文诉求经翻译后才能填入槽位。
- 每次遇到新的 issue 类别或 broker response 类别(现有 9 个 issue slug /
  6 个 response slug 都覆盖不了),必须在同一任务内更新
  `knowledge/concepts/drafting/issue-taxonomy.md` 或 `response-taxonomy.md`,
  并在 `knowledge/log.md` 追加记录(same-task 规则,参见 `CLAUDE.md`)。
- 永远不臆造事实性槽位(地址/日期/费用/联系方式);缺失一律 `[[MISSING: …]]`。
- 永远不自动发送邮件;每次起草流程都必须在第 7 步停下等待人工审核。
