"""Billing routes -- Stripe Checkout, webhooks, portal, plan info (Phase 17).

BILL-01: POST /billing/checkout — create Stripe Checkout session
BILL-03: POST /billing/webhook — handle Stripe webhook events
BILL-04: POST /billing/portal — create Stripe Customer Portal session
BILL-02: GET /billing/plans — list available plans with limits
        GET /billing/subscription — current user subscription status
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import db_session, get_current_user
from src.billing.schemas import (
    CheckoutRequest,
    CheckoutResponse,
    PlanInfoResponse,
    PortalResponse,
    SubscriptionResponse,
    WebhookResponse,
)

logger = logging.getLogger("clip-flow.billing")

router = APIRouter(prefix="/billing", tags=["Billing"])


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
async def create_checkout(
    body: CheckoutRequest,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
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
async def stripe_webhook(
    request: Request,
    session: AsyncSession = Depends(db_session),
):
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
