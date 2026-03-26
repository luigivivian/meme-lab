"""Stripe billing service — checkout, portal, webhooks, plan definitions.

Phase 17: Billing & Stripe.
Provides plan tier definitions, tier-aware limit lookups, and a
StripeBillingService class wrapping all Stripe SDK interactions.

Graceful degradation: works without Stripe SDK or STRIPE_SECRET_KEY.
The get_tier_limit() helper reads from PLAN_TIERS regardless of Stripe config.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import (
    STRIPE_ENTERPRISE_PRICE_ID,
    STRIPE_PRO_PRICE_ID,
    STRIPE_SECRET_KEY,
    STRIPE_WEBHOOK_SECRET,
)

logger = logging.getLogger("clip-flow.billing")


# ── Plan tier definitions (D-01, D-02, D-09) ────────────────────────────────

PLAN_TIERS: dict[str, dict] = {
    "free": {
        "name": "Free",
        "price_usd": 0,
        "limits": {
            ("gemini_image", "free"): 15,
            ("gemini_text", "free"): 500,
            ("gemini_web", "free"): 500,
            ("kie_video", "standard"): 5,
            ("meme_compose", "free"): 50,
        },
    },
    "pro": {
        "name": "Pro",
        "price_usd": 19,
        "limits": {
            ("gemini_image", "free"): 100,
            ("gemini_text", "free"): 5000,
            ("gemini_web", "free"): 5000,
            ("kie_video", "standard"): 50,
            ("meme_compose", "free"): 500,
        },
    },
    "enterprise": {
        "name": "Enterprise",
        "price_usd": 49,
        "limits": {
            ("gemini_image", "free"): 0,  # 0 = unlimited
            ("gemini_text", "free"): 0,
            ("gemini_web", "free"): 0,
            ("kie_video", "standard"): 0,
            ("meme_compose", "free"): 0,
        },
    },
}


# ── Helpers ──────────────────────────────────────────────────────────────────


def is_stripe_configured() -> bool:
    """Return True if STRIPE_SECRET_KEY is set (non-empty)."""
    return bool(STRIPE_SECRET_KEY)


def get_tier_limit(plan_tier: str, service: str, tier: str) -> int:
    """Look up daily limit for a plan tier + service + tier combo.

    Falls back to free plan limits if plan_tier is unknown.
    Returns 0 for unlimited (Enterprise).
    """
    plan = PLAN_TIERS.get(plan_tier, PLAN_TIERS["free"])
    return plan["limits"].get((service, tier), 50)


# ── Stripe Billing Service ───────────────────────────────────────────────────


class StripeBillingService:
    """Wraps Stripe SDK for checkout, portal, and webhook handling.

    All Stripe SDK calls are lazy-imported at function level to avoid
    ImportError when the stripe package is not installed.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    def _get_stripe(self):
        """Lazy import and configure stripe SDK."""
        import stripe

        stripe.api_key = STRIPE_SECRET_KEY
        return stripe

    async def create_checkout_session(
        self,
        user,
        price_id: str,
        success_url: str,
        cancel_url: str,
    ) -> str:
        """Create a Stripe Checkout Session for subscription.

        Returns the checkout session URL.
        Creates a Stripe Customer if the user doesn't have one yet.
        """
        if not is_stripe_configured():
            raise ValueError("Stripe not configured")

        stripe = self._get_stripe()

        # Create Stripe Customer if needed
        if not user.stripe_customer_id:
            customer = stripe.Customer.create(
                email=user.email,
                metadata={"user_id": str(user.id)},
            )
            user.stripe_customer_id = customer.id
            await self.session.flush()

        checkout_session = stripe.checkout.Session.create(
            mode="subscription",
            customer=user.stripe_customer_id,
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
        )
        return checkout_session.url

    async def create_portal_session(self, user, return_url: str) -> str:
        """Create a Stripe Customer Portal session.

        Returns the portal session URL.
        """
        if not is_stripe_configured():
            raise ValueError("Stripe not configured")
        if not user.stripe_customer_id:
            raise ValueError("No billing account")

        stripe = self._get_stripe()
        portal_session = stripe.billing_portal.Session.create(
            customer=user.stripe_customer_id,
            return_url=return_url,
        )
        return portal_session.url

    async def handle_webhook_event(self, payload: bytes, sig_header: str) -> dict:
        """Verify and process a Stripe webhook event.

        Returns {"status": "ok", "event_type": ...}.
        Raises ValueError on bad signature.
        """
        stripe = self._get_stripe()

        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )

        event_type = event.type
        data_object = event.data.object

        if event_type == "checkout.session.completed":
            await self._handle_checkout_completed(data_object)
        elif event_type == "customer.subscription.updated":
            await self._handle_subscription_updated(data_object)
        elif event_type == "customer.subscription.deleted":
            await self._handle_subscription_deleted(data_object)
        elif event_type == "invoice.payment_failed":
            await self._handle_payment_failed(data_object)
        else:
            logger.info("Unhandled Stripe event type: %s", event_type)

        return {"status": "ok", "event_type": event_type}

    # ── Private webhook handlers ─────────────────────────────────────────

    async def _handle_checkout_completed(self, data_object) -> None:
        """Process checkout.session.completed: activate subscription."""
        customer_id = data_object.get("customer")
        subscription_id = data_object.get("subscription")

        user = await self._find_user_by_stripe_customer(customer_id)
        if not user:
            logger.warning("checkout.session.completed: no user for customer %s", customer_id)
            return

        user.stripe_subscription_id = subscription_id
        user.subscription_status = "active"

        # Determine tier from price_id in line items
        if hasattr(data_object, "line_items") and data_object.line_items:
            price_id = data_object.line_items.data[0].price.id if data_object.line_items.data else None
        else:
            # Fetch subscription to get price
            stripe = self._get_stripe()
            sub = stripe.Subscription.retrieve(subscription_id)
            price_id = sub["items"]["data"][0]["price"]["id"] if sub["items"]["data"] else None

        user.plan_tier = self._price_id_to_tier(price_id) if price_id else "free"
        await self.session.flush()
        logger.info("Checkout completed: user %s -> %s", user.id, user.plan_tier)

    async def _handle_subscription_updated(self, data_object) -> None:
        """Process customer.subscription.updated: sync status."""
        subscription_id = data_object.get("id")
        status = data_object.get("status", "active")

        user = await self._find_user_by_subscription(subscription_id)
        if not user:
            logger.warning("subscription.updated: no user for sub %s", subscription_id)
            return

        user.subscription_status = status

        if status == "active":
            # Sync tier from price
            items = data_object.get("items", {}).get("data", [])
            if items:
                price_id = items[0].get("price", {}).get("id")
                user.plan_tier = self._price_id_to_tier(price_id) if price_id else user.plan_tier
        # past_due: keep current tier (grace period per BILL-05)

        current_period_end = data_object.get("current_period_end")
        if current_period_end:
            user.subscription_ends_at = datetime.fromtimestamp(
                current_period_end, tz=timezone.utc
            ).replace(tzinfo=None)

        await self.session.flush()
        logger.info("Subscription updated: user %s status=%s tier=%s", user.id, status, user.plan_tier)

    async def _handle_subscription_deleted(self, data_object) -> None:
        """Process customer.subscription.deleted: downgrade to free."""
        subscription_id = data_object.get("id")

        user = await self._find_user_by_subscription(subscription_id)
        if not user:
            logger.warning("subscription.deleted: no user for sub %s", subscription_id)
            return

        user.plan_tier = "free"
        user.subscription_status = "canceled"
        user.subscription_ends_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await self.session.flush()
        logger.info("Subscription deleted: user %s downgraded to free", user.id)

    async def _handle_payment_failed(self, data_object) -> None:
        """Process invoice.payment_failed: set past_due grace period."""
        customer_id = data_object.get("customer")

        user = await self._find_user_by_stripe_customer(customer_id)
        if not user:
            logger.warning("payment_failed: no user for customer %s", customer_id)
            return

        if user.subscription_status != "past_due":
            user.subscription_status = "past_due"
            await self.session.flush()
            logger.info("Payment failed: user %s set to past_due (grace period)", user.id)

    # ── Private helpers ──────────────────────────────────────────────────

    async def _find_user_by_stripe_customer(self, customer_id: str):
        """Find User by stripe_customer_id."""
        from src.database.models import User

        result = await self.session.execute(
            select(User).where(User.stripe_customer_id == customer_id)
        )
        return result.scalar_one_or_none()

    async def _find_user_by_subscription(self, subscription_id: str):
        """Find User by stripe_subscription_id."""
        from src.database.models import User

        result = await self.session.execute(
            select(User).where(User.stripe_subscription_id == subscription_id)
        )
        return result.scalar_one_or_none()

    def _price_id_to_tier(self, price_id: str) -> str:
        """Map Stripe Price ID to plan tier name."""
        if price_id == STRIPE_PRO_PRICE_ID:
            return "pro"
        elif price_id == STRIPE_ENTERPRISE_PRICE_ID:
            return "enterprise"
        return "free"
