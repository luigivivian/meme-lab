---
phase: 18-job-status-sync-management
plan: 01
subsystem: api
tags: [fastapi, asyncio, kie-ai, video, background-task, retry]

# Dependency graph
requires:
  - phase: 999.1-video-generation-kie-sora2
    provides: "KieSora2Client, video routes, ContentPackage video columns"
provides:
  - "Stale job scanner (15-min threshold, 5-min interval)"
  - "POST /generate/video/retry/{id} endpoint"
  - "GET /generate/video/progress/{id} with step labels"
  - "Transient error retry logic in kie_client (max 2, exponential backoff)"
affects: [18-job-status-sync-management, frontend-jobs-page]

# Tech tracking
tech-stack:
  added: []
  patterns: ["asyncio background task for periodic scanning", "retry loop with exponential backoff for transient HTTP errors"]

key-files:
  created:
    - src/video_gen/stale_job_scanner.py
  modified:
    - src/api/routes/video.py
    - src/api/models.py
    - src/api/app.py
    - src/video_gen/kie_client.py

key-decisions:
  - "Stale scanner checks Kie.ai task status before marking as failed (avoids false positives)"
  - "Retry endpoint resets video_metadata and video_task_id on retry (clean slate)"
  - "Progress endpoint queries Kie.ai live for generating jobs, returns from DB for terminal states"

patterns-established:
  - "asyncio.Task background scanner: start/stop functions with module-level _scanner_task"
  - "STEP_LABELS dict for Kie.ai state to Portuguese UI label mapping"

requirements-completed: [JOB-01, JOB-02]

# Metrics
duration: 3min
completed: 2026-03-27
---

# Phase 18 Plan 01: Job Status Sync & Management Summary

**Stale job scanner with 15-min auto-fail, retry endpoint for failed video jobs, progress API with step labels, and kie_client transient retry logic**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-27T15:28:36Z
- **Completed:** 2026-03-27T15:32:07Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Created stale job scanner that auto-detects stuck video jobs (generating >15min) and marks them as failed, with smart Kie.ai status check before marking
- Added retry endpoint (POST /generate/video/retry/{id}) that resubmits failed jobs with same parameters
- Added progress endpoint (GET /generate/video/progress/{id}) with Portuguese step labels (Na fila, Gerando, Concluido, Falhou)
- Wired scanner to FastAPI lifespan (starts on boot, stops on shutdown)
- Added transient error retry (429, 5xx, timeouts) with exponential backoff to kie_client.create_task

## Task Commits

Each task was committed atomically:

1. **Task 1: Create stale job scanner + retry endpoint + progress response** - `9787980` (feat)
2. **Task 2: Wire scanner to app lifespan + add retry logic to kie_client** - `dd6b12d` (feat)

## Files Created/Modified
- `src/video_gen/stale_job_scanner.py` - New module: stale job detection with asyncio background task
- `src/api/routes/video.py` - Added retry endpoint, progress endpoint, STEP_LABELS mapping
- `src/api/models.py` - Added VideoProgressDetailResponse model
- `src/api/app.py` - Wired stale scanner start/stop in lifespan
- `src/video_gen/kie_client.py` - Added _MAX_TRANSIENT_RETRIES=2 retry loop in create_task

## Decisions Made
- Stale scanner checks Kie.ai task status before marking as failed -- prevents false positives when Kie.ai is just slow
- Retry endpoint extracts duration/model from previous video_metadata, reuses same prompt via video_prompt_used
- Progress endpoint returns "Enviando..." for jobs with no task_id yet (submission in progress)
- Scanner runs as asyncio.Task (not APScheduler) for simplicity and to avoid adding a dependency

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Created progress endpoint from scratch**
- **Found during:** Task 1 (progress enhancement)
- **Issue:** Plan said "enhance progress endpoint" but no progress endpoint existed -- only status endpoint returned basic info
- **Fix:** Created full GET /generate/video/progress/{id} endpoint with Kie.ai live querying and step label mapping
- **Files modified:** src/api/routes/video.py
- **Verification:** Endpoint in code, VideoProgressDetailResponse importable
- **Committed in:** 9787980 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 missing critical)
**Impact on plan:** Progress endpoint was needed for the step labels feature. Created as new endpoint rather than modifying existing status endpoint. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Backend stale detection and retry ready for Phase 18-02 frontend integration
- STEP_LABELS mapping available for jobs page UI step label display
- Progress endpoint ready for frontend polling

## Self-Check: PASSED

All 5 created/modified files verified present. Both commit hashes (9787980, dd6b12d) found in git log.

---
*Phase: 18-job-status-sync-management*
*Completed: 2026-03-27*
