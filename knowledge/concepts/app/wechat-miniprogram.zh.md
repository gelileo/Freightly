---
title: 微信小程序前端 + 鉴权
type: concept
area: app
updated: 2026-07-11
status: thin
load_bearing: true
affects:
  - app/wechat.py
  - app/auth.py
  - miniprogram/**
references:
  - concepts/app/customer-web.md
  - concepts/app/api.md
  - concepts/app/identity-model.md
  - concepts/drafting/summarize.md
---

# 微信小程序前端 + 鉴权

**状态:后端鉴权适配器与原生客户视图均已构建(2026-07-11);在真机/DevTools 上运行由你完成。**
本文记录**为什么**以及**如何**用微信小程序作为客户的原生前端,并且——最关键的部分——
**微信身份/登录到底如何运作**。服务端的 `wx.login → code2session → openid/unionid` 适配器与
邀请/绑定入驻已实现(`app/wechat.py`、`app/auth.py`,接入 `app/api.py`;见
`docs/superpowers/specs/2026-07-11-wechat-login-adapter-design.md` 与 `concepts/app/identity-model.md`)。
原生视图位于 `miniprogram/`(见下文"视图")。**小程序无法在微信/DevTools 之外运行**,故视图在此
通过 Playwright 验证的浏览器原型确认,而非实时运行。

## 为什么用小程序(以及它为何是一个独立前端)

我们的客户是已经在微信上就货件问题发起沟通的中国终端用户。小程序是**微信内部**的原生界面——
无需应用商店安装,通过小程序码、聊天分享卡片、搜索或关联公众号打开。它正好展示我们已经产出的
面向客户的中文更新([summarize](../drafting/summarize.md):`channel=app, lang=zh, status=posted`)。

它是**独立前端,而非复用** `web/customer/index.html`:小程序**不是浏览器**。你写
**WXML**(标记)、**WXSS**(样式)、**JS** 与 **JSON** 页面配置,运行在微信自有运行时中,
**没有 `window`、没有 `document`、没有 DOM**。API 契约([api](api.md))原样复用;视图层重写。

## 双线程架构(小程序的定义性特征)

小程序运行在**两条彼此隔离、不能直接互相访问的线程**中——这是最需要理解的一点。

```
┌─────────────────────────── 微信客户端(超级 App)──────────────────────────────────────┐
│                                                                                    │
│   渲染层(视图层)                            逻辑层(AppService)                        │
│   ┌─────────────────────────┐                ┌──────────────────────────────────┐  │
│   │ WXML + WXSS             │  ◄── setData ──│ 你的 JS(业务逻辑)                  │  │
│   │ 每个页面一个 WebView      │                │ 跑在 JSCore(iOS)/ V8(安卓)        │  │
│   │ (或 Skyline 原生渲染)     │── 用户事件 ───► │ 无 DOM、无 window / document      │  │
│   └─────────────────────────┘                │ wx.login()、wx.request() ...     │  │
│              ▲                               └──────────────────────────────────┘  │
│              │      两者均通过桥接层**异步**传递                                       │
│              └──────────  WeixinJSBridge  ◄──►  微信原生层  ────────────────────────┤
│                                                        │                           │
└────────────────────────────────────────────────────────┼───────────────────────────┘
                                                         │ HTTPS(仅限白名单域名)
                                                         ▼
                                                 腾讯服务器  +  我们的后端
```

- **渲染层**——每个页面一个 WebView 渲染 WXML/WXSS。约 2023 年起有替代的原生渲染器
  **Skyline**,替换 WebView 以获得更好性能。
- **逻辑层**——你的 JS 跑在一个纯 JS 引擎(iOS 上 JavaScriptCore、安卓上 V8)里,
  完全没有渲染能力。
- 两者**只能异步、经桥接(`WeixinJSBridge`)**由微信原生层中转通信。逻辑→视图是
  `this.setData({...})`;视图→逻辑是事件。

**微信为何这样设计:** 安全(你的 JS 永远不能直接操纵渲染页面——微信控制运行内容)、
性能(重 JS 永不阻塞渲染)、平台管控(每个网络调用与能力都被中转)。**实际代价:**
`setData` 是性能瓶颈——过大或过频的 `setData` 载荷是小程序经典性能坑。推送的状态要小。

## 生态:账号、分发、审核、网络

- **账号:** 在 MP 平台(mp.weixin.qq.com)注册 → **AppID + AppSecret**。多数实际能力
  (支付、手机号、许多 API)需要**已认证的企业账号**(营业执照/主体认证);个人账号受限。
- **发布:** 每个版本都要**经腾讯审核**:开发 → 体验版 → 提交 → 审核 → 发布。没有独立
  URL/部署。
- **分发:** 仅在微信生态内——小程序码、聊天分享卡片、搜索、附近、公众号菜单。
- **网络:** 只有 `wx.request`(HTTPS)、`wx.uploadFile`、`wx.downloadFile`、WebSocket——
  **不能任意 fetch**。必须在 MP 后台**预先登记服务器域名**(request / socket / upload /
  download)——硬白名单,强制 TLS。境内托管域名通常需 ICP 备案。**这与我们的美国数据驻留
  决策相冲突**,构建时须解决(跨境延迟 + 合规)。
- **推送:** **订阅消息**(取代了模板消息)——用户按消息类型逐条授权,之后我们的服务器推送。
  这是"代理已回复您"通知的天然通道,替代轮询。
- **工具:** 微信开发者工具 + 真机预览。

## 微信鉴权——登录到底如何运作(load-bearing)

小程序**无密码**,建立在微信身份之上。我们的后端永远看不到密码;它用一个短时效的 code
向腾讯换取稳定的用户身份。

```
  小程序(客户端)                   我们的后端(美国)              腾讯(api.weixin.qq.com)
  ─────────────────                 ────────────────               ───────────────────────────
        │                                  │                                     │
   (1)  │ wx.login()                       │                                     │
        │───────────► js_code(临时)         │                                     │
        │                                  │                                     │
   (2)  │ wx.request POST /auth/wechat     │                                     │
        │   { js_code }                    │                                     │
        │──────────────────────────────────►                                     │
        │                                  │  (3) GET /sns/jscode2session        │
        │                                  │      appid + secret + js_code       │
        │                                  │─────────────────────────────────────►
        │                                  │                                      │
        │                                  │  (4) { openid, unionid, session_key }│
        │                                  │◄─────────────────────────────────────
        │                                  │                                     │
        │                                  │  (5) 将 openid → users 行            │
        │                                  │      (auth_type='wechat',           │
        │                                  │       auth_ref=openid);签发我们       │
        │                                  │       自己的 session token           │
   (6)  │  { session_token }               │                                     │
        │◄──────────────────────────────────                                     │
        │                                  │                                     │
   (7)  │ 之后每次调用带上我们的 token         │  (验证 → 解析出 user_id → 就是 API    │
        │  (Authorization / 自定义 header)  │   已通过 app.access 强制的同一         
        │──────────────────────────────────►  X-User-Id 接缝)                     │
```

1. **`wx.login()`** 返回一个**临时 `js_code`**(一次性,约 5 分钟)。
2. 小程序把 `js_code` 发给**我们的**服务器(绝不直接发给腾讯——AppSecret 必须留在服务端)。
3. 我们的服务器带 `appid + secret + js_code` 调腾讯的 **`code2Session`** 端点
   (`/sns/jscode2session`)。
4. 腾讯返回 **`openid`**、可选的 **`unionid`**,以及 **`session_key`**。
5. 我们把微信身份映射到 `users` 表中的一行,并签发**我们自己**的 session token。
   `session_key` 留在服务端(仅用于解密微信加密载荷如手机号——绝不下发给客户端)。
6. 客户端保存我们的 session token。
7. 之后每次 `wx.request` 都带上我们的 token;网关校验并解析为 `user_id`——喂给 API
   已经假定的**同一"已认证身份"接缝**。

### openid 与 unionid(务必分清)

| ID | 作用域 | 用途 |
| --- | --- | --- |
| **openid** | 稳定,唯一到*该用户在这一个小程序内* | 把微信用户关联到我们 `users` 行的主键 |
| **unionid** | 在同一**开放平台**账号下,跨*所有*微信资产(小程序 + 公众号 + App)稳定 | 当同一人也经公众号触达我们时识别为同一人;仅当小程序绑定了开放平台账号时存在 |

**我们的设计规则:** 用 `openid` 作每个应用的关联键,`unionid`(若有)作跨资产身份,
这样日后经公众号到来的客户能被识别为同一人。

### 手机号 / 资料

仅通过明确的用户授权按钮(如 `getPhoneNumber`)获取,返回**加密载荷**,由我们服务器用
`session_key` 解密。没有静默访问。

## 如何映射到我们的系统(构建清单)

我们的后端已是 **API 优先、与前端无关**:`app/api.py` 把鉴权交给上游已认证身份
(`X-User-Id`),正是为了让新客户端能插入。小程序成为**同一 API 的第三个客户端**,
与 `web/agent`、`web/customer` 并列。

| 关注点 | 复用 | 新增工作 |
| --- | --- | --- |
| **API 契约**(`/engagements`、`/issue-types`、`/cases`、消息动作) | ✅ 原样 | 在 MP 后台登记域名 |
| **视图**(`web/customer/index.html`) | ❌ HTML 不可复用 | 重写为 WXML/WXSS 页面 + `setData` 逻辑 |
| **鉴权**([api](api.md) 中暂缓的"网关职责") | `X-User-Id` 接缝 | 新增 `wx.login → code2Session` 服务端流程;把 **openid/unionid → `users`**(`wechat` 鉴权类型)。**这最终补上了网关那一块。** |
| **通知** | 目前轮询 | 用订阅消息推"代理已回复您" |
| **数据驻留** | 已决定美国后端 | 解决 MP 域名白名单 + 中↔美延迟/合规(可能需 ICP 备案) |

唯一真正新增的**后端**改动是**微信登录适配器**(openid→user 映射 + 我们自己的 session
token);其余都是针对已存在 API 的视图重写。适配器要扩展的 `users`/`orgs` 模型见
[identity-model](identity-model.md)。

## 视图(已构建)—— `miniprogram/`

原生 WXML/WXSS/JS(无构建、无依赖),与 `web/agent`、`web/customer` 并列,是同一 API 的第三个客户端。
规格:`docs/superpowers/specs/2026-07-11-wechat-miniprogram-views-design.md`。

- **页面**(`miniprogram/pages/`):`login`(`wx.login` → `POST /auth/wechat/login` → 存 token →
  `needs_bind` ? bind : cases)、`bind`(邀请码,经小程序码进入时从启动 `scene` 预填 →
  `POST /auth/bind`)、`cases`(`GET /cases` → 与 `web/customer` 相同的中文状态药丸)、
  `case`(`GET /cases/{id}` → 服务端已过滤的已批准中文更新流)、`new-case`(`GET /engagements` +
  `GET /issue-types` → agent/broker/issue 选择 + schema 驱动动态字段 → `POST /cases {…, fields}`)。
- **会话**(`utils/api.js`):附 `Authorization: Bearer <token>`;**401** 时清除已存 token 并
  `wx.reLaunch` 到 login。`baseUrl` 是 `app.js` 中单一配置常量(直连美国域名 MVP)。AppSecret 绝不入客户端。
- **验证**分两层:(1)Playwright 检查的浏览器原型(`prototype.html`)复现全部五屏(mock API)——
  login → bind → cases → case → new-case,动态字段随 issue 切换——用于**布局/流程**;(2)对照微信
  组件集与真实 API 契约的静态审查。原型是纯 HTML,**无法**捕获 WXML 特有问题(例如状态徽章必须用
  `<text>` 而非 HTML `<span>`)——那是静态审查的职责。真实 API 由后端测试覆盖;小程序本身只在
  微信/DevTools 内运行。

### DevTools 交接(如何运行)

1. 用你的 **AppID**(在 `project.config.json` 设置)在微信开发者工具中打开 `miniprogram/`。
2. 把 `app.js` 的 `globalData.baseUrl` 设为你部署的 API 域名。
3. 在 MP 后台 开发管理 → 服务器域名 登记该域名(request 域名,HTTPS)。
4. 在模拟器/真机预览运行。首次登录会停在 bind,直到消费一个代理签发的邀请。

## 暂缓 / 待定问题

- **数据驻留 vs 域名白名单:** 美国后端 + 境内小程序跨境——延迟、ICP 备案与合规需在生产前给出明确答案。
- **代理侧仍为网页:** 代理控制台([agent-console](agent-console.md))仍是浏览器应用;只有*客户*前端变成小程序。
- **仍暂缓:** 小程序码图片生成(`wxacode.getUnlimited`)、订阅消息推送("代理已回复您")、支付、
  手机号采集(`session_key` 槽位预留)。
