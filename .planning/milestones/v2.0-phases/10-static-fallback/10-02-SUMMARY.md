---
phase: 10-static-fallback
plan: 02
subsystem: pipeline
tags: [gemini, image-worker, static-fallback, quota-exhaustion, fallback-reason]

# Dependency graph
requires:
  - phase: 10-static-fallback
    plan: 01
    provides: "KeyResolution tier='exhausted' sentinel from UsageAwareKeySelector.resolve()"
  - phase: 09-dual-key-wiring
    provides: "UsageAwareKeySelector with resolve() and KeyResolution dataclass"
provides:
  - "compose() pre-checks quota exhaustion and falls back to static backgrounds"
  - "fallback_reason metadata distinguishes quota_exhausted, generation_failed, mode_static"
  - "GenerationLayer.process() propagates user_id/session to compose()"
  - "Backward-compatible compose() -- works without user_id/session for CLI usage"
affects: [api-routes, async-orchestrator, dashboard-usage]

# Tech tracking
tech-stack:
  added: []
  patterns: ["quota pre-check at compose() entry point before backend selection", "optional user_id/session params for backward compatibility"]

key-files:
  created:
    - tests/test_static_fallback.py
  modified:
    - src/pipeline/workers/image_worker.py
    - src/pipeline/workers/generation_layer.py

key-decisions:
  - "Pre-check wrapped in bg is None guard to skip backend selection when exhaustion already resolved"
  - "fallback_reason set as metadata field inside gen_metadata dict, not as separate ComposeResult field"

patterns-established:
  - "Quota pre-check pattern: lazy import UsageAwareKeySelector inside compose() to avoid circular imports"
  - "Backward compat pattern: user_id/session default to None, pre-check only runs when both provided"

requirements-completed: [QUOT-06]

# Metrics
duration: 3min
completed: 2026-03-24
---

# Phase 10 Plan 02: ImageWorker Static Fallback on Exhaustion Summary

**compose() pre-checks quota exhaustion via UsageAwareKeySelector, falls back to static backgrounds with fallback_reason metadata distinguishing 3 failure modes**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-24T20:02:12Z
- **Completed:** 2026-03-24T20:05:44Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Added quota exhaustion pre-check to compose() using UsageAwareKeySelector.resolve()
- Implemented 3 distinct fallback_reason values: quota_exhausted, generation_failed, mode_static
- Propagated user_id/session through GenerationLayer.process() to all 3 compose() call sites
- Maintained full backward compatibility -- compose() without user_id/session works exactly as before
- 5 new integration tests covering all fallback paths, all 18 tests pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Create test_static_fallback.py with exhaustion flow tests (RED)** - `653104a` (test)
2. **Task 2: Add pre-check to compose() and fallback_reason metadata (GREEN)** - `cd6cb80` (feat)

_Note: TDD task -- RED committed separately from GREEN_

## Files Created/Modified
- `tests/test_static_fallback.py` - 5 async tests covering exhaustion, metadata, backward compat, generation_failed, mode_static
- `src/pipeline/workers/image_worker.py` - compose() signature with user_id/session, quota pre-check block, fallback_reason metadata in 3 paths
- `src/pipeline/workers/generation_layer.py` - process() signature with user_id/session, propagated to 3 compose() call sites

## Decisions Made
- Pre-check block is guarded by `if bg is None` before backend selection to avoid overwriting the exhaustion result with normal backend flow
- fallback_reason is stored inside gen_metadata dict rather than as a separate ComposeResult field, keeping the dataclass stable
- UsageAwareKeySelector is imported lazily inside compose() to avoid circular imports at module load time

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Added bg is None guard before backend selection**
- **Found during:** Task 2 (GREEN phase)
- **Issue:** After pre-check set bg from exhaustion, the code continued into the backend selection block (auto mode) which overwrote bg, bg_source, and gen_metadata
- **Fix:** Wrapped the entire backend selection block in `if bg is None:` so it only runs when pre-check did not already resolve a background
- **Files modified:** src/pipeline/workers/image_worker.py
- **Verification:** All 5 tests pass including test_compose_static_on_exhaustion
- **Committed in:** cd6cb80 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Necessary guard to prevent backend selection from overwriting pre-check result. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all code paths are fully implemented and tested.

## Next Phase Readiness
- Static fallback pipeline is complete end-to-end
- Callers of GenerationLayer.process() can now pass user_id/session to enable quota pre-check
- AsyncPipelineOrchestrator needs to be updated to pass user_id/session when running in authenticated context

---
*Phase: 10-static-fallback*
*Completed: 2026-03-24*
