---
title: Identity & Relationship Model
type: concept
area: app
updated: 2026-07-10
status: mature
affects:
  - app/db.py
  - app/models.py
  - app/repo.py
  - app/access.py
  - app/auth.py
---

# Identity & Relationship Model

Slice 2 of the app (`docs/superpowers/specs/2026-07-10-broker-app-system-design.md`): the
persisted, relationship-scoped identity foundation. Dependency-free (stdlib `sqlite3`);
headless; Postgres is a later migration (swap `app/db.py`'s DDL/driver — the repo layer stays).

## Entities (schema in `app/db.py`; dataclasses in `app/models.py`)

- **Org** — `type ∈ {customer, agent}`. The account unit; individuals are orgs of size 1.
- **User** — `auth_kind ∈ {wechat, phone, email}`, unique `auth_id`, nullable `union_id`. For a
  WeChat user, `auth_id` is the `openid` and `union_id` is the (optional) cross-property identity;
  `repo.user_by_auth_id` looks a user up by `(auth_kind, auth_id)` for login upsert.
- **Membership** — `User × Org × role(admin|operator|member)`.
- **Engagement** — customer-org ↔ agent-org, `status ∈ {pending, active, revoked}`. Created
  `pending` (invite/request), `approve_engagement` → `active`, `revoke_engagement` → `revoked`.
  `UNIQUE(customer_org_id, agent_org_id)`. `create_engagement` **validates** the two orgs are
  of type customer and agent respectively (raises `ValueError` on role mismatch).
  **Transition-guarded:** `approve_engagement` only fires from `pending` (a revoked
  engagement cannot be silently reactivated); `revoke` is terminal. `revoked` is thus a dead
  end for that pair (UNIQUE blocks a fresh re-invite) — **re-engagement after revoke is not
  yet supported** and would need an explicit path (future work).
- **Broker** — directory entry (not a user).
- **BrokerAccount** — agent-org ↔ broker, with the connected `mailbox`. `UNIQUE(agent_org_id,
  broker_id)`. `connect_broker_account` validates the org is an agent. **`mailbox` is UNIQUE
  across all broker accounts** (partial index, non-null) and `connect_broker_account` raises
  `ValueError` if a mailbox is already claimed — it is the inbound router's tenant-routing key,
  so it must map to exactly one agent org. `agent_for_mailbox()` resolves which agent owns an
  inbound mailbox — the hook the Slice-3 inbound router uses.

## Agent-initiated onboarding (`router.onboard_customer`)

An agent operator provisions a customer in one step (`POST /onboard-customer`, agent-org members
only): create a **customer org**, a customer **web-login user** (their `X-User-Id` is the chosen
`login`) with a membership, and an **active engagement** with the agent org. Returns
`{customer_org_id, engagement_id, login}`; a taken `login` → 409 (unique `auth_id`). This is the
provisioning path for the web apps (there is no self-serve signup); the WeChat invite/bind path
(below) is the alternative for Mini Program users. Surfaced in the agent console
("Onboard customer"). `router.add_agent_operator` + `POST /agents` lets an agent-org **admin** create another **agent operator/admin** (email+password, temp password if none given) in their own org — surfaced as the console's "Add operator" panel. See `concepts/app/deployment.md` for local seeding vs onboarding.

## Relationship-scoped access (`app/access.py`) — the security boundary

The M:N network is isolated by relationship, not by per-org DB:

- `user_can_see_org` / `visible_org_ids` — membership scope.
- `parties_connected(customer, agent)` — True iff an **active** engagement links them.
- `user_may_access_engagement(user, engagement)` — True iff the engagement is **active** AND
  the user is a member of either party org. This is the primitive Slice 3's case-access builds
  on (a case is visible only to members of its customer/agent orgs via an active engagement).

**Isolation guarantee (tested):** with two independent engagements `c1↔a1` and `c2↔a2`, a user
in `c1` cannot access `c2↔a2`, and pending/revoked engagements grant no access. See
`tests/test_access.py`.

## WeChat login: sessions & invites (`app/auth.py`)

The WeChat-login adapter (`docs/superpowers/specs/2026-07-11-wechat-login-adapter-design.md`)
extends this model without changing the access boundary above — a WeChat login only *produces* a
`user_id`, and bind only *adds a membership*; everything downstream is the same relationship-scoped
access.

- **sessions** — `token_hash` (PK, `sha256` of an opaque `secrets.token_urlsafe(32)`; the raw token
  is returned to the client once and never stored), `user_id`, `created_at`, `expires_at`,
  `revoked`, `session_key` (WeChat `session_key`, server-only, for future phone decrypt).
  `resolve_session` returns a `user_id` only when not revoked and not expired; `revoke_session`
  (logout) sets `revoked=1`. Time is injectable for deterministic tests.
- **invites** — `code_hash` (PK, `sha256` of a **128-bit** `secrets.token_urlsafe(16)`; raw code
  returned once, QR-scene-sized ≤32 chars), `customer_org_id`, `role`, `created_by`, `created_at`,
  `expires_at`, `consumed_by_user`, `consumed_at`. **Single-use, agent-issued.** `create_invite`
  mints one; `bind_via_invite` validates (exists/unexpired/unconsumed) and, in **one transaction**,
  consumes it (guarded by `WHERE consumed_by_user IS NULL`) and adds the membership — so a WeChat
  user joins the agent-provisioned customer org and immediately sees its cases via the existing
  active engagement.

Both credentials follow the same rule: strong random value, stored hashed, raw value revealed once.

### Email/password login (agents)

`users.password_hash` (PBKDF2-HMAC-SHA256 via stdlib `hashlib`, `pbkdf2_sha256$iters$salt$hash`)
holds an agent's password; NULL for wechat/passwordless users. `auth.hash_password`/`verify_password`
/`set_password`, and `auth.login_password(email, password)` verifies against an `auth_kind='email'`
user and (on success) mints the **same opaque session** as WeChat (`_mint_session` → `sessions`),
returning `(token, user)`. Endpoint `POST /auth/login` → `{session_token, user}` (401 on bad
creds). The **agent console** logs in with email+password and then sends `Authorization: Bearer
<token>`. Passwords are set out-of-band (no self-serve): `scripts/set_agent_password.py <email>
<pw>`; `seed_demo.py` sets the demo accounts'. **Both the agent console AND the customer web app now
log in with email+password → Bearer session** — the customer's password is set at onboarding
(`onboard_customer` accepts a `password` or returns a generated `temp_password` for the agent to
hand off). `X-User-Id` remains only for tests / trusted internal calls.

## Not in this slice

The case state machine, audit log, and inbound router are Slice 3; the API server and console are
later. Sessions/invites arrived with the WeChat-login adapter (2026-07-11).
