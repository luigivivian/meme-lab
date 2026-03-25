# Requirements: Clip-Flow

**Defined:** 2026-03-24
**Core Value:** Pipeline compoe e publica memes automaticamente — simples, rapido, sem depender de APIs caras de geracao de imagem

## v2.0 Requirements

Requirements for milestone v2.0: Pipeline Simplification, Auto-Publicacao & Multi-Tenant.

### Pipeline Simplification

- [ ] **PIPE-01**: User can run pipeline in manual mode with pre-existing backgrounds (zero Gemini Image calls)
- [ ] **PIPE-02**: User can select theme/background for pipeline composition
- [ ] **PIPE-03**: User can preview composed memes before publishing (approve/reject)
- [ ] **PIPE-04**: Pipeline composes images via Pillow with static backgrounds + phrases

### Multi-Tenant Isolation

- [ ] **TENANT-01**: User sees only their own data across all resources (characters, runs, images, posts)
- [ ] **TENANT-02**: All tables have user_id FK with scoped queries (pipeline_runs, content_packages, generated_images, scheduled_posts, work_orders, batch_jobs, themes)
- [ ] **TENANT-03**: Admin user can access all users' data via admin bypass
- [ ] **TENANT-04**: Cross-user data access returns 403 (not 404)

### Instagram Auto-Publishing

- [ ] **PUB-01**: User can connect Instagram Business Account and store credentials securely
- [ ] **PUB-02**: Images are uploaded to CDN (Cloudflare R2) with public URLs for Instagram API
- [ ] **PUB-03**: User can schedule a post for a specific date/time
- [ ] **PUB-04**: Scheduler automatically publishes posts at scheduled time via Instagram Graph API
- [ ] **PUB-05**: User can view, cancel, and retry scheduled posts
- [ ] **PUB-06**: User can view a content calendar (month/week views) of scheduled and published posts
- [ ] **PUB-07**: Instagram tokens auto-refresh before 60-day expiry

### Dashboard v2

- [ ] **DASH-01**: User can view 30-day usage history chart
- [ ] **DASH-02**: User sees limit alerts at 80% and 95% of plan quota
- [ ] **DASH-03**: User can view estimated cost report by service/tier
- [ ] **DASH-04**: User can view pipeline run history with status

### Billing (Stripe)

- [ ] **BILL-01**: User can subscribe to a plan (Free/Pro/Enterprise) via Stripe Checkout
- [ ] **BILL-02**: Plan limits are enforced (posts/day, characters, etc.) with upgrade prompt
- [ ] **BILL-03**: Stripe webhooks handle subscription lifecycle (create, renew, update, cancel)
- [ ] **BILL-04**: User can manage billing via Stripe Customer Portal (update card, change plan, cancel)
- [ ] **BILL-05**: Failed payments trigger grace period with downgrade to Free

## Future Requirements

Deferred to future milestones. Tracked but not in current roadmap.

### Auth v2

- **AUTH-01**: User can reset password via email link
- **AUTH-02**: User can enable TOTP 2FA with authenticator app
- **AUTH-03**: User can login with Google OAuth
- **AUTH-04**: API keys encrypted at rest (Fernet)

### Multi-Character Pipeline

- **CHAR-01**: Pipeline workers generate content per character with visual DNA isolation
- **CHAR-02**: Trend agents decoupled from pipeline flow (standalone queries)

### Advanced Publishing

- **APUB-01**: Publishing analytics via Instagram Insights
- **APUB-02**: Engagement feedback loop (content scoring from Insights data)
- **APUB-03**: Multi-platform publishing (TikTok, Twitter)
- **APUB-04**: Bulk drag-and-drop scheduling calendar

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Gemini Image in pipeline | v2 goal is zero API image costs; keep as standalone notebook |
| Instagram DM automation | Violates Instagram ToS, high ban risk |
| Follower growth tools | Grey-area, Instagram bans automation aggressively |
| SMS-based 2FA | Cost per message, carrier issues in BR; TOTP only |
| Custom payment forms | Stripe Checkout handles PCI compliance |
| Redis for rate limiting | MySQL counters sufficient at current scale |
| Usage-based metered billing | Start with flat tier pricing; metered in v3 |
| OAuth providers beyond Google | Diminishing returns for BR market |
| Team workspaces | Defer to v3 |
| Mobile app | Web-first |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| PIPE-01 | — | Pending |
| PIPE-02 | — | Pending |
| PIPE-03 | — | Pending |
| PIPE-04 | — | Pending |
| TENANT-01 | — | Pending |
| TENANT-02 | — | Pending |
| TENANT-03 | — | Pending |
| TENANT-04 | — | Pending |
| PUB-01 | — | Pending |
| PUB-02 | — | Pending |
| PUB-03 | — | Pending |
| PUB-04 | — | Pending |
| PUB-05 | — | Pending |
| PUB-06 | — | Pending |
| PUB-07 | — | Pending |
| DASH-01 | — | Pending |
| DASH-02 | — | Pending |
| DASH-03 | — | Pending |
| DASH-04 | — | Pending |
| BILL-01 | — | Pending |
| BILL-02 | — | Pending |
| BILL-03 | — | Pending |
| BILL-04 | — | Pending |
| BILL-05 | — | Pending |

**Coverage:**
- v2.0 requirements: 24 total
- Mapped to phases: 0
- Unmapped: 24

---
*Requirements defined: 2026-03-24*
*Last updated: 2026-03-24 after initial definition*
