---
phase: 18-job-status-sync-management
plan: 02
subsystem: frontend
tags: [nextjs, swr, video-jobs, card-grid, progress-bar, retry, kie-ai]

# Dependency graph
requires:
  - phase: 18-job-status-sync-management
    plan: 01
    provides: "POST /generate/video/retry/{id}, GET /generate/video/progress/{id} with step_label"
provides:
  - "Card grid video jobs UI with thumbnail, status badge, model, duration, BRL cost"
  - "Real-time progress bar with Kie.ai step labels (Na fila, Gerando, Concluido)"
  - "One-click retry button for failed video jobs"
  - "Expandable detail row with task_id, error, prompt, creation date"
  - "Video status filter tabs (all/generating/completed/failed)"
  - "retryVideo API client function"
  - "useVideoProgress hook with 3s polling"
affects: [jobs-page, video-workflow]

# Tech tracking
tech-stack:
  added: []
  patterns: ["card grid with responsive breakpoints", "inline sub-components for VideoJobCard and VideoProgressBar"]

key-files:
  created: []
  modified:
    - memelab/src/lib/api.ts
    - memelab/src/hooks/use-api.ts
    - memelab/src/app/(app)/jobs/page.tsx

key-decisions:
  - "Video section shown always (even when empty) with empty state message"
  - "BRL cost displayed as cost_usd * 5.5 (approximate USD-BRL conversion)"
  - "VideoJobCard and VideoProgressBar as inline components in same file (not separate)"
  - "Idle polling updated from 10s to 30s per CONTEXT.md decision"

patterns-established:
  - "Video filter tabs separate from batch job filter tabs (independent state)"
  - "Retry triggers SWR mutate for immediate list refresh"

requirements-completed: [JOB-03, JOB-04]

# Metrics
duration: 5min
completed: 2026-03-27
---

# Phase 18 Plan 02: Video Jobs Frontend Redesign Summary

**Card grid video jobs UI with progress bars, retry buttons, expandable detail rows, and status filter tabs**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-27T15:36:09Z
- **Completed:** 2026-03-27T15:41:12Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Added `retryVideo` API function and `step_label` to `VideoProgressResponse` interface
- Updated `useVideoList` hook idle polling from 10s to 30s per CONTEXT.md decision
- Redesigned Video Jobs section from flat list to responsive card grid (1/2/3 columns)
- Each card shows: thumbnail with status badge overlay, phrase, model/duration/BRL cost, action buttons
- Generating jobs display real-time progress bar with Kie.ai step labels via `useVideoProgress` hook
- Failed jobs show red badge and one-click "Tentar Novamente" retry button
- Completed jobs show green badge and "Ver Video" link
- Expandable detail row shows task_id, creation date, error message, and video prompt
- Video status filter tabs (Todos/Gerando/Concluidos/Falhou) with counts
- Video section always visible (empty state when no videos)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add retry API function and progress type to api.ts + useVideoProgress hook** - `91365d9` (feat)
2. **Task 2: Redesign Video Jobs section with card grid, progress bars, retry, expandable details** - `c3492c5` (feat)

## Files Created/Modified
- `memelab/src/lib/api.ts` - Added retryVideo function, step_label to VideoProgressResponse
- `memelab/src/hooks/use-api.ts` - Updated useVideoList idle polling to 30s
- `memelab/src/app/(app)/jobs/page.tsx` - Full redesign: VideoJobCard, VideoProgressBar, card grid, filter tabs, retry handler

## Decisions Made
- Video section shown always (even when empty) with centered empty state message
- BRL cost displayed as `cost_usd * 5.5` (approximate USD-BRL conversion)
- VideoJobCard and VideoProgressBar as inline components in same file (not separate files)
- Idle polling updated from 10s to 30s per CONTEXT.md decision
- Video filter tabs use independent state from batch job filter tabs

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None - all data is wired to backend APIs from Plan 18-01.

## Issues Encountered
None

## User Setup Required
None - all changes are frontend-only, consuming existing backend endpoints.

## Next Phase Readiness
- Video jobs page fully functional with progress, retry, and filtering
- Backend stale detection + retry endpoint from Plan 18-01 consumed by frontend

## Self-Check: PASSED

All 3 modified files verified present. Both commit hashes (91365d9, c3492c5) found in git log.

---
*Phase: 18-job-status-sync-management*
*Completed: 2026-03-27*
