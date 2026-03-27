# Milestones

## v2.0 Pipeline Simplification, Auto-Publicacao & Multi-Tenant (Shipped: 2026-03-27)

**Phases completed:** 4 phases, 8 plans, 15 tasks

**Key accomplishments:**

- BRL-native cost tracking via ApiUsage cost_brl column, per-model tier grouping, and credits summary API endpoint with prices_brl lookup
- VideoCreditsCard component with per-model BRL cost breakdown table, daily budget progress bar, and all-time stats on dashboard
- GET /dashboard/business-metrics endpoint with 5 metric groups (videos, avg cost BRL, budget, trends, packages) using period comparison queries and legacy USD-to-BRL fallback
- 4 business StatsCards with colored icon backgrounds and trend arrow icons, plus full USD-to-BRL conversion for cost pie chart, total text, and video dialog budget

---

## v2.0 Pipeline Simplification, Auto-Publicacao & Multi-Tenant (Shipped: 2026-03-27)

**Phases completed:** 9 phases, 23 plans, 43 tasks

**Key accomplishments:**

- Manual pipeline backend with hex-color Pillow composition, approval workflow, 27 theme palettes, and 9 API endpoints forcing zero Gemini Image calls
- Pipeline page rewrite with manual run form (input mode tabs, theme/color/image selectors), results grid with optimistic approve/reject per card and bulk actions, matching UI-SPEC design contract
- Alembic migration 010 with backfill/NOT NULL, CharacterRepository tenant filtering with admin bypass, and get_user_character deps helper
- PipelineRunRepository
- Alembic migration 012 with 6 video columns on ContentPackage, video_prompt_notes on Theme, 13 config constants for Kie.ai Sora 2, and GCS uploader service for public image URLs
- 4 video API endpoints (generate, batch, status, budget) with daily budget enforcement, background async processing, and cost tracking via kie_video service

---
