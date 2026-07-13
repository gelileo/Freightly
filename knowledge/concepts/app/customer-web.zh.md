---
title: 客户网页 + 录入表单引擎
type: concept
area: app
updated: 2026-07-11
status: mature
affects:
  - web/customer/index.html
  - app/forms.py
  - app/api.py
references:
  - concepts/app/api.md
  - concepts/app/agent-console.md
  - concepts/drafting/template-system.md
---

# 客户网页 + 录入表单引擎

Slice 7(第二个前端):无依赖的客户网页应用 + schema 驱动的**录入表单引擎**。客户通过**按类别
的表单**发起 case,并以友好的**中文状态**查看自己的 case——从不看到内部英文草稿。

## 表单引擎(`app/forms.py`)

`FORM_SCHEMAS[slug] = [Field…]`,`Field = {name, label_zh, label_en, type, required}`。字段
`name` **就是模板槽位名**(pickup→`pickup_address/contact_name/contact_phone`,delivery-window→
`requested_window/receiver_contact`,reconsignment→`new_address/…`,damage→`damage_desc`,…),
因此录入正好收集起草引擎要填的内容。`issue_types()` 返回面向客户的类型 + 标签 + schema。唯一
真源;新增类型是这里的数据改动——前端无需重新发布。(多租户版中改为每代理覆盖。)

## 端点(`app/api.py`)

- `GET /issue-types` → `forms.issue_types()`(需鉴权)。
- `GET /engagements` → 调用者的 **active** engagement(其为 customer org 成员),每个带
  `agent_name` 及该 agent 的 `broker_accounts`(id + broker 名)——有作用域;无关用户得 `[]`。
- `POST /cases` 增加可选 **`fields`**(dict)→ `open_customer_case(fields=…)`,并入草稿 `facts`
  (填槽)与 `source_text`(校验器保留)。已验证:`requested_window` 值进入所起草的经纪人邮件。

## 客户应用(`web/customer/index.html`,在 `/customer` 提供)

中文优先、双语。登录(`X-User-Id`)。**我的 case:** `GET /cases` → 行,带友好中文状态
(`SENT_TO_BROKER`→"已转交承运商",`PENDING_APPROVAL`→"代理审核中",…)——**无英文消息正文**。
**新建 case:** 选 agent(`/engagements`)→ broker → issue 类型(`/issue-types` → 动态字段渲染)
→ BOL + 备注 → `POST /cases {…, fields}`。做 XSS 转义。

## 验证(Playwright,真实浏览器)

以客户登录 → 新建 case → agent/broker/issue 下拉填充 → 选 送达时间(字段切换为 requested_window)
→ 填写 + BOL → 提交 → case 出现在"我的 case"显示"代理审核中";所起草的经纪人邮件包含提交的时间窗。
静态 HTML 冒烟:`tests/test_console.py`;表单/端点测试:`tests/test_forms.py`、`tests/test_api.py`。

## 暂缓 / 说明

- **面向客户的中文更新现已实现**(Slice 8,见 `concepts/drafting/summarize.md`):点击 case 可
  查看代理批准的中文更新(`channel=app, lang=zh, status=posted`)——broker 回复被摘要成中文、
  经审批后展示。客户端仍绝不显示内部英文草稿。
- WeChat 小程序(同一 API)是需 WeChat 工具链的独立切片。

## 身份门禁(2026-07-12)

与代理控制台对称:登录/刷新校验身份载荷的 `is_customer` 标志,拒绝非客户会话(如代理账号,其没有
客户 case),提示"此账号非客户账号,请用客户账号登录";刷新经 `GET /auth/me` 确认身份。此为 UX
门禁,访问权限仍由服务端强制。详见 `identity-model.md`。
