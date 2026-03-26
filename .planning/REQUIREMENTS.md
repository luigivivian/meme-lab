# Requirements: Clip-Flow

**Defined:** 2026-03-24
**Core Value:** Pipeline compoe e publica memes automaticamente — simples, rapido, sem depender de APIs caras de geracao de imagem

## v2.0 Requirements

Requirements for milestone v2.0: Pipeline Simplification, Auto-Publicacao & Multi-Tenant.

### Pipeline Simplification

- [x] **PIPE-01**: User can run pipeline in manual mode with pre-existing backgrounds (zero Gemini Image calls)
- [x] **PIPE-02**: User can select theme/background for pipeline composition
- [x] **PIPE-03**: User can preview composed memes before publishing (approve/reject)
- [x] **PIPE-04**: Pipeline composes images via Pillow with static backgrounds + phrases

### Multi-Tenant Isolation

- [x] **TENANT-01**: User sees only their own data across all resources (characters, runs, images, posts)
- [x] **TENANT-02**: All tables have user_id FK with scoped queries (pipeline_runs, content_packages, generated_images, scheduled_posts, work_orders, batch_jobs, themes)
- [x] **TENANT-03**: Admin user can access all users' data via admin bypass
- [x] **TENANT-04**: Cross-user data access returns 403 (not 404)

### Viral Content Engine (Phase 12.1 — INSERTED)

- [x] **VIRAL-01**: HackerNewsAgent removed from pipeline (irrelevant for BR meme content)
- [x] **VIRAL-02**: LemmyCommunitiesAgent removed from pipeline (low-volume, duplicates Reddit)
- [x] **VIRAL-03**: RSSFeedAgent simplified to Sensacionalista + cannabis feeds only (no Reddit RSS overlap)
- [x] **VIRAL-04**: RedditMemesAgent uses BR-first scoring (BR subs 0.6 base, English subs 0.3 base)
- [x] **VIRAL-05**: YouTubeRSSAgent expanded with 5+ major Brazilian comedy/entertainment channels
- [x] **VIRAL-06**: GeminiWebTrendsAgent requests 25 topics per fetch for broader coverage
- [x] **VIRAL-07**: BlueSkyAgent uses specific BR humor keywords instead of generic terms
- [x] **VIRAL-08**: Google Trends traffic parsing uses regex with K/M/B suffix support
- [x] **VIRAL-09**: Trend scores apply temporal velocity decay (e^(-age_hours/24))
- [x] **VIRAL-10**: TrendAggregator applies multi-source boost (1 + 0.2*(sources-1), capped at 2.0x)
- [x] **VIRAL-11**: Reddit posts use engagement/position-based scoring instead of fixed 0.4
- [ ] **VIRAL-12**: Curator uses LLM-based theme mapping instead of rigid KEYWORD_MAP
- [ ] **VIRAL-13**: Curator processes 20+ trends and produces 10-15 WorkOrders per run
- [ ] **VIRAL-14**: Curator filters topics with meme potential below 3 (LLM-rated 1-5)
- [ ] **VIRAL-15**: Generated phrases validated for length (<120 chars), language, and format before use
- [ ] **VIRAL-16**: Topic-image coherence checked before generation, with LLM-based theme remapping on mismatch

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

## Backlog Requirements

Tracked for backlog phases. Not in current milestone but planned and allocated.

### Video Generation (Phase 999.1)

- [x] **VID-01**: ContentPackage table has video columns (video_path, video_source, video_prompt_used, video_task_id, video_metadata, video_status)
- [x] **VID-02**: Theme table has video_prompt_notes for per-theme motion prompt improvement
- [x] **VID-03**: KieSora2Client can create video tasks, poll status, and download results via Kie.ai API
- [x] **VID-04**: VideoPromptBuilder generates unique LLM motion prompts per video via Gemini
- [x] **VID-05**: Motion prompts incorporate per-theme video_prompt_notes for iterative quality improvement
- [x] **VID-06**: User can trigger video generation for approved content packages via POST /generate/video
- [x] **VID-07**: User can check video status and view completed videos via GET /generate/video/status/{id}
- [x] **VID-08**: User can generate videos in batch via POST /generate/video/batch
- [x] **VID-09**: Daily video budget cap enforced via VIDEO_DAILY_BUDGET_USD with cost tracking in api_usage
- [x] **VID-10**: Character consistency via Kie.ai character_id_list registration

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
| PIPE-01 | Phase 12 | Complete |
| PIPE-02 | Phase 12 | Complete |
| PIPE-03 | Phase 12 | Complete |
| PIPE-04 | Phase 12 | Complete |
| TENANT-01 | Phase 13 | Complete |
| TENANT-02 | Phase 13 | Complete |
| TENANT-03 | Phase 13 | Complete |
| TENANT-04 | Phase 13 | Complete |
| VIRAL-01 | Phase 12.1 | Complete |
| VIRAL-02 | Phase 12.1 | Complete |
| VIRAL-03 | Phase 12.1 | Complete |
| VIRAL-04 | Phase 12.1 | Complete |
| VIRAL-05 | Phase 12.1 | Complete |
| VIRAL-06 | Phase 12.1 | Complete |
| VIRAL-07 | Phase 12.1 | Complete |
| VIRAL-08 | Phase 12.1 | Complete |
| VIRAL-09 | Phase 12.1 | Complete |
| VIRAL-10 | Phase 12.1 | Complete |
| VIRAL-11 | Phase 12.1 | Complete |
| VIRAL-12 | Phase 12.1 | Pending |
| VIRAL-13 | Phase 12.1 | Pending |
| VIRAL-14 | Phase 12.1 | Pending |
| VIRAL-15 | Phase 12.1 | Pending |
| VIRAL-16 | Phase 12.1 | Pending |
| PUB-01 | Phase 14 | Pending |
| PUB-02 | Phase 14 | Pending |
| PUB-07 | Phase 14 | Pending |
| PUB-03 | Phase 15 | Pending |
| PUB-04 | Phase 15 | Pending |
| PUB-05 | Phase 15 | Pending |
| PUB-06 | Phase 15 | Pending |
| DASH-01 | Phase 16 | Pending |
| DASH-02 | Phase 16 | Pending |
| DASH-03 | Phase 16 | Pending |
| DASH-04 | Phase 16 | Pending |
| BILL-01 | Phase 17 | Pending |
| BILL-02 | Phase 17 | Pending |
| BILL-03 | Phase 17 | Pending |
| BILL-04 | Phase 17 | Pending |
| BILL-05 | Phase 17 | Pending |
| VID-01 | Phase 999.1 | Complete |
| VID-02 | Phase 999.1 | Complete |
| VID-03 | Phase 999.1 | Complete |
| VID-04 | Phase 999.1 | Complete |
| VID-05 | Phase 999.1 | Complete |
| VID-06 | Phase 999.1 | Complete |
| VID-07 | Phase 999.1 | Complete |
| VID-08 | Phase 999.1 | Complete |
| VID-09 | Phase 999.1 | Complete |
| VID-10 | Phase 999.1 | Complete |

**Coverage:**
- v2.0 requirements: 40 total (24 original + 16 VIRAL)
- Mapped to phases: 40
- Unmapped: 0
- Backlog requirements: 10 (VID-01 through VID-10)

---
*Requirements defined: 2026-03-24*
*Last updated: 2026-03-26 after Phase 12.1 planning*
