# Phase 7: Usage Tracking Table - Context

**Gathered:** 2026-03-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Add an `api_usage` table to MySQL via Alembic migration (008) that records per-user per-day API consumption with timezone-correct daily reset at midnight Pacific Time. The table tracks all external API services (not just Gemini Image) and supports both per-user and system-level (shared key) usage tracking. No runtime logic — just the table, model, and migration.

</domain>

<decisions>
## Implementation Decisions

### Service Granularity
- **D-01:** Track ALL external API services, not just Gemini Image. Column `service` is `String(50)` with values: `gemini_image`, `gemini_text`, `gemini_web`, `comfyui`. Extensible for future services without schema changes.
- **D-02:** Tier values are simple `free`/`paid` — matches existing `User.active_key_tier` values. No service-prefixed tiers.

### Timezone & Date Storage
- **D-03:** The `date` column stores UTC `DateTime`, NOT a PT date. All reads convert UTC to America/Los_Angeles before bucketing by day.
- **D-04:** PT conversion lives in the Python repository layer (using `zoneinfo`), not MySQL `CONVERT_TZ()`. This preserves SQLite compatibility for tests (Phase 3 pattern).

### Status Column
- **D-05:** `status` column represents call outcome with values: `success`, `error`, `rejected`.
  - `success` = API call completed successfully
  - `error` = API returned an error (500, timeout, etc.)
  - `rejected` = call was blocked because daily limit was reached
- **D-06:** Only `success` rows count toward the daily limit. Failed API calls (`error`) do NOT consume quota.

### Multi-User & Shared Keys
- **D-07:** `user_id` is a nullable FK to `users.id`. `NULL` = system/shared key usage (when using `.env` keys without a logged-in user).
- **D-08:** UniqueConstraint on `(user_id, service, tier, date)` — one row per user/service/tier/day. Phase 8 will use `INSERT ... ON DUPLICATE KEY UPDATE usage_count = usage_count + 1` for atomic increments.

### Claude's Discretion
- Migration file naming and revision chain (should be 008 after 007)
- Additional indexes beyond the unique constraint (e.g., idx_api_usage_user_id, idx_api_usage_date)
- Whether to add a `usage_count` default of 0 or 1 on first insert
- ORM relationship back-populates on User model

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Database Models & Patterns
- `src/database/models.py` — All existing ORM models (13 tables). Follow same column definition patterns. User model at line 506.
- `src/database/base.py` — `Base` and `TimestampMixin` classes. ApiUsage model must inherit both.
- `src/database/session.py` — Async session factory.

### Migration Examples
- `src/database/migrations/versions/006_add_users_table.py` — Pattern for adding a new table with FKs and indexes.
- `src/database/migrations/versions/007_add_refresh_tokens.py` — Latest migration (revision chain: 007 → 008).

### Repository Pattern
- `src/database/repositories/schedule_repo.py` — Example of repository pattern for data access.

### Requirements & Roadmap
- `.planning/REQUIREMENTS.md` — QUOT-01 (api_usage table), QUOT-07 (timezone-aware reset)
- `.planning/ROADMAP.md` §119-131 — Phase 7 success criteria (3 conditions)

### Prior Phase Context
- `.planning/phases/02-users-table/02-CONTEXT.md` — Users table decisions (D-01 to D-12), especially API key storage and TimestampMixin pattern.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `TimestampMixin` in `src/database/base.py` — Provides `created_at` + `updated_at` with `func.now()` defaults
- Migration infrastructure fully configured for MySQL via `alembic.ini` + `src/database/migrations/env.py`
- Repository pattern in `src/database/repositories/` — will need a UsageRepository (Phase 8 concern)

### Established Patterns
- MySQL compatibility: `String` columns use `server_default=`, `Text/JSON` use ORM `default=`
- Index naming: `idx_{table}_{column}` (e.g., `idx_users_role`, `idx_characters_user_id`)
- Unique constraints: inline in `create_table()` or via `UniqueConstraint` in model
- Tests: SQLite in-memory with session singleton reset (Phase 3 pattern) — PT conversion must work without MySQL-specific functions

### Integration Points
- `User` model (line 506 in models.py) — `user_id` FK references `users.id`
- Migration chain: 007 (refresh_tokens) → 008 (api_usage)
- Phase 8 will add the atomic counter logic on top of this table
- Phase 9 will query this table to decide free vs paid key

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches for migration structure and model definition.

</specifics>

<deferred>
## Deferred Ideas

- **UsageRepository with atomic increment** — Phase 8 concern, not Phase 7
- **Usage read endpoint (GET /auth/me/usage)** — Phase 8 (QUOT-03)
- **UsageAwareKeySelector** — Phase 9 (QUOT-04, QUOT-05)
- **Per-endpoint HTTP rate limiting** — Out of scope per REQUIREMENTS.md

</deferred>

---

*Phase: 07-usage-tracking-table*
*Context gathered: 2026-03-24*
