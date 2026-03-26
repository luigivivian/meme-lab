---
phase: 14-instagram-connection-cdn
plan: 02
subsystem: api
tags: [instagram, oauth, fastapi, gcs, scheduler, cdn]
dependency_graph:
  requires:
    - phase: 14-01
      provides: InstagramOAuthService, InstagramConnection model, config constants
  provides:
    - 5 Instagram API endpoints under /instagram/* prefix
    - Token refresh background job in scheduler (every 12h)
    - Media upload to GCS (meme-lab-bucket) with signed URLs
  affects: [14-03, frontend-instagram-settings]
tech_stack:
  added: []
  patterns: [lazy-import-in-endpoints, GCSUploader-reuse-for-instagram, scheduler-multi-job]
key_files:
  created:
    - src/api/routes/instagram.py
  modified:
    - src/api/app.py
    - src/services/scheduler_worker.py
key_decisions:
  - "Ownership verification via character.user_id chain for upload-media endpoint"
  - "GCS bucket 'meme-lab-bucket' for Instagram media (per D-01), not default clipflow-video-uploads"
  - "Token refresh every 12h with misfire_grace_time=3600 for resilience"
patterns-established:
  - "Instagram route pattern: service instantiated per-request with session injection"
  - "Scheduler multi-job: publishing (60s) + token refresh (12h) coexist in same scheduler"
requirements-completed: [PUB-01, PUB-02, PUB-07]
duration: 3min
completed: "2026-03-26T19:19:55Z"
---

# Phase 14 Plan 02: Instagram API Routes & Token Refresh Summary

**5 Instagram API endpoints (auth-url, callback, status, disconnect, upload-media) wired to FastAPI with GCS media upload and 12h token refresh scheduler job**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-26T19:16:52Z
- **Completed:** 2026-03-26T19:19:55Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- 5 Instagram API endpoints operational at /instagram/* prefix with full auth protection
- Media upload to GCS (meme-lab-bucket) with signed URLs for Instagram Graph API consumption
- Automatic token refresh every 12 hours via APScheduler (tokens expiring within 7 days)

## Task Commits

Each task was committed atomically:

1. **Task 1: Instagram API route module with 5 endpoints** - `7280528` (feat)
2. **Task 2: Token refresh background job in scheduler** - `373a44e` (feat)

## Files Created/Modified
- `src/api/routes/instagram.py` - 5 Instagram API endpoints (auth-url, callback, status, disconnect, upload-media) with Pydantic UploadMediaRequest model
- `src/api/app.py` - Instagram router registration after video router
- `src/services/scheduler_worker.py` - Added _refresh_instagram_tokens job (12h interval) alongside existing publishing job

## Decisions Made
- Ownership verification for upload-media: traverses content_package -> character -> user_id chain, with fallback through pipeline_run
- Used "meme-lab-bucket" for Instagram media per D-01 (distinct from default clipflow-video-uploads)
- Token refresh runs every 12 hours with misfire_grace_time=3600 to handle missed runs
- State param in callback is optional (frontend validates CSRF client-side per plan spec)

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None. All endpoints are fully implemented with real service calls. Requires valid Facebook OAuth credentials and GCS credentials at runtime.

## Issues Encountered
None.

## User Setup Required

None beyond what Plan 01 already requires (FACEBOOK_APP_ID, FACEBOOK_APP_SECRET, INSTAGRAM_TOKEN_ENCRYPTION_KEY env vars).

## Next Phase Readiness
- All 5 API endpoints ready for frontend integration (Plan 03: Settings UI)
- Token refresh scheduler active alongside publishing scheduler
- GCS upload path organized as instagram-media/{content_package_id}/{filename}

## Self-Check: PASSED

All files exist. All commits verified.

---
*Phase: 14-instagram-connection-cdn*
*Completed: 2026-03-26*
