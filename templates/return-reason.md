# Template: return-reason

> 说明(中文):询问退运原因,并索要 POD / 司机备注(常牵涉是否应付费用)。经纪人回复
> 常见 `declined`(坚持收费)。骨架保持英文;涉及费用争议时只陈述事实、请对方确认,不代客户下结论。

## Skeleton

Hi {broker_contact},

Shipment {BOL}{pro_clause} was returned. Please confirm the reason.
{return_reason}

Also, could you please provide the POD and any driver notes from the delivery attempt?

Thank you,
{shipper_signoff}

## Slots

- `{broker_contact}` — 经纪人联系人名;缺失则用 "team"。
- `{BOL}` — case 号(必填)。
- `{pro_clause}` — 若有 PRO#,填 " (PRO# {pro})",否则空串。
- `{return_reason}` — 若客户已提供背景或质疑(如"我们没收到取消邮件,是否需要付费?"),译成英文补充句;无则空。
- `{shipper_signoff}` — 固定 Justnano 签名(见 template-system.md)。

## Tone

事实陈述,不预设立场;涉及费用问题用疑问句让经纪人确认,不代客户主张免责。

## Examples

- `LTL-mail/Re_ Request for Return Reason --- 60113820374.eml`(客户:"This shipment was returned. Please confirm the reason. Also provide the POD and any driver notes from the delivery attempt."；broker `declined`:"The carrier will still apply charges, as the freight was tendered, picked up, and later returned to the shipper.")
