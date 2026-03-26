"""Plan definitions with quota limits for Free/Pro/Enterprise tiers.

Each plan defines daily limits per service. A limit of 0 means unlimited.
The usage_repo checks these limits when enforcing quotas.

Phase 17: Billing & Stripe (BILL-02)
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PlanLimits:
    """Quota limits for a subscription plan."""

    # Gemini Image generations per day (free tier)
    gemini_image_free: int = 15
    # Gemini Image generations per day (paid tier)
    gemini_image_paid: int = 0
    # Gemini Text calls per day
    gemini_text_free: int = 500
    # Pipeline runs per day
    pipeline_runs: int = 5
    # Max characters allowed
    max_characters: int = 1
    # Max scheduled posts per day
    scheduled_posts: int = 5
    # Video generations per day (0 = unlimited, budget-capped)
    kie_video: int = 0


# Plan definitions
PLANS: dict[str, PlanLimits] = {
    "free": PlanLimits(
        gemini_image_free=15,
        gemini_image_paid=0,
        gemini_text_free=500,
        pipeline_runs=5,
        max_characters=1,
        scheduled_posts=5,
        kie_video=0,
    ),
    "pro": PlanLimits(
        gemini_image_free=100,
        gemini_image_paid=0,  # unlimited
        gemini_text_free=0,   # unlimited
        pipeline_runs=50,
        max_characters=5,
        scheduled_posts=30,
        kie_video=0,  # budget-capped, not count-capped
    ),
    "enterprise": PlanLimits(
        gemini_image_free=0,   # unlimited
        gemini_image_paid=0,   # unlimited
        gemini_text_free=0,    # unlimited
        pipeline_runs=0,       # unlimited
        max_characters=0,      # unlimited (0 = no limit)
        scheduled_posts=0,     # unlimited
        kie_video=0,           # unlimited
    ),
}


# Map (service, tier) to PlanLimits field name
_LIMIT_FIELD_MAP: dict[tuple[str, str], str] = {
    ("gemini_image", "free"): "gemini_image_free",
    ("gemini_image", "paid"): "gemini_image_paid",
    ("gemini_text", "free"): "gemini_text_free",
    ("gemini_web", "free"): "gemini_text_free",  # Same limit as text
    ("kie_video", "standard"): "kie_video",
}


def get_plan_limit(plan: str, service: str, tier: str) -> int:
    """Get the daily limit for a specific service/tier under a plan.

    Args:
        plan: Subscription plan name (free/pro/enterprise)
        service: Service name (gemini_image, gemini_text, etc.)
        tier: Service tier (free/paid/standard)

    Returns:
        Daily limit (0 = unlimited)
    """
    plan_limits = PLANS.get(plan, PLANS["free"])
    field_name = _LIMIT_FIELD_MAP.get((service, tier))
    if field_name:
        return getattr(plan_limits, field_name, 50)
    # Default fallback for unknown service/tier combos
    return 50


def get_plan_info(plan: str) -> dict:
    """Get human-readable plan information for API responses."""
    limits = PLANS.get(plan, PLANS["free"])
    plan_names = {
        "free": "Free",
        "pro": "Pro",
        "enterprise": "Enterprise",
    }
    plan_prices = {
        "free": 0,
        "pro": 29.90,
        "enterprise": 99.90,
    }
    return {
        "plan": plan,
        "name": plan_names.get(plan, plan.title()),
        "price_brl": plan_prices.get(plan, 0),
        "limits": {
            "gemini_image_daily": limits.gemini_image_free if limits.gemini_image_free > 0 else "unlimited",
            "gemini_text_daily": limits.gemini_text_free if limits.gemini_text_free > 0 else "unlimited",
            "pipeline_runs_daily": limits.pipeline_runs if limits.pipeline_runs > 0 else "unlimited",
            "max_characters": limits.max_characters if limits.max_characters > 0 else "unlimited",
            "scheduled_posts_daily": limits.scheduled_posts if limits.scheduled_posts > 0 else "unlimited",
        },
    }


def get_all_plans() -> list[dict]:
    """Get info for all available plans."""
    return [get_plan_info(plan) for plan in ["free", "pro", "enterprise"]]
