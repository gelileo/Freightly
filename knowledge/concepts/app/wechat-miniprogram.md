---
title: WeChat Mini Program Frontend + Auth
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

# WeChat Mini Program Frontend + Auth

**Status: backend auth adapter AND the native customer views are BUILT (2026-07-11); running on a
real device/DevTools is yours.** This article captures *why* and *how* a WeChat Mini Program (小程序)
becomes the customer's native frontend, and — the load-bearing part — exactly how WeChat
identity/login works. The server-side `wx.login → code2session → openid/unionid` adapter and the
invite/bind onboarding are implemented (`app/wechat.py`, `app/auth.py`, wired into `app/api.py`; see
`docs/superpowers/specs/2026-07-11-wechat-login-adapter-design.md` and `concepts/app/identity-model.md`).
The native views live under `miniprogram/` (see "Views" below). **A Mini Program cannot run outside
WeChat/DevTools**, so the views are verified here via a Playwright-checked browser prototype, not a
live run.

## Why a Mini Program (and why it's a distinct frontend)

Our customers are Chinese end-users who already raise shipment issues over WeChat. A Mini
Program is the native surface *inside* WeChat — no app-store install, opened by QR code
(小程序码), chat share card, search, or a linked Official Account. It renders exactly the
customer-facing Chinese updates we already produce ([summarize](../drafting/summarize.md):
`channel=app, lang=zh, status=posted`).

It is a **distinct frontend, not a reuse** of `web/customer/index.html`: a Mini Program is
**not a browser**. You write **WXML** (markup), **WXSS** (styling), **JS**, and **JSON**
page config, running in WeChat's own runtime with **no `window`, no `document`, no DOM**.
The API contract ([api](api.md)) is reused as-is; the view layer is rewritten.

## The dual-thread architecture (the defining feature)

A Mini Program runs in **two isolated threads that cannot touch each other directly** — the
single most important thing to understand.

```
┌─────────────────────────── WeChat client (super-app) ────────────────────────────┐
│                                                                                    │
│   RENDER LAYER (视图层)                      LOGIC LAYER (逻辑层 / AppService)       │
│   ┌─────────────────────────┐                ┌─────────────────────────────────┐  │
│   │ WXML + WXSS              │  ◄── setData ──│ your JS (business logic)         │  │
│   │ one WebView per page     │                │ runs in JSCore (iOS) / V8 (And.) │  │
│   │ (or Skyline native)      │── user event ─►│ NO DOM, NO window / document     │  │
│   └─────────────────────────┘                │ wx.login(), wx.request(), ...    │  │
│              ▲                                └─────────────────────────────────┘  │
│              │      both marshalled ASYNCHRONOUSLY through                          │
│              └──────────  WeixinJSBridge  ◄──►  WeChat Native layer  ───────────────┤
│                                                        │                            │
└────────────────────────────────────────────────────────┼───────────────────────────┘
                                                          │ HTTPS (allowlisted domains only)
                                                          ▼
                                                 Tencent servers  +  OUR backend
```

- **Render layer** — one WebView per page renders WXML/WXSS. Since ~2023 an alternative
  native renderer, **Skyline**, replaces the WebView for better performance.
- **Logic layer** — your JS runs in a bare JS engine (JavaScriptCore on iOS, V8 on Android)
  with no rendering ability at all.
- They communicate **only asynchronously, over a bridge** (`WeixinJSBridge`) mediated by
  WeChat's native layer. Logic → view is `this.setData({...})`; view → logic is events.

**Why WeChat built it this way:** security (your JS can never manipulate the rendered page
directly — WeChat controls what runs), performance (heavy JS never blocks rendering), and
platform control (every network call and capability is mediated). **Practical cost:**
`setData` is the perf bottleneck — large or chatty `setData` payloads are the classic
Mini-Program performance bug. Keep pushed state small.

## Ecosystem: accounts, distribution, review, networking

- **Account:** register on the MP platform (mp.weixin.qq.com) → **AppID + AppSecret**. Most
  real capabilities (payment, phone number, many APIs) require a **verified business account**
  (营业执照 / entity verification); individual accounts are limited.
- **Release:** every version is **reviewed by Tencent** (审核): dev → trial (体验版) →
  submit → review → release. There is no independent URL/deploy.
- **Distribution:** only inside the WeChat graph — QR codes, chat share cards, search,
  "nearby", Official Account menus.
- **Networking:** only `wx.request` (HTTPS), `wx.uploadFile`, `wx.downloadFile`, WebSocket —
  **no arbitrary fetch**. You must **pre-register your server domains** (request / socket /
  upload / download) in the MP console — a hard allowlist, TLS required. Mainland-hosted
  domains generally need ICP filing (备案). **This collides with our US-data-residency
  decision** and must be resolved when we build (cross-border latency + compliance).
- **Push:** **Subscription Messages** (订阅消息, which replaced template messages) — the user
  opts in per message type, then our server pushes. The natural channel for a "broker replied
  / 代理已回复您" notification instead of polling.
- **Tooling:** WeChat DevTools (微信开发者工具) + real-device preview.

## WeChat auth — exactly how login works (load-bearing)

Mini Programs are **passwordless**, built on WeChat identity. Our backend never sees a
password; it exchanges a short-lived code with Tencent for a stable user identity.

```
  Mini Program (client)              OUR backend (US)                 Tencent (api.weixin.qq.com)
  ─────────────────────              ────────────────                 ───────────────────────────
        │                                  │                                     │
   (1)  │ wx.login()                       │                                     │
        │───────────► js_code (temporary)  │                                     │
        │                                  │                                     │
   (2)  │ wx.request POST /auth/wechat      │                                     │
        │   { js_code }                     │                                     │
        │──────────────────────────────────►                                     │
        │                                  │  (3) GET /sns/jscode2session         │
        │                                  │      appid + secret + js_code        │
        │                                  │─────────────────────────────────────►
        │                                  │                                     │
        │                                  │  (4) { openid, unionid, session_key }│
        │                                  │◄─────────────────────────────────────
        │                                  │                                     │
        │                                  │  (5) map openid → users row          │
        │                                  │      (auth_type='wechat',            │
        │                                  │       auth_ref=openid); mint OUR      │
        │                                  │       session token                  │
   (6)  │  { session_token }               │                                     │
        │◄──────────────────────────────────                                     │
        │                                  │                                     │
   (7)  │ every later call sends our token │  (verified → resolves to user_id →   │
        │  (Authorization / custom header) │   the SAME X-User-Id seam the API    │
        │──────────────────────────────────►  already enforces via app.access)   │
```

1. **`wx.login()`** returns a **temporary `js_code`** (single-use, ~5 min).
2. The Mini Program sends `js_code` to **our** server (never to Tencent directly — the
   AppSecret must stay server-side).
3. Our server calls Tencent's **`code2Session`** endpoint
   (`/sns/jscode2session`) with `appid + secret + js_code`.
4. Tencent returns **`openid`**, optionally **`unionid`**, and a **`session_key`**.
5. We map the WeChat identity to a row in our `users` table and mint **our own** session
   token. `session_key` stays server-side (used only to decrypt WeChat-encrypted payloads
   like phone number — never sent to the client).
6. Client stores our session token.
7. Every subsequent `wx.request` carries our token; our gateway verifies it and resolves it
   to a `user_id` — feeding the **same authenticated-identity seam** the API already assumes.

### openid vs unionid (get this right)

| ID | Scope | Use for |
| --- | --- | --- |
| **openid** | Stable, unique to *this user in this one Mini Program* | The primary key linking a WeChat user to our `users` row |
| **unionid** | Stable across *all* your WeChat properties (Mini Program + Official Account + app) under one **Open Platform** (开放平台) account | Recognising the same person if they also reach us via an Official Account; only present when the MP is bound to an Open Platform account |

**Design rule for us:** store `openid` as the per-app link and `unionid` (when available) as
the cross-property identity, so a customer who later arrives through a WeChat Official Account
is recognised as the same person.

### Phone number / profile

Obtained only via explicit user-consent buttons (e.g. `getPhoneNumber`), returned as an
**encrypted payload** that our server decrypts with `session_key`. No silent access.

## How it maps onto our system (build checklist)

Our backend is already **API-first and frontend-agnostic**: `app/api.py` defers auth to an
upstream authenticated identity (`X-User-Id`) precisely so a new client can plug in. The Mini
Program becomes a **third client of the same API**, beside `web/agent` and `web/customer`.

| Concern | Reuse | New work |
| --- | --- | --- |
| **API contract** (`/engagements`, `/issue-types`, `/cases`, message actions) | ✅ as-is | register domain in MP console |
| **Views** (`web/customer/index.html`) | ❌ HTML not reusable | rewrite as WXML/WXSS pages + `setData` logic |
| **Auth** (deferred "gateway concern" in [api](api.md)) | the `X-User-Id` seam | add `wx.login → code2Session` server flow; map **openid/unionid → `users`** (a `wechat` auth type). **This finally fills the gateway box.** |
| **Notifications** | polling today | Subscription Messages for "代理已回复您" |
| **Data residency** | US backend decided | resolve MP domain allowlist + China↔US latency/compliance (possible ICP filing) |

The only genuinely new *backend* addition is the **WeChat login adapter** (openid→user
mapping + our own session token); everything else is a view rewrite against an API that
already exists. See [identity-model](identity-model.md) for the `users`/`orgs` model the
adapter would extend.

## Views (built) — `miniprogram/`

Native WXML/WXSS/JS (no build step, no dependencies), the third client of the same API beside
`web/agent` and `web/customer`. Spec: `docs/superpowers/specs/2026-07-11-wechat-miniprogram-views-design.md`.

- **Pages** (`miniprogram/pages/`): `login` (`wx.login` → `POST /auth/wechat/login` → store token →
  `needs_bind` ? bind : cases), `bind` (invite code, prefilled from the 小程序码 launch `scene` param
  → `POST /auth/bind`), `cases` (`GET /cases` → rows with the same ZH status pills as
  `web/customer`), `case` (`GET /cases/{id}` → the approved ZH update feed the server already
  filters), `new-case` (`GET /engagements` + `GET /issue-types` → agent/broker/issue selects +
  schema-driven dynamic fields → `POST /cases {…, fields}`).
- **Session** (`utils/api.js`): attaches `Authorization: Bearer <token>`; on **401** clears the
  stored token and `wx.reLaunch`es to login. `baseUrl` is a single config constant in `app.js`
  (the direct-to-US-domain MVP). The AppSecret never lives in the client.
- **Verified** at two levels: (1) a Playwright-checked browser prototype (`prototype.html`)
  reproducing all five screens with a mock API — login → bind → cases → case → new-case, dynamic
  fields switching by issue type — for **layout/flow**; and (2) a static review against WeChat's
  component set and the real API contract. The prototype is plain HTML, so it does **not** catch
  WXML-specific issues (e.g. a status badge must be `<text>`, not HTML `<span>`) — those are the
  static review's job. The real API is covered by the backend test suite; the MP itself runs only
  in WeChat/DevTools.

### DevTools handoff (to run it)

1. Open `miniprogram/` in WeChat DevTools (微信开发者工具) with your **AppID** (set it in
   `project.config.json`).
2. Set `app.js` `globalData.baseUrl` to your deployed API host.
3. Register that host under 开发管理 → 服务器域名 (request domain, HTTPS) in the MP admin console.
4. Run in the simulator / preview on a device. First login lands on bind until an agent-issued
   invite is consumed.

## Deferred / open questions

- **Data-residency vs domain allowlist:** US backend + mainland-China Mini Program crossing
  the border — latency, ICP filing, and compliance need a concrete answer for production.
- **Agent side stays web:** the agent console ([agent-console](agent-console.md)) remains a
  browser app; only the *customer* frontend becomes a Mini Program.
- **Still deferred:** 小程序码 image generation (`wxacode.getUnlimited`), Subscription-Message
  push ("代理已回复您"), payments, and phone-number capture (`session_key` slot reserved).
