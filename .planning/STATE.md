---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: Pipeline Simplification, Auto-Publicacao & Multi-Tenant
status: Phase complete — ready for verification
stopped_at: Completed 999.3-02-PLAN.md
last_updated: "2026-03-27T01:44:04.630Z"
progress:
  total_phases: 9
  completed_phases: 8
  total_plans: 23
  completed_plans: 22
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-24)

**Core value:** Pipeline compoe e publica memes automaticamente — simples, rapido, sem depender de APIs caras de geracao de imagem
**Current focus:** Phase 999.3 — sora2-prompt-engineering-research

## Current Position

Phase: 999.3 (sora2-prompt-engineering-research) — EXECUTING
Plan: 2 of 2

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
| Phase 15 P01 | 4min | 2 tasks | 4 files |
| Phase 15 P02 | 4min | 2 tasks | 3 files |
| Phase 16 P02 | 4min | 2 tasks | 4 files |
| Phase 999.2 P01 | 6min | 2 tasks | 6 files |
| Phase 999.2 P02 | 5min | 3 tasks | 5 files |
| Phase 999.3 P01 | 4min | 1 tasks | 3 files |
| Phase 999.3 P02 | 4min | 1 tasks | 3 files |

## Accumulated Context

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
- [Phase 15]: InstagramStatus type includes token_expires_at for future expiry warnings
- [Phase 15]: useInstagramStatus refreshes every 60s with errorRetryCount 1 (non-critical)
- [Phase 15]: Month view uses colored dots (not full cards) for compact calendar cells
- [Phase 15]: Schedule dialog hard-blocks submit when Instagram not connected
- [Phase 16]: QuotaAlerts uses existing useUsage() data (no new endpoint/DB tables needed)
- [Phase 16]: Charts placed below existing dashboard content, not replacing anything
- [Phase 999.2]: Migration 014 chains from 012 (not 013) because 013 migrations exist only in parallel worktrees
- [Phase 999.2]: Textfile approach for FFmpeg drawtext phrase text to avoid Windows escaping issues
- [Phase 999.2]: Typewriter mode uses line-by-line reveal with per-line fade-in (not char-by-char)
- [Phase 999.2]: LegendWorker uses lazy renderer init to avoid importing FFmpeg deps when disabled
- [Phase 999.2]: Legend runs AFTER asyncio.gather in PostProductionLayer (sequential post-step for I/O-heavy FFmpeg)
- [Phase 999.3]: v2 templates use 4 sentences 300-355 chars; camera mapped per theme emotional tone; MOTION_TEMPLATES alias points to V2 for backward compat
- [Phase 999.3]: v2 system prompt uses structured CAMERA/SUBJECT/PHYSICS/ATMOSPHERE sections per OpenAI Cookbook
- [Phase 999.3]: max_tokens 250 for v2 (4-5 sentences, 300-500 chars); _get_system_prompt()/_get_enhance_prompt() version switching

### Pending Todos

None.

### Blockers/Concerns

- Facebook App Review for `instagram_content_publish` takes 2-6 weeks — must start early (during Phase 13)
- Cloudflare R2 CDN setup required before Phase 14 testing
- `api_usage.date` column DateTime vs Date ambiguity — resolve during Phase 16 planning

## Session Continuity

Last session: 2026-03-27T01:44:04.627Z
Stopped at: Completed 999.3-02-PLAN.md
Resume file: None
