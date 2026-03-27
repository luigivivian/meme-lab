# Phase 13: Tenant Isolation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-25
**Phase:** 13-tenant-isolation
**Areas discussed:** Scoping strategy, Enforcement layer, Existing data migration

---

## Scoping Strategy

### Q1: Tenant scoping for models without user_id

| Option | Description | Selected |
|--------|-------------|----------|
| Transitive via character | Keep current structure — repos join through character to filter by user. No new columns needed. | ✓ |
| Direct user_id on every table | Add user_id FK to 6+ tables. Redundant but simpler queries. | |
| Hybrid approach | Add user_id to top-level entities only. Child records stay transitive. | |

**User's choice:** Transitive via character
**Notes:** None

### Q2: PipelineRun orphan policy

| Option | Description | Selected |
|--------|-------------|----------|
| Always require character | Make character_id non-nullable. Assign orphans to default character. | ✓ |
| Keep character_id optional | Allow orphan runs. Add separate user_id FK for runs without characters. | |
| You decide | Claude picks simpler approach. | |

**User's choice:** Always require character
**Notes:** None

### Q3: Theme ownership model

| Option | Description | Selected |
|--------|-------------|----------|
| Global + user themes | Keep global themes visible to all. Users can create own themes. | ✓ |
| All themes per-user | Add user_id to all themes. Each user gets own copy. | |
| Global only | Themes stay shared, no per-user. | |

**User's choice:** Global + user themes
**Notes:** None

### Q4: 403 vs 404 behavior

| Option | Description | Selected |
|--------|-------------|----------|
| 403 for others' data, 404 for missing | Standard REST semantics. | ✓ |
| Always 403 for unauthorized | Both cases return 403. More secure, harder to debug. | |
| You decide | Claude picks based on security posture. | |

**User's choice:** 403 for others' data, 404 for missing
**Notes:** None

---

## Enforcement Layer

### Q1: Where to enforce ownership

| Option | Description | Selected |
|--------|-------------|----------|
| Repository level | All repo methods take user_id param and filter. Single enforcement point. | ✓ |
| Route-level validation | Routes fetch then check ownership. Repos unchanged. | |
| Middleware/dependency | Auto-inject user context into DB queries. Transparent but magical. | |

**User's choice:** Repository level
**Notes:** None

### Q2: Route authentication requirement

| Option | Description | Selected |
|--------|-------------|----------|
| All routes require auth | Every route except /auth/*, /health, /docs injects get_current_user. Activates AUTH-05. | ✓ |
| Only tenant-scoped routes | Only data-access routes require auth. | |
| You decide | Claude picks based on which routes need protection. | |

**User's choice:** All routes require auth
**Notes:** Activates deferred AUTH-05 from Phase 4

### Q3: Admin bypass mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Admin role skips user filter | Repos check role == "admin", skip filtering. Simple, no extra headers. | ✓ |
| Explicit admin flag in request | Admin must send X-Admin-Bypass header to access other users' data. | |
| Separate /admin/* endpoints | Duplicate routes under /admin/ prefix. Clean separation but doubles routes. | |

**User's choice:** Admin role skips user filter
**Notes:** None

---

## Existing Data Migration

### Q1: Handling existing rows without ownership

| Option | Description | Selected |
|--------|-------------|----------|
| Assign all to seed admin | Backfill all characters to admin user (id=1). Orphan runs to default character. | ✓ |
| Keep nullable, backfill later | Make nullable initially. Add backfill script for later. | |
| Wipe and reseed | Drop non-auth tables and reseed fresh. | |

**User's choice:** Assign all to seed admin
**Notes:** None

### Q2: Character.user_id nullability after migration

| Option | Description | Selected |
|--------|-------------|----------|
| Non-nullable after backfill | Alter to NOT NULL. Enforces at DB level. | ✓ |
| Keep nullable | App code enforces, DB allows nulls. | |

**User's choice:** Non-nullable
**Notes:** None

### Q3: PipelineRun.character_id nullability after migration

| Option | Description | Selected |
|--------|-------------|----------|
| Non-nullable after backfill | Alter to NOT NULL. Consistent with always-require-character decision. | ✓ |
| Keep nullable | Allow runs without character for edge cases. | |

**User's choice:** Non-nullable
**Notes:** Consistent with D-02 decision

---

## Claude's Discretion

- Repo parameter design (user_id vs User object)
- Helper dependency for character ownership validation
- Migration ordering and Alembic chaining
- AgentStat/TrendEvent scoping (monitoring data)
- 403 check implementation approach

## Deferred Ideas

- Granular admin access (X-Admin-As-User header) — if needed later
