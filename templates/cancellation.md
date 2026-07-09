# Template: cancellation

> 说明(中文):取消一票 shipment(有时附带"我方账号只能下单不能取消,请协助")。
> 经纪人回复多为 `confirmed-completed`("canceled")。骨架保持英文。

## Skeleton

Hi {broker_contact},

Please cancel shipment {BOL}{pro_clause}.
{cancel_reason}

Thank you,
{shipper_signoff}

## Slots

- `{broker_contact}` — 经纪人联系人名;缺失则用 "team"。
- `{BOL}` — case 号(必填)。
- `{pro_clause}` — 若有 PRO#,填 " (PRO# {pro})",否则空串。
- `{cancel_reason}` — 取消原因或补充说明译文(如账号权限问题);无则空串。
- `{shipper_signoff}` — 固定 Justnano 签名(见 template-system.md)。

## Tone

直接、简短;一句话请求;若涉及账号/权限问题需明确写出但不指责经纪人。

## Examples

- `LTL-mail/Re_ Cancel shipment --- 60114304778.eml`(客户:"Please cancel this shipment... our login ID is huang@justnanoinc.com, we only book a shipment but can not cancel it under this same ID."；broker:"canceled")
- `LTL-mail/Re_ Cancel --- 60113887167.eml`
