# Clip-Flow: Auth, Rate Limiting & Gemini Image Fix

## What This Is

Evolução do Clip-Flow para suportar autenticação de usuários, controle de uso da Gemini Image API respeitando limites do plano free, e fallback inteligente para backgrounds estáticos quando o limite é atingido. Preparação para multi-tenant futuro onde cada usuário terá seu próprio personagem/marca.

## Core Value

O pipeline nunca para de gerar conteúdo — quando a Gemini Image API atinge o limite free, o sistema degrada graciosamente usando backgrounds existentes + Pillow, sem interromper a produção de memes.

## Requirements

### Validated

- ✓ Pipeline multi-agente 5 camadas (L1→L5) — existing
- ✓ Geração de frases via Gemini API — existing
- ✓ Geração de backgrounds via Gemini Image + ComfyUI + estáticos — existing
- ✓ Composição Pillow 1080x1350 — existing
- ✓ API REST FastAPI com 50+ rotas — existing
- ✓ Frontend memeLab Next.js 15 — existing
- ✓ Banco MySQL + SQLAlchemy 2.0 async + Alembic — existing
- ✓ Multi-personagem backend (CRUD characters) — existing
- ✓ 9 agents de trends ativos — existing
- ✓ Tabela users no MySQL com roles e API keys — Validated in Phase 2: Users Table
- ✓ Auth backend: register, login, refresh, logout com JWT + bcrypt — Validated in Phase 3: auth-backend
- ✓ Sessão de usuário com JWT tokens (access 2h + refresh 30d, rotação) — Validated in Phase 3: auth-backend
- ✓ get_current_user dependency para proteção de rotas — Validated in Phase 3: auth-backend

### Active

- [ ] Nova Google API key configurada e funcionando (fix 400)
- [ ] Página de login no frontend memeLab
- [ ] Registro de novo usuário (frontend)
- [ ] Tracking de uso da API por usuário por dia
- [ ] Sistema de tiers: key free (padrão) + key paga (fallback)
- [ ] Rate limiting baseado nos limites do plano free do Google
- [ ] Fallback automático para backgrounds estáticos quando limite atingido
- [ ] Dashboard de uso mostrando consumo diário vs limite
- [ ] Proteção de rotas da API (autenticação obrigatória)

### Out of Scope

- OAuth / login social — complexidade desnecessária para v1
- 2FA — futuro, quando multi-tenant estiver ativo
- Reset de senha por email — requer SMTP, diferir para v2
- Billing/pagamento — monetização é milestone separado
- Multi-tenant completo — v1 prepara a estrutura, não implementa isolamento total

## Context

**Problema atual:** A Gemini Image API está retornando 400. Precisa de nova API key.

**Plano atual:** Pay-as-you-go no Google AI Studio. Quer usar key free como padrão e key paga como fallback.

**Limites do plano free Google AI Studio (Gemini Image):**
- Imagen 3: 50 requests/minuto, ~500/dia (rate limited)
- Gemini 2.0 Flash: 15 RPM, 1M TPM, 1500 RPD (free tier)
- Os limites exatos precisam ser confirmados na documentação atual

**Codebase existente:**
- Backend: Python 3.14, FastAPI, SQLAlchemy 2.0 async, MySQL
- Frontend: Next.js 15, TypeScript, Tailwind CSS
- 13 tabelas ORM (incl. users + refresh_tokens), Alembic migrations (001-007)
- `src/image_gen/gemini_client.py` — GeminiImageClient atual
- `src/api/` — API REST modular com 9 route modules (incl. auth)
- `src/auth/` — Auth module: JWT, bcrypt, AuthService
- `memelab/` — Frontend dashboard

**Multi-tenant futuro:** Cada usuário terá personagem/marca próprios. A estrutura de auth e usage tracking de agora deve ser desenhada pensando nisso.

## Constraints

- **API Limits**: Respeitar limites do plano free do Google como padrão
- **Backward Compatible**: Pipeline existente deve continuar funcionando
- **Stack**: Manter Python + FastAPI + MySQL + Next.js (não introduzir novos frameworks)
- **Security**: Senhas com bcrypt/argon2, JWT com expiração, nunca logar API keys
- **Graceful Degradation**: Pipeline nunca para — fallback para estáticos

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Email + senha (não OAuth) | Simplicidade para v1, multi-tenant futuro não precisa de social login | ✓ Phase 3 |
| Key free + key paga (dual tier) | Maximiza uso gratuito, paga só quando necessário | — Pending |
| Fallback para BG estático (não fila) | Pipeline não pode parar, conteúdo sai sempre | — Pending |
| JWT para sessão (não session cookie) | API REST stateless, facilita multi-tenant futuro | ✓ Phase 3 — HS256, access 2h, refresh 30d |
| Preparar estrutura multi-tenant | Tabelas com user_id desde o início, isolamento depois | — Pending |

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
*Last updated: 2026-03-24 after Phase 3 completion*
