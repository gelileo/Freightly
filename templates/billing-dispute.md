# Template: billing-dispute

> 说明(中文):经纪人/承运商提出的**额外收费或计费差异**(FFBA Free Freight Bill Audit 的
> pricing variance、out-of-route 费用、reweigh/reclass、accessorial 等)。目标是**先审再认**:
> 请对方给出承运商支持文件、确认 Priority1 是否可代为 dispute,不当场认款、不臆造金额。骨架英文。

## Skeleton

Hi {broker_contact},

Regarding {charge_ref} on shipment {BOL}{pro_clause}: we would like to review this before it is invoiced.
{dispute_basis}
Could you please share the carrier's supporting documentation for this charge, and confirm whether Priority1 can dispute it on our behalf?

Thank you,
{shipper_signoff}

## Slots

- `{broker_contact}` — 经纪人联系人名(取自来信签名);缺失用 "team"。
- `{charge_ref}` — 该笔费用的指称,照实转述(如 "the FFBA pricing variance" / "the out-of-route charge to 145b Talmadge Rd");必填,缺失填 `[[MISSING: …]]`。
- `{BOL}` — case 号(必填)。
- `{pro_clause}` — 有 PRO# 填 " (PRO# {pro})",否则空串。
- `{dispute_basis}` — 我方异议/背景一句话(由客户微信译文或线程事实而来);无则留空。**不臆造金额或责任归属。**
- `{shipper_signoff}` — 固定 Justnano 签名(见 template-system.md)。

## Tone

先复述费用、要求支持文件与 dispute 途径;客观、不当场认款、不臆造金额或过错方。

## Examples

- `LTL-mail-2/FFBA BOL# 60112079078.eml`(broker:"processed through Priority1's Free Freight Bill Audit and have accrued a pricing variance … additional charge(s) … Priority1 CAN dispute")。
- `LTL-mail-2/BOL 60114409180 _ P-118701-2621.eml`(broker William Jerry 转 Warp:"out of route charge … driver was redirected … 145b Talmadge Rd, Edison, NJ")。
