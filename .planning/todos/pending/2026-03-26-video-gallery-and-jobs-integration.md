---
title: Video Gallery & Jobs Integration
area: ui
priority: high
created: 2026-03-26
status: pending
---

## Problem

Generated videos have no dedicated page to view/play them. Video generation jobs don't appear in the /jobs page — the user has no visibility into video task progress outside the inline dialog polling.

## Solution

Two deliverables:

### 1. Video Gallery Page (`/videos` or section in `/gallery`)
- Grid of generated videos with thumbnail preview
- Inline video player (click to play)
- Metadata display: duration, cost, model, generation time, prompt used
- Download button (with watermark)
- Filter by status (generating/success/failed)
- Link to source content package

### 2. Video Jobs in `/jobs` Page
- Video generation tasks appear alongside image batch jobs
- Real-time status polling (generating → success/failed)
- Show: content package phrase, duration, estimated cost, elapsed time
- Progress indicator during generation
- Link to view generated video on completion

## Files
- `memelab/src/app/(app)/gallery/page.tsx` — add video section or new page
- `memelab/src/app/(app)/jobs/page.tsx` — integrate video jobs
- `memelab/src/lib/api.ts` — video status/list endpoints
- `memelab/src/hooks/use-api.ts` — video polling hooks
- `src/api/routes/video.py` — may need list endpoint for generated videos
- `src/api/routes/jobs.py` — may need video job listing
