---
phase: 08-atomic-counter
plan: 01
subsystem: database, api
tags: [sqlalchemy, upsert, atomic-counter, usage-tracking, fastapi, pydantic, timezone]

# Dependency graph
requires:
  - phase: 07-usage-tracking-table
    provides: ApiUsage model with UniqueConstraint on (user_id, service, tier, date)
  - phase: 03-auth-backend
    provides: JWT auth, get_current_user dependency, auth routes
provides:
  - UsageRepository with atomic dialect-aware upsert (MySQL + SQLite)
  - Configurable daily limits via env vars with sensible defaults
  - check_limit pre-check flow with rejected row insertion
  - GET /auth/me/usage endpoint with per-service breakdown
  - ServiceUsage and UsageResponse Pydantic schemas
affects: [09-dual-key-management, 10-static-fallback, 11-dashboard]

# Tech tracking
tech-stack:
  added: []
  patterns: [dialect-aware-upsert, env-var-limits, pt-timezone-bucketing]

key-files:
  created:
    - src/database/repositories/usage_repo.py
    - tests/test_atomic_counter.py
  modified:
    - src/auth/schemas.py
    - src/api/routes/auth.py

key-decisions:
  - "PT timezone (America/Los_Angeles) for daily bucketing, naive UTC stored in DB"
  - "Rejected rows use full timestamp (not bucketed) to avoid unique constraint collision"
  - "0 means unlimited, remaining=-1 as sentinel for unlimited services"
  - "Known services always included in usage response even with 0 usage"

patterns-established:
  - "Dialect-aware upsert: _is_sqlite() check from config.DATABASE_URL, dispatch to sqlite_insert/mysql_insert"
  - "Env var limit pattern: {SERVICE}_DAILY_LIMIT_{TIER} with _DEFAULT_LIMITS fallback dict"

requirements-completed: [QUOT-02, QUOT-03]

# Metrics
duration: 3min
completed: 2026-03-24
---

# Phase 8 Plan 1: Atomic Counter Summary

**Atomic usage counter with dialect-aware upsert, configurable env-var limits, and GET /auth/me/usage endpoint**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-24T18:11:23Z
- **Completed:** 2026-03-24T18:14:39Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- UsageRepository with atomic increment via SQLite on_conflict_do_update / MySQL on_duplicate_key_update
- Daily limit enforcement: env vars override defaults, 0 = unlimited, rejected rows tracked (D-03)
- GET /auth/me/usage returns per-service breakdown with used/limit/remaining/resets_at (D-04)
- 14 tests pass including 10-concurrent-call atomicity and exact boundary enforcement

## Task Commits

Each task was committed atomically:

1. **Task 1: UsageRepository with atomic increment and limit config** - `cab385f` (test: RED), `e1b1ddd` (feat: GREEN)
2. **Task 2: Usage endpoint and Pydantic schemas** - `7c6c356` (feat)

## Files Created/Modified
- `src/database/repositories/usage_repo.py` - UsageRepository: atomic increment, check_limit, get_user_usage, get_daily_limit
- `src/auth/schemas.py` - Added ServiceUsage and UsageResponse Pydantic schemas
- `src/api/routes/auth.py` - Added GET /auth/me/usage endpoint
- `tests/test_atomic_counter.py` - 14 tests: unit (9) + integration (5)

## Decisions Made
- PT timezone (America/Los_Angeles) for daily reset bucketing, consistent with Phase 7 D-04
- Rejected rows stored with full datetime.now(UTC) timestamp to avoid unique constraint collision with the daily-bucketed success rows
- remaining = -1 as sentinel for unlimited services (limit=0)
- Known services (gemini_image/free, gemini_text/free) always appear in usage response even when unused

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed deprecated datetime.utcnow()**
- **Found during:** Task 1
- **Issue:** datetime.utcnow() is deprecated in Python 3.14, generates DeprecationWarning
- **Fix:** Replaced with datetime.now(ZoneInfo("UTC")).replace(tzinfo=None)
- **Files modified:** src/database/repositories/usage_repo.py
- **Verification:** Tests pass with no warnings
- **Committed in:** e1b1ddd

---

**Total deviations:** 1 auto-fixed (1 bug fix)
**Impact on plan:** Minor fix for Python 3.14 compatibility. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- UsageRepository ready for Phase 9 (dual key management) to integrate with UsageAwareKeySelector
- check_limit pre-check flow ready for injection before external API calls
- GET /auth/me/usage endpoint ready for Phase 11 dashboard consumption

## Self-Check: PASSED

- All 5 files exist
- All 3 commits found (cab385f, e1b1ddd, 7c6c356)
- All acceptance criteria verified: classes, methods, imports, patterns, 14 test functions

---
*Phase: 08-atomic-counter*
*Completed: 2026-03-24*
