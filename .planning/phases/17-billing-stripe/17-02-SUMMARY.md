---
phase: 17-billing-stripe
plan: 02
subsystem: billing-api
tags: [stripe, billing, api-routes, tier-enforcement, webhooks, checkout, portal]

# Dependency graph
requires:
  - phase: 17-billing-stripe
    plan: 01
    provides: StripeBillingService, PLAN_TIERS, User billing fields, config constants
provides:
  - 4 billing API endpoints (status, checkout, webhook, portal)
  - Billing router registered in app.py
  - Tier-aware quota enforcement in UsageRepository
affects: [frontend-billing-page, dashboard-v2, generation-endpoints]

# Tech tracking
tech-stack:
  added: []
  patterns: [tier-aware-quota-lookup, raw-body-webhook-verification, graceful-503-degradation]

key-files:
  created:
    - src/api/routes/billing.py
    - src/database/migrations/versions/013_add_billing_fields.py
    - src/services/stripe_billing.py
  modified:
    - src/api/app.py
    - src/database/repositories/usage_repo.py
    - src/database/models.py
    - config.py

key-decisions:
  - "Webhook endpoint uses Request.body() for raw bytes, not Pydantic model (Stripe signature verification requires raw payload)"
  - "All Stripe-dependent endpoints return 503 when STRIPE_SECRET_KEY is empty (graceful degradation)"
  - "plan_tier parameter defaults to 'free' for backward compatibility (existing callers unaffected)"
  - "get_tier_limit() imported inside function body with ImportError fallback to get_daily_limit() (no hard dependency)"

patterns-established:
  - "Tier-aware limit lookup: try get_tier_limit() from stripe_billing, fallback to get_daily_limit()"
  - "Billing status endpoint: merges plan info + usage data with tier-aware limit overrides"
  - "Raw body webhook pattern: Request param, not Pydantic body, for signature verification"

requirements-completed: [BILL-01, BILL-02, BILL-03, BILL-04, BILL-05]

# Metrics
duration: 4min
completed: 2026-03-26
---

# Phase 17 Plan 02: Billing API Routes & Tier Enforcement Summary

**4 billing API endpoints with Stripe Checkout/Portal/Webhook integration and tier-aware quota enforcement in UsageRepository**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-26T20:38:23Z
- **Completed:** 2026-03-26T20:42:37Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- 4 billing API endpoints: GET /billing/status (plan info + tier-aware usage), POST /billing/create-checkout (Stripe Checkout URL), POST /billing/webhook (raw body signature verification), POST /billing/portal (Customer Portal URL)
- Billing router registered in app.py alongside existing 11 routers
- UsageRepository.check_limit() and get_user_usage() now accept optional plan_tier parameter for tier-aware limit lookups
- Backward compatible: all existing callers continue to work with default "free" tier
- Graceful degradation: billing endpoints return 503 when Stripe is not configured

## Task Commits

Each task was committed atomically:

0. **Prerequisite: Billing foundation** - `299d29a` (feat) - [Rule 3 deviation: Plan 17-01 artifacts missing from worktree]
1. **Task 1: Billing API routes (4 endpoints) + wire to app.py** - `29784b8` (feat)
2. **Task 2: Tier-aware quota enforcement in UsageRepository** - `5bc370b` (feat)

## Files Created/Modified

- `src/api/routes/billing.py` - 4 billing endpoints (status, create-checkout, webhook, portal)
- `src/api/app.py` - billing router imported and registered
- `src/database/repositories/usage_repo.py` - check_limit and get_user_usage with plan_tier parameter
- `src/database/migrations/versions/013_add_billing_fields.py` - Migration adding 5 billing columns + 2 indexes to users table
- `src/database/models.py` - User model with stripe_customer_id, stripe_subscription_id, plan_tier, subscription_status, subscription_ends_at
- `src/services/stripe_billing.py` - StripeBillingService, PLAN_TIERS, is_stripe_configured(), get_tier_limit()
- `config.py` - STRIPE_SECRET_KEY, STRIPE_PUBLISHABLE_KEY, STRIPE_WEBHOOK_SECRET, STRIPE_PRO_PRICE_ID, STRIPE_ENTERPRISE_PRICE_ID

## Decisions Made

- Webhook endpoint uses Request.body() for raw bytes (Stripe signature verification requires unmodified payload)
- All Stripe-dependent endpoints return HTTP 503 when STRIPE_SECRET_KEY is empty
- plan_tier parameter defaults to "free" in check_limit/get_user_usage for backward compatibility
- get_tier_limit() imported at function level with ImportError fallback (no hard stripe dependency)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Plan 17-01 artifacts missing from worktree**
- **Found during:** Pre-execution dependency check
- **Issue:** Plan 17-02 depends on src/services/stripe_billing.py, User billing fields, and config constants from Plan 17-01, but these artifacts were not present in the worktree (17-01 was executed in a different worktree)
- **Fix:** Created all prerequisite artifacts: migration 013, User model billing fields, config constants, StripeBillingService module
- **Files created:** src/database/migrations/versions/013_add_billing_fields.py, src/services/stripe_billing.py
- **Files modified:** src/database/models.py, config.py
- **Commit:** 299d29a

## Known Stubs

None. All endpoints are fully wired to StripeBillingService. Tier-aware limits work without Stripe configured.

## Next Phase Readiness

- Backend billing API complete, ready for frontend billing page (Plan 03)
- All generation endpoints can opt into tier-aware limits by passing plan_tier to check_limit()
- Stripe webhook endpoint ready to receive events once STRIPE_SECRET_KEY and STRIPE_WEBHOOK_SECRET are configured

## Self-Check: PASSED

All 7 files verified present. All 3 commit hashes verified in git log.
