---
phase: 421-product-studio-ai-video-ads-generator
plan: 06
subsystem: ui
tags: [react, nextjs, swr, ads, wizard, typescript]

requires:
  - phase: 421-01
    provides: backend API endpoints for /ads/*
  - phase: 421-05
    provides: stepper page for ad job detail

provides:
  - API client types and functions for all /ads/* endpoints
  - SWR hooks for ad jobs listing and detail with polling
  - /ads listing page with status badges and cost display
  - /ads/new wizard page with 4 collapsible sections
  - Sidebar navigation item for Ads

affects: [421-07]

tech-stack:
  added: []
  patterns: [collapsible-section-wizard, ad-job-cards]

key-files:
  created:
    - memelab/src/hooks/use-ads.ts
    - memelab/src/app/(app)/ads/page.tsx
    - memelab/src/app/(app)/ads/new/page.tsx
    - memelab/src/components/ads/wizard.tsx
  modified:
    - memelab/src/lib/api.ts
    - memelab/src/lib/constants.ts

key-decisions:
  - "Manual collapsible sections (no Accordion UI component available) using state toggle pattern from reels page"
  - "Client-side cost estimate based on style (cinematic=2.5, narrated=3.0, lifestyle=2.0 BRL) — server estimate available via fetchAdCostEstimate"
  - "AI analysis uses direct fetch to /api/ads/analyze (not createAdJob flow) for pre-fill before job creation"

patterns-established:
  - "Section component: numbered collapsible card with filled badge, reusable for wizard UIs"
  - "Ad hooks follow same pattern as use-reels.ts: SWR with deterministic string keys and api.* fetchers"

requirements-completed: [ADS-14, ADS-15, ADS-16]

duration: 3min
completed: 2026-03-29
---

# Phase 421 Plan 06: Frontend Foundation Summary

**API client types, SWR hooks, ads listing page, and 4-section wizard for creating video ads**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-29T21:33:53Z
- **Completed:** 2026-03-29T21:37:01Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

### Task 1: API client types and functions
- Added 4 interfaces (AdJob, AdCreateRequest, AdCostEstimate, AdAnalysisResult) to api.ts
- Added 9 API functions following existing `request<T>()` pattern
- Created use-ads.ts with 3 SWR hooks (useAdJobs, useAdJob, useAdSteps) with polling intervals

### Task 2: Listing page and wizard
- /ads page with job cards showing product_name, style badge, status badge, cost_brl
- Status badges: Rascunho (amber), Gerando (sky), Completo (emerald), Falhou (red)
- AdWizard component with 4 collapsible sections: Produto, Contexto, Estilo, Audio & Formato
- "Analisar com IA" button for AI-powered auto-fill of niche, tone, audience, scene description
- Style radio cards with Portuguese labels and descriptions (Cinematico, Narrado, Lifestyle)
- Output format toggle buttons (9:16, 16:9, 1:1) with at-least-one validation
- Cost estimate display before submission
- Submit calls createAdJob and redirects to /ads/{job_id}
- Added Ads nav item to sidebar constants

## Commits

| Task | Commit | Message |
|------|--------|---------|
| 1 | 96c1fa3 | feat(421-06): add API client types, functions, and SWR hooks for ads endpoints |
| 2 | b903d5d | feat(421-06): add ads listing page, wizard with 4 collapsible sections, and nav item |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing] Added nav item to sidebar**
- **Found during:** Task 2
- **Issue:** Plan did not mention adding Ads to sidebar navigation
- **Fix:** Added `{ label: "Ads", href: "/ads", icon: ShoppingBag }` to NAV_ITEMS in constants.ts
- **Files modified:** memelab/src/lib/constants.ts
- **Commit:** b903d5d

## Known Stubs

None. All data flows are wired to real API endpoints.

## Self-Check: PASSED
