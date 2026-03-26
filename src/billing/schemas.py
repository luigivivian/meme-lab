"""Pydantic schemas for billing API endpoints (Phase 17)."""

from datetime import datetime
from pydantic import BaseModel


class CheckoutRequest(BaseModel):
    """Request to create a Stripe Checkout session."""
    plan: str  # "pro" or "enterprise"


class CheckoutResponse(BaseModel):
    """Response with Stripe Checkout session URL."""
    checkout_url: str
    session_id: str


class PortalResponse(BaseModel):
    """Response with Stripe Customer Portal URL."""
    portal_url: str


class PlanLimitsResponse(BaseModel):
    """Plan quota limits."""
    gemini_image_daily: int | str
    gemini_text_daily: int | str
    pipeline_runs_daily: int | str
    max_characters: int | str
    scheduled_posts_daily: int | str


class PlanInfoResponse(BaseModel):
    """Single plan info."""
    plan: str
    name: str
    price_brl: float
    limits: PlanLimitsResponse


class SubscriptionResponse(BaseModel):
    """Current user subscription status."""
    plan: str
    status: str
    stripe_customer_id: str | None = None
    period_end: datetime | None = None
    cancel_at_period_end: bool = False


class WebhookResponse(BaseModel):
    """Webhook processing result."""
    received: bool = True
