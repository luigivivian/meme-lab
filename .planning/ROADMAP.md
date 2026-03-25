# Roadmap: Clip-Flow

## Completed Milestones

- [x] **v1.0**: Auth, Rate Limiting & Gemini Image Fix — 11 phases, 25/25 requirements, completed 2026-03-24 — [details](milestones/v1.0-ROADMAP.md)

## Current Milestone: v2.0 Pipeline Simplification, Auto-Publicacao & Multi-Tenant

**Milestone Goal:** Pipeline simplificado que compoe memes (backgrounds existentes + frases) sem chamar Gemini Image API, com publicacao automatica Instagram, isolamento multi-tenant, dashboard de metricas e billing via Stripe.

## Phases

**Phase Numbering:**
- Integer phases (12, 13, ...): Planned milestone work (continuing from v1.0 phase 11)
- Decimal phases (12.1, 12.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 12: Pipeline Simplification** - Manual pipeline mode with static backgrounds and Pillow composition, zero Gemini Image calls
- [ ] **Phase 13: Tenant Isolation** - Per-user data scoping across all resources with admin bypass
- [ ] **Phase 14: Instagram Connection & CDN** - Connect Instagram Business Account, CDN image upload, token lifecycle management
- [ ] **Phase 15: Publishing & Scheduling** - Schedule, publish, manage, and calendar-view Instagram posts
- [ ] **Phase 16: Dashboard v2** - 30-day usage history, limit alerts, cost reports, and pipeline run history
- [ ] **Phase 17: Billing & Stripe** - Subscription plans with Stripe Checkout, webhooks, portal, and plan enforcement

## Phase Details

### Phase 12: Pipeline Simplification
**Goal**: Users can generate composed memes through a manual pipeline using pre-existing backgrounds and Pillow composition, without any Gemini Image API calls
**Depends on**: Nothing (first phase of v2.0; builds on v1.0 infrastructure)
**Requirements**: PIPE-01, PIPE-02, PIPE-03, PIPE-04
**Success Criteria** (what must be TRUE):
  1. User can trigger a pipeline run that produces composed meme images using only static backgrounds and Gemini text phrases — no Gemini Image API calls are made
  2. User can select a theme and background style before running the pipeline
  3. User can preview composed memes in a gallery and approve or reject each one before they move downstream
  4. Pipeline output images are visually correct compositions (background + phrase text rendered by Pillow)
**Plans**: 3 plans

Plans:
- [x] 12-01-PLAN.md — Backend: DB migration, image_maker hex colors, themes.yaml palettes, API endpoints
- [ ] 12-02-PLAN.md — Frontend: API client, hooks, Pipeline page rewrite per UI-SPEC
- [ ] 12-03-PLAN.md — Integration: migration + servers + human verification checkpoint

### Phase 13: Tenant Isolation
**Goal**: Every user sees only their own data across all resources, with admin users able to bypass isolation
**Depends on**: Phase 12
**Requirements**: TENANT-01, TENANT-02, TENANT-03, TENANT-04
**Success Criteria** (what must be TRUE):
  1. User can only see their own characters, pipeline runs, content packages, images, scheduled posts, and batch jobs — no other user's data appears anywhere
  2. All tenant-scoped tables have a user_id foreign key and all repository queries filter by it
  3. An admin user can access any user's data through admin-flagged requests
  4. A user attempting to access another user's resource receives a 403 Forbidden (not 404 Not Found)
**Plans**: TBD

Plans:
- [ ] 13-01: TBD
- [ ] 13-02: TBD

### Phase 14: Instagram Connection & CDN
**Goal**: Users can connect their Instagram Business Account and have their images uploaded to a CDN with public URLs ready for Instagram publishing
**Depends on**: Phase 13
**Requirements**: PUB-01, PUB-02, PUB-07
**Success Criteria** (what must be TRUE):
  1. User can connect an Instagram Business Account via Facebook OAuth flow and see the connected account in their settings
  2. Composed meme images are automatically uploaded to Cloudflare R2 CDN and assigned public URLs accessible by Instagram's servers
  3. Instagram access tokens auto-refresh before the 60-day expiry — user never has to manually reconnect due to token expiration
**Plans**: TBD
**UI hint**: yes

Plans:
- [ ] 14-01: TBD
- [ ] 14-02: TBD

### Phase 15: Publishing & Scheduling
**Goal**: Users can schedule posts to specific times, have them auto-published via Instagram Graph API, manage the queue, and view everything in a content calendar
**Depends on**: Phase 14
**Requirements**: PUB-03, PUB-04, PUB-05, PUB-06
**Success Criteria** (what must be TRUE):
  1. User can schedule an approved meme for a specific date and time
  2. The scheduler automatically publishes posts at the scheduled time via Instagram Graph API (container create, poll, publish)
  3. User can view, cancel, and retry scheduled posts from a management interface
  4. User can view a content calendar (month and week views) showing scheduled and published posts
**Plans**: TBD
**UI hint**: yes

Plans:
- [ ] 15-01: TBD
- [ ] 15-02: TBD

### Phase 16: Dashboard v2
**Goal**: Users can monitor their usage, costs, and pipeline activity through an enhanced dashboard with charts, alerts, and history
**Depends on**: Phase 13
**Requirements**: DASH-01, DASH-02, DASH-03, DASH-04
**Success Criteria** (what must be TRUE):
  1. User can view a 30-day usage history chart showing daily consumption trends
  2. User sees alert notifications when approaching 80% and 95% of their plan quota
  3. User can view an estimated cost report broken down by service and tier
  4. User can view pipeline run history with status indicators (success, failed, in-progress)
**Plans**: TBD
**UI hint**: yes

Plans:
- [ ] 16-01: TBD
- [ ] 16-02: TBD

### Phase 17: Billing & Stripe
**Goal**: Users can subscribe to plans, have limits enforced, and manage their billing entirely through Stripe integration
**Depends on**: Phase 16
**Requirements**: BILL-01, BILL-02, BILL-03, BILL-04, BILL-05
**Success Criteria** (what must be TRUE):
  1. User can subscribe to a plan (Free, Pro, or Enterprise) via Stripe Checkout and see their active plan in the app
  2. Plan limits are enforced — user hitting their quota sees an upgrade prompt instead of being able to exceed limits
  3. Stripe webhooks correctly handle subscription lifecycle events (create, renew, update, cancel) and the app reflects changes within seconds
  4. User can manage billing (update card, change plan, cancel subscription) via Stripe Customer Portal without leaving the flow
  5. Failed payments trigger a grace period and eventual automatic downgrade to Free tier
**Plans**: TBD
**UI hint**: yes

Plans:
- [ ] 17-01: TBD
- [ ] 17-02: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 12 -> 12.1 -> 12.2 -> 13 -> ...

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 12. Pipeline Simplification | 1/3 | In Progress|  |
| 13. Tenant Isolation | 0/? | Not started | - |
| 14. Instagram Connection & CDN | 0/? | Not started | - |
| 15. Publishing & Scheduling | 0/? | Not started | - |
| 16. Dashboard v2 | 0/? | Not started | - |
| 17. Billing & Stripe | 0/? | Not started | - |
