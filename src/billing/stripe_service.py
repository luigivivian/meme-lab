"""Stripe integration service for subscription management (Phase 17).

Handles:
- Customer creation in Stripe
- Checkout session creation for upgrades
- Webhook event processing (subscription lifecycle)
- Customer Portal session creation
- Grace period tracking and auto-downgrade on failed payments

BILL-01: Stripe Checkout for plan subscription
BILL-03: Webhook handling for subscription lifecycle
BILL-04: Stripe Customer Portal
BILL-05: Failed payment grace period + downgrade
"""

import logging
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import (
    STRIPE_CANCEL_URL,
    STRIPE_ENTERPRISE_PRICE_ID,
    STRIPE_GRACE_PERIOD_DAYS,
    STRIPE_PRO_PRICE_ID,
    STRIPE_SECRET_KEY,
    STRIPE_SUCCESS_URL,
    STRIPE_WEBHOOK_SECRET,
)
from src.database.models import Subscription, User

logger = logging.getLogger("clip-flow.billing")

# Plan -> Stripe Price ID mapping
_PLAN_PRICE_MAP: dict[str, str] = {
    "pro": STRIPE_PRO_PRICE_ID,
    "enterprise": STRIPE_ENTERPRISE_PRICE_ID,
}


def _get_stripe():
    """Lazy import and configure stripe SDK."""
    import stripe

    stripe.api_key = STRIPE_SECRET_KEY
    return stripe


class StripeService:
    """Manages Stripe subscription lifecycle."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # -- Customer management ---------------------------------------------------

    async def ensure_stripe_customer(self, user: User) -> str:
        """Get or create a Stripe customer for the user.

        Returns the stripe_customer_id.
        """
        if user.stripe_customer_id:
            return user.stripe_customer_id

        stripe = _get_stripe()
        customer = stripe.Customer.create(
            email=user.email,
            metadata={"user_id": str(user.id)},
        )
        user.stripe_customer_id = customer.id
        await self.session.flush()
        logger.info(f"Created Stripe customer {customer.id} for user {user.id}")
        return customer.id

    # -- Checkout session creation ---------------------------------------------

    async def create_checkout_session(self, user: User, plan: str) -> dict:
        """Create a Stripe Checkout session for plan upgrade.

        Args:
            user: Current user
            plan: Target plan ("pro" or "enterprise")

        Returns:
            Dict with checkout_url and session_id

        Raises:
            ValueError: If plan is invalid or already subscribed
        """
        if plan not in _PLAN_PRICE_MAP:
            raise ValueError(f"Invalid plan: {plan}. Must be 'pro' or 'enterprise'")

        price_id = _PLAN_PRICE_MAP[plan]
        if not price_id:
            raise ValueError(f"Stripe Price ID not configured for plan: {plan}")

        if user.subscription_plan == plan and user.subscription_status == "active":
            raise ValueError(f"Already subscribed to {plan}")

        customer_id = await self.ensure_stripe_customer(user)
        stripe = _get_stripe()

        checkout_session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=STRIPE_SUCCESS_URL,
            cancel_url=STRIPE_CANCEL_URL,
            metadata={"user_id": str(user.id), "plan": plan},
        )

        logger.info(f"Created checkout session {checkout_session.id} for user {user.id} -> {plan}")
        return {
            "checkout_url": checkout_session.url,
            "session_id": checkout_session.id,
        }

    # -- Customer Portal -------------------------------------------------------

    async def create_portal_session(self, user: User) -> dict:
        """Create a Stripe Customer Portal session for billing management.

        Args:
            user: Current user (must have stripe_customer_id)

        Returns:
            Dict with portal_url

        Raises:
            ValueError: If user has no Stripe customer
        """
        if not user.stripe_customer_id:
            raise ValueError("User has no Stripe customer. Subscribe to a plan first.")

        stripe = _get_stripe()
        portal_session = stripe.billing_portal.Session.create(
            customer=user.stripe_customer_id,
            return_url=STRIPE_CANCEL_URL.replace("?canceled=true", ""),
        )

        logger.info(f"Created portal session for user {user.id}")
        return {"portal_url": portal_session.url}

    # -- Webhook handling ------------------------------------------------------

    async def handle_webhook(self, payload: bytes, sig_header: str) -> dict:
        """Process a Stripe webhook event.

        Verifies signature, routes to appropriate handler.

        Args:
            payload: Raw request body bytes
            sig_header: Stripe-Signature header value

        Returns:
            Dict with event type and processing result

        Raises:
            ValueError: If signature verification fails
        """
        stripe = _get_stripe()

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, STRIPE_WEBHOOK_SECRET
            )
        except stripe.error.SignatureVerificationError:
            raise ValueError("Invalid webhook signature")
        except Exception as e:
            raise ValueError(f"Webhook construction failed: {e}")

        event_type = event["type"]
        data = event["data"]["object"]
        logger.info(f"Processing webhook: {event_type}")

        handlers = {
            "checkout.session.completed": self._handle_checkout_completed,
            "customer.subscription.updated": self._handle_subscription_updated,
            "customer.subscription.deleted": self._handle_subscription_deleted,
            "invoice.payment_failed": self._handle_payment_failed,
            "invoice.payment_succeeded": self._handle_payment_succeeded,
        }

        handler = handlers.get(event_type)
        if handler:
            await handler(data)
            await self.session.commit()
            return {"event": event_type, "processed": True}

        logger.info(f"Unhandled webhook event: {event_type}")
        return {"event": event_type, "processed": False}

    async def _handle_checkout_completed(self, session_data: dict) -> None:
        """Handle successful checkout -- create/update subscription."""
        customer_id = session_data.get("customer")
        subscription_id = session_data.get("subscription")

        if not customer_id or not subscription_id:
            logger.warning("Checkout completed without customer or subscription ID")
            return

        user = await self._get_user_by_stripe_customer(customer_id)
        if not user:
            logger.error(f"No user found for Stripe customer {customer_id}")
            return

        # Fetch full subscription from Stripe
        stripe = _get_stripe()
        sub = stripe.Subscription.retrieve(subscription_id)
        plan = self._resolve_plan_from_price(sub["items"]["data"][0]["price"]["id"])

        # Update user plan
        user.subscription_plan = plan
        user.subscription_status = "active"
        user.plan_period_end = datetime.utcfromtimestamp(sub["current_period_end"])

        # Create subscription record
        db_sub = Subscription(
            user_id=user.id,
            stripe_subscription_id=subscription_id,
            stripe_price_id=sub["items"]["data"][0]["price"]["id"],
            plan=plan,
            status="active",
            current_period_start=datetime.utcfromtimestamp(sub["current_period_start"]),
            current_period_end=datetime.utcfromtimestamp(sub["current_period_end"]),
        )
        self.session.add(db_sub)
        logger.info(f"Checkout completed: user {user.id} -> {plan}")

    async def _handle_subscription_updated(self, sub_data: dict) -> None:
        """Handle subscription update (plan change, renewal, cancellation schedule)."""
        stripe_sub_id = sub_data.get("id")
        customer_id = sub_data.get("customer")

        user = await self._get_user_by_stripe_customer(customer_id)
        if not user:
            logger.error(f"No user found for Stripe customer {customer_id}")
            return

        status = sub_data.get("status", "active")
        cancel_at_period_end = sub_data.get("cancel_at_period_end", False)
        plan = self._resolve_plan_from_price(
            sub_data["items"]["data"][0]["price"]["id"]
        )

        # Update user
        user.subscription_plan = plan
        user.subscription_status = status
        user.plan_period_end = datetime.utcfromtimestamp(sub_data["current_period_end"])

        # Update subscription record
        db_sub = await self._get_subscription_by_stripe_id(stripe_sub_id)
        if db_sub:
            db_sub.plan = plan
            db_sub.status = status
            db_sub.current_period_start = datetime.utcfromtimestamp(sub_data["current_period_start"])
            db_sub.current_period_end = datetime.utcfromtimestamp(sub_data["current_period_end"])
            db_sub.cancel_at_period_end = cancel_at_period_end
            if cancel_at_period_end:
                db_sub.canceled_at = datetime.utcnow()

        logger.info(f"Subscription updated: user {user.id} -> {plan} ({status})")

    async def _handle_subscription_deleted(self, sub_data: dict) -> None:
        """Handle subscription cancellation -- downgrade to free."""
        customer_id = sub_data.get("customer")
        stripe_sub_id = sub_data.get("id")

        user = await self._get_user_by_stripe_customer(customer_id)
        if not user:
            return

        user.subscription_plan = "free"
        user.subscription_status = "active"
        user.plan_period_end = None

        db_sub = await self._get_subscription_by_stripe_id(stripe_sub_id)
        if db_sub:
            db_sub.status = "canceled"
            db_sub.canceled_at = datetime.utcnow()

        logger.info(f"Subscription deleted: user {user.id} downgraded to free")

    async def _handle_payment_failed(self, invoice_data: dict) -> None:
        """Handle failed payment -- start grace period (BILL-05)."""
        customer_id = invoice_data.get("customer")

        user = await self._get_user_by_stripe_customer(customer_id)
        if not user:
            return

        user.subscription_status = "past_due"

        # Set grace period end: if plan_period_end exists, add grace days
        if user.plan_period_end:
            grace_end = user.plan_period_end + timedelta(days=STRIPE_GRACE_PERIOD_DAYS)
        else:
            grace_end = datetime.utcnow() + timedelta(days=STRIPE_GRACE_PERIOD_DAYS)

        # If past grace period, auto-downgrade
        if datetime.utcnow() > grace_end:
            user.subscription_plan = "free"
            user.subscription_status = "active"
            user.plan_period_end = None
            logger.warning(f"Grace period expired: user {user.id} auto-downgraded to free")
        else:
            logger.info(f"Payment failed: user {user.id} in grace period until {grace_end}")

    async def _handle_payment_succeeded(self, invoice_data: dict) -> None:
        """Handle successful payment -- clear past_due status."""
        customer_id = invoice_data.get("customer")

        user = await self._get_user_by_stripe_customer(customer_id)
        if not user:
            return

        if user.subscription_status == "past_due":
            user.subscription_status = "active"
            logger.info(f"Payment succeeded: user {user.id} status restored to active")

    # -- Helpers ---------------------------------------------------------------

    async def _get_user_by_stripe_customer(self, customer_id: str) -> User | None:
        """Look up user by Stripe customer ID."""
        result = await self.session.execute(
            select(User).where(User.stripe_customer_id == customer_id)
        )
        return result.scalar_one_or_none()

    async def _get_subscription_by_stripe_id(self, stripe_sub_id: str) -> Subscription | None:
        """Look up subscription by Stripe subscription ID."""
        result = await self.session.execute(
            select(Subscription).where(Subscription.stripe_subscription_id == stripe_sub_id)
        )
        return result.scalar_one_or_none()

    def _resolve_plan_from_price(self, price_id: str) -> str:
        """Map Stripe price ID to plan name."""
        for plan, pid in _PLAN_PRICE_MAP.items():
            if pid == price_id:
                return plan
        logger.warning(f"Unknown price ID: {price_id}, defaulting to 'pro'")
        return "pro"

    # -- Plan enforcement helpers ----------------------------------------------

    @staticmethod
    def is_plan_active(user: User) -> bool:
        """Check if user's subscription is in a usable state.

        Active and past_due (grace period) both allow usage.
        """
        return user.subscription_status in ("active", "past_due", "trialing")
