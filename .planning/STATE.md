---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: Pipeline Simplification, Auto-Publicacao & Multi-Tenant
status: Executing
stopped_at: Completed 15-01-PLAN.md
last_updated: "2026-03-26T19:42:00Z"
progress:
  total_phases: 9
  completed_phases: 5
  total_plans: 16
  completed_plans: 17
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-24)

**Core value:** Pipeline compoe e publica memes automaticamente — simples, rapido, sem depender de APIs caras de geracao de imagem
**Current focus:** Phase 15 — publishing-scheduling

## Current Position

Phase: 15
Plan: 02

## Performance Metrics

**Velocity:**

- Total plans completed: 0 (v2.0)
- Average duration: -
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**

- Last 5 plans: -
- Trend: -

*Updated after each plan completion*
| Phase 12 P01 | 9min | 2 tasks | 9 files |
| Phase 12 P02 | 8min | 2 tasks | 4 files |
| Phase 13 P01 | 3min | 2 tasks | 5 files |
| Phase 13 P02 | 3min | 2 tasks | 5 files |
| Quick 260325-qhl | 6min | 3 tasks | 7 files |
| Phase 999.1 P01 | 2min | 2 tasks | 6 files |
| Phase 999.1 P02 | 3min | 2 tasks | 3 files |
| Phase 999.1 P03 | 3min | 2 tasks | 4 files |
| Phase 12.1 P04 | 4min | 2 tasks | 2 files |
| Phase 12.1 P02 | 3min | 2 tasks | 3 files |
| Phase 12.1 P01 | 2min | 2 tasks | 9 files |
| Phase 12.1 P03 | 4min | 2 tasks | 3 files |
| Phase 14 P01 | 3min | 2 tasks | 4 files |
| Phase 14 P03 | 3min | 3 tasks | 5 files |
| Phase 14 P02 | 3min | 2 tasks | 3 files |
| Phase 15 P01 | 4min | 2 tasks | 4 files |

## Accumulated Context

### Roadmap Evolution

- Phase 12.1 inserted after Phase 12: Viral Content Engine — Trend Agents & Content Quality Overhaul (URGENT)

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [v2.0 Roadmap]: Split Instagram publishing into two phases (14: Connection/CDN, 15: Scheduling/Publishing) for cleaner delivery boundaries
- [v2.0 Roadmap]: Dashboard v2 (Phase 16) depends only on Phase 13 (tenant isolation), not on publishing — can be parallelized
- [v2.0 Roadmap]: Auth v2 (password reset, 2FA, OAuth) deferred to future milestone
- Pipeline nao chama Gemini Image API — apenas compoe backgrounds existentes + frases
- Agentes de trends desacoplados do pipeline (consulta avulsa)
- [Phase 12]: Hex color passed via background_path param — avoids new parameter, detected by startswith('#')
- [Phase 12]: Manual pipeline forces background_mode=static and use_gemini_image=False — zero Gemini Image calls guaranteed
- [Phase 12]: Optimistic UI updates for approve/reject — immediate feedback, revert on API error
- [Phase 13]: Fetch-then-check pattern for 403 vs 404 distinction in CharacterRepository
- [Phase 13]: PermissionError at repo level, HTTPException 403 at deps.py helper level
- [Phase 13]: Transitive ownership via Character join for all child-table repos (consistent pattern)
- [Phase 13]: ThemeRepository hybrid ownership: global themes public, user themes by user_id, character themes by Character.user_id
- [Quick 260325-qhl]: Tile-based token estimation: ceil(w/768)*ceil(h/768)*258 per input image
- [Quick 260325-qhl]: cost_usd accumulated via upsert per day/service/tier bucket in api_usage
- [Phase 999.1]: Migration 012 chains from 011 (sequential pattern); all video columns nullable; GCSUploader lazy client init
- [Phase 999.1]: Config fallback chain (param -> config module -> env var) for video_gen modules
- [Phase 999.1]: 17 motion templates for full theme coverage (15 core + cotidiano + descanso)
- [Phase 999.1]: Background video task uses get_session_factory() for independent DB sessions (request session unavailable in BackgroundTasks)
- [Phase 999.1]: Budget enforcement: pre-check estimated cost before generation, track actual cost after completion via kie_video service
- [Phase 12.1]: Delete HN/Lemmy agents entirely rather than disable — dead code removal
- [Phase 12.1]: Agents own their curated data sources (DEFAULT_SUBREDDITS/DEFAULT_FEEDS) instead of config.py overrides
- [Phase 12.1]: Regex-based traffic parsing with K/M/B suffix support replaces brittle char-by-char iteration
- [Phase 12.1]: Exponential decay e^(-age/24) for temporal freshness; multi-source boost min(1+0.2*(n-1), 2.0)
- [Phase 12.1]: Language detection via PT markers + English-only words instead of per-word dictionary -- handles accent-less informal BR text
- [Phase 12.1]: Coherence check uses _OBVIOUS_MATCHES shortcut for 13 themes to avoid unnecessary LLM calls
- [Phase 12.1]: LLM theme mapping uses generate() with tier=lite for cheap Gemini flash-lite calls (~$0.001/mapping)
- [Phase 12.1]: KEYWORD_MAP preserved as offline/error fallback; LLM -> KEYWORD_MAP -> random graceful degradation
- [Phase 12.1]: meme_potential filter >= 3 threshold with safety fallback to keep all if everything filtered
- [Phase 14]: Fernet symmetric encryption for Instagram OAuth tokens at rest (cryptography.fernet)
- [Phase 14]: Ephemeral Fernet key fallback with warning when INSTAGRAM_TOKEN_ENCRYPTION_KEY not set
- [Phase 14]: OAuth popup flow with postMessage relay for seamless UX (no full-page redirect)
- [Phase 14]: Ownership verification via character.user_id chain for upload-media endpoint
- [Phase 14]: GCS bucket meme-lab-bucket for Instagram media (per D-01), token refresh every 12h with misfire grace
- [Phase 15]: Lazy imports inside _publish_instagram to avoid circular imports and heavy startup cost
- [Phase 15]: GCS bucket name hardcoded as meme-lab-bucket in publisher (same as video_gen)
- [Phase 15]: Exponential backoff: retry_count * 120 seconds delay between retries
- [Phase 15]: getattr safe access for content_package/character relationships in serializers

### Pending Todos

None.

### Blockers/Concerns

- Facebook App Review for `instagram_content_publish` takes 2-6 weeks — must start early (during Phase 13)
- Cloudflare R2 CDN setup required before Phase 14 testing
- `api_usage.date` column DateTime vs Date ambiguity — resolve during Phase 16 planning

## Session Continuity

Last session: 2026-03-26T19:42:00Z
Stopped at: Completed 15-01-PLAN.md
Resume file: None
