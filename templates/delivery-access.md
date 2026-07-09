# Template: delivery-access

> 说明(中文):因尺寸/设备/道路原因无法常规送达(装不上 liftgate、bobtail 进不去、路太窄),
> 需协调替代车型或改 terminal 自提。多由 broker 转述承运商而**发起**(broker response 常为
> `declined` + `offered-alternative`)。骨架保持英文。**不臆造**替代方案是否可行、费用、或客户的
> 最终选择——未定的填 `[[MISSING: …]]`。客户一旦同意 terminal 自提,issue 转为 `pickup`。

## Skeleton

Hi {broker_contact},

Regarding shipment {BOL}{pro_clause}: {access_constraint}

{proposed_resolution}

Thank you,
{shipper_signoff}

## Slots

- `{broker_contact}` — 经纪人联系人名(取自其来信签名);缺失则用 "team"。
- `{BOL}` — case 号(必填)。
- `{pro_clause}` — 若有 PRO#,填 " (PRO# {pro})",否则空串。
- `{access_constraint}` — 无法送达的具体原因,照实转述(如 "AAA reports the crate's dimensions will not fit on a liftgate, and it will not fit on the bobtail that runs the receiver's area.");必填,缺失填 `[[MISSING: …]]`。
- `{proposed_resolution}` — 下一步请求:询问是否可安排替代车型(平板/箱式/更小的车)及最早送达日期与是否有额外费用;和/或确认 terminal 自提方案(附 terminal 地址,若已知)。**客户的最终选择未确认时,必须以 `[[MISSING: 客户决定]]` 标出,不代客户拍板。**
- `{shipper_signoff}` — 固定 Justnano 签名(见 template-system.md)。

## Tone

先客观陈述为何常规配送不可行,再给明确的下一步请求;不承诺理赔口径,不臆造费用/日期/客户决定。

## Examples

- BOL 60114821897(broker 来信):"these dimensions will not fit on a liftgate … it will not fit on our bobtail that runs that area … The receiver can come pick this up at the terminal for no cost."(broker response:`declined` + `offered-alternative`;terminal 地址 900 E Street, West Sacramento CA 95605;PRO# 72406971。)
