# Phase 7: Usage Tracking Table - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-24
**Phase:** 07-usage-tracking-table
**Areas discussed:** Service granularity, Timezone reset logic, Status column semantics, Multi-user prep

---

## Service Granularity

### Q1: What services should the api_usage table track?

| Option | Description | Selected |
|--------|-------------|----------|
| Gemini Image only | Just 'gemini_image' for now — the only service with quota limits | |
| All Gemini services | Track 'gemini_image', 'gemini_text', 'gemini_web' | |
| All external APIs | Track every external call: gemini_image, gemini_text, gemini_web, comfyui | ✓ |

**User's choice:** All external APIs
**Notes:** Maximum observability — track all external API calls.

### Q2: Tier column values — simple or prefixed?

| Option | Description | Selected |
|--------|-------------|----------|
| Simple: free/paid | Matches User.active_key_tier values | ✓ |
| Prefixed: gemini_free/gemini_paid | More explicit, service-specific tiers | |

**User's choice:** Simple: free/paid
**Notes:** Consistency with existing User.active_key_tier schema.

---

## Timezone Reset Logic

### Q3: How should the daily date bucket be stored?

| Option | Description | Selected |
|--------|-------------|----------|
| Store as PT date | DATE column, Python converts to PT before insert | |
| Store as UTC datetime + convert on read | DATETIME(UTC) column, convert to PT on every read | ✓ |

**User's choice:** Store as UTC datetime + convert on read
**Notes:** Keeps raw data timezone-agnostic.

### Q4: Where should PT conversion live?

| Option | Description | Selected |
|--------|-------------|----------|
| Python/repository layer | Use zoneinfo in UsageRepository, keeps SQLite tests working | ✓ |
| MySQL CONVERT_TZ | DB-level conversion, ties to MySQL | |

**User's choice:** Python/repository layer
**Notes:** Preserves SQLite test compatibility from Phase 3 pattern.

---

## Status Column Semantics

### Q5: What should the status column represent?

| Option | Description | Selected |
|--------|-------------|----------|
| Call outcome | Values: success, error, rejected | ✓ |
| Quota state | Values: ok, limit_reached, exhausted | |
| You decide | Claude picks based on Phase 8-10 needs | |

**User's choice:** Call outcome (success/error/rejected)
**Notes:** None.

### Q6: Should failed API calls count toward the daily limit?

| Option | Description | Selected |
|--------|-------------|----------|
| No — only success counts | Only 'success' rows count toward daily limit | ✓ |
| Yes — all attempts count | Every call counts regardless of outcome | |

**User's choice:** No — only success counts
**Notes:** Users shouldn't lose quota for API failures.

---

## Multi-User Prep

### Q7: How should api_usage handle shared key usage?

| Option | Description | Selected |
|--------|-------------|----------|
| Always per-user | Every row has a user_id FK, even for shared keys | |
| System rows for shared keys | user_id=NULL for shared .env key usage | ✓ |

**User's choice:** System rows for shared keys
**Notes:** Separate tracking for system-level shared key usage.

### Q8: User FK nullability

| Option | Description | Selected |
|--------|-------------|----------|
| Nullable | user_id is nullable FK, NULL = system/shared key | ✓ |
| NOT NULL + system user | Create sentinel 'system' user row | |

**User's choice:** Nullable
**Notes:** Simpler, allows pipeline to track usage before auth is enforced.

### Q9: Unique constraint on row granularity

| Option | Description | Selected |
|--------|-------------|----------|
| One row per combo | UniqueConstraint on (user_id, service, tier, date) | ✓ |
| One row per API call | Each call inserts a new row | |

**User's choice:** One row per (user_id, service, tier, date)
**Notes:** Phase 8 uses INSERT ON DUPLICATE KEY UPDATE for atomic increment.

---

## Claude's Discretion

- Migration version number and naming convention (008)
- Additional indexes beyond unique constraint
- usage_count default value
- ORM relationship back-populates

## Deferred Ideas

- UsageRepository with atomic increment (Phase 8)
- Usage read endpoint (Phase 8)
- UsageAwareKeySelector (Phase 9)
