---
title: Issue-to-Template Flow
type: connection
area: drafting
updated: 2026-07-09
status: mature
references:
  - concepts/drafting/issue-taxonomy.md
  - concepts/drafting/response-taxonomy.md
  - concepts/drafting/template-system.md
  - concepts/drafting/platform-architecture.md
---

# Issue-to-Template Flow

How the two classification dimensions combine to pick a template and shape a draft.

## Rule

- **Issue type**(见 [issue-taxonomy](../concepts/drafting/issue-taxonomy.md))决定
  *用哪个* `templates/<issue-type>.md` 文件。
- **Broker response type**(见 [response-taxonomy](../concepts/drafting/response-taxonomy.md))
  决定同一模板下*用哪种措辞/分支*——例如 `pickup` 模板在上一轮 broker 回复是
  `needs-info`(补充缺失信息)时,与是 `declined`(转达客户下一步指示或接受替代方案)
  时,写法不同。

## 两种入口(完整循环)

1. **新问题**:尚无 broker 回复;客户微信原文直接驱动一封*首次*外发邮件,用issue
   模板的"开场"措辞(即模板 `## Skeleton` 的默认写法,通常等价于下表的
   `accepted`/首轮框架,因为还没有 broker 立场可参照)。
2. **进行中的线程**:已有 broker 回复;先按 `response-taxonomy.md` 的判定优先级
   (`confirmed-completed` → `declined` → `needs-info` → `offered-alternative` →
   否则 `accepted`)分类该回复,再挑*跟进*分支。超尺寸/货损线程是典范的多轮案例
   (见下方 `damage` 一节):`declined`(常规/小车送不了)→ `offered-alternative`
   (平板/箱车或 terminal 自提)→ 客户接受自提后,issue 类型转为 `pickup` 续写。

## Issue × Response → 模板分支矩阵

对每个高频 issue,下面列出 `needs-info` / `declined` / `accepted`(及相关时的
`offered-alternative`)三到四种 broker response 下,`templates/<issue-type>.md`
措辞应如何调整。**默认原则:response type 判定含糊时,偏向 `needs-info` 框架
——问询/澄清,不过度承诺**(不要在不确定时写成 `accepted` 的肯定语气,也不要写成
`confirmed-completed` 的既成事实语气)。

### `pickup`(模板:`templates/pickup.md`)

- **`accepted`**(真实引文:"reaching out to carrier!",`cases/60114338678`)——
  骨架默认分支:直接用 Skeleton 原句"Following up on BOL … the shipment has not
  been picked up yet. Could you please contact the carrier and confirm the earliest
  pickup date?"。`{customer_request}` 留空或只补充催促语气,因为 broker 已经在推进,
  无需重复施压。
- **`needs-info`**(推断默认,语料中无 pickup 专属引文,按 response-taxonomy 的通用
  needs-info 措辞类推,如 60113972680 的问法风格)——broker 上一轮若在问地址/联系人
  是否仍有效,`{customer_request}` 要直接回答该问题(如"the pickup address is
  unchanged, please confirm with the carrier"),而不是重复催促;`{pickup_address}`/
  `{contact_name}`/`{contact_phone}` 必须重新确认或原样重申,缺一项就 `[[MISSING: …]]`。
- **`declined`**(语料中无 pickup 专属 declined 引文;若出现,同 damage 的 declined
  处理方式)——若 broker 明确表示承运商无法按原计划取件,`{customer_request}` 改为
  询问下一步方案(是否需要改期、改用其他承运商),不要重复原始的"尽快取货"请求。

### `shipment-status`(模板:`templates/shipment-status.md`)

- **`accepted`**(真实引文:"relayed to the carrier" / "Checking",
  `cases/60114476384`、`cases/60114356900`)——默认分支:Skeleton 原句,
  `{last_known_status}` 填 broker 上一轮的说法原样转述("relayed to the carrier"),
  语气客观陈述"多日无更新"而不指责。
- **`confirmed-completed`**(真实引文:"Per carrier: POD attached",
  `cases/60114476384` 最终轮)——此时问题已解决,通常*不再*需要 `shipment-status`
  跟进邮件;若客户仍有疑问(如对 POD 内容有异议),改用 `pod-request` 或
  `return-reason` 模板,而不是继续用 shipment-status 的措辞。
- **`needs-info`**(语料中无 shipment-status 专属引文;按通用 needs-info 处理)——
  若 broker 反问 PRO#/取件日期等以便查询,`{customer_request}` 直接给出该信息
  (从 thread 或客户微信取,缺失则 `[[MISSING: …]]`),不要重复"请查最新状态"的原始请求。

### `pod-request`(模板:`templates/pod-request.md`)

- **`accepted`**(真实引文:"We have requested this from the carrier.",
  `cases/60114592263`)——默认分支:Skeleton 原句,一句话请求即可,`{delivery_date_clause}`
  留空(尚未确认送达日期)。
- **`confirmed-completed`**(真实引文:"Per carrier: POD attached",
  `cases/60114476384`)——POD 已给出;若此时还要起草邮件,通常是确认收到/核对内容有异议,
  应转 `return-reason` 或直接不起草(问题已解决)。
- **`needs-info`**(语料中无 pod-request 专属引文;按通用 needs-info 处理)——若 broker
  反问送达日期以便向承运商核实,`{delivery_date_clause}` 必须填已知送达日期
  ("The shipment was delivered on {delivery_date}.");不知道就 `[[MISSING: 送达日期]]`,
  不能凭空给一个日期。

### `delivery-window`(模板:`templates/delivery-window.md`)

- **`accepted`**(真实引文:"Relayed to ABF",`cases/60114839031`)——默认分支:
  Skeleton 原句,`{requested_window}` 原样转达客户要求的时间窗(如"无需预约"要
  一字不改地传达,不做主观解释)。
- **`needs-info`**(语料中无 delivery-window 专属引文;按通用 needs-info 处理,
  类比 `reconsignment` 的问法风格)——若 broker 反问是否仍需预约/联系人是否有更新,
  `{receiver_contact}` 必须给出最新联系人信息;若客户没提供新联系人,`[[MISSING: …]]`,
  不要照抄旧联系人当作"确认"。
- **`declined`**(语料中无 delivery-window 专属引文)——若 broker 表示该时间窗无法
  满足,`{requested_window}` 改写为向 broker 询问可行的替代时间窗,而不是重复原始
  时间窗要求。

### `cancellation`(模板:`templates/cancellation.md`)

- **`confirmed-completed`**(真实引文:"canceled",`cases/60114304778`)——默认分支:
  这是 cancellation 最常见的落点;若已 confirmed-completed,通常无需再起草邮件
  (向客户确认即可),除非客户对取消细节有异议。
- **`needs-info`**(语料中无 cancellation 专属引文;按通用 needs-info 处理)——若 broker
  反问账号权限或取消原因细节,`{cancel_reason}` 必须直接回答该问题(如账号只能下单
  不能取消的说明,`cases/60114304778` 客户原话可参照措辞),不要重复"请取消"的原始请求。
- **`declined`**(语料中无 cancellation 专属引文;费用场景类推自 `return-reason` 的
  declined 措辞)——若 broker 表示因已提货/已在途无法取消(或需收费),`{cancel_reason}`
  改为事实陈述+疑问句请对方确认收费口径,不代客户主张免责(同 `return-reason` 的 Tone)。

### `damage`(模板:`templates/damage.md`)—— 唯一有真实 `offered-alternative` 案例的 issue

超尺寸/货损线程 `cases/60114821897` 是典型多轮案例,四种 response 依次出现:

- **`declined`**(客户转述承运商立场:常规/小车无法送达)——`{customer_request}`
  说明为何常规配送不可行,请求 broker 联系承运商确认可行方案。
- **`offered-alternative`**(客户转述:"may need a flatbed truck or box truck to
  deliver to the customer's door")——`{customer_request}` 明确提出具体替代方案
  (平板车/箱式车,或改到 terminal 自提),让 broker 向承运商确认是否可行及是否有
  额外费用(不承诺理赔口径,不臆造费用数字)。
- **`accepted`**(真实引文:"Working on this",`cases/60114821897`)——默认分支:
  Skeleton 原句,`{damage_desc}` 描述损坏事实,`{customer_request}` 补充紧急送达
  的具体日期要求(如"July 7, or the earliest possible date"),语气紧迫但专业。
- **客户接受 terminal 自提后 → 转 `pickup`**——一旦客户同意改自提,issue 类型从
  `damage` 切换为 `pickup`,后续邮件改用 `templates/pickup.md`(自提地址填 terminal
  地址),不再用 damage 模板的"紧急/损坏"措辞。

### `reconsignment`(模板:`templates/reconsignment.md`)

- **`needs-info`**(真实引文:"Can you confirm if the consignee still requires an
  appointment? Do you have an updated point of contact?",`cases/60113972680`)——
  这是 reconsignment 最常见、也是本矩阵*唯一有真实引文*的分支:回复邮件必须逐一回答
  broker 提出的两个问题(预约需求、最新联系人),`{contact_name}`/`{contact_phone}`
  必须是本轮更新后的值,不能照抄旧地址的联系人。
- **`accepted`**(语料中无 reconsignment 专属 accepted 引文;按通用 accepted 处理)——
  若 broker 已受理但未提问,`{new_address}` 按 Skeleton 默认写法一次性给全(地址、
  联系人),`{customer_request}` 留空。
- **`declined`**(语料中无 reconsignment 专属引文)——若 broker 表示该地址无法配送
  (超区/无法预约等),改为询问 broker 建议的替代方案,而不是重复原地址要求。

## 消歧提醒(呼应 issue-taxonomy 的说明)

- `delivery-window` 改的是**时间**,`reconsignment` 改的是**地址**——即便 broker
  response 相同(如都是 `needs-info` 问"是否仍需预约"),模板与措辞完全不同,选错
  issue 类型会导致漏填 `{new_address}` 或 `{requested_window}`。
- 语料中不存在独立的 `delivery-access` issue slug(已并入 `damage`/`pickup`,见
  `issue-taxonomy.md`);起草时不要引用不存在的 `templates/delivery-access.md`。
