"""Dual-key selector (Phase 9 — QUOT-04, QUOT-05).

Resolves which Gemini API key (free vs paid) to use based on daily usage.
Priority chain: force_tier param > GEMINI_FORCE_TIER env > free-only mode > auto (DB check).
"""

import logging
import os
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from src.database.repositories.usage_repo import UsageRepository

logger = logging.getLogger("clip-flow.key_selector")


@dataclass(frozen=True)
class KeyResolution:
    """Immutable result of key selection."""

    api_key: str
    tier: str   # "gemini_free", "gemini_paid", or "exhausted"
    mode: str   # "auto", "forced_env", "forced_request", "free_only"


class UsageAwareKeySelector:
    """Selects free or paid Gemini API key based on usage and overrides."""

    def __init__(self) -> None:
        self._free_key: str = os.getenv("GOOGLE_API_KEY", "")
        self._paid_key: str = os.getenv("GOOGLE_API_KEY_PAID", "")
        self._force_tier_env: str = os.getenv("GEMINI_FORCE_TIER", "").lower()

        if not self._free_key:
            raise ValueError("GOOGLE_API_KEY not configured")

        # Detect free-only mode (D-01, D-02)
        if not self._paid_key:
            self._free_only = True
            logger.warning("GOOGLE_API_KEY_PAID not configured -- free-only mode")
        elif self._paid_key == self._free_key:
            self._free_only = True
            self._paid_key = ""
            logger.warning(
                "GOOGLE_API_KEY_PAID identical to free key -- free-only mode"
            )
        else:
            self._free_only = False

    async def resolve(
        self,
        user_id: int,
        session: AsyncSession,
        force_tier: str | None = None,
    ) -> KeyResolution:
        """Resolve which API key to use.

        Priority (D-09):
          1. force_tier param (request-level override)
          2. GEMINI_FORCE_TIER env var
          3. Free-only mode (no paid key available)
          4. Automatic: check daily usage via UsageRepository
        """
        # Priority 1: request-level force
        if force_tier:
            return self._forced_resolution(force_tier, mode="forced_request")

        # Priority 2: env-level force
        if self._force_tier_env in ("free", "paid"):
            return self._forced_resolution(self._force_tier_env, mode="forced_env")

        # Priority 3: free-only mode — check limit before returning (D-02)
        if self._free_only:
            repo = UsageRepository(session)
            allowed, info = await repo.check_limit(user_id, "gemini_image", "free")
            if allowed:
                return KeyResolution(
                    api_key=self._free_key,
                    tier="gemini_free",
                    mode="free_only",
                )
            logger.warning("Free tier exhausted and no paid key -- tier=exhausted")
            return KeyResolution(api_key="", tier="exhausted", mode="auto")

        # Priority 4: automatic — check DB usage
        repo = UsageRepository(session)
        allowed, info = await repo.check_limit(user_id, "gemini_image", "free")

        if allowed:
            return KeyResolution(
                api_key=self._free_key,
                tier="gemini_free",
                mode="auto",
            )

        # Free exhausted — check paid tier (D-01)
        allowed_paid, info_paid = await repo.check_limit(user_id, "gemini_image", "paid")
        if allowed_paid:
            logger.info(
                "Free tier limit reached (used=%d/%d), switching to paid key",
                info.get("used", 0),
                info.get("limit", 0),
            )
            return KeyResolution(
                api_key=self._paid_key,
                tier="gemini_paid",
                mode="auto",
            )

        # Both tiers exhausted (D-01)
        logger.warning(
            "Both free and paid tiers exhausted — tier=exhausted"
        )
        return KeyResolution(api_key="", tier="exhausted", mode="auto")

    def _forced_resolution(self, tier: str, mode: str) -> KeyResolution:
        """Build a forced KeyResolution, with fallback if paid key unavailable."""
        if tier == "paid" and self._free_only:
            logger.warning(
                "Force paid requested but no paid key -- using free"
            )
            return KeyResolution(
                api_key=self._free_key,
                tier="gemini_free",
                mode=mode,
            )

        if tier == "paid":
            return KeyResolution(
                api_key=self._paid_key,
                tier="gemini_paid",
                mode=mode,
            )

        # Default: free
        return KeyResolution(
            api_key=self._free_key,
            tier="gemini_free",
            mode=mode,
        )
