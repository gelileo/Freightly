# Template: damage

> 说明(中文):货物损坏(如木箱底部破损)并请求紧急/尽早送达。经纪人回复常见
> `accepted`("Working on this")或 `offered-alternative`(需平板车/箱车,或改到 terminal 自提,
> 此时常转为 `pickup`)。骨架保持英文;附件照片单独发送,邮件正文只描述。

## Skeleton

Hi {broker_contact},

Reporting a damage issue on shipment {BOL}{pro_clause}.
{damage_desc}
{customer_request}

This shipment is urgent — please contact the carrier and push for the earliest possible
resolution. Photos attached separately.

Thank you,
{shipper_signoff}

## Slots

- `{broker_contact}` — 经纪人联系人名;缺失则用 "team"。
- `{BOL}` — case 号(必填)。
- `{pro_clause}` — 若有 PRO#,填 " (PRO# {pro})",否则空串。
- `{damage_desc}` — 货损描述译文(如 "The wooden crate is damaged, especially the bottom part.");必填,缺失填 `[[MISSING: …]]`。
- `{customer_request}` — 客户具体诉求译文(如要求指定日期送达、或改用平板/箱车);无则空。
- `{shipper_signoff}` — 固定 Justnano 签名(见 template-system.md)。

## Tone

紧迫但专业;先说明损坏事实,再提具体请求;不承诺理赔口径,不臆造承运商方案。

## Examples

- `LTL-mail/Re_ Urgent Delivery Request – Crate Damaged _ 60114821897.eml`(客户:"the wooden crate is damaged, especially the bottom part... please contact the carrier and ask if they can deliver this shipment on July 7, or the earliest possible date"；broker:"Working on this")
