---
phase: 20-kie-ai-credits-cost-tracking
plan: 02
subsystem: ui
tags: [next.js, typescript, swr, dashboard, brl, cost-tracking]

# Dependency graph
requires:
  - phase: 20-kie-ai-credits-cost-tracking-01
    provides: "GET /generate/video/credits/summary endpoint with per-model BRL cost breakdown"
provides:
  - "VideoCreditsResponse TypeScript interface matching backend Pydantic schema"
  - "getVideoCredits() API client function"
  - "useVideoCredits() SWR hook with 60s refresh"
  - "VideoCreditsCard dashboard component with per-model BRL table, daily budget bar, expand toggle"
  - "formatBRL() helper using Intl.NumberFormat pt-BR"
affects: [dashboard, video-generation, cost-tracking]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "formatBRL via Intl.NumberFormat pt-BR for currency display"
    - "Budget progress bar with color thresholds (green <80%, amber 80-95%, rose >=95%)"
    - "Expandable model table (show 5, toggle for rest)"

key-files:
  created: []
  modified:
    - "memelab/src/lib/api.ts"
    - "memelab/src/hooks/use-api.ts"
    - "memelab/src/app/(app)/dashboard/page.tsx"

key-decisions:
  - "VideoCreditsCard placed below existing dashboard content, before Dialog (per Phase 16 pattern)"
  - "No existing cost_usd displays modified (deferred to Phase 21 per user decision)"
  - "formatBRL uses Intl.NumberFormat for locale-aware BRL formatting"

patterns-established:
  - "formatBRL helper: reusable BRL currency formatter for future cost displays"
  - "Budget progress bar pattern: color thresholds at 80% and 95%"

requirements-completed: [CRED-04]

# Metrics
duration: 2min
completed: 2026-03-27
---

# Phase 20 Plan 02: Video Credits Dashboard Card Summary

**VideoCreditsCard component with per-model BRL cost breakdown table, daily budget progress bar, and all-time stats on dashboard**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-27T18:51:27Z
- **Completed:** 2026-03-27T18:53:44Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Added TypeScript interfaces (ModelCostBreakdown, VideoCreditsResponse) matching backend Pydantic schema exactly
- Added getVideoCredits() API client function and useVideoCredits() SWR hook with 60s refresh
- Built VideoCreditsCard component with summary stats, daily budget bar, per-model table, expand toggle, failed count, and all-time totals

## Task Commits

Each task was committed atomically:

1. **Task 1: API client type + fetch function + SWR hook** - `b76192b` (feat)
2. **Task 2: Video Credits dashboard card with per-model BRL table** - `3378e79` (feat)

## Files Created/Modified
- `memelab/src/lib/api.ts` - Added ModelCostBreakdown and VideoCreditsResponse interfaces, getVideoCredits() fetch function
- `memelab/src/hooks/use-api.ts` - Added useVideoCredits() SWR hook with 60s refresh and error retry
- `memelab/src/app/(app)/dashboard/page.tsx` - Added formatBRL helper, VideoCreditsCard component, wired into DashboardPage

## Decisions Made
- VideoCreditsCard placed below existing dashboard content, before the Video Generation Dialog (follows Phase 16 pattern of appending new cards)
- No existing cost_usd displays modified -- per user decision, this is Phase 21 scope
- formatBRL uses Intl.NumberFormat with pt-BR locale for consistent currency formatting

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 20 complete: backend endpoint (Plan 01) and frontend card (Plan 02) both delivered
- Dashboard now shows per-model BRL video costs with daily budget tracking
- Phase 21 can extend existing cost_usd displays to use BRL data from this endpoint

## Self-Check: PASSED

- All 3 modified files exist on disk
- Both task commits (b76192b, 3378e79) found in git history
- SUMMARY.md created at expected path

---
*Phase: 20-kie-ai-credits-cost-tracking*
*Completed: 2026-03-27*
