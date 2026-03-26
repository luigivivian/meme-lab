<<<<<<< HEAD
"""Billing routes -- Stripe Checkout, webhooks, portal, plan info (Phase 17).

BILL-01: POST /billing/checkout — create Stripe Checkout session
BILL-03: POST /billing/webhook — handle Stripe webhook events
BILL-04: POST /billing/portal — create Stripe Customer Portal session
BILL-02: GET /billing/plans — list available plans with limits
        GET /billing/subscription — current user subscription status
=======
"""Billing routes — Stripe Checkout, webhooks, portal, plan status.

Phase 17: Billing & Stripe (Plan 02).

Endpoints:
  GET  /billing/status          — current plan, usage vs tier limits
  POST /billing/create-checkout — create Stripe Checkout Session URL
  POST /billing/webhook         — Stripe webhook handler (no JWT auth)
  POST /billing/portal          — create Stripe Customer Portal URL
>>>>>>> worktree-agent-a7949fff
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
<<<<<<< HEAD
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import db_session, get_current_user
from src.billing.schemas import (
    CheckoutRequest,
    CheckoutResponse,
    PlanInfoResponse,
    PortalResponse,
    SubscriptionResponse,
    WebhookResponse,
=======
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import db_session, get_current_user
from src.services.stripe_billing import (
    PLAN_TIERS,
    StripeBillingService,
    get_tier_limit,
    is_stripe_configured,
>>>>>>> worktree-agent-a7949fff
)

logger = logging.getLogger("clip-flow.billing")

router = APIRouter(prefix="/billing", tags=["Billing"])


<<<<<<< HEAD
@router.get("/plans", summary="List available subscription plans")
async def list_plans():
    """Return all available plans with their limits and pricing (BILL-02)."""
    from src.billing.plans import get_all_plans

    return get_all_plans()


@router.get("/subscription", response_model=SubscriptionResponse, summary="Current subscription")
async def get_subscription(
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
    """Return the current user's subscription status."""
    from sqlalchemy import select
    from src.database.models import Subscription

    # Get latest active subscription for cancel_at_period_end
    result = await session.execute(
        select(Subscription)
        .where(Subscription.user_id == current_user.id)
        .order_by(Subscription.created_at.desc())
        .limit(1)
    )
    sub = result.scalar_one_or_none()

    return SubscriptionResponse(
        plan=current_user.subscription_plan,
        status=current_user.subscription_status,
        stripe_customer_id=current_user.stripe_customer_id,
        period_end=current_user.plan_period_end,
        cancel_at_period_end=sub.cancel_at_period_end if sub else False,
    )


@router.post("/checkout", response_model=CheckoutResponse, summary="Create Checkout session")
=======
# ── Request/Response schemas ─────────────────────────────────────────────────


class CheckoutRequest(BaseModel):
    price_id: str
    success_url: str
    cancel_url: str


class PortalRequest(BaseModel):
    return_url: str


# ── GET /billing/status ─────────────────────────────────────────────────────


@router.get("/status")
async def billing_status(
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
    """Return current plan, subscription status, and per-service usage vs tier limits (D-14).

    Always works, even without Stripe configured — returns Free tier info.
    """
    from src.database.repositories.usage_repo import UsageRepository

    plan_tier = getattr(current_user, "plan_tier", "free") or "free"
    plan_info = PLAN_TIERS.get(plan_tier, PLAN_TIERS["free"])

    # Get today's usage with tier-aware limits
    repo = UsageRepository(session)
    usage_data = await repo.get_user_usage(current_user.id, plan_tier=plan_tier)

    # Override limits in the response with tier-aware values
    for svc in usage_data.get("services", []):
        tier_limit = get_tier_limit(plan_tier, svc["service"], svc["tier"])
        svc["limit"] = tier_limit
        svc["remaining"] = tier_limit - svc["used"] if tier_limit > 0 else -1

    return {
        "plan": plan_tier,
        "plan_name": plan_info["name"],
        "subscription_status": getattr(current_user, "subscription_status", None),
        "subscription_ends_at": (
            current_user.subscription_ends_at.isoformat()
            if getattr(current_user, "subscription_ends_at", None)
            else None
        ),
        "stripe_configured": is_stripe_configured(),
        "services": usage_data.get("services", []),
        "resets_at": usage_data.get("resets_at", ""),
    }


# ── POST /billing/create-checkout ───────────────────────────────────────────


@router.post("/create-checkout")
>>>>>>> worktree-agent-a7949fff
async def create_checkout(
    body: CheckoutRequest,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
<<<<<<< HEAD
    """Create a Stripe Checkout session for plan upgrade (BILL-01).

    Returns a URL to redirect the user to Stripe Checkout.
    """
    from src.billing.stripe_service import StripeService

    service = StripeService(session)
    try:
        result = await service.create_checkout_session(current_user, body.plan)
        await session.commit()
        return CheckoutResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Checkout creation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to create checkout session")


@router.post("/portal", response_model=PortalResponse, summary="Open billing portal")
async def create_portal(
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
    """Create a Stripe Customer Portal session for billing management (BILL-04).

    Returns a URL to redirect the user to manage their subscription.
    """
    from src.billing.stripe_service import StripeService

    service = StripeService(session)
    try:
        result = await service.create_portal_session(current_user)
        return PortalResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Portal creation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to create portal session")


@router.post("/webhook", response_model=WebhookResponse, summary="Stripe webhook endpoint")
=======
    """Create a Stripe Checkout Session for Pro or Enterprise subscription (D-12).

    Returns {"checkout_url": "https://checkout.stripe.com/..."}.
    Returns 503 if Stripe is not configured.
    """
    if not is_stripe_configured():
        raise HTTPException(
            status_code=503,
            detail="Billing not configured. Set STRIPE_SECRET_KEY in .env",
        )

    # Validate price_id
    from config import STRIPE_ENTERPRISE_PRICE_ID, STRIPE_PRO_PRICE_ID

    valid_prices = {STRIPE_PRO_PRICE_ID, STRIPE_ENTERPRISE_PRICE_ID}
    if body.price_id not in valid_prices:
        raise HTTPException(
            status_code=400,
            detail="Invalid price_id. Must be a valid Pro or Enterprise price.",
        )

    service = StripeBillingService(session)
    try:
        url = await service.create_checkout_session(
            user=current_user,
            price_id=body.price_id,
            success_url=body.success_url,
            cancel_url=body.cancel_url,
        )
        return {"checkout_url": url}
    except Exception as e:
        logger.error("Checkout creation failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ── POST /billing/webhook ───────────────────────────────────────────────────


@router.post("/webhook")
>>>>>>> worktree-agent-a7949fff
async def stripe_webhook(
    request: Request,
    session: AsyncSession = Depends(db_session),
):
<<<<<<< HEAD
    """Handle Stripe webhook events (BILL-03, BILL-05).

    This endpoint does NOT require authentication -- Stripe signs the payload
    with STRIPE_WEBHOOK_SECRET instead.

    Handles:
    - checkout.session.completed: New subscription created
    - customer.subscription.updated: Plan change, renewal, cancellation
    - customer.subscription.deleted: Subscription ended
    - invoice.payment_failed: Failed payment (start grace period)
    - invoice.payment_succeeded: Payment succeeded (clear past_due)
    """
    from src.billing.stripe_service import StripeService

    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature", "")

    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")

    service = StripeService(session)
    try:
        result = await service.handle_webhook(payload, sig_header)
        logger.info(f"Webhook processed: {result}")
        return WebhookResponse(received=True)
    except ValueError as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
=======
    """Stripe webhook handler — NO JWT auth, uses signature verification (D-13).

    Reads raw body bytes for Stripe signature verification.
    Handles: checkout.session.completed, customer.subscription.updated,
    customer.subscription.deleted, invoice.payment_failed.
    """
    if not is_stripe_configured():
        raise HTTPException(
            status_code=503,
            detail="Billing not configured",
        )

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    service = StripeBillingService(session)
    try:
        result = await service.handle_webhook_event(payload, sig_header)
        return result
    except ValueError as e:
        logger.warning("Webhook signature verification failed: %s", e)
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        logger.error("Webhook processing failed: %s", e)
        raise HTTPException(status_code=500, detail="Webhook processing error")


# ── POST /billing/portal ────────────────────────────────────────────────────


@router.post("/portal")
async def billing_portal(
    body: PortalRequest,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
    """Create a Stripe Customer Portal session for self-service management (D-15).

    Returns {"portal_url": "https://billing.stripe.com/..."}.
    Returns 503 if Stripe is not configured.
    Returns 400 if user has no Stripe customer account.
    """
    if not is_stripe_configured():
        raise HTTPException(
            status_code=503,
            detail="Billing not configured. Set STRIPE_SECRET_KEY in .env",
        )

    if not getattr(current_user, "stripe_customer_id", None):
        raise HTTPException(
            status_code=400,
            detail="No billing account. Subscribe to a plan first.",
        )

    service = StripeBillingService(session)
    try:
        url = await service.create_portal_session(
            user=current_user,
            return_url=body.return_url,
        )
        return {"portal_url": url}
    except Exception as e:
        logger.error("Portal session creation failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
>>>>>>> worktree-agent-a7949fff
