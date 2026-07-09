# Template: pod-request

> 说明(中文):索取签收凭证(Proof of Delivery)。经纪人回复多为 `accepted`
> ("We have requested this from the carrier.")或 `confirmed-completed`("POD attached")。
> 骨架保持英文。

## Skeleton

Hi {broker_contact},

Could you please help forward the POD (Proof of Delivery) for BOL {BOL}{pro_clause}?
{delivery_date_clause}

Thank you,
{shipper_signoff}

## Slots

- `{broker_contact}` — 经纪人联系人名;缺失则用 "team"。
- `{BOL}` — case 号(必填)。
- `{pro_clause}` — 若有 PRO#,填 " (PRO# {pro})",否则空串。
- `{delivery_date_clause}` — 若已知送达日期,填 "The shipment was delivered on {delivery_date}."一句;未知则空串(不臆造日期)。
- `{shipper_signoff}` — 固定 Justnano 签名(见 template-system.md)。

## Tone

简短、事务性;直接给出 BOL,一句话请求即可;无需铺垫背景。

## Examples

- `LTL-mail/Re_ POD --- 60114592263.eml`(客户:"Can you please help forward POD of below shipment"；broker:"We have requested this from the carrier.")
- `LTL-mail/Re_ POD --- 60113820484.eml`
