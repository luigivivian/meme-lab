---
phase: 421-product-studio-ai-video-ads-generator
plan: 03
subsystem: api, video
tags: [kie-ai, suno, ffmpeg, audio-mixing, blur-pad, product-studio]

requires:
  - phase: 421-01
    provides: ADS_* config constants, MUSIC_MAP, TEXT_LAYOUTS, ADS_EXPORT_FORMATS
provides:
  - KieMusicClient for Suno music generation via Kie.ai
  - FFmpeg format exporter with overlay_text, mix_audio, export_blur_pad, export_all_formats
affects: [421-04, 421-05, 421-06, 421-07]

tech-stack:
  added: []
  patterns: [kie-ai-suno-music-client, ffmpeg-blur-pad-export, tempfile-drawtext, amix-audio-mixing]

key-files:
  created:
    - src/product_studio/music_client.py
    - src/product_studio/format_exporter.py
  modified: []

key-decisions:
  - "KieMusicClient uses same Bearer token auth and BASE_URL as KieSora2Client (no shared base class)"
  - "Text overlay writes to tempfiles before FFmpeg drawtext (per Phase 999.2 escaping pattern)"
  - "mix_audio returns None for mute mode (caller handles no-audio case)"

patterns-established:
  - "Kie.ai Suno client: create_music_task -> poll_music_status -> download_music flow"
  - "FFmpeg blur pad: split[orig][copy] + gblur=sigma=20 + overlay centered"
  - "Audio mixing: amix weights=1 0.2 for narrated mode (TTS 100%, music 20%)"

requirements-completed: [ADS-07, ADS-08, ADS-09]

duration: 2min
completed: 2026-03-29
---

# Phase 421 Plan 03: Audio and Export Modules Summary

**KieMusicClient for Suno music via Kie.ai, FFmpeg format exporter with blur pad, text overlay (drawtext+tempfile), and 4-mode audio mixing**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-29T21:19:49Z
- **Completed:** 2026-03-29T21:21:36Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- KieMusicClient with async create/poll/download flow matching KieSora2Client auth pattern
- FFmpeg format exporter with 4 functions: overlay_text, mix_audio, export_blur_pad, export_all_formats
- Audio mixing handles 4 modes (mute/music/narrated/ambient) with proper amix weights
- Multi-format export produces 9:16, 16:9, 1:1 variants with blur-padded backgrounds

## Task Commits

Each task was committed atomically:

1. **Task 1: Kie.ai Suno music client** - `a51f706` (feat)
2. **Task 2: FFmpeg format exporter** - `b309cdd` (feat)

## Files Created/Modified
- `src/product_studio/music_client.py` - KieMusicClient with create_music_task, poll_music_status, download_music, generate_and_download
- `src/product_studio/format_exporter.py` - overlay_text (drawtext+tempfile), mix_audio (4 modes), export_blur_pad (split+gblur), export_all_formats (3 ratios)

## Decisions Made
- KieMusicClient uses same Bearer token auth and BASE_URL as KieSora2Client — separate class per anti-pattern guidance (no shared base)
- Text overlay writes to tempfiles before passing to FFmpeg drawtext — avoids shell escaping issues per Phase 999.2 pattern
- mix_audio returns None for mute mode so the caller can skip audio attachment entirely

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- KieMusicClient ready for pipeline audio step (Plan 05)
- format_exporter ready for assembly and export steps (Plan 05)
- All functions importable and verified

---
*Phase: 421-product-studio-ai-video-ads-generator*
*Completed: 2026-03-29*

## Self-Check: PASSED

All 2 created files verified on disk. Both commit hashes (a51f706, b309cdd) found in git log.
