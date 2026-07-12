---
title: 部署(Vercel serverless + Turso)
type: concept
area: app
updated: 2026-07-11
status: thin
load_bearing: true
affects:
  - api/index.py
  - api/poll.py
  - vercel.json
  - requirements.txt
  - app/db.py
references:
  - concepts/app/api.md
  - concepts/app/transport-and-config.md
  - concepts/app/identity-model.md
---

# 部署(Vercel serverless + Turso)

Staging 跑在 **Vercel**(静态前端 + serverless Python API + Vercel Cron),用 **Turso/libSQL** 作
持久 DB。生产(GoDaddy 仅域名/DNS,随后)与微信小程序暂缓。规格:
`docs/superpowers/specs/2026-07-11-vercel-serverless-deployment-design.md`。

## 拓扑

```
 浏览器 ─► Vercel: /            → web/agent/index.html      (静态)
                   /customer     → web/customer/index.html   (静态)
                   /api/*         → api/index.py  → app.api.dispatch()   (Python 函数)
                   cron */5m      → api/poll.py   → app.inbound.poll_once (Vercel Cron)
                        │ env: LIBSQL_URL、LIBSQL_AUTH_TOKEN、GEMINI_API_KEY、
                        │      SMTP_ADDRESS、SMTP_PASSWORD、WEBHOOK_SECRET、[CRON_SECRET]
                        ▼
                   Turso(托管 libSQL)—— 网络上的持久 DB
```

- **同源、无 CORS。** 前端调 `/api/...`;`api/index.py` 去掉 `/api` 后调用既有纯函数 `dispatch()`
  (它仍看到 `/cases`、`/engagements`…)。两个 `web/*/index.html` 里前端基路径为 `const API = "/api"`。
- **无状态函数 + 网络 DB。** 每请求开一个 libSQL 连接并关闭;`llm`/`transport`/`wechat` 每个热实例
  构建一次。Turso 是 API 函数与 cron 轮询共享的存储。

## 本地开发(无需 Vercel/Turso)

**没有自助注册** —— 身份是被"发放"的(网页应用信任上游 `X-User-Id`;微信用户经邀请/绑定入驻)。
本地运行并使用应用:

```bash
python3 scripts/seed_demo.py      # 在 ./hs.db 建演示账号(幂等)
python3 scripts/serve_local.py    # 在 http://127.0.0.1:8000 提供 /(代理)+ /customer + /api
```

- `serve_local.py` 用 `app.server` 对**持久 sqlite 文件**(`HS_DB`,默认 `hs.db`)运行,提供静态前端
  与 API。前端调用 `/api/*`;服务器去掉前缀(与 Vercel 同路由)。默认用 **FAKE** llm/transport/wechat
  (无外部调用,审批邮件**不会**真发);`USE_REAL_SERVICES=1` 则从 `.env` 接真实服务。
- `seed_demo.py` 建代理 org(`Justnano`,操作员 **`op`**)、客户 org(`Acme Shipping`,成员 **`uc`**)、
  一个 active engagement 及一个 broker account。**登录即输入 `X-User-Id`:** 代理控制台 → `op`,
  客户应用 → `uc`。新增客户/org 通过扩展 seed(或未来的管理/入驻界面)完成,不在应用 UI 内。

## DB 后端(`app/db.py`)

设了 `LIBSQL_URL`(Vercel)时 `connect()` 返回 **libSQL** 连接,否则标准库 `sqlite3`(本地/测试)。
`_LibsqlConnection` 把 libsql-client(HTTP)适配成 app 使用的有状态 sqlite3 风格接口 ——
`execute`/`commit`/`rollback`/`executescript`、带 `fetchone`/`fetchall`/迭代/`rowcount` 的游标、
`row["col"]` 行,并把约束错误规范化为 `sqlite3.IntegrityError` —— 故 `repo`/`cases`/`auth`/`inbound`
不变。经 `scripts/verify_libsql.py` 对本地 `file:` DB 端到端验证。stdlib-sqlite 测试套仍是正确性基线
(libsql-client 的 sync-over-async 客户端会卡住 pytest teardown,故不入套件)。

## 操作手册(运维步骤 —— 无法由仓库自动完成)

```bash
# 1. Turso DB + schema
turso db create hs-staging
turso db show hs-staging --url          # → LIBSQL_URL
turso db tokens create hs-staging       # → LIBSQL_AUTH_TOKEN
python3 scripts/export_schema.py        # → schema.sql(与 app.db._SCHEMA 同步)
turso db shell hs-staging < schema.sql  # 导入 schema

# 2. Vercel 项目 + 环境变量
vercel link
vercel env add LIBSQL_URL
vercel env add LIBSQL_AUTH_TOKEN
vercel env add GEMINI_API_KEY
vercel env add SMTP_ADDRESS             # hs@justnanoinc.com
vercel env add SMTP_PASSWORD            # 16 位阿里应用密码
vercel env add WEBHOOK_SECRET           # 供 POST /api/inbound
# 可选:CRON_SECRET(保护 /api/poll)、IMAP_HOST/PORT(默认 qiye.aliyun.com:993)

# 3. 部署 + 验证
vercel deploy
#   <url>/          → 代理控制台   ;  <url>/customer → 客户应用
#   先播种演示 org/engagement/broker(一次性脚本或 /api/inbound),登录点选走查
```

## 本地已验证 / 部署时验证

- **本地:** stdlib 套件全绿(133 passed);`scripts/verify_libsql.py` 对 `file:` libSQL DB 全 PASS;
  `_strip_api`、`vercel.json` 路由、`schema.sql` 同步测试通过。
- **你部署时(一起):** 线上应用 —— 登录(网页应用用 `X-User-Id`)、列/开 case、起草、审批;
  随后 cron 轮询拉取 broker 回复。

## 暂缓

- 生产主机 + GoDaddy DNS → 所选主机(单一部署模型)。
- 每请求新建 libSQL 客户端在低量下可接受;连接复用/池化是性能后续。SQLite→Postgres 仍是可选项
  (repo 层已隔离)。
- 微信小程序(其 API 基路径随后指向 Vercel 域名)。
- 面向公网生产前,在网关层锁定 `X-User-Id`(见 `api.md`)。
