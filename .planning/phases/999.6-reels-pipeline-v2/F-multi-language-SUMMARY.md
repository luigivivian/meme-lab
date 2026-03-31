---
phase: "999.6"
plan: "F-multi-language"
subsystem: "reels-pipeline"
tags: [multi-language, i18n, reels, script-gen, tts, frontend]
dependency_graph:
  requires: [999.6-03]
  provides: [multi-language-reels]
  affects: [reels-pipeline, reels-frontend, database-schema]
tech_stack:
  added: []
  patterns: [language-specific-system-prompts, config-override-threading]
key_files:
  created:
    - src/database/migrations/versions/024_add_language_to_reels.py
  modified:
    - src/database/models.py
    - src/reels_pipeline/models.py
    - src/reels_pipeline/script_gen.py
    - src/api/routes/reels.py
    - memelab/src/lib/api.ts
    - memelab/src/app/(app)/reels/page.tsx
decisions:
  - "Language-specific system prompts for pt-BR, en-US, es-ES with English fallback for other languages"
  - "Language stored per-job on ReelsJob.language (not just in config) for persistence across interactive steps"
  - "TTS inherits language from script text (Gemini TTS auto-detects language from content)"
  - "legenda_overlay stays in English for image gen prompts even in non-English reels (via fallback template)"
metrics:
  completed_date: "2026-03-31"
  tasks: 3
  files: 7
---

# Phase 999.6 Plan F: Multi-Language Support Summary

Multi-language reels pipeline: language-specific script generation (pt-BR/en-US/es-ES), language threading through API and pipeline config, and frontend language selector.

## What Was Built

### 1. Database Schema (Migration 024)

Added `language` column to `reels_jobs` table:
- `VARCHAR(10)`, default `'pt-BR'`, nullable
- Persists language choice per job for interactive step-by-step execution
- Each pipeline step reads language from the job record

### 2. Backend Pipeline Language Threading

**script_gen.py** -- The core change. Replaced single hardcoded Portuguese system prompt with:
- `_SYSTEM_PROMPTS` dict: full native prompts for pt-BR, en-US, es-ES
- `_SYSTEM_PROMPT_FALLBACK`: English template with `{language}` instruction for any other language
- Language-specific `image_instruction` and `cena_instruction` strings
- `legenda_overlay` instructions remain visual-description-focused (English in fallback for image gen quality)

**API routes (reels.py):**
- `_execute_step_task`: injects `job.language` into `config_override["script_language"]` before running any pipeline step
- `generate_reel`: reads `req.language`, falls back to config's `script_language`, stores on job record
- `create_interactive_reel`: passes `req.language` to job creation

**Pydantic models:**
- `ReelGenerateRequest`: added `language: str = "pt-BR"`
- `ReelCreateInteractiveRequest`: added `language: str = "pt-BR"`

### 3. Frontend Language Selector

**reels/page.tsx:**
- New `language` state variable (default `"pt-BR"`)
- Language selector dropdown in the Ajustes (settings) panel: Portugues (BR) / English (US) / Espanol
- Language passed to both `generateReel()` and `createInteractiveReel()` requests

**api.ts:**
- `ReelGenerateRequest.language?: string`
- `InteractiveReelRequest.language?: string`

## How Language Flows Through the System

```
Frontend (language selector)
  -> POST /reels/generate { language: "en-US" }
  -> ReelsJob.language = "en-US" (DB)
  -> _execute_step_task reads job.language -> config_override["script_language"] = "en-US"
  -> script_gen.py: selects en-US system prompt template
  -> TTS: narrates English text (Gemini auto-detects)
  -> Transcriber: transcribes with language="en-US" hint
  -> SRT subtitles in English
```

## Deviations from Plan

None -- plan executed as designed. The plan file itself did not exist on disk (Phase F was specified in the prompt context without a PLAN.md file), so implementation was driven by the critical context constraints.

## Known Stubs

None. All language paths are fully wired end-to-end.

## Decisions Made

1. **Three native templates + fallback**: pt-BR, en-US, es-ES get fully localized system prompts. Any other language code uses an English fallback template that instructs Gemini to write in the target language.

2. **Job-level language persistence**: Stored on `ReelsJob.language` rather than only in config, because interactive reels execute steps across multiple API calls and the language must be consistent.

3. **TTS auto-detects language**: Gemini TTS speaks whatever language the input text is in. No explicit language parameter needed for TTS -- the script text carries the language.

4. **legenda_overlay guidance**: For non-Portuguese languages, the fallback template instructs to keep `legenda_overlay` in English since it feeds into image generation prompts (Gemini image gen performs best with English prompts).
