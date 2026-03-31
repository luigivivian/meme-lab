---
phase: "999.8"
plan: B
subsystem: reels-pipeline
tags: [video-builder, transitions, duration, ffmpeg, config-panel]
dependency_graph:
  requires: [999.6-reels-pipeline-v2]
  provides: [proportional-scene-duration, configurable-transitions, transitions-endpoint]
  affects: [video_builder.py, main.py, config.py, reels.py, reels-page.tsx]
tech_stack:
  added: []
  patterns: [proportional-duration-allocation, narration-weighted-scenes]
key_files:
  created: []
  modified:
    - src/reels_pipeline/config.py
    - src/reels_pipeline/video_builder.py
    - src/reels_pipeline/main.py
    - src/api/routes/reels.py
    - memelab/src/app/(app)/reels/page.tsx
decisions:
  - "Proportional duration weighted by narration char count with 3s minimum per scene"
  - "21 FFmpeg xfade transitions exposed via config endpoint and frontend Select"
  - "Removed image_duration slider from ConfigPanel (auto-calculated from narration)"
  - "transition_duration default 0.3s for Hailuo clips, 0.5s for segments"
metrics:
  duration: "5min"
  completed: "2026-03-31"
---

# Phase 999.8 Plan B: Auto-Duration + Configurable Transitions Summary

Proportional scene duration allocation weighted by narration length, 21 FFmpeg xfade transition types configurable via API and frontend panel.

## What Was Built

### Task 1: Backend -- Proportional duration + transition config

1. **`compute_scene_durations_from_script()`** in `video_builder.py`: New function that weights each scene by narration character count, allocates total audio duration proportionally, and enforces a 3s minimum per scene with deficit redistribution to longer scenes.

2. **`REELS_AVAILABLE_TRANSITIONS`** in `config.py`: List of 21 FFmpeg xfade transition types (fade, fadeblack, fadewhite, dissolve, wipeleft, wiperight, wipeup, wipedown, slideleft, slideright, slideup, slidedown, circlecrop, circleopen, circleclose, radial, smoothleft, smoothright, zoomin, pixelize, diagtl, diagtr).

3. **`concat_clips_with_audio()`** and **`concat_segments()`** in `video_builder.py`: Both functions now accept `transition_type` parameter instead of hardcoding `transition=fade` in the xfade filter.

4. **`run_step_video_hailuo()`** and **`run_step_video()`** in `main.py`: Now pass `transition_type` and `transition_duration` from `self.config` to builder functions instead of hardcoded values.

5. **`GET /reels/config/transitions`** endpoint in `reels.py`: Returns the available transitions list for the frontend config panel.

### Task 2: Frontend -- Config panel updates

1. **Removed `image_duration` slider** from ConfigPanel (duration is now auto-calculated from narration).

2. **Expanded transition Select**: From 2 options (fade/cut) to 22 FFmpeg xfade types with PT-BR labels (Fade, Fade Preto, Fade Branco, Dissolver, Limpar Esquerda/Direita/Cima/Baixo, Slide variants, Circulo variants, Radial, Suave variants, Zoom In, Pixelizar, Diagonal variants).

3. **Added `transition_duration` slider**: Range 0.1-1.0s, step 0.1, default 0.3s.

4. **Updated save payload**: Includes `transition_duration`, excludes `image_duration`. No type changes needed -- `ReelsConfig` interface already had both fields.

## Deviations from Plan

None -- plan executed exactly as written.

## Known Stubs

None -- all functionality is fully wired.

## Commits

Commits pending -- git write operations were permission-blocked during execution. All 5 files are staged and ready to commit.

Files modified:
- `src/reels_pipeline/config.py` (+10 lines)
- `src/reels_pipeline/video_builder.py` (+64 lines, -2 lines)
- `src/reels_pipeline/main.py` (+9 lines, -2 lines)
- `src/api/routes/reels.py` (+7 lines)
- `memelab/src/app/(app)/reels/page.tsx` (+52 lines, -17 lines)
