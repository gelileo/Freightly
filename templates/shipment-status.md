# Template: shipment-status

> 说明(中文):询问货物当前状态、位置或预计到达("请与承运商核实,没有任何更新")。
> 经纪人回复常见 `accepted`("relayed to the carrier")或 `confirmed-completed`("POD attached")。
> 骨架保持英文;客户微信中文由技能翻译后填入 `{customer_request}`。

## Skeleton

Hi {broker_contact},

Following up on BOL {BOL}{pro_clause} — {customer_request}
Last known status on file: {last_known_status}

Could you please check with the carrier for the latest status and expected delivery date?

Thank you,
{shipper_signoff}

## Slots

- `{broker_contact}` — 经纪人联系人名,取自最近一轮 broker 邮件签名;缺失则用 "team"。
- `{BOL}` — case 号(必填)。
- `{pro_clause}` — 若有 PRO#,填 " (PRO# {pro})",否则空串。
- `{customer_request}` — 客户微信诉求译文,如 "there has been no update since 06/03."(取自 thread 原句改写);无则空。
- `{last_known_status}` — thread 中最新的 broker/carrier 说法(如 "relayed to the carrier" / "no update since last check");缺失填 `[[MISSING: …]]`。
- `{shipper_signoff}` — 固定 Justnano 签名(见 template-system.md)。

## Tone

简洁、专业;强调"多日无更新"的紧迫感但不指责;不臆造 ETA 或位置。

## Examples

- `LTL-mail/Re_ Shipment status --- 60114476384(6).eml`(多轮:broker "This has been relayed to the carrier." → 最终 "Per carrier: POD attached")
- `LTL-mail/Re_ Shipment status --- 60114356900.eml`(客户:"there is no any update inforamtion from 05/20"；broker 回 "Checking")
