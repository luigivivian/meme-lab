# Clip-Flow

## What This Is

Pipeline multi-agente para geração automatizada de memes do personagem "O Mago Mestre" para Instagram (@magomestre420). Trends → frases Gemini → backgrounds Gemini Image → composição Pillow → publicação.

## Current State (v1.0 shipped 2026-03-24)

**Auth & Quota complete.** Full authentication (register/login/JWT/refresh/logout), all API routes protected, frontend auth pages with route guards, dual Gemini key management with atomic usage tracking, and graceful static fallback when API limits are exhausted.

**What's working:**
- 9 trend agents feeding ~227+ events per run
- Gemini phrase generation + image generation with dual-key quota control
- Full auth flow (backend + frontend) with JWT route protection on all endpoints
- Usage dashboard showing daily consumption and per-image source badges
- Pipeline never stops — degrades gracefully from Gemini → static backgrounds

**Tech debt carried forward:**
- JWT SECRET_KEY is 31 bytes (below 32-byte HS256 minimum) — set strong key in production
- Phase 11 vitest stubs are `it.todo()` placeholders
- User API keys stored as plaintext (encryption deferred to v2)

## Core Value

O pipeline nunca para de gerar conteúdo — quando limites são atingidos, degrada graciosamente.

## Stack

- **Backend:** Python 3.14, FastAPI, SQLAlchemy 2.0 async, MySQL, Alembic (8 migrations)
- **Frontend:** Next.js 15, TypeScript, Tailwind CSS
- **AI:** Google Gemini API (text + image), Ollama/Gemma3 (local fallback)
- **Image:** Gemini Image → ComfyUI → static backgrounds (3-tier fallback)
- **DB:** 14 tables ORM (incl. users, refresh_tokens, api_usage)

## Constraints

- Respeitar limites do plano free do Google como padrão
- Pipeline existente deve continuar funcionando (backward compatible)
- Manter stack atual (Python + FastAPI + MySQL + Next.js)
- Senhas com bcrypt, JWT com expiração, nunca logar API keys
- Pipeline nunca para — fallback para estáticos

## Out of Scope (v1)

- OAuth / login social — complexidade desnecessária para v1
- 2FA — futuro, quando multi-tenant estiver ativo
- Reset de senha por email — requer SMTP
- Billing/pagamento — monetização é milestone separado
- Multi-tenant completo — v1 preparou a estrutura, não implementa isolamento total

## Next Milestone Goals

_Not yet defined. Run `/gsd:new-milestone` to start planning._

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

---
*Last updated: 2026-03-24 — v1.0 milestone archived*
