# Phase 2: Users Table - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-23
**Phase:** 02-users-table
**Areas discussed:** API key encryption, Seed admin strategy, Multi-tenant prep, Email uniqueness & validation, Role storage

---

## API Key Encryption

| Option | Description | Selected |
|--------|-------------|----------|
| Fernet encryption | Encrypt with cryptography.fernet using server-side SECRET_KEY from .env | |
| Plaintext columns | Store API keys as plain VARCHAR. DB is local-only. | ✓ |
| Env-only, no DB storage | Don't store keys per-user. Use shared .env keys only. | |

**User's choice:** Plaintext columns
**Notes:** DB is local-only, simplicity preferred for v1.

### Follow-up: Key nullable?

| Option | Description | Selected |
|--------|-------------|----------|
| Nullable, default NULL | Users start without keys. System falls back to shared .env keys. | ✓ |
| Empty string default | Non-nullable with default ''. | |

**User's choice:** Nullable, default NULL

### Follow-up: Column type?

| Option | Description | Selected |
|--------|-------------|----------|
| String(500) | Standard length for API keys | |
| Text | Unbounded length, flexible | ✓ |

**User's choice:** Text

### Follow-up: active_key_tier default?

| Option | Description | Selected |
|--------|-------------|----------|
| Default 'free' | New users default to free tier | ✓ |
| Default NULL | No tier until explicitly set | |
| Default 'none' | Explicit 'no tier selected' state | |

**User's choice:** Default 'free'

---

## Seed Admin Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| In seed.py | Add to existing seed script. Keeps migration pure DDL. | ✓ |
| In the Alembic migration | INSERT admin row in upgrade(). Admin always exists after migration. | |
| At app startup (lifespan) | Check-and-create in FastAPI lifespan. | |

**User's choice:** In seed.py
**Notes:** Follows existing pattern where seed.py handles data population.

### Follow-up: Admin credentials source?

| Option | Description | Selected |
|--------|-------------|----------|
| Env vars (ADMIN_EMAIL, ADMIN_PASSWORD) | Secure, configurable per environment | ✓ |
| Hardcoded defaults | admin@clipflow.local / changeme123 | |

**User's choice:** Env vars

---

## Multi-Tenant Prep

| Option | Description | Selected |
|--------|-------------|----------|
| Defer to later phase | Phase 2 only creates users table. Add user_id to other tables later. | ✓ |
| Add user_id to key tables now | Nullable user_id FK to pipeline_runs, content_packages, batch_jobs | |
| Add user_id to all tables now | Comprehensive but large migration scope | |

**User's choice:** Defer to later phase

### Follow-up: Timestamps?

| Option | Description | Selected |
|--------|-------------|----------|
| TimestampMixin (created_at + updated_at) | Matches existing model patterns | ✓ |
| Just created_at | Matches roadmap columns exactly | |

**User's choice:** TimestampMixin

### Follow-up: User-Character FK?

| Option | Description | Selected |
|--------|-------------|----------|
| Add user_id to characters now | Nullable FK, establishes ownership early | ✓ |
| Defer all FKs | Keep Phase 2 strictly about users table only | |

**User's choice:** Add user_id to characters now

### Follow-up: Extra columns?

| Option | Description | Selected |
|--------|-------------|----------|
| No extras | Just what's in success criteria + updated_at | |
| Add display_name | Optional String(200) for UI greeting | ✓ |
| Add last_login_at | Track last login timestamp | |

**User's choice:** Add display_name

---

## Email Uniqueness & Validation

| Option | Description | Selected |
|--------|-------------|----------|
| Unique index, store lowercase | Always lowercase before storing. Unique constraint. | ✓ |
| Case-insensitive collation | MySQL utf8mb4_general_ci on email column | |
| Unique index, case-sensitive | Store as-is, app handles case comparison | |

**User's choice:** Unique index, store lowercase

### Email validation level?

| Option | Description | Selected |
|--------|-------------|----------|
| App level only (Pydantic) | Phase 3 validates format. DB stores string. | ✓ |
| DB CHECK constraint | Regex constraint on column | |

**User's choice:** App level only

---

## Role Storage

| Option | Description | Selected |
|--------|-------------|----------|
| String column | String(20) with 'admin'/'user' values. Default 'user'. | ✓ |
| MySQL ENUM type | Native ENUM. DB enforces values. Harder to extend. | |
| Separate roles table | FK to roles table. Overkill for admin/user. | |

**User's choice:** String column

---

## Claude's Discretion

- Migration version number and naming
- Index strategy for users table
- User-Character relationship back_populates
- bcrypt vs argon2 choice (needed for seed.py)

## Deferred Ideas

- Add user_id FK to all content tables (Phase 4+)
- API key encryption with Fernet (production deployment)
- last_login_at column (Phase 3 when login endpoint is built)
