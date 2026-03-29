---
phase: 421-product-studio-ai-video-ads-generator
plan: 02
subsystem: ai, pipeline
tags: [rembg, gemini-image, gemini-text, scene-composition, prompt-generation]

requires: [421-01]
provides:
  - bg_remover module for rembg-based background removal
  - scene_composer module for Gemini Image scene composition and product analysis
  - prompt_builder module for style-aware cinematic video prompt generation
  - copy_generator module for Portuguese headline + CTA + hashtags
affects: [421-03, 421-04, 421-05]

tech-stack:
  added: []
  patterns: [asyncio-to-thread-gemini, negative-prompt-per-style, gemini-vision-analysis]

key-files:
  created:
    - src/product_studio/bg_remover.py
    - src/product_studio/scene_composer.py
    - src/product_studio/prompt_builder.py
    - src/product_studio/copy_generator.py
  modified: []

key-decisions:
  - "compose_scene uses gemini-2.5-flash-image (same model as reels image_gen) for scene composition"
  - "analyze_product uses gemini-2.5-flash (text model) for JSON-structured product analysis"
  - "prompt_builder appends negative prompt from config after LLM-generated motion prompt"
  - "copy_generator uses response_mime_type application/json for structured output"

patterns-established:
  - "Product Studio AI modules follow reels_pipeline pattern: asyncio.to_thread wrapping sync Gemini client"
  - "Style-specific instructions dict (_STYLE_INSTRUCTIONS) for per-style prompt customization"

requirements-completed: [ADS-03, ADS-04, ADS-05, ADS-06]

duration: 2min
completed: 2026-03-29
---

# Phase 421 Plan 02: Scene Generation Modules Summary

**Four AI modules for product ad pipeline: rembg background removal, Gemini scene composition with product preservation, style-aware cinematic prompt builder, and Portuguese copy generator**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-29T21:19:34Z
- **Completed:** 2026-03-29T21:21:10Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- bg_remover wraps rembg with configurable model (ADS_REMBG_MODEL) for zero-cost local background removal
- scene_composer places product cutout into AI-generated scenes via Gemini Image, with explicit "Keep the product IDENTICAL" prompt to prevent product distortion
- scene_composer includes analyze_product for wizard auto-defaults (niche, tone, audience, scene suggestions)
- prompt_builder generates style-aware cinematic prompts (cinematic/narrated/lifestyle) with negative prompt appended from config
- copy_generator produces Portuguese headline + CTA + 5-8 hashtags via Gemini with JSON response mode

## Task Commits

Each task was committed atomically:

1. **Task 1: Background remover and scene composer** - `1f8a37f` (feat)
2. **Task 2: Prompt builder and copy generator** - `265a619` (feat)

## Files Created/Modified

- `src/product_studio/bg_remover.py` - rembg wrapper with remove_background(input_path, output_path)
- `src/product_studio/scene_composer.py` - compose_scene (Gemini Image) + analyze_product (Gemini Vision)
- `src/product_studio/prompt_builder.py` - build_video_prompt with 3 style instruction sets + negative prompts
- `src/product_studio/copy_generator.py` - generate_copy returning {headline, cta, hashtags}

## Decisions Made

- compose_scene uses gemini-2.5-flash-image (matching reels image_gen pattern) for scene composition
- analyze_product uses gemini-2.5-flash (text model) for structured JSON analysis
- prompt_builder appends negative prompt from NEGATIVE_PROMPTS config after LLM-generated motion prompt
- copy_generator uses response_mime_type="application/json" for reliable structured output

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## Self-Check: PASSED

All 4 created files verified on disk. Both commit hashes (1f8a37f, 265a619) found in git log.

---
*Phase: 421-product-studio-ai-video-ads-generator*
*Completed: 2026-03-29*
