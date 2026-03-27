---
plan: 13-03
phase: 13-tenant-isolation
status: complete
started: 2026-03-25
completed: 2026-03-25
executor: claude-sonnet-4-6
---

## What Was Built

Wired tenant filtering into all 9 API route handlers. Every authenticated route now passes `current_user` to repository methods, catches `PermissionError` as 403, and uses `get_user_character` for character-scoped operations.

## Key Changes

### characters.py
- Imported `get_user_character` from deps
- Updated `_get_char_with_counts` helper to accept and use `current_user`
- All slug-based routes use `get_user_character(slug, current_user, session)` instead of direct repo calls
- `list_all` passes `user=current_user`
- Character creation sets `user_id=current_user.id`
- `api_delete_character` validates ownership before soft-delete

### pipeline.py
- Imported `get_user_character`
- `list_runs`/`count_runs` pass `user=current_user`
- `pipeline_status` catches `PermissionError` → 403 on `get_by_run_id`
- approve/reject/unreject validate package ownership before mutating
- bulk_approve/bulk_reject validate all package IDs before bulk update
- Background upload/list use `get_user_character` for character validation

### content.py
- `list_packages`/`count` pass `user=current_user`
- `list_images`/`count` pass `user=current_user`
- All single-resource routes catch `PermissionError` → 403

### themes.py
- `list_effective` passes `user=current_user`
- Theme creation sets `user_id=current_user.id`
- Theme delete checks ownership before deleting

### jobs.py
- `list_jobs`/`count` pass `user=current_user`
- `get_by_job_id` catches `PermissionError` → 403

### publishing.py
- `list_posts`/`count` pass `user=current_user`
- `get_scheduled_post` catches `PermissionError` → 403
- Calendar `get_posts_by_date_range` passes `user=current_user`

### generation.py
- No changes needed — already had `current_user` on all routes for key selection

### agents.py
- No changes needed — already had `current_user` on all routes

### drive.py
- Added `current_user=Depends(get_current_user)` to `get_image` route (the one missing auth)

## Self-Check: PASSED

- [x] All 9 route files have `current_user` dependency
- [x] characters.py uses `get_user_character` for slug-based routes
- [x] characters.py list route passes `user=current_user`
- [x] characters.py creation sets `user_id=current_user.id`
- [x] pipeline.py list/status pass `user=current_user`
- [x] content.py list/single routes pass `user=current_user`
- [x] All single-resource routes catch `PermissionError` → 403
- [x] Background task functions use `user=None` (internal ops)
- [x] `python -m pytest tests/test_tenant.py` — 8/8 passed

## Commits

- `00427ad` feat(13-03): wire tenant filtering into characters, pipeline, content routes
- `69eedd5` feat(13-03): wire tenant filtering into themes, jobs, publishing, drive routes
