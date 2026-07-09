# Template: reconsignment

> 说明(中文):改配/重新配送到新地址(与 `delivery-window` 的区别:这里改的是**地址**,
> 不是时间窗)。主题往往是裸 BOL 号、无关键词。经纪人回复常见 `needs-info`("Can you confirm
> if the consignee still requires an appointment? Do you have an updated point of contact?")。
> 骨架保持英文。

## Skeleton

Hi {broker_contact},

Please reconsign shipment {BOL}{pro_clause} to the following new address:
{new_address}

New contact: {contact_name}, {contact_phone}

Please advise if this is approved and confirm whether an appointment is still required.

Thank you,
{shipper_signoff}

## Slots

- `{broker_contact}` — 经纪人联系人名(取自最近一轮 broker 邮件签名);缺失则用 "team"。
- `{BOL}` — case 号(必填)。
- `{pro_clause}` — 若有 PRO#,填 " (PRO# {pro})",否则空串。
- `{new_address}` — 客户提供的新收货地址,原文照抄不改写;必填,缺失填 `[[MISSING: …]]`。
- `{contact_name}` / `{contact_phone}` — 新地址的联系人姓名/电话;取自 thread 或客户微信;缺失填 `[[MISSING: …]]`。
- `{shipper_signoff}` — 固定 Justnano 签名(见 template-system.md)。

## Tone

简洁、明确给出新地址与联系人;地址是事实性数据,一字不差抄录,不做翻译或规范化改写。

## Examples

- `LTL-mail/Re_ 60113972680.eml`(及其 `(1)(2)(3)` 快照;经纪人 Jalen Turner 转述:"The customer called and needs this to be reconsigned to their new address. Their address is 122 Timberline Dr, Unit 100, Spring Hill, TN 37174."；broker `needs-info`:"Can you confirm if the consignee still requires an appointment? Do you have an updated point of contact?" — 见 `cases/60113972680/thread.md`)
