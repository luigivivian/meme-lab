"""Billing routes — Stripe Checkout, webhooks, portal, plan status.

Phase 17: Billing & Stripe (Plan 02).

Endpoints:
  GET  /billing/status          — current plan, usage vs tier limits
  POST /billing/create-checkout — create Stripe Checkout Session URL
  POST /billing/webhook         — Stripe webhook handler (no JWT auth)
  POST /billing/portal          — create Stripe Customer Portal URL
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import db_session, get_current_user
from src.services.stripe_billing import (
    PLAN_TIERS,
    StripeBillingService,
    get_tier_limit,
    is_stripe_configured,
)

logger = logging.getLogger("clip-flow.billing")

router = APIRouter(prefix="/billing", tags=["Billing"])


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
async def create_checkout(
    body: CheckoutRequest,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
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
async def stripe_webhook(
    request: Request,
    session: AsyncSession = Depends(db_session),
):
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
