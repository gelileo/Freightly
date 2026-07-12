---
title: Broker Response Taxonomy
type: concept
area: drafting
updated: 2026-07-09
status: mature
references:
  - concepts/drafting/issue-taxonomy.md
  - connections/issue-to-template-flow.md
---

# Broker Response Taxonomy

经纪人(Priority-1 / LTL West,常转达承运商)回复的**类型**,是分类的第二个维度;与[客户问题类型](issue-taxonomy.md)组合后决定回复模板与措辞。

语料中经纪人的最新一轮回复通常**极短**(如 "Checking"、"canceled"、"Working on this"、"Relayed to ABF"),真正的实质答复往往出现在更深的历史轮次里。以下定义与引文均取自真实线程(用 CLI 生成 `cases/<BOL>/thread.md` 后阅读)。

## 类别(6 类)

| Slug | 中文定义 | 真实引文/依据(英文原文保留;注明说话人) | 出处 |
| --- | --- | --- | --- |
| `accepted` | 接受诉求并已在推进/受理,但尚未给出结果。 | broker 原话:"reaching out to carrier!" / "Working on this" | `cases/60114338678`(pickup)、`cases/60114821897`(damage) |
| `declined` | 拒绝诉求或明确不予让步(如坚持收费)。 | broker 原话:"The carrier will still apply charges, as the freight was tendered, picked up, and later returned to the shipper." | `cases/60113820374`(return-reason) |
| `offered-alternative` | 提出替代方案(如改用平板/箱式车、或收货方到 terminal 自提)。 | **注意:此依据非 broker 原话**——为客户转述承运商方案:"may need a flatbed truck or box truck to deliver to the customer's door"。语料中经纪人**主动、独立**给出替代方案的明确引文较少;此格记录的是最接近的替代方案依据。 | `cases/60114821897`(damage,Turn 1 由 `hs@example.com` 所写) |
| `needs-info` | 需要更多信息才能推进(预约、联系人、地址、PRO 等)。 | broker 原话:"Can you confirm if the consignee still requires an appointment? Do you have an updated point of contact?" | `cases/60113972680`(reconsignment) |
| `quoted-cost-eta` | 给出费用/收费口径或时间口径。语料中**费用**类明确(见 return-reason 收费说明);**明确到达日期(ETA)**在已采样线程中罕见——多为 "Checking"/"Per carrier:" 之类过程性答复,尚无硬性日期承诺。 | broker 原话(费用口径):"The carrier will still apply charges …";ETA 暂无硬性示例。 | `cases/60113820374` |
| `confirmed-completed` | 确认动作已完成(已取消、已送达、POD 已附)。 | broker 原话:"canceled" / "Per carrier: POD attached" | `cases/60114304778`(cancellation)、`cases/60114476384`(shipment-status) |

## 优先级与判定说明

- 一封 broker 邮件可能混合信号(如 `needs-info` + `offered-alternative`)。判定优先级:先看是否**已完成**(`confirmed-completed`)→ 是否**拒绝**(`declined`)→ 是否**索要信息**(`needs-info`)→ 是否**给方案**(`offered-alternative`)→ 否则 `accepted`(在办)。
- 超尺寸/货损线程(BOL 60114821897)是典型多轮案例:`declined`(常规/小车送不了)→ `offered-alternative`(平板/箱车或 terminal 自提)→ 客户接受自提后转为 `pickup`。
- `quoted-cost-eta` 的 ETA 子类在当前 71 文件中样本稀少;若后续线程出现明确到达日期,按 same-task 规则补一条真实引文。
- **v2(2026-07-09):** 账单侧(`issue-taxonomy.md` 的 `billing-dispute`)broker 回复复用现有 6 类,不新增 slug——常见 `needs-info`(索要承运商支持文件/发票等)、`declined`(坚持收费)、`accepted`(同意代为 dispute);暂不新增,除非后续语料出现这 6 类覆盖不了的情形,再按 same-task 规则补充。
