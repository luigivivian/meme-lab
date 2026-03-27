---
phase: 20-kie-ai-credits-cost-tracking
plan: 01
subsystem: api, database
tags: [sqlalchemy, alembic, fastapi, pydantic, brl-cost-tracking]

# Dependency graph
requires:
  - phase: 999.1-video-generation
    provides: ApiUsage tracking for kie_video, VIDEO_MODELS config with prices_brl
provides:
  - cost_brl and model columns on ApiUsage
  - Migration 016 with tier widening
  - compute_video_cost_brl helper for BRL price lookup
  - UsageRepository.increment with cost_brl/model accumulation
  - get_credits_summary method with per-model BRL breakdown
  - GET /generate/video/credits/summary endpoint
  - VideoCreditsResponse and ModelCostBreakdown Pydantic models
affects: [20-02-dashboard-credits-card, phase-21-usd-to-brl-migration]

# Tech tracking
tech-stack:
  added: []
  patterns: [tier=model_id for per-model cost grouping, BRL-native cost recording via prices_brl lookup]

key-files:
  created:
    - src/database/migrations/versions/016_add_cost_brl_and_model.py
  modified:
    - src/database/models.py
    - src/database/repositories/usage_repo.py
    - src/api/routes/video.py
    - src/api/models.py
    - config.py
    - tests/test_credits.py
    - tests/test_api_usage.py

key-decisions:
  - "tier=model_id approach: per-model rows via existing unique constraint, no schema change needed"
  - "Legacy rows (cost_brl=0, cost_usd>0) handled by fallback conversion in summary query"
  - "compute_video_cost_brl uses prices_brl lookup with closest-duration snap, USD*BRL fallback for unknown models"

patterns-established:
  - "BRL cost tracking: compute_video_cost_brl(model_id, duration) -> float from VIDEO_MODELS prices_brl"
  - "Per-model usage grouping: tier=model_id in api_usage creates separate daily buckets per model"

requirements-completed: [CRED-01, CRED-02, CRED-03]

# Metrics
duration: 4min
completed: 2026-03-27
---

# Phase 20 Plan 01: Video Credits Backend Summary

**BRL-native cost tracking via ApiUsage cost_brl column, per-model tier grouping, and credits summary API endpoint with prices_brl lookup**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-27T18:44:24Z
- **Completed:** 2026-03-27T18:49:07Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- ApiUsage model extended with cost_brl (Float) and model (String(100)) columns, tier widened to String(100)
- Alembic migration 016 chains from 015 with full upgrade/downgrade
- compute_video_cost_brl helper: prices_brl lookup with closest-duration snap, USD*BRL fallback
- UsageRepository.increment accumulates cost_brl in dialect-aware upsert (MySQL/SQLite)
- get_credits_summary returns per-model BRL breakdown, all-time totals, daily budget
- GET /generate/video/credits/summary endpoint returns VideoCreditsResponse
- _generate_video_task records BRL cost with tier=model_id on success only (CRED-01)

## Task Commits

Each task was committed atomically:

1. **Task 1: DB migration, model update, cost helper, and test scaffold**
   - `1c6fdfb` (test: TDD RED - failing tests)
   - `e9d4262` (feat: TDD GREEN - schema, migration, helper)
2. **Task 2: Extend UsageRepository, wire _generate_video_task, add credits summary endpoint** - `19132ef` (feat)

## Files Created/Modified
- `src/database/migrations/versions/016_add_cost_brl_and_model.py` - Alembic migration adding cost_brl, model columns, widening tier
- `src/database/models.py` - ApiUsage with cost_brl, model columns, tier String(100)
- `config.py` - compute_video_cost_brl helper function
- `src/database/repositories/usage_repo.py` - Extended increment() with cost_brl/model, new get_credits_summary()
- `src/api/routes/video.py` - GET /credits/summary endpoint, updated _generate_video_task success path
- `src/api/models.py` - VideoCreditsResponse and ModelCostBreakdown Pydantic models
- `tests/test_credits.py` - 9 tests covering schema, helper, response models
- `tests/test_api_usage.py` - Updated tier length assertion for String(100)

## Decisions Made
- tier=model_id approach reuses existing unique constraint for per-model daily buckets without schema changes
- Legacy rows handled via cost_usd * VIDEO_USD_TO_BRL fallback in summary query (no migration backfill)
- compute_video_cost_brl placed in config.py near VIDEO_MODELS for co-location

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated test_api_usage.py tier length assertion**
- **Found during:** Task 1 (after widening tier from String(20) to String(100))
- **Issue:** Existing test asserted tier.type.length == 20, now fails with 100
- **Fix:** Updated assertion to expect String(100) with comment noting Phase 20 change
- **Files modified:** tests/test_api_usage.py
- **Verification:** All 7 existing tests pass
- **Committed in:** e9d4262 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Necessary test update for schema change. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all data flows are wired end-to-end.

## Next Phase Readiness
- Backend complete: credits summary API and cost recording are production-ready
- Ready for Plan 02: dashboard Video Credits card can fetch from GET /generate/video/credits/summary
- Migration 016 needs to be run on production MySQL before deployment

## Self-Check: PASSED

All files verified present. All 3 commits verified in git log.

---
*Phase: 20-kie-ai-credits-cost-tracking*
*Completed: 2026-03-27*
