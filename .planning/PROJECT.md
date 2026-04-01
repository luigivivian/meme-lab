# Clip-Flow

## What This Is

Plataforma de geração e publicação automatizada de memes para Instagram. Pipeline simplificado compõe backgrounds existentes + frases, sem depender de APIs externas de imagem. Suporta múltiplos personagens e publicação automática.

## Completed Milestones

- **v1.0** Auth, Rate Limiting & Gemini Image Fix — shipped 2026-03-24
- **v2.0** Pipeline Simplification, Auto-Publicacao & Multi-Tenant — shipped 2026-04-01

See `.planning/milestones/` for archived details.

## Current State (updated 2026-04-01)

**v2.0 shipped.** 17 phases, 27 plans, 599 commits in 24 days. Full platform with meme pipeline, reels generation, product video ads, and business dashboard.

**What's working:**
- 9 trend agents feeding ~227+ events per run
- Manual pipeline composes memes without Gemini Image API
- Full auth flow (JWT) with tenant isolation on all endpoints
- Instagram scheduling, publishing, and content calendar
- Kie.ai video generation with 10+ models, motion prompts, and legends
- Video gallery with inline player, approve/delete, filters
- BRL-native cost tracking per model, credits summary API
- Business dashboard with trend indicators and 7d comparison
- Stripe billing with plan enforcement
- Interactive Reels pipeline: 6-step stepper, Hailuo per-scene video, SRT trim-to-narration
- Product Studio: 8-step wizard for AI video ads (cinematic/narrated/lifestyle), multi-format export
- Scene asset registry with semantic reuse (cosine similarity)
- Pipeline never stops — degrades gracefully from Gemini → static backgrounds

**Tech debt carried forward:**
- JWT SECRET_KEY is 31 bytes (below 32-byte HS256 minimum) — set strong key in production
- Phase 11 vitest stubs are `it.todo()` placeholders
- User API keys stored as plaintext (encryption deferred to v2)

## Core Value

Pipeline compõe e publica memes automaticamente — simples, rápido, sem depender de APIs caras de geração de imagem.

## Stack

- **Backend:** Python 3.14, FastAPI, SQLAlchemy 2.0 async, MySQL, Alembic (8 migrations)
- **Frontend:** Next.js 15, TypeScript, Tailwind CSS
- **AI:** Google Gemini API (text only for phrases), Ollama/Gemma3 (local fallback)
- **Video:** Kie.ai Sora 2 image-to-video (opt-in, budget-capped), GCS for public URLs
- **Image:** Composição Pillow com backgrounds existentes (lisos/estáticos)
- **DB:** 14 tables ORM (incl. users, refresh_tokens, api_usage)

## Constraints

- Pipeline não chama Gemini Image API — apenas compõe backgrounds existentes + frases
- Agentes de trends desacoplados do pipeline (consulta avulsa)
- Manter stack atual (Python + FastAPI + MySQL + Next.js)
- Senhas com bcrypt, JWT com expiração, nunca logar API keys
- Multi-tenant: isolamento por usuário desde o início

## Out of Scope (v2)

- Geração de imagens via Gemini Image API no pipeline (disponível como ferramenta separada)
- Redis para rate limiting (MySQL-based counter suficiente)
- Mobile app nativo

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Pipeline sem Gemini Image | Simplificar, reduzir custos, backgrounds lisos suficientes | v2.0 |
| Desacoplar trends do pipeline | Pipeline manual, trends como consulta independente | v2.0 |
| Billing via Stripe | Standard para SaaS | Pending |

<details>
<summary>v1.0 Key Decisions</summary>

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Email + senha (não OAuth) | Simplicidade para v1 | Shipped Phase 3 |
| Key free + key paga (dual tier) | Maximiza uso gratuito | Shipped Phase 9 |
| Fallback para BG estático | Pipeline não pode parar | Shipped Phase 10 |
| JWT para sessão (não session cookie) | API REST stateless | Shipped Phase 3 — HS256, access 2h, refresh 30d |
| Client-side redirect (não Edge) | Simpler than middleware | Shipped Phase 6 |

</details>

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-03-26 — Phase 999.1 (Video Generation) complete*
