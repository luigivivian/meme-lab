---
phase: 15-publishing-scheduling
plan: "01"
subsystem: publishing
tags: [instagram, graph-api, scheduler, serializers, publishing]
dependency_graph:
  requires: [14-instagram-connection-cdn]
  provides: [real-instagram-publishing, content-summary-api, schedule-validation]
  affects: [scheduler-worker, publishing-routes, serializers]
tech_stack:
  added: []
  patterns: [lazy-import-in-publish-method, exponential-backoff-retry, selectinload-eager-loading]
key_files:
  created: []
  modified:
    - src/services/publisher.py
    - src/api/serializers.py
    - src/api/routes/publishing.py
    - src/database/repositories/schedule_repo.py
decisions:
  - "Lazy imports inside _publish_instagram to avoid circular imports and heavy startup cost"
  - "GCS bucket name hardcoded as meme-lab-bucket in publisher (same as video_gen)"
  - "Exponential backoff: retry_count * 120 seconds delay between retries"
  - "getattr safe access for content_package/character relationships in serializers"
metrics:
  duration: 4min
  completed: "2026-03-26"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 4
---

# Phase 15 Plan 01: Wire Instagram Publishing & Enrich Serializers Summary

Real Instagram Graph API publishing via scheduler with enriched content_summary API responses

## What Was Done

### Task 1: Wire real Instagram publishing into PublishingService
Replaced the placeholder `_publish_instagram()` method with a complete Instagram Graph API integration flow:
1. Resolves user_id from post's character (or content_package chain fallback)
2. Loads active InstagramConnection for that user from DB
3. Decrypts OAuth access token via InstagramOAuthService._decrypt_token
4. Uploads image to GCS (meme-lab-bucket) with `instagram-media/{pkg_id}/{filename}` path
5. Builds caption from package.caption (or phrase fallback) with hashtag appending
6. Publishes via InstagramClient.publish_image() or publish_carousel() based on carousel_slides
7. Returns result with instagram_media_id, permalink, and timestamp
8. Updated _mark_failed with exponential backoff (retry_count * 120s delay)

### Task 2: Enrich serializers and routes with content_summary data
- Added selectinload for content_package and character relationships in all schedule_repo query methods (list_posts, get_by_id, get_due_posts, get_posts_by_date_range)
- Enriched scheduled_post_to_dict with `content_summary` (phrase, topic, image_path, quality_score) and `character_name`
- Enriched scheduled_post_calendar_item with `content_summary`
- Added Instagram connection validation in schedule_post route -- rejects scheduling if no active connection

## Commits

| # | Hash | Message | Files |
|---|------|---------|-------|
| 1 | cad4f49 | feat(15-01): wire real Instagram publishing into PublishingService | src/services/publisher.py |
| 2 | 90207a3 | feat(15-01): enrich serializers and routes with content_summary data | src/api/serializers.py, src/api/routes/publishing.py, src/database/repositories/schedule_repo.py |

## Verification Results

| Check | Expected | Actual | Status |
|-------|----------|--------|--------|
| Import PublishingService + scheduled_post_to_dict | ok | ok | PASS |
| "placeholder" in publisher.py | 0 | 0 | PASS |
| "InstagramClient" in publisher.py | >= 1 | 4 | PASS |
| "content_summary" in serializers.py | >= 2 | 6 | PASS |
| "selectinload" in schedule_repo.py | >= 3 | 9 | PASS |

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None. All functionality is fully wired to real implementations (InstagramClient, GCSUploader, InstagramOAuthService).

## Decisions Made

1. **Lazy imports inside _publish_instagram**: All Instagram/GCS/model imports are done inside the method body to avoid circular imports and keep startup lightweight.
2. **GCS bucket hardcoded**: Using "meme-lab-bucket" consistent with video_gen module. Can be made configurable later.
3. **Exponential backoff formula**: `retry_count * 120` seconds gives 2min, 4min, 6min delays for retries 1-3.
4. **Safe relationship access**: Using `getattr(post, 'content_package', None)` in serializers to handle cases where relationship wasn't loaded.

## Self-Check: PASSED

- All 4 modified files exist on disk
- Commit cad4f49 found in git log
- Commit 90207a3 found in git log
