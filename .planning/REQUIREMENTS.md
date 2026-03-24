# Requirements: Clip-Flow Auth, Rate Limiting & Gemini Image Fix

**Defined:** 2026-03-23
**Core Value:** O pipeline nunca para de gerar conteúdo — degrada graciosamente quando limites são atingidos

## v1 Requirements

### Pre-Conditions

- [ ] **PRE-01**: CORS configurado com origins específicos (não wildcard) para suportar credentials
- [ ] **PRE-02**: Gemini Image model names validados via list_models() e corrigidos (fix 400)
- [ ] **PRE-03**: API keys mascaradas em todos os logs (fix exposição existente)

### Authentication Backend

- [ ] **AUTH-01**: Usuário pode criar conta com email e senha (bcrypt hash)
- [ ] **AUTH-02**: Usuário pode fazer login e receber JWT access token + refresh token
- [ ] **AUTH-03**: Usuário pode renovar access token usando refresh token
- [ ] **AUTH-04**: Usuário pode fazer logout (invalidar refresh token)
- [ ] **AUTH-05**: Todas as rotas da API protegidas por JWT (exceto login/registro/health)
- [ ] **AUTH-06**: Sistema de roles (admin/user) com seed admin na migration
- [ ] **AUTH-07**: Tabela users no MySQL (email, hashed_password, role, api_keys criptografadas, created_at)

### Authentication Frontend

- [ ] **FAUTH-01**: Página de login com formulário email/senha no memeLab
- [ ] **FAUTH-02**: Página de registro para criar conta nova
- [ ] **FAUTH-03**: Middleware Next.js redirecionando rotas protegidas para login
- [ ] **FAUTH-04**: AuthContext gerenciando tokens e estado de autenticação
- [ ] **FAUTH-05**: api.ts injetando Authorization header em todas as requisições

### Quota Control

- [ ] **QUOT-01**: Tabela api_usage no MySQL (user_id, service, tier, date, count, status)
- [ ] **QUOT-02**: Tracking atômico de uso por usuário por dia (SELECT FOR UPDATE)
- [ ] **QUOT-03**: Limites diários configuráveis via env vars (GEMINI_IMAGE_DAILY_LIMIT_FREE)
- [ ] **QUOT-04**: Dual key management: key free como padrão, key paga como fallback
- [ ] **QUOT-05**: UsageAwareKeySelector que resolve qual key usar baseado no consumo
- [ ] **QUOT-06**: Fallback automático para backgrounds estáticos quando limite free atingido
- [ ] **QUOT-07**: Reset diário do contador (timezone-aware)

### Usage Dashboard

- [ ] **DASH-01**: Widget no dashboard mostrando consumo diário vs limite
- [ ] **DASH-02**: Indicador visual de source usado (gemini/comfyui/static) por imagem
- [ ] **DASH-03**: Endpoint API retornando estatísticas de uso do usuário

## v2 Requirements

### Authentication

- **AUTH-V2-01**: Reset de senha por email (requer SMTP)
- **AUTH-V2-02**: 2FA (quando multi-tenant ativo)
- **AUTH-V2-03**: OAuth / login social (Google)

### Usage Dashboard

- **DASH-V2-01**: Histórico de uso em gráfico (últimos 30 dias)
- **DASH-V2-02**: Alertas quando próximo do limite (80%, 95%)
- **DASH-V2-03**: Relatório de custos estimados

### Multi-Tenant

- **MT-V2-01**: Isolamento completo por usuário (personagem/marca próprios)
- **MT-V2-02**: API keys por usuário (cada um traz sua key)
- **MT-V2-03**: Billing/pagamento por uso

## Out of Scope

| Feature | Reason |
|---------|--------|
| OAuth / login social | Complexidade desnecessária para v1 |
| 2FA | Futuro, quando multi-tenant estiver ativo |
| Reset de senha por email | Requer SMTP, diferir para v2 |
| Billing/pagamento | Monetização é milestone separado |
| Redis para rate limiting | MySQL-based counter suficiente, evita nova infra |
| Per-endpoint HTTP rate limiting | Foco é quota da API externa, não throttling HTTP |
| Rate limiting por IP | Autenticação por JWT é suficiente |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| PRE-01 | Phase 1 | Pending |
| PRE-02 | Phase 1 | Pending |
| PRE-03 | Phase 1 | Pending |
| AUTH-07 | Phase 2 | Pending |
| AUTH-01 | Phase 3 | Pending |
| AUTH-02 | Phase 3 | Pending |
| AUTH-03 | Phase 3 | Pending |
| AUTH-04 | Phase 3 | Pending |
| AUTH-06 | Phase 3 | Pending |
| AUTH-05 | Phase 4 | Pending |
| FAUTH-01 | Phase 5 | Pending |
| FAUTH-02 | Phase 5 | Pending |
| FAUTH-04 | Phase 5 | Pending |
| FAUTH-05 | Phase 5 | Pending |
| FAUTH-03 | Phase 6 | Pending |
| QUOT-01 | Phase 7 | Pending |
| QUOT-07 | Phase 7 | Pending |
| QUOT-02 | Phase 8 | Pending |
| QUOT-03 | Phase 8 | Pending |
| QUOT-04 | Phase 9 | Pending |
| QUOT-05 | Phase 9 | Pending |
| QUOT-06 | Phase 10 | Pending |
| DASH-01 | Phase 11 | Pending |
| DASH-02 | Phase 11 | Pending |
| DASH-03 | Phase 11 | Pending |

**Coverage:**
- v1 requirements: 25 total
- Mapped to phases: 25
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-23*
*Last updated: 2026-03-23 — traceability mapped after roadmap creation*
