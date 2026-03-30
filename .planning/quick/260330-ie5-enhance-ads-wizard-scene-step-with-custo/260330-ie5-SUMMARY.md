---
phase: quick-260330-ie5
plan: 01
subsystem: ads-wizard
tags: [presets, niche-filtering, editable-analysis, ads-pipeline]
dependency_graph:
  requires: []
  provides: [niche-filtered-presets, editable-analysis-fields]
  affects: [step-scene, step-prompt, step-analysis, ad-job-page]
tech_stack:
  added: []
  patterns: [niche-organized-presets, getPresetsForNiche-helper, editable-list-pattern]
key_files:
  created:
    - memelab/src/components/ads/ad-presets.ts
  modified:
    - memelab/src/components/ads/step-scene.tsx
    - memelab/src/components/ads/step-prompt.tsx
    - memelab/src/components/ads/step-analysis.tsx
    - memelab/src/app/(app)/ads/[jobId]/page.tsx
decisions:
  - "Preset data organized by niche key matching wizard NICHES values (food, beauty, tech, moda, fitness, outros)"
  - "getPresetsForNiche falls back to 'outros' for unknown or empty niche"
  - "Analysis niche/tone/audience remain read-only in step-analysis (already editable in wizard)"
  - "Niche extracted from analysis step result only when status is approved/completed"
metrics:
  duration: 3min
  completed: "2026-03-30T16:22:00Z"
  tasks: 2
  files: 5
---

# Quick Plan 260330-ie5: Enhance Ads Wizard Scene Step with Custom Presets

Niche-organized presets for backgrounds, cameras, lighting, scene lights with fallback to full lists, plus editable product_description and scene_suggestions in the analysis step.

## Task Summary

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create niche-organized preset data and update step-scene + step-prompt | df96c8d | ad-presets.ts (new), step-scene.tsx, step-prompt.tsx |
| 2 | Make analysis step editable and wire niche prop through stepper | de09d2f | step-analysis.tsx, [jobId]/page.tsx |

## What Changed

### ad-presets.ts (new)
Single source of truth for all preset data. Exports:
- `NICHE_BACKGROUNDS` — 6 niches x 5-8 curated background options + custom entry
- `NICHE_SCENE_LIGHTS` — 6 niches x 4-6 lighting options
- `NICHE_CAMERAS` — 6 niches x 5-8 camera move options
- `NICHE_LIGHTINGS` — 6 niches x 4-8 lighting setup options
- `COMPOSITIONS` — 7 shared composition presets
- `MOODS` — 8 shared mood presets
- `getPresetsForNiche(presetMap, niche)` — returns niche-specific presets, falls back to `outros`

### step-scene.tsx
- Added `niche` prop (optional, defaults to "")
- Shows niche-filtered background and scene light Select components before image is generated
- Custom background option triggers Input field for description
- Composition Select added

### step-prompt.tsx
- Added `niche` prop (optional, defaults to "")
- Shows niche-filtered camera and lighting Select components before prompt is generated
- Mood Select added from shared presets

### step-analysis.tsx
- `product_description`: now renders as editable Textarea instead of read-only div
- `scene_suggestions`: renders as editable Input list with remove (X) and add (+) buttons
- `niche`, `tone`, `audience` remain read-only display
- New `onUpdate` prop fires edited values when user clicks "Confirmar Analise"
- Approved state uses ReadOnlyFields component (same display as before)

### [jobId]/page.tsx
- Extracts `niche` from analysis step result (only when approved/completed)
- Passes `niche` prop to StepScene and StepPrompt components
- Empty string fallback when analysis not yet done (components show full preset lists)

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None - all data sources are wired.

## Verification

- TypeScript compiles with zero errors in all modified files
- Pre-existing errors in wizard.tsx and api.ts (duplicate declarations) are out of scope

## Self-Check: PASSED
