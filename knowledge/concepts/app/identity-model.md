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
---

# Identity & Relationship Model

Slice 2 of the app (`docs/superpowers/specs/2026-07-10-broker-app-system-design.md`): the
persisted, relationship-scoped identity foundation. Dependency-free (stdlib `sqlite3`);
headless; Postgres is a later migration (swap `app/db.py`'s DDL/driver — the repo layer stays).

## Entities (schema in `app/db.py`; dataclasses in `app/models.py`)

- **Org** — `type ∈ {customer, agent}`. The account unit; individuals are orgs of size 1.
- **User** — `auth_kind ∈ {wechat, phone, email}`, unique `auth_id`.
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

## Not in this slice

Cases, messages, the case state machine, audit log, and the inbound router are Slice 3;
the API server and console are later. This slice is exercised only through the repo/access
functions (no HTTP surface yet).
