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

## 类别(10 类,按出现频次排序;`billing-dispute` 为 v2 新增,见下方说明)

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
| `delivery-access` | 因**尺寸/设备/道路**原因无法按常规送达(货太大装不上 liftgate、bobtail 进不去、道路太窄),需协调替代车型或改 terminal 自提。**主题行无固定关键词,常出现在 broker 转述承运商的正文里**;`classify_issue` 靠主题匹配不到,需人工判定。 | 0(语料主题中无独立样本;见下方说明) | broker 来信正文,如 "these dimensions will not fit on a liftgate … will not fit on our bobtail … receiver can come pick this up at the terminal"(BOL 60114821897) |
| `return-reason` | 询问退运原因,并索要 POD / 司机备注(常牵涉是否应付费用)。 | 1 | `Re_ Request for Return Reason --- 60113820374.eml` |
| `billing-dispute` | 经纪人/承运商提出的**额外收费或计费差异**(FFBA Free Freight Bill Audit 的 pricing variance、out-of-route 费用、reweigh/reclass、accessorial 等),需先审再认、不当场认款。**来自 `LTL-mail-2/` 语料,非 71 篇 `LTL-mail/` 主表计数范围**。 | — | `LTL-mail-2/FFBA BOL# 60112079078.eml`(broker:"processed through Priority1's Free Freight Bill Audit and have accrued a pricing variance … additional charge(s) … Priority1 CAN dispute")、`LTL-mail-2/BOL 60114409180 _ P-118701-2621.eml`(broker William Jerry 转 Warp:"out of route charge … driver was redirected … 145b Talmadge Rd, Edison, NJ") |

## v2:`triage` 前置维度(governs `scripts/triage.py`)

v2 引入了 `triage` 作为**分类前的前置维度**,先于本表所有 issue slug 生效,决定一封来信是否值得起草。三个结果:

- `skip` —— 非可执行(broker 的营销推广、月结 statement、drayage/集装箱到港通知、out-of-office/日历邀请等)。**不起草**,不进入下面任何 issue 类别。
- `billing-dispute` —— 见上表新行;**可起草**,专用模板 `templates/billing-dispute.md`。
- `shipment` —— 其余所有货运类诉求(即本表 `pickup`/`shipment-status`/`pro-lookup`/`pod-request`/`cancellation`/`reconsignment`/`delivery-window`/`damage`/`delivery-access`/`return-reason` 九类的总闸门);**可起草**,再按主题/正文细分到具体 issue slug。

本文是 `triage` 维度的**治理文档(governing doc)**:`scripts/triage.py` 的判定规则(`_SKIP_SENDER`/`_SKIP_BODY`/`_BILLING` 三个正则)必须与此说明保持同步,新增或调整判定关键词时按 same-task 规则一并更新本节。`triage` 与本表下方的 issue 分类是**两个独立维度**——`triage` 决定"是否/去哪起草",issue 分类决定"用哪个模板骨架"。

## 说明与消歧

- `reconsignment` 的真实印证(读 `cases/60113972680/thread.md`):客户来电要求把这票 reconsign 到新地址 `122 Timberline Dr, Unit 100, Spring Hill, TN 37174`,经纪人回问是否仍需预约、是否有更新的联系人。
- `delivery-window` 与 `reconsignment` 的区别:前者改的是**时间**(预约/时间窗),后者改的是**收货地址**。
- `Statue` 是语料中 `Status` 的拼写错误,`RULES` 已一并匹配到 `shipment-status`。
- 常见并发关系:`delivery-access`/`damage` 在客户同意后常转为 `pickup`(改到 terminal 自提)。
- **关于 `delivery-access`(同一任务内新增,2026-07-09):** 该类别在建库时曾因"71 个语料文件的
  主题未单独出现"而并入 `damage`/`pickup`。后收到一封独立的 broker 来信(BOL 60114821897:货物
  尺寸装不上 liftgate、bobtail 进不去,承运商建议改 terminal 自提),`damage`(无货损)与 `pickup`
  (非主动约提货)的骨架都会**误述**该情形,故按 same-task 规则重新引入本类别并新增
  `templates/delivery-access.md`。因语料主题中仍无对应样本,`corpus_report()` 的 `by_issue`
  不会出现该 slug(计数 0),这属正常——它源于**正文/live 消息**而非主题。
- **关于 `billing-dispute`(v2 新增,2026-07-09):** 与上面 9 类不同,`billing-dispute` 不来自
  71 篇 `LTL-mail/` 主表(该表的计数与 `unknown = []` 断言均只覆盖 `LTL-mail/`),而来自 v2 新引入的
  `LTL-mail-2/`(Justnano 全量 broker 收件箱)语料;判定也不走 `classify_issue`/`corpus_report`
  的主题匹配,而由 `scripts/triage.py` 的 `_BILLING` 正则对**正文**匹配(FFBA/pricing variance/
  additional charge/out of route/accessorial/reweigh/reclass 等关键词)。因此表中"计数"列填 `—`,
  `tests/test_taxonomy.py`(仅跑 `LTL-mail/`)不覆盖它;其正确性由 `tests/test_triage.py` 与
  `tests/test_billing_template.py` 验证。
