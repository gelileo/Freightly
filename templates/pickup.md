# Template: pickup

> 说明(中文):催促/安排提货。经纪人回复多为 `accepted`(reaching out to carrier)
> 或 `needs-info`。骨架保持英文;客户微信中文由技能翻译后填入 `{customer_request}`。

## Skeleton

Hi {broker_contact},

Following up on BOL {BOL}{pro_clause} — the shipment has not been picked up yet.
{customer_request}

Could you please contact the carrier and confirm the earliest pickup date?
Pickup details on file:
- Address: {pickup_address}
- Contact: {contact_name}, {contact_phone}

Thank you,
{shipper_signoff}

## Slots

- `{broker_contact}` — 经纪人联系人名(取自最近一轮 broker 邮件签名),缺失则用 "team"。
- `{BOL}` — case 号(必填,来自 thread)。
- `{pro_clause}` — 若有 PRO#,填 " (PRO# {pro})",否则空串。
- `{customer_request}` — 客户微信诉求,翻译成英文的一句话;无则空。
- `{pickup_address}` / `{contact_name}` / `{contact_phone}` — 取自 thread;缺失填 `[[MISSING: …]]`。
- `{shipper_signoff}` — 固定 Justnano 签名(见 template-system.md)。

## Tone

简洁、专业、面向经纪人;首句即给 BOL/PRO;不臆造地址/日期/费用。

## Examples

- `LTL-mail/Re_ pickup --- 60114338678.eml`(broker `accepted`:"reaching out to carrier!")
- `LTL-mail/Re_ Pickup --- 60113887167.eml`
