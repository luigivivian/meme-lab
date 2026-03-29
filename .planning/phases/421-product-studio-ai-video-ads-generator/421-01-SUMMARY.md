---
phase: 421-product-studio-ai-video-ads-generator
plan: 01
subsystem: database, api
tags: [pydantic, sqlalchemy, alembic, rembg, product-studio]

requires: []
provides:
  - ProductAdJob SQLAlchemy model and migration 020
  - ADS_* config constants with env var fallback
  - Pydantic models for wizard request/response/analysis/copy/cost
  - rembg[cpu] dependency for background removal
affects: [421-02, 421-03, 421-04, 421-05, 421-06, 421-07]

tech-stack:
  added: [rembg]
  patterns: [env-var-config-fallback, pydantic-request-response, sqlalchemy-mapped-column]

key-files:
  created:
    - src/product_studio/__init__.py
    - src/product_studio/config.py
    - src/product_studio/models.py
    - src/database/migrations/versions/020_product_ad_jobs.py
  modified:
    - src/database/models.py
    - requirements.txt

key-decisions:
  - "Migration 020 chains from 018 (latest numbered migration, skipping unnumbered ee583b64523f)"
  - "Float for cost columns (matching ReelsJob pattern) instead of Decimal"
  - "Config follows reels_pipeline/config.py pattern exactly (env var with defaults)"

patterns-established:
  - "Product Studio config: ADS_* prefix for all env vars"
  - "Style-keyed dicts (STYLE_SCENE_COUNT, STYLE_AUDIO_DEFAULTS, etc.) for style-specific behavior"

requirements-completed: [ADS-01, ADS-02]

duration: 3min
completed: 2026-03-29
---

# Phase 421 Plan 01: Product Studio Foundation Summary

**ProductAdJob table, ADS_* config constants, Pydantic wizard models, and rembg dependency for product ad video pipeline**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-29T21:13:13Z
- **Completed:** 2026-03-29T21:16:30Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Config module with 15+ constants covering styles, music, text layouts, negative prompts, and pipeline step order
- 6 Pydantic models covering full wizard lifecycle (request, response, analysis, copy, cost estimate, step state)
- ProductAdJob SQLAlchemy model with 24 columns and migration 020
- rembg[cpu] installed and importable for background removal

## Task Commits

Each task was committed atomically:

1. **Task 1: Install rembg, create config.py and models.py** - `af4fb2e` (feat)
2. **Task 2: DB migration and SQLAlchemy model for product_ad_jobs** - `afb7746` (feat)

## Files Created/Modified
- `src/product_studio/__init__.py` - Package init
- `src/product_studio/config.py` - ADS_* constants, MUSIC_MAP, NEGATIVE_PROMPTS, TEXT_LAYOUTS, style mappings
- `src/product_studio/models.py` - AdCreateRequest, AdJobResponse, AdStepStateResponse, AdAnalysisResult, AdCopyResult, AdCostEstimate
- `src/database/migrations/versions/020_product_ad_jobs.py` - product_ad_jobs table creation
- `src/database/models.py` - ProductAdJob SQLAlchemy model added
- `requirements.txt` - rembg[cpu] added

## Decisions Made
- Migration 020 chains from 018 (latest numbered migration) — unnumbered ee583b64523f branches from 001 and is unrelated
- Float for cost columns (matching ReelsJob pattern) rather than Decimal
- Config module follows reels_pipeline/config.py pattern exactly for consistency

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- ProductAdJob model ready for repository and route implementation (Plan 02)
- Config constants ready for pipeline steps (Plans 03-05)
- Pydantic models ready for API endpoints (Plan 02)

## Self-Check: PASSED

All 4 created files verified on disk. Both commit hashes (af4fb2e, afb7746) found in git log.

---
*Phase: 421-product-studio-ai-video-ads-generator*
*Completed: 2026-03-29*
