# Phase 15: Publishing & Scheduling - Context

**Gathered:** 2026-03-26
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous --auto)

<domain>
## Phase Boundary

Enable users to schedule approved content packages for auto-publishing to Instagram at specific times. Manage the publishing queue with status tracking (queued/publishing/published/failed), provide a calendar view of scheduled posts, and auto-publish via the Instagram Graph API using OAuth tokens from Phase 14.

</domain>

<decisions>
## Implementation Decisions

### Publishing Flow
- **D-01:** User selects approved content package → chooses date/time → schedules for publishing. Backend creates ScheduledPost record.
- **D-02:** Background scheduler (APScheduler, already exists) checks for posts due every 60 seconds and publishes them via Instagram Graph API.
- **D-03:** Publishing pipeline: upload image to GCS → create media container via Instagram API → wait for container ready → publish → update status.

### Database
- **D-04:** Use existing `scheduled_posts` table (migration 004 already exists with status, scheduled_at, published_at, retry_count, error_message fields).
- **D-05:** Statuses: queued → publishing → published | failed. Failed posts can be retried (max 3 retries).

### API Endpoints (already partially exist from earlier work)
- **D-06:** Extend existing publishing routes at `/publishing/` with full Instagram Graph API integration.
- **D-07:** `POST /publishing/schedule` — schedule a content package
- **D-08:** `GET /publishing/queue` — list scheduled posts with filters
- **D-09:** `GET /publishing/calendar` — calendar view grouped by date
- **D-10:** `POST /publishing/queue/{id}/cancel` — cancel queued post
- **D-11:** `POST /publishing/queue/{id}/retry` — retry failed post
- **D-12:** `GET /publishing/best-times` — suggested best posting times

### Frontend
- **D-13:** Publishing page already exists at `/publishing` — extend with real Instagram publishing, not just queue management.
- **D-14:** Calendar view showing scheduled, published, and failed posts by date.
- **D-15:** Quick schedule from gallery: "Agendar" button on approved content packages.

### Instagram Graph API
- **D-16:** Use InstagramOAuthService from Phase 14 for token management.
- **D-17:** Media publishing flow: POST /me/media (create container) → GET /media/{id} (poll for ready) → POST /me/media_publish (publish).
- **D-18:** Support both image (single) and carousel (multi-image) publishing.

### Claude's Discretion
- Retry backoff strategy for failed publishes
- Calendar date range defaults
- Best times algorithm (static defaults per day of week)
- Error message formatting for failed posts

</decisions>

<canonical_refs>
## Canonical References

### Instagram Publishing
- `src/services/instagram_client.py` — existing publish methods (extend)
- `src/services/instagram_oauth.py` — OAuth service from Phase 14
- `src/services/scheduler_worker.py` — APScheduler job runner
- `src/services/publisher.py` — existing publisher service

### Database
- `src/database/migrations/versions/004_add_scheduled_posts.py` — existing migration
- `src/database/models.py` — ScheduledPost model

### Frontend
- `memelab/src/app/(app)/publishing/page.tsx` — existing publishing page
- `memelab/src/lib/api.ts` — existing publishing API functions

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ScheduledPost` model already exists with all needed fields
- Publishing API routes partially exist (schedule, queue, calendar, cancel, retry, best-times)
- Frontend publishing page has queue management UI
- `instagram_client.py` has publish_reel() and other methods
- APScheduler already running with 60s interval job

### Integration Points
- `scheduler_worker.py` — add Instagram publish job
- `instagram_oauth.py` — get valid token for publishing
- `GCSUploader` — upload image for public URL before publishing
- Publishing page — wire to real Instagram Graph API

</code_context>

<specifics>
## Specific Ideas

- Much of the infrastructure already exists — this phase wires it together with real Instagram API calls
- The scheduler_worker already processes posts on 60s interval — needs Instagram Graph API integration
- Frontend publishing page needs calendar view enhancement and real status updates

</specifics>

<deferred>
## Deferred Ideas

- Instagram Reels publishing (video) — separate from image posts
- Instagram Stories publishing
- Analytics/insights for published posts
- A/B testing of posting times

</deferred>

---

*Phase: 15-publishing-scheduling*
*Context gathered: 2026-03-26 via autonomous mode*
