# Template: delivery-window

> 说明(中文):预约、指定或更改送达时间窗(与 `reconsignment` 的区别:这里改的是**时间**,
> 不是地址)。经纪人回复多为 `accepted`("Relayed to ABF")。骨架保持英文。

## Skeleton

Hi {broker_contact},

For shipment {BOL}{pro_clause}, please advise the carrier of the following delivery window:
{requested_window}

Receiver contact: {receiver_contact}

Thank you,
{shipper_signoff}

## Slots

- `{broker_contact}` — 经纪人联系人名;缺失则用 "team"。
- `{BOL}` — case 号(必填)。
- `{pro_clause}` — 若有 PRO#,填 " (PRO# {pro})",否则空串。
- `{requested_window}` — 客户要求的送达时间窗译文(如 "direct delivery by noon on the 6th, no appointment needed");必填,缺失填 `[[MISSING: …]]`。
- `{receiver_contact}` — 收货人联系方式(姓名/电话),取自 thread;缺失填 `[[MISSING: …]]`。
- `{shipper_signoff}` — 固定 Justnano 签名(见 template-system.md)。

## Tone

简洁、明确给出时间窗;若客户要求"无需预约"要原样传达,不做主观解释。

## Examples

- `LTL-mail/Re_ Delivery window --- 60114839031.eml`(客户:"please advise carrier no need appointment, the receiver has requested direct delivery by noon on the 6th"；broker:"Relayed to ABF")
