---
phase: 21-dashboard-business-metrics
plan: 01
subsystem: api
tags: [fastapi, sqlalchemy, dashboard, brl, metrics, business-intelligence]

# Dependency graph
requires:
  - phase: 20-video-credits-brl
    provides: cost_brl column on ApiUsage, VIDEO_USD_TO_BRL config, get_credits_summary() pattern
provides:
  - GET /dashboard/business-metrics endpoint returning 5 consolidated business metrics
  - UsageRepository.get_business_metrics() method with 4 efficient queries
  - 7-day period comparison (current vs previous) for trend indicators
affects: [21-02-frontend-dashboard-cards, dashboard-ui, business-metrics-frontend]

# Tech tracking
tech-stack:
  added: []
  patterns: [sqlalchemy-case-period-bucketing, tenant-scoped-trend-aggregation, legacy-brl-fallback]

key-files:
  created:
    - tests/test_dashboard_metrics.py
  modified:
    - src/database/repositories/usage_repo.py
    - src/api/routes/dashboard.py

key-decisions:
  - "All-time totals use separate unbounded queries (not limited to 14-day window)"
  - "Active packages defined as ContentPackage with video_status IS NOT NULL"
  - "Legacy cost_brl=0 fallback applied at both period and daily level"

patterns-established:
  - "Period comparison via SQLAlchemy case() expressions: single query returns current/previous buckets"
  - "Tenant scoping for TrendEvent/ContentPackage via PipelineRun->Character.user_id join with NULL character fallback"

requirements-completed: [DASH-05, DASH-06, DASH-07]

# Metrics
duration: 2min
completed: 2026-03-27
---

# Phase 21 Plan 01: Business Metrics Backend Summary

**GET /dashboard/business-metrics endpoint with 5 metric groups (videos, avg cost BRL, budget, trends, packages) using period comparison queries and legacy USD-to-BRL fallback**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-27T21:44:15Z
- **Completed:** 2026-03-27T21:46:34Z
- **Tasks:** 1
- **Files modified:** 3

## Accomplishments
- Added `get_business_metrics()` to UsageRepository with 4 efficient SQL queries using SQLAlchemy `case()` for period bucketing
- Added GET `/dashboard/business-metrics` endpoint returning all 5 metric groups with current/previous 7d period values
- Applied legacy `cost_brl=0` fallback using `VIDEO_USD_TO_BRL` conversion for backward compatibility
- Tenant-scoped trend and package queries via PipelineRun->Character.user_id join
- 11 passing unit tests covering method existence, schema validation, BRL conversion, and endpoint registration

## Task Commits

Each task was committed atomically:

1. **Task 1: Backend -- get_business_metrics() repository method + API endpoint**
   - `4ad652c` (test) - TDD RED: failing tests for business metrics
   - `1329932` (feat) - TDD GREEN: implementation passes all 11 tests

## Files Created/Modified
- `tests/test_dashboard_metrics.py` - 11 unit tests validating method signature, response schema, BRL conversion, endpoint registration
- `src/database/repositories/usage_repo.py` - Added `get_business_metrics()` async method (~160 lines) with 4 queries
- `src/api/routes/dashboard.py` - Added GET `/dashboard/business-metrics` endpoint with DASH-05/06/07 references

## Decisions Made
- All-time totals (videos_generated.total, trends_collected.total) use separate unbounded queries, not limited to the 14-day comparison window, ensuring accurate lifetime counts
- Active packages defined as ContentPackage rows where video_status IS NOT NULL (matches existing idx_pkg_video_status index)
- Legacy cost_brl=0 fallback applied consistently at period level (current/previous) and daily level, using same pattern as get_credits_summary()

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Test initially used `/business-metrics` path but FastAPI APIRouter includes prefix in route.path (`/dashboard/business-metrics`). Fixed test to match using `any("business-metrics" in r ...)` pattern.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Business metrics endpoint ready for frontend consumption in Plan 02
- Response schema provides all data needed for StatsCard trend indicators
- BRL values pre-computed server-side for direct display

## Self-Check: PASSED

All files verified present, all commit hashes found in git log.

---
*Phase: 21-dashboard-business-metrics*
*Completed: 2026-03-27*
