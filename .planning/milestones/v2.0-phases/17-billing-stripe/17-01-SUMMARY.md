---
phase: 17-billing-stripe
plan: 01
subsystem: payments
tags: [stripe, billing, subscriptions, webhooks, checkout, portal]

# Dependency graph
requires:
  - phase: 13-tenant-isolation
    provides: Per-user data scoping, user_id on all resources
provides:
  - Subscription ORM model with Stripe lifecycle fields
  - Stripe service (checkout, webhooks, portal, grace period)
  - Plan definitions (Free/Pro/Enterprise) with quota limits
  - Billing API routes (checkout, webhooks, portal, plans, subscription)
  - Plan-aware quota enforcement in usage repository
affects: [dashboard-v2, frontend-billing-page]

# Tech tracking
tech-stack:
  added: [stripe (Python SDK)]
  patterns: [webhook-signature-verification, plan-aware-quota-enforcement, grace-period-downgrade]

key-files:
  created:
    - src/database/migrations/versions/013_add_subscriptions.py
    - src/billing/__init__.py
    - src/billing/plans.py
    - src/billing/schemas.py
    - src/billing/stripe_service.py
    - src/api/routes/billing.py
  modified:
    - src/database/models.py
    - config.py
    - src/api/app.py
    - src/database/repositories/usage_repo.py
    - src/api/routes/auth.py

key-decisions:
  - "Plan limits defined as dataclass (PlanLimits) for type safety and immutability"
  - "Env var override takes priority over plan-aware limits for operator flexibility"
  - "Grace period (7 days default) before auto-downgrade on failed payment"
  - "Webhook endpoint unauthenticated (Stripe signature verification instead of JWT)"
  - "Subscription table separate from User (tracks full lifecycle history)"

patterns-established:
  - "Plan-aware limits: get_daily_limit(service, tier, user_plan=plan) with 3-tier priority"
  - "Stripe webhook handler dispatch via event_type -> handler function map"
  - "Lazy stripe import (_get_stripe) to avoid import errors when STRIPE_SECRET_KEY empty"

requirements-completed: [BILL-01, BILL-02, BILL-03, BILL-04, BILL-05]

# Metrics
duration: 6min
completed: 2026-03-26
---

# Phase 17 Plan 01: Billing & Stripe Summary

**Full Stripe billing integration with subscription lifecycle, plan-aware quota enforcement, checkout/portal/webhook routes, and Free/Pro/Enterprise plan definitions**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-26T20:27:58Z
- **Completed:** 2026-03-26T20:33:49Z
- **Tasks:** 4
- **Files modified:** 11

## Accomplishments
- Migration 013 adds subscriptions table and billing columns (stripe_customer_id, subscription_plan, subscription_status, plan_period_end) to users
- Stripe service handles full subscription lifecycle: checkout creation, webhook signature verification, portal sessions, grace period with auto-downgrade
- Plan definitions (Free/Pro/Enterprise) with typed quota limits enforced at the usage repo layer
- 5 billing API routes: GET /billing/plans, GET /billing/subscription, POST /billing/checkout, POST /billing/portal, POST /billing/webhook

## Task Commits

Each task was committed atomically:

1. **Task 1: DB migration + ORM model updates for subscriptions** - `6c2625b` (feat)
2. **Task 2: Config constants + plan definitions + billing schemas** - `fe74765` (feat)
3. **Task 3: Stripe service + billing API routes + app wiring** - `774a0c8` (feat)
4. **Task 4: Plan-aware quota enforcement in usage repo** - `69e7c20` (feat)

## Files Created/Modified
- `src/database/migrations/versions/013_add_subscriptions.py` - Alembic migration adding subscriptions table and user billing columns
- `src/database/models.py` - Subscription ORM model + User billing fields (stripe_customer_id, subscription_plan, etc.)
- `config.py` - STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, STRIPE_*_PRICE_ID, grace period config
- `src/billing/__init__.py` - Module init
- `src/billing/plans.py` - Free/Pro/Enterprise plan definitions with PlanLimits dataclass
- `src/billing/schemas.py` - Pydantic models for billing API (CheckoutRequest, SubscriptionResponse, etc.)
- `src/billing/stripe_service.py` - StripeService with checkout, webhook handling, portal, grace period
- `src/api/routes/billing.py` - 5 billing API routes
- `src/api/app.py` - Billing router wired into FastAPI
- `src/database/repositories/usage_repo.py` - Plan-aware get_daily_limit with user_plan parameter
- `src/api/routes/auth.py` - /me/usage passes subscription_plan to usage query

## Decisions Made
- Plan limits defined as frozen dataclass (PlanLimits) -- type-safe, immutable, easy to test
- Env var override takes priority over plan-aware limits -- operators can always override
- Grace period defaults to 7 days (STRIPE_GRACE_PERIOD_DAYS) before auto-downgrade
- Webhook endpoint does not require JWT auth -- uses Stripe signature verification instead
- Subscription table tracks full history separate from User's current plan snapshot
- Lazy stripe SDK import to avoid import errors when SDK not installed or key empty

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None. All code paths are wired to real Stripe SDK calls. The only requirement is setting STRIPE_SECRET_KEY and STRIPE_WEBHOOK_SECRET environment variables for runtime operation.

## User Setup Required

**External services require manual configuration:**
- `STRIPE_SECRET_KEY` - Stripe API secret key (sk_test_... or sk_live_...)
- `STRIPE_WEBHOOK_SECRET` - Stripe webhook signing secret (whsec_...)
- `STRIPE_PRO_PRICE_ID` - Stripe Price ID for Pro plan
- `STRIPE_ENTERPRISE_PRICE_ID` - Stripe Price ID for Enterprise plan
- Install `stripe` Python package: `pip install stripe`
- Configure Stripe webhook endpoint in Stripe Dashboard pointing to `/billing/webhook`
- Run migration: `alembic upgrade head`

## Issues Encountered

None.

## Next Phase Readiness
- Backend billing infrastructure complete, ready for frontend billing page
- Plan enforcement active at usage layer -- Pro/Enterprise users get higher limits
- Stripe webhook endpoint ready to receive events once configured

## Self-Check: PASSED

All 8 files verified present. All 4 commit hashes verified in git log.

---
*Phase: 17-billing-stripe*
*Completed: 2026-03-26*
