# Phase 17: Billing & Stripe - Context

**Gathered:** 2026-03-26
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous --auto)

<domain>
## Phase Boundary

Integrate Stripe for subscription billing. Users can subscribe to plans (Free/Pro/Enterprise), have API quotas enforced per plan tier, manage their subscription from a billing page, and handle Stripe webhooks for payment events. All configurable via .env — no Stripe account required to run the app (graceful degradation).

</domain>

<decisions>
## Implementation Decisions

### Plans & Pricing
- **D-01:** 3 tiers: Free (default, no Stripe needed), Pro ($19/mo), Enterprise ($49/mo).
- **D-02:** Quotas per tier: Free (50 memes/day, 5 videos/day), Pro (500 memes/day, 50 videos/day), Enterprise (unlimited).
- **D-03:** Free tier is the default — works without Stripe configured. Pro/Enterprise require active Stripe subscription.

### Stripe Integration
- **D-04:** Use `stripe` Python SDK for backend, `@stripe/stripe-js` + `@stripe/react-stripe-js` for frontend checkout.
- **D-05:** Stripe Checkout Session for subscriptions (hosted by Stripe — no custom payment form needed).
- **D-06:** Stripe Webhooks for: `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.payment_failed`.
- **D-07:** Store `stripe_customer_id`, `stripe_subscription_id`, `plan_tier`, `subscription_status` on User model.

### Database
- **D-08:** New migration adding billing fields to `users` table: `stripe_customer_id`, `stripe_subscription_id`, `plan_tier` (default "free"), `subscription_status`, `subscription_ends_at`.
- **D-09:** New `plans` config table or hardcoded plan definitions (simpler — hardcode in config.py).

### Quota Enforcement
- **D-10:** Extend existing `UsageRepository.check_limit()` to read plan_tier from user and apply tier-specific limits.
- **D-11:** Existing `api_usage` table already tracks daily usage — just change the limit lookup.

### API Endpoints
- **D-12:** `POST /billing/create-checkout` — creates Stripe Checkout Session, returns URL.
- **D-13:** `POST /billing/webhook` — Stripe webhook handler (no auth, verifies signature).
- **D-14:** `GET /billing/status` — current plan, subscription status, usage vs limits.
- **D-15:** `POST /billing/portal` — creates Stripe Customer Portal session for self-service management.

### Frontend
- **D-16:** Billing page with plan cards (Free/Pro/Enterprise), current plan indicator, upgrade/downgrade buttons.
- **D-17:** Usage vs limits display per service.
- **D-18:** "Gerenciar assinatura" button opens Stripe Customer Portal.

### Graceful Degradation
- **D-19:** If STRIPE_SECRET_KEY is not set, billing routes return "Billing not configured" and all users get Free tier limits. App works fine without Stripe.

### Claude's Discretion
- Stripe API version
- Webhook signature verification implementation
- Plan card styling
- Usage limit error message formatting

</decisions>

<canonical_refs>
## Canonical References

### Existing Code
- `src/database/models.py` — User model (add billing fields)
- `src/database/repositories/usage_repo.py` — check_limit(), _DEFAULT_LIMITS
- `config.py` — env var patterns
- `src/api/deps.py` — get_current_user dependency

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `UsageRepository` already enforces daily limits — just needs tier-aware lookup
- `_DEFAULT_LIMITS` dict in usage_repo.py — extend with per-tier limits
- User model already has `role` field — add billing fields alongside

### Integration Points
- `src/api/routes/` — new `billing.py`
- `src/api/app.py` — register billing router
- Quota checks in all generation endpoints already call `check_limit()`

</code_context>

<specifics>
## Specific Ideas

- Structure ready for Stripe but works without it (Free tier default)
- User configures STRIPE_SECRET_KEY and STRIPE_PUBLISHABLE_KEY in .env when ready

</specifics>

<deferred>
## Deferred Ideas

- Annual billing discount
- Team/organization billing
- Usage-based billing (pay per meme)
- Invoice PDF generation

</deferred>

---

*Phase: 17-billing-stripe*
*Context gathered: 2026-03-26 via autonomous mode*
