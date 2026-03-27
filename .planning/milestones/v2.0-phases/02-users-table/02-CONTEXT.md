# Phase 2: Users Table - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a `users` table to MySQL via Alembic migration. This is the DB foundation for all auth phases (3-11). Also adds a nullable `user_id` FK to the `characters` table to establish ownership. The migration must be reversible. A seed admin user is created via `seed.py`.

</domain>

<decisions>
## Implementation Decisions

### API Key Storage
- **D-01:** Store `gemini_free_key` and `gemini_paid_key` as plaintext `Text` columns. DB is local-only; encryption not needed for v1.
- **D-02:** Both key columns are nullable, default NULL. When NULL, system falls back to shared `.env` keys (`GOOGLE_API_KEY` / `GOOGLE_API_KEY_PAID`).
- **D-03:** `active_key_tier` is `String(20)`, default `'free'`. Values: `'free'`, `'paid'`, `'none'`.

### Seed Admin
- **D-04:** Seed admin created in `src/database/seed.py` (not in migration, not at app startup). Keeps migration as pure DDL.
- **D-05:** Admin credentials from env vars: `ADMIN_EMAIL` and `ADMIN_PASSWORD`. seed.py reads them and creates the admin user with role `'admin'`.

### Multi-Tenant Prep
- **D-06:** Defer adding `user_id` FK to most existing tables (pipeline_runs, content_packages, batch_jobs, etc.) to a later phase when auth is enforced (Phase 4+).
- **D-07:** Exception: add nullable `user_id` FK to `characters` table now. Establishes ownership model early. Existing characters keep `user_id=NULL`.

### Email & Uniqueness
- **D-08:** Always store email as lowercase (normalize before INSERT/UPDATE). Unique index on email column.
- **D-09:** Email format validation at app level only (Pydantic in Phase 3). DB stores as `String(255)` with unique constraint.

### Role Storage
- **D-10:** Role stored as `String(20)` column with default `'user'`. Values: `'admin'`, `'user'`. Matches existing status column pattern throughout codebase.

### Timestamps & Extra Columns
- **D-11:** Use `TimestampMixin` for `created_at` + `updated_at`. Matches Character, CharacterRef, ScheduledPost patterns.
- **D-12:** Add optional `display_name` column — `String(200)`, nullable, default NULL. For UI greeting in dashboard.

### Claude's Discretion
- Migration version number and naming convention
- Index strategy for the users table (email is unique, role and is_active as needed)
- Whether to add a User relationship back-populates on Character model
- bcrypt vs argon2 choice for password hashing (Phase 3 concern, but seed.py will need it)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Database Models & Patterns
- `src/database/models.py` — All 11 existing ORM models. Follow the same column definition patterns (Mapped, mapped_column, server_default for MySQL compat).
- `src/database/base.py` — `Base` and `TimestampMixin` classes. User model must inherit both.
- `src/database/session.py` — Async session factory. Seed script will use this.

### Existing Seed Script
- `src/database/seed.py` — Current seeding logic (YAML + filesystem to MySQL). Add admin user seeding here.

### Migration Examples
- `src/database/migrations/versions/001_initial_schema.py` — Pattern for initial table creation
- `src/database/migrations/versions/004_add_scheduled_posts.py` — Pattern for adding a new table with FKs

### Requirements & Roadmap
- `.planning/REQUIREMENTS.md` — AUTH-07 (users table columns and purpose)
- `.planning/ROADMAP.md` §44-53 — Phase 2 success criteria (4 conditions that must be TRUE)

### Characters Table (for user_id FK)
- `src/database/models.py` §28-91 — Character model where nullable `user_id` FK will be added

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `TimestampMixin` in `src/database/base.py` — Provides `created_at` + `updated_at` with `func.now()` defaults
- `src/database/seed.py` — Existing seed script to extend with admin user creation
- `src/database/repositories/__init__.py` — Repository pattern for data access (will need a UserRepository in Phase 3)

### Established Patterns
- MySQL compatibility: `Text`/`JSON` columns use ORM `default=` not `server_default=` (MySQL limitation)
- `String` columns with simple values use `server_default=` for MySQL compatibility
- Indexes: named `idx_{table}_{column}` pattern (e.g., `idx_characters_status`)
- Soft delete: `is_deleted` Boolean pattern exists but not needed for users (`is_active` serves similar purpose)
- Relationships: `back_populates` bidirectional, `cascade="all, delete-orphan"` for owned collections

### Integration Points
- `Character` model needs `user_id` FK column + relationship added
- `src/database/models.py` — New `User` class goes here (table 12)
- `alembic.ini` + `src/database/migrations/env.py` — Migration infrastructure already configured for MySQL

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches for migration structure and seed implementation.

</specifics>

<deferred>
## Deferred Ideas

- **Add user_id FK to all content tables** — Defer to Phase 4+ when auth is enforced and data backfill strategy is clear
- **API key encryption (Fernet)** — Revisit when deploying to production or enabling multi-tenant
- **last_login_at column** — Could be useful for admin dashboard; add when login endpoint is built (Phase 3)

</deferred>

---

*Phase: 02-users-table*
*Context gathered: 2026-03-23*
