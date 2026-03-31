---
phase: E
plan: multi-platform
subsystem: reels-pipeline
tags: [multi-platform, metadata, gemini, captions, hashtags]
dependency_graph:
  requires: [999.6-reels-pipeline-v2]
  provides: [platform-metadata-api, platform-checkboxes-ui, platform-output-tabs]
  affects: [reels_jobs-table, reels-api, reels-frontend]
tech_stack:
  added: [platform_metadata.py]
  patterns: [gemini-json-response, per-platform-prompt-engineering, tab-based-ui]
key_files:
  created:
    - src/reels_pipeline/platform_metadata.py
    - src/database/migrations/versions/023_add_reels_platforms.py
  modified:
    - src/database/models.py
    - src/reels_pipeline/models.py
    - src/api/routes/reels.py
    - memelab/src/lib/api.ts
    - memelab/src/app/(app)/reels/page.tsx
    - memelab/src/components/reels/step-video.tsx
decisions:
  - "Platform metadata generated as separate module (not inside main.py or video_builder.py) per constraints"
  - "Gemini 2.5 Flash with JSON response_mime_type for structured platform metadata"
  - "Fallback metadata from script data when Gemini call fails (no hard failure)"
  - "Instagram always included and non-removable in platform checkboxes"
  - "Tab-based UI for platform outputs (not accordion) for quick switching"
metrics:
  completed: "2026-03-31"
  tasks: 2
  files: 8
---

# Phase E: Multi-Platform Output Summary

Same 9:16 video with adapted captions/hashtags/titles per platform (Instagram, YouTube Shorts, TikTok, Facebook) via Gemini-powered metadata generation.

## Task 1: Backend -- Platform metadata generation

Added `platforms` (JSON list) and `platform_outputs` (JSON dict) columns to ReelsJob via migration 023. Created `src/reels_pipeline/platform_metadata.py` with `generate_platform_metadata()` that uses Gemini 2.5 Flash to generate per-platform adapted metadata:

- **Instagram**: caption (max 2200 chars) + hashtags (max 30)
- **YouTube Shorts**: title (max 100 chars) + description (max 5000) + tags
- **TikTok**: caption with inline hashtags (max 2200, casual tone)
- **Facebook**: caption + hashtags (descriptive, engagement-focused)

Platform metadata auto-generates after the video step completes in `_execute_step_task`. Falls back to script-derived metadata on Gemini failure. Added `GET /reels/{job_id}/platforms` endpoint returning platform_outputs. Both `generate` and `interactive` create endpoints accept `platforms` list.

## Task 2: Frontend -- Platform checkboxes + output tabs

Added `platforms` field to `InteractiveReelRequest`, `ReelGenerateRequest`, and `ReelJob` types. Added `PlatformOutput` and `PlatformOutputsResponse` interfaces. Added `getPlatformOutputs()` API function.

GenerationForm now has platform checkboxes between tema textarea and Ajustes section. Instagram is always checked and disabled. YouTube Shorts, TikTok, Facebook are toggleable. Selected platforms flow through to create/generate requests.

StepVideo now fetches platform outputs after video completes and shows tabbed interface per platform. Each tab displays caption, title, description, hashtags/tags with copy-to-clipboard buttons. JobHistory cards show platform abbreviation badges (IG, YT, TT, FB) when multiple platforms selected.

## Deviations from Plan

None -- plan executed exactly as written.

## Known Stubs

None -- all data sources are wired to the Gemini API with fallback.

## Commits Pending

Git staging/commit operations were blocked by sandbox restrictions during execution. The following commits need to be created manually:

**Task 1 commit:**
```
git add src/database/models.py src/reels_pipeline/models.py src/api/routes/reels.py src/database/migrations/versions/023_add_reels_platforms.py src/reels_pipeline/platform_metadata.py
git commit -m "feat(E-multi-platform): backend platform metadata generation"
```

**Task 2 commit:**
```
git add memelab/src/lib/api.ts memelab/src/app/(app)/reels/page.tsx memelab/src/components/reels/step-video.tsx
git commit -m "feat(E-multi-platform): frontend platform checkboxes and output tabs"
```
