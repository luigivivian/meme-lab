---
phase: 10-static-fallback
plan: 01
subsystem: api
tags: [gemini, key-selector, exhaustion, fallback, usage-tracking]

# Dependency graph
requires:
  - phase: 09-dual-key-wiring
    provides: "UsageAwareKeySelector with resolve() and KeyResolution dataclass"
  - phase: 08-atomic-counter
    provides: "UsageRepository.check_limit() for daily limit enforcement"
provides:
  - "KeyResolution tier='exhausted' when all API key tiers are over daily limit"
  - "Free-only mode exhaustion detection (D-02)"
  - "Dual-key exhaustion detection with paid tier check (D-01)"
affects: [10-02-PLAN, image-worker, static-fallback]

# Tech tracking
tech-stack:
  added: []
  patterns: ["exhaustion sentinel: tier='exhausted' with empty api_key signals downstream to skip Gemini"]

key-files:
  created: []
  modified:
    - src/services/key_selector.py
    - tests/test_key_selector.py

key-decisions:
  - "Free-only mode now checks DB limits instead of returning free key unconditionally"
  - "Existing tests 2-4 updated to mock dual check_limit calls after behavior change"

patterns-established:
  - "Exhaustion pattern: KeyResolution(api_key='', tier='exhausted', mode='auto') signals downstream consumers to use static fallback"

requirements-completed: [QUOT-06]

# Metrics
duration: 2min
completed: 2026-03-24
---

# Phase 10 Plan 01: Key Selector Exhaustion Detection Summary

**UsageAwareKeySelector.resolve() returns tier='exhausted' when all Gemini API key tiers hit daily limits, enabling static fallback in Plan 02**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-24T19:57:07Z
- **Completed:** 2026-03-24T19:59:36Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Extended resolve() with exhaustion detection for both free-only and dual-key modes
- Added 3 new tests covering exhaustion paths (both tiers exhausted, free-only exhausted, paid fallback when free exhausted)
- Updated valid_tiers set to include "exhausted"
- All 13 tests pass with no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Add exhaustion tests (TDD RED)** - `1b67a63` (test)
2. **Task 2: Implement exhaustion detection (TDD GREEN)** - `2a37585` (feat)

_Note: TDD task — RED committed separately from GREEN_

## Files Created/Modified
- `src/services/key_selector.py` - Added exhaustion detection in Priority 3 (free-only) and Priority 4 (auto) paths; updated KeyResolution docstring
- `tests/test_key_selector.py` - Added 3 new tests (11-13), updated test 9 valid_tiers, updated tests 2-4 to mock dual check_limit calls

## Decisions Made
- Free-only mode (Priority 3) now checks DB limits via check_limit() before returning free key, instead of returning unconditionally. This was necessary per D-02 to detect exhaustion in free-only deployments.
- Existing tests 2, 3, and 4 were updated to provide check_limit mocks since free-only mode now invokes the repository. This is a behavioral change in the tests but preserves the same assertions.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated existing tests 2, 3, 4 for new free-only behavior**
- **Found during:** Task 2 (GREEN phase)
- **Issue:** Tests 2 (paid when over limit), 3 (free-only no paid key), and 4 (identical keys) failed because free-only mode now calls check_limit() but tests did not mock UsageRepository
- **Fix:** Updated test 2 to use side_effect for two check_limit calls; tests 3 and 4 to mock check_limit returning (True, ...) for the free tier
- **Files modified:** tests/test_key_selector.py
- **Verification:** All 13 tests pass
- **Committed in:** 2a37585 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Necessary adaptation of existing tests to match new behavior. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all code paths are fully implemented and tested.

## Next Phase Readiness
- KeyResolution with tier='exhausted' is ready for Plan 02 (ImageWorker static fallback)
- Downstream consumers can check `result.tier == "exhausted"` to skip Gemini and use static backgrounds

---
*Phase: 10-static-fallback*
*Completed: 2026-03-24*
