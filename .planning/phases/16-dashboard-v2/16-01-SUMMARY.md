---
phase: 16-dashboard-v2
plan: 01
subsystem: api
tags: [fastapi, sqlalchemy, dashboard, analytics, recharts-backend]

requires:
  - phase: 13-tenant-isolation
    provides: "Tenant-scoped data access pattern (Character.user_id join)"
  - phase: 08-atomic-counter
    provides: "api_usage table and UsageRepository with atomic upsert"
provides:
  - "4 dashboard analytics GET endpoints under /dashboard/*"
  - "UsageRepository.get_usage_history and get_cost_breakdown methods"
  - "Pipeline activity aggregation with tenant scoping"
  - "Publishing stats aggregation with tenant scoping"
affects: [16-02-frontend-charts]

tech-stack:
  added: []
  patterns: ["date-range aggregate queries with zero-fill", "outerjoin tenant scoping for nullable character_id"]

key-files:
  created:
    - src/api/routes/dashboard.py
  modified:
    - src/database/repositories/usage_repo.py
    - src/api/app.py

key-decisions:
  - "Pipeline activity uses outerjoin + OR for tenant scoping: Character.user_id match OR character_id IS NULL (legacy runs)"
  - "Usage history zero-fills all dates in range including common services (gemini_text, gemini_image, kie_video) even if no data"
  - "Cost breakdown only returns services with cost > 0 or calls > 0 (no zero-fill for cost)"
  - "Days param clamped to 1-90 via Query validation"

patterns-established:
  - "Dashboard endpoint pattern: Query param days with ge=1/le=90, lazy repo import, tenant via get_current_user"

requirements-completed: [DASH-01, DASH-02, DASH-03, DASH-04]

duration: 2min
completed: 2026-03-26
---

# Phase 16 Plan 01: Dashboard Backend API Summary

**4 dashboard analytics endpoints (usage-history, cost-breakdown, pipeline-activity, publishing-stats) with tenant-scoped SQL aggregation and date zero-fill**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-26T20:01:41Z
- **Completed:** 2026-03-26T20:04:15Z
- **Tasks:** 1
- **Files modified:** 3

## Accomplishments
- Created `/dashboard/usage-history` endpoint returning 30-day daily usage grouped by service with zero-filled dates
- Created `/dashboard/cost-breakdown` endpoint returning per-service cost aggregation with total
- Created `/dashboard/pipeline-activity` endpoint with tenant-scoped outerjoin on Character table
- Created `/dashboard/publishing-stats` endpoint with status counts (published/queued/failed/cancelled)
- Added `get_usage_history` and `get_cost_breakdown` methods to UsageRepository

## Task Commits

Each task was committed atomically:

1. **Task 1: Add usage_repo history/cost methods + create dashboard route module** - `341a2fc` (feat)

## Files Created/Modified
- `src/api/routes/dashboard.py` - New module with 4 GET dashboard analytics endpoints
- `src/database/repositories/usage_repo.py` - Added get_usage_history and get_cost_breakdown aggregate methods
- `src/api/app.py` - Registered dashboard router import and include_router

## Decisions Made
- Pipeline activity uses outerjoin on Character + OR condition to include both user-owned character runs and legacy runs (character_id IS NULL) -- consistent with schedule_repo tenant pattern
- Usage history always includes gemini_text, gemini_image, kie_video in services_seen set even if no data exists -- ensures frontend charts have consistent series
- Cost breakdown filters out zero-cost/zero-call services to keep response clean
- Days parameter validated via FastAPI Query(ge=1, le=90) plus explicit clamp

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all endpoints return real aggregated data from existing DB tables.

## Next Phase Readiness
- All 4 backend endpoints ready for frontend consumption in Plan 02
- Response shapes match TypeScript interfaces defined in Plan 02

## Self-Check: PASSED

- All 3 files verified present on disk
- Commit 341a2fc verified in git log

---
*Phase: 16-dashboard-v2*
*Completed: 2026-03-26*
