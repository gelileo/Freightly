# Template: pro-lookup

> 说明(中文):查询或核对承运商的 PRO(跟踪)号。经纪人回复常见 `accepted`("Checking")。
> 骨架保持英文,篇幅最短。

## Skeleton

Hi {broker_contact},

Shipment {BOL} was already picked up, but the PRO# is still not showing on our end.
Could you please advise?
{customer_request}

Thank you,
{shipper_signoff}

## Slots

- `{broker_contact}` — 经纪人联系人名;缺失则用 "team"。
- `{BOL}` — case 号(必填)。
- `{customer_request}` — 客户补充说明译文(如已知的近似取货日期);无则空。
- `{shipper_signoff}` — 固定 Justnano 签名(见 template-system.md)。

## Tone

极简、事务性;一两句话即可,不铺垫。

## Examples

- `LTL-mail/Re_ Pro# ---- 60114662390.eml`(客户:"Following shipment already picked up last week, but still not show Pro#, can you please help advise"；broker:"Checking")
- `LTL-mail/Re_ 回复： Pro# ---- 60114662390.eml`
