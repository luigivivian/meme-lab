---
phase: quick
plan: 260325-qhl
subsystem: api, database, image-gen
tags: [gemini, cost-tracking, token-estimation, pricing, usage]

# Dependency graph
requires:
  - phase: 08-quotas
    provides: ApiUsage model and UsageRepository with upsert pattern
provides:
  - Tile-based token estimation for Gemini Image input images
  - Per-generation USD cost calculation and logging
  - cost_usd column in api_usage table with cumulative tracking
  - GET /auth/me/cost-stats endpoint for cost aggregation
affects: [dashboard, billing, usage-monitoring]

# Tech tracking
tech-stack:
  added: []
  patterns: [tile-based-token-estimation, per-generation-cost-tracking]

key-files:
  created:
    - src/database/migrations/versions/011_add_cost_usd_to_api_usage.py
  modified:
    - src/image_gen/gemini_client.py
    - src/database/models.py
    - src/database/repositories/usage_repo.py
    - src/api/routes/generation.py
    - src/api/routes/auth.py
    - src/auth/schemas.py

key-decisions:
  - "Tile-based formula: ceil(w/768)*ceil(h/768)*258 tokens per input image"
  - "Output cost fixed at 1290 tokens * $30/1M = ~$0.0387 per generated image"
  - "Refine endpoint uses output-only cost estimate (conservative) since ref dims not easily available"
  - "cost_usd accumulated via upsert (same pattern as usage_count) per day/service/tier bucket"

patterns-established:
  - "Cost estimation pattern: estimate_generation_cost() returns dict with input_tokens, output_tokens, estimated_cost_usd"
  - "Cost passthrough pattern: generation endpoints extract cost from result and pass to _increment_usage"

requirements-completed: [COST-TRACK]

# Metrics
duration: 6min
completed: 2026-03-25
---

# Quick Plan 260325-qhl: Gemini Image Cost Tracking Summary

**Tile-based token estimation with per-generation USD cost tracking, cumulative stats in api_usage table, and /auth/me/cost-stats endpoint**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-25T22:08:44Z
- **Completed:** 2026-03-25T22:14:32Z
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments
- Fixed token estimation from flat 258 to real tile-based calculation (ceil(w/768)*ceil(h/768)*258)
- Added per-generation cost calculation using Gemini 2.5 Flash Image pricing ($0.30/1M input, $30/1M output)
- Added cost_usd column to api_usage table with migration 011, cumulative tracking via upsert
- Exposed GET /auth/me/cost-stats returning total_cost_usd, total_images, avg_cost_per_image, days_tracked

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix token estimation and add cost calculation** - `102c20f` (feat)
2. **Task 2: Add cost_usd to database and update usage tracking** - `5602f4d` (feat)
3. **Task 3: Add cost stats endpoint** - `7bf574f` (feat)

## Files Created/Modified
- `src/image_gen/gemini_client.py` - Added math import, cost constants, estimate_image_input_tokens(), estimate_generation_cost(), estimated_cost_usd field on ImageGenerationResult, tile-based estimation in _tentar_gerar/_tentar_modelos, cost logging in generate_image()/refine_image()
- `src/database/models.py` - Added cost_usd Float column to ApiUsage
- `src/database/migrations/versions/011_add_cost_usd_to_api_usage.py` - Alembic migration adding cost_usd column
- `src/database/repositories/usage_repo.py` - Updated increment() with cost_usd accumulation, added get_cost_stats()
- `src/api/routes/generation.py` - Updated _increment_usage() and all 3 endpoints to pass cost_usd, added estimated_cost_usd to responses
- `src/api/routes/auth.py` - Added GET /auth/me/cost-stats endpoint
- `src/auth/schemas.py` - Added CostStatsResponse Pydantic model

## Decisions Made
- Token estimation uses real tile formula matching Google's pricing documentation
- Cost per generation at 3 refs 1024x1024 is approximately $0.0398 (output dominates at $0.0387)
- Refine endpoint uses conservative output-only cost estimate since extracting ref dims would require significant refactoring of the refine call chain
- Cost accumulates in the same upsert pattern as usage_count (per day/service/tier bucket)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed bg_result undefined in compose_image scope**
- **Found during:** Task 2 (updating compose_image endpoint)
- **Issue:** bg_result variable was only defined inside the non-auto_refine branch, causing potential NameError when checking cost
- **Fix:** Initialized bg_result = None at the top of compose_image before the conditional branches
- **Files modified:** src/api/routes/generation.py
- **Verification:** Code path analysis confirms bg_result always defined
- **Committed in:** 5602f4d (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Necessary for correctness. No scope creep.

## Issues Encountered
None.

## Known Stubs
None - all data paths are fully wired.

## User Setup Required
- Run migration 011: `alembic upgrade head` (adds cost_usd column to api_usage table)

## Next Phase Readiness
- Cost tracking is passive and backward-compatible (defaults to 0.0 for existing rows)
- Dashboard phase (16) can consume /auth/me/cost-stats to display cost metrics
- Future: actual Gemini API response metadata could provide real token counts to replace estimates

---
## Self-Check: PASSED

All 7 modified/created files verified on disk. All 3 task commits (102c20f, 5602f4d, 7bf574f) found in git log.

---
*Quick Plan: 260325-qhl*
*Completed: 2026-03-25*
