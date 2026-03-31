---
phase: D
plan: kie-model-retry
subsystem: reels-pipeline
tags: [kie-ai, model-selection, retry, per-scene-ui]
dependency_graph:
  requires: [999.6-02]
  provides: [video-model-selection, per-scene-retry, scene-grid-ui]
  affects: [reels-pipeline, reels-config, reels-api, frontend-reels]
tech_stack:
  added: []
  patterns: [per-scene-status-tracking, retry-with-prompt-simplification, on-scene-update-callback]
key_files:
  created:
    - src/database/migrations/versions/021_add_video_model_to_reels_config.py
  modified:
    - src/reels_pipeline/config.py
    - src/reels_pipeline/main.py
    - src/reels_pipeline/models.py
    - src/database/models.py
    - src/api/routes/reels.py
    - memelab/src/lib/api.ts
    - memelab/src/hooks/use-reels.ts
    - memelab/src/components/reels/step-video.tsx
    - memelab/src/app/(app)/reels/page.tsx
decisions:
  - "Migration 021 chains from 020 (not 021 as constraint specified — 021 did not exist)"
  - "run_step_video_hailuo kept as backward-compatible alias forwarding to run_step_video_kie"
  - "Retry logic: 3 attempts per scene (full prompt, simplified prompt, static fallback)"
  - "on_scene_update callback uses async fire-and-forget for real-time DB persistence"
metrics:
  tasks: 3
  files: 10
---

# Phase D: Kie.ai Model Selection + Retry Logic + Scene UI Summary

User-selectable Kie.ai video model with per-scene retry (3 attempts: full prompt, simplified, static fallback) and individual scene grid UI with inline retry.

## What Was Built

### Task 1: Backend -- Model registry + selection
- Added `REELS_AVAILABLE_MODELS` dict to `src/reels_pipeline/config.py` with 7 models (Hailuo, Wan, Kling, Seedance) including label, price_brl, durations, resolution
- Added `REELS_VIDEO_MODEL` env-backed default config constant
- Added `video_model` String(100) column to ReelsConfig in `src/database/models.py`
- Created migration 021 chaining from 020 (add video_model to reels_config)
- Added `GET /reels/config/models` endpoint returning the full model registry
- Renamed `run_step_video_hailuo` to `run_step_video_kie` (kept backward alias)
- `run_step_video_kie` reads model from `self.config.get("video_model")` with fallback to REELS_VIDEO_MODEL
- Added `video_model` field to ReelsConfigRequest/ReelsConfigResponse pydantic models
- Propagated video_model through all config_override loading paths (generate, execute_step, interactive)
- Interactive reel creation persists config.video_model in step_state["config"]

### Task 2: Backend -- Retry logic + per-scene tracking
- Rewrote `run_step_video_kie` with per-scene status tracking via `on_scene_update` callback
- Each scene tracked with: index, status, task_id, clip_path, img_path, prompt, duration, error
- 3-attempt retry per scene: attempt 1 (full prompt), attempt 2 (simplified to 500 chars), attempt 3 (static fallback)
- `_execute_step_task` video handler passes scene update callback that persists to DB via flag_modified
- Added `retry_single_scene` method to ReelsPipeline for single-scene retry with custom prompt
- Added `POST /reels/{job_id}/retry-scene/{scene_index}` endpoint with optional custom prompt
- Background task `_retry_scene_task`: retries single scene, auto-reassembles video when all scenes have clips

### Task 3: Frontend -- Model selector + per-scene retry UI
- Added `ReelsModelInfo`, `ReelsModels`, `SceneStatus` interfaces to api.ts
- Added `getReelsModels()` and `retryScene(jobId, sceneIndex, prompt?)` API functions
- Added `video_model` to ReelsConfig type and StepState.video.scenes array
- Added `useReelsModels` SWR hook
- ConfigPanel: model Select dropdown showing label + price/scene + resolution, with durations hint
- StepVideo: complete rewrite with per-scene grid showing thumbnails, status badges, error display
- Each SceneCard: 9:16 aspect ratio thumbnail, status overlay, editable prompt textarea, individual retry button
- Failed/static_fallback scenes show "Tentar Novamente" button with optional prompt editing
- Grid shows progress counter (X/Y cenas prontas)
- Final assembled video displayed below scene grid when available

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Migration chain target 021 did not exist**
- **Found during:** Task 1
- **Issue:** Constraint said "chain from 021 (use 022)" but latest migration was 020, no 021 existed
- **Fix:** Created migration 021 chaining from 020 instead
- **Files modified:** src/database/migrations/versions/021_add_video_model_to_reels_config.py

## Known Stubs

None -- all data sources are wired and functional.
