---
phase: 421-product-studio-ai-video-ads-generator
plan: 04
subsystem: pipeline
tags: [orchestrator, kie-ai, gcs-upload, ffmpeg, suno, gemini-vision, cost-estimation]

requires:
  - phase: 421-02
    provides: bg_remover, scene_composer, prompt_builder, copy_generator modules
  - phase: 421-03
    provides: KieMusicClient, format_exporter modules
provides:
  - ProductAdPipeline class with 8 run_step_* methods for full ad video generation
  - estimate_cost method for pre-generation BRL cost breakdown
affects: [421-05, 421-06, 421-07]

tech-stack:
  added: []
  patterns: [8-step-pipeline-orchestrator, gcs-upload-before-kie-video, lazy-import-per-step, explicit-io-no-hidden-state]

key-files:
  created:
    - src/product_studio/pipeline.py
  modified: []

key-decisions:
  - "GCS upload_image before every Kie.ai create_task call (Kie.ai requires public URL, not local path)"
  - "Single-shot vs multi-scene decided by STYLE_SCENE_COUNT config (cinematic=1, narrated=4, lifestyle=5)"
  - "Audio step returns dict with music_path/tts_path/mixed_path for flexible downstream assembly"
  - "Assembly step chains overlay_text -> audio attach -> subtitle burn as sequential FFmpeg passes"

patterns-established:
  - "ProductAdPipeline follows ReelsPipeline pattern: constructor with config dict, per-step async methods"
  - "Each step uses lazy imports inside method body to avoid loading heavy deps at module level"
  - "estimate_cost uses $0.0175/s * ADS_USD_TO_BRL for video, fixed rates for audio/image"

requirements-completed: [ADS-10, ADS-11]

duration: 2min
completed: 2026-03-29
---

# Phase 421 Plan 04: Pipeline Orchestrator Summary

**ProductAdPipeline with 8 step methods chaining all modules -- GCS upload for video gen, Suno music, FFmpeg assembly, and BRL cost estimation before generation**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-29T21:24:45Z
- **Completed:** 2026-03-29T21:26:30Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- ProductAdPipeline class with 8 run_step_* methods matching D-21 step order
- run_step_video uploads scene image to GCS for public URL before Kie.ai create_task
- run_step_video handles single-shot (cinematic, 1 clip) and multi-scene (narrated/lifestyle, N clips)
- run_step_audio generates Suno music via KieMusicClient + optional TTS, mixes via format_exporter
- run_step_assembly chains text overlay + audio attachment + subtitle burning as sequential FFmpeg passes
- estimate_cost returns {video_brl, audio_brl, image_brl, total_brl} for pre-generation cost display

## Task Commits

Each task was committed atomically:

1. **Task 1: ProductAdPipeline orchestrator with 8 step methods** - `7789687` (feat)

## Files Created/Modified

- `src/product_studio/pipeline.py` - 8-step pipeline orchestrator with estimate_cost, lazy imports, explicit I/O

## Decisions Made

- GCS upload_image before every Kie.ai create_task call (Kie.ai requires public URL)
- Single-shot vs multi-scene decided by STYLE_SCENE_COUNT config
- Audio step returns dict with all audio paths for flexible downstream assembly
- Assembly chains overlay_text -> audio attach -> subtitle burn sequentially

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## Self-Check: PASSED

All 1 created file verified on disk. Commit hash 7789687 found in git log.
