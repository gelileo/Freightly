---
title: 代理控制台(前端)
type: concept
area: app
updated: 2026-07-11
status: mature
affects:
  - web/agent/index.html
  - app/server.py
references:
  - concepts/app/api.md
  - concepts/app/case-workflow.md
---

# 代理控制台

Slice 6(首个前端):一个无依赖、自包含的 **HTML + 原生 JS** 页面,operator 用它跑审批流程。
无框架、无构建。它是一个**薄 API 客户端**——所有规则(鉴权、访问、审批门、状态机)都由服务端
强制;控制台只调用 JSON API。

## 提供方式

`app/server.py` 在 `GET /`(以及 `/console`、`/index.html`)返回 `web/agent/index.html`;
`/favicon.ico` → 204;其余路径落到 JSON `dispatch`。因此 `GET /` 返回 HTML 而 `GET /cases`
返回 JSON——无路由冲突。`serve()` 的 `static_dir` 默认指向 `web/agent/`。

## 功能

- **登录栏** —— operator 用户 id(存 `localStorage`),每次请求作 `X-User-Id`。(实际部署:由
  网关完成 WeChat/OAuth 登录并注入该头;控制台的输入框是开发/替身用途。)
- **case 列表** —— `GET /cases` → 行(BOL、issue 类型、状态徽标、来源)。
- **case 详情** —— `GET /cases/{id}` → 消息线程 + `pending_approval` 草稿(放入可编辑
  `<textarea>`,`[[MISSING: …]]` 可见),外加 `GET /cases/{id}/audit`。
- **动作** —— 批准并发送(先 `edit` 当前文本再 `approve`)、保存编辑(`edit`)、驳回
  (`reject`);API 错误(401/403/409)内联显示;每次操作后刷新 case。

## 安全

- **不绕过后端:** 控制台仅通过 API 改状态;审批仍是唯一的发送/张贴路径。
- **XSS:** 所有服务端数据插入前都做 HTML 转义(`esc()`);`[[MISSING]]` 标记按文本渲染。
- 鉴权仅 `X-User-Id`(生产中由网关提供,已注明)。

## 验证

用真实浏览器端到端验证(Playwright):以 agent operator 登录 → 看到预置 case → 打开 →
**批准并发送** → 消息变为 `sent`,case 在 UI 中推进到 `AWAITING_BROKER`。另有静态 HTML 冒烟
测试(`tests/test_console.py`)。

## 暂不包含 / 下一步

真实登录/会话、面向客户的前端(WeChat 小程序 + 响应式网页——各自工具链)、分页、更丰富的
case 过滤,留待后续切片。
