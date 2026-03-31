---
phase: "999.8"
plan: C
subsystem: reels-pipeline
tags: [video-sync, srt-alignment, duration-validation, ffmpeg]
dependency_graph:
  requires: [B-audio-subtitle-sync]
  provides: [video-sync-fix, srt-scene-alignment, duration-validation]
  affects: [reels-pipeline/video_builder, reels-pipeline/main]
tech_stack:
  added: []
  patterns: [proportional-duration-weighting, srt-scene-alignment, ffprobe-validation]
key_files:
  created: []
  modified:
    - src/reels_pipeline/video_builder.py
    - src/reels_pipeline/main.py
decisions:
  - "Proportional scene durations weighted by narracao character count with 3s minimum enforcement"
  - "SRT alignment uses midpoint overlap to map entries to scene windows, clamping within boundaries"
  - "Duration validation uses 2s tolerance by default (configurable)"
  - "xfade offsets rounded to 3 decimal places to avoid FFmpeg floating-point precision issues"
metrics:
  completed: "2026-03-30"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 2
---

# Phase 999.8 Plan C: Video Sync Fix Summary

Proportional scene duration computation from script narration text, SRT-to-scene alignment, xfade offset rounding, and ffprobe-based duration validation.

## Changes

### Task 1: video_builder.py

**New functions:**

1. `compute_scene_durations_from_script(script_json, total_audio_duration, n_scenes)` -- Distributes total audio duration across scenes proportionally to their `narracao` text length. Enforces `_MIN_SCENE_DURATION` (3s) by stealing time from longer scenes. Used by both `concat_clips_with_audio` and available for external callers.

2. `_align_srt_to_scenes(srt_path, scene_durations, script_json)` -- Parses SRT entries, computes expected time windows per scene from durations, maps each SRT entry to its scene by midpoint timestamp overlap, clamps entries within scene boundaries, writes `_aligned.srt` file.

3. `_validate_video_duration(output_path, expected_duration, tolerance=2.0)` -- Uses ffprobe to check actual video duration against expected. Returns dict with actual_duration, expected_duration, drift, and valid flag. Logs warning when drift exceeds tolerance.

**Modified functions:**

4. `concat_clips_with_audio()` -- Added `script_json` parameter. When provided, computes proportional scene durations and aligns SRT before subtitle burn. Rounded xfade offset values to 3 decimal places to prevent FFmpeg floating-point errors.

### Task 2: main.py

1. Updated `run_step_video_hailuo()` imports to include `_validate_video_duration`.
2. Passes `script_json=script` to `concat_clips_with_audio()` call.
3. After assembly: computes expected duration from cenas, calls `_validate_video_duration`, logs timing diagnostics (actual, expected, drift, valid).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] compute_scene_durations_from_script did not exist**
- **Found during:** Task 1
- **Issue:** Plan said Phase B already merged this function, but it was not present in the codebase
- **Fix:** Implemented the function as specified (proportional weighting by narracao char count, 3s min enforcement)
- **Files modified:** src/reels_pipeline/video_builder.py

**2. [Rule 3 - Blocking] _compute_scene_durations_from_srt referenced but not needed**
- **Found during:** Task 1
- **Issue:** Plan mentioned updating `_compute_scene_durations_from_srt` but this function did not exist and was not needed -- the SRT-based duration computation is handled by the new `compute_scene_durations_from_script` function
- **Fix:** Skipped this subtask as the functionality is covered by the implemented functions

**3. [Rule 3 - Blocking] run_step_video_kie not renamed yet**
- **Found during:** Task 2
- **Issue:** Plan said Phase D renamed `run_step_video_hailuo` to `run_step_video_kie`, but method is still `run_step_video_hailuo`
- **Fix:** Modified the existing `run_step_video_hailuo` method as-is (rename will happen in Phase D)

## Known Stubs

None -- all functions are fully implemented with real logic.

## Commits

Pending -- Bash permissions intermittently blocked during execution. Files are modified and ready to commit:
- `src/reels_pipeline/video_builder.py` -- 4 new functions + 1 modified function
- `src/reels_pipeline/main.py` -- import update + script_json passthrough + duration validation
