---
title: Customer Issue Taxonomy
type: concept
area: drafting
updated: 2026-07-09
status: mature
references:
  - concepts/drafting/response-taxonomy.md
  - connections/issue-to-template-flow.md
---

# Customer Issue Taxonomy

客户(经微信中文)提出、由 shipper 转达给经纪人的**诉求类型**。类别是从数据中涌现并经人工整理的:每遇到一个现有类别覆盖不了的新 `.eml`,必须在同一任务内补进本表(same-task 规则)。分类规则实现在 `scripts/corpus_report.py` 的 `RULES`,与本文保持同步。

分类依据是主题行(subject)。计数为对全部 71 个 `LTL-mail/*.eml` 跑 `corpus_report()` 得到的 **BOL 出现数(含同一线程的多份快照,故会高于唯一 BOL 数)**;全部文件均可归类,`unknown = []`。

## 类别(9 类,按出现频次排序)

| Slug | 客户诉求(中文定义) | 计数 | 真实示例文件 |
| --- | --- | --- | --- |
| `pickup` | 安排、催促或确认承运商上门提货;常见为"已下单但迟迟未取件,请推动尽快提货"。 | 21 | `Re_ pickup --- 60114338678.eml`、`Re_ Pickup --- 60113887167.eml`、`Re_ Pickup ---  60113972601.eml` |
| `shipment-status` | 查询货物当前状态、位置或预计到达情况("请与承运商核实,没有任何更新")。 | 20 | `Re_ Shipment status --- 60114476384.eml`、`Re_ Shipment status --- 60114356900.eml`、`Re_ Shipment status ---60113656921.eml` |
| `pro-lookup` | 查询或核对承运商的 PRO(跟踪)号。 | 11 | `Re_ Pro# ---- 60114662390.eml`、`Re_ 回复： Pro# ---- 60114662390.eml` |
| `pod-request` | 索取签收凭证(Proof of Delivery)。 | 10 | `Re_ POD --- 60114592263.eml`、`Re_ POD --- 60113820484.eml`、`Re_ POD --- 60113837994.eml` |
| `cancellation` | 取消一票 shipment(有时附带"我方账号只能下单不能取消,请协助")。 | 6 | `Re_ Cancel shipment --- 60114304778.eml`、`Re_ Cancel --- 60113887167.eml`、`Re_ Cancel ---- 60114838856, 60114838936.eml` |
| `reconsignment` | 改配/重新配送到新地址(主题仅为裸 BOL 号、无关键词;正文要求 reconsign)。**本类别由全语料扫描新发现**,种子表原先没有。 | 4 | `Re_ 60113972680.eml`(及其 `(1)(2)(3)` 快照) |
| `delivery-window` | 预约、指定或更改送达时间窗(如"6 号中午前直送、无需预约")。 | 4 | `Re_ Delivery window --- 60114839031.eml`(及其 `(1)(2)(3)` 快照) |
| `damage` | 货物损坏(如木箱底部破损)并请求紧急/尽早送达。 | 2 | `Re_ Urgent Delivery Request – Crate Damaged _ 60114821897.eml`、`Re_ 回复： Urgent Delivery Request – Crate Damaged _ 60114821897.eml` |
| `return-reason` | 询问退运原因,并索要 POD / 司机备注(常牵涉是否应付费用)。 | 1 | `Re_ Request for Return Reason --- 60113820374.eml` |

## 说明与消歧

- `reconsignment` 的真实印证(读 `cases/60113972680/thread.md`):客户来电要求把这票 reconsign 到新地址 `122 Timberline Dr, Unit 100, Spring Hill, TN 37174`,经纪人回问是否仍需预约、是否有更新的联系人。
- `delivery-window` 与 `reconsignment` 的区别:前者改的是**时间**(预约/时间窗),后者改的是**收货地址**。
- `Statue` 是语料中 `Status` 的拼写错误,`RULES` 已一并匹配到 `shipment-status`。
- 常见并发关系:`delivery-access`/`damage` 在客户同意后常转为 `pickup`(改到 terminal 自提)。种子表曾列出 `delivery-access`,但当前 71 个文件的主题未单独出现该关键词,已并入 `damage`/`pickup` 场景;若后续出现独立的通行受限主题,按 same-task 规则新增。
