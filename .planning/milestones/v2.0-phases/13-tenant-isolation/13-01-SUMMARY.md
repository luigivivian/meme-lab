---
phase: 13-tenant-isolation
plan: 01
subsystem: database
tags: [sqlalchemy, alembic, tenant-isolation, multi-tenant, permission]

# Dependency graph
requires:
  - phase: 03-auth-backend
    provides: User model with role field, JWT auth
provides:
  - Migration 010 with backfill + NOT NULL constraints + Theme.user_id
  - CharacterRepository tenant filtering (reference implementation)
  - get_user_character deps.py helper (403/404)
  - Test scaffold for TENANT-01..04
affects: [13-02, 13-03, 14-instagram-connection]

# Tech tracking
tech-stack:
  added: []
  patterns: [fetch-then-check ownership, admin bypass via role check, PermissionError for 403]

key-files:
  created:
    - src/database/migrations/versions/010_tenant_isolation.py
    - tests/test_tenant.py
  modified:
    - src/database/models.py
    - src/database/repositories/character_repo.py
    - src/api/deps.py

key-decisions:
  - "Fetch-then-check pattern for 403 (not query-level filter) to distinguish 404 vs 403"
  - "Admin bypass via user.role == 'admin' check in _is_admin helper"
  - "PermissionError raised at repo level, caught as HTTPException 403 in deps.py helper"

patterns-established:
  - "Tenant filtering: user param on repo methods, _is_admin helper, PermissionError for forbidden"
  - "get_user_character: standard helper for routes needing character ownership check"

requirements-completed: [TENANT-01, TENANT-02, TENANT-03, TENANT-04]

# Metrics
duration: 3min
completed: 2026-03-25
---

# Phase 13 Plan 01: Tenant Isolation Foundation Summary

**Alembic migration 010 with backfill/NOT NULL, CharacterRepository tenant filtering with admin bypass, and get_user_character deps helper**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-25T02:51:53Z
- **Completed:** 2026-03-25T02:54:56Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Migration 010 backfills orphan characters/pipeline_runs, enforces NOT NULL on user_id/character_id, adds Theme.user_id column
- CharacterRepository is now the reference implementation for tenant filtering with fetch-then-check ownership and admin bypass
- get_user_character helper in deps.py translates PermissionError to HTTP 403 and None to HTTP 404
- 8 tests covering all 4 TENANT requirements pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Migration + Model updates** - `bdf2b50` (feat)
2. **Task 2: CharacterRepository tenant filtering + deps helper + test scaffold** - `236936b` (feat)

## Files Created/Modified
- `src/database/migrations/versions/010_tenant_isolation.py` - Backfill + NOT NULL + Theme.user_id migration
- `src/database/models.py` - Character.user_id NOT NULL, PipelineRun.character_id NOT NULL, Theme.user_id added
- `src/database/repositories/character_repo.py` - Tenant-filtered queries with admin bypass and PermissionError
- `src/api/deps.py` - get_user_character helper for route-level ownership enforcement
- `tests/test_tenant.py` - 8 tests for TENANT-01..04 (isolation, filtering, admin bypass, 403)

## Decisions Made
- Fetch-then-check pattern for get_by_slug/get_by_id (fetch first, then check ownership) to properly distinguish 404 vs 403
- Query-level filtering for list_all (WHERE user_id = X) for efficiency on list queries
- Admin bypass via _is_admin helper checking user.role == "admin"
- PermissionError("forbidden") raised at repo level, translated to HTTPException(403) in deps.py

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- CharacterRepository is the reference implementation; Plan 02 will replicate this pattern to other repositories
- Plan 03 will wire tenant filtering into API routes using get_user_character helper
- Migration 010 must be run on the database before deploying

---
*Phase: 13-tenant-isolation*
*Completed: 2026-03-25*
