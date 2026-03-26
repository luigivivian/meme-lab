"""Repository for atomic API usage tracking (Phase 8 — QUOT-02, QUOT-03).

Provides dialect-aware upsert (MySQL/SQLite), configurable daily limits
via env vars, and per-user usage aggregation.

Phase 16 additions: get_usage_history and get_cost_breakdown for dashboard analytics.
"""

import logging
import os
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select, cast, Date
from sqlalchemy.ext.asyncio import AsyncSession

from config import DATABASE_URL
from src.database.models import ApiUsage

logger = logging.getLogger("clip-flow.usage")

# Default daily limits per (service, tier).  0 = unlimited.
_DEFAULT_LIMITS: dict[tuple[str, str], int] = {
    ("gemini_image", "free"): 15,
    ("gemini_text", "free"): 500,
    ("gemini_web", "free"): 500,
    ("comfyui", "free"): 0,
    ("gemini_image", "paid"): 0,
    ("gemini_text", "paid"): 0,
    ("gemini_web", "paid"): 0,
    ("kie_video", "standard"): 0,  # Unlimited count -- budget enforced by VIDEO_DAILY_BUDGET_USD
}

# Known services to always include in usage response
_KNOWN_SERVICES: list[tuple[str, str]] = [
    ("gemini_image", "free"),
    ("gemini_text", "free"),
    ("kie_video", "standard"),
]


def _is_sqlite() -> bool:
    """Detect SQLite backend from DATABASE_URL (matches session.py pattern)."""
    return "sqlite" in DATABASE_URL


def get_daily_limit(service: str, tier: str) -> int:
    """Read daily limit from env var, falling back to hardcoded defaults.

    Env var pattern: {SERVICE}_DAILY_LIMIT_{TIER}  (e.g. GEMINI_IMAGE_DAILY_LIMIT_FREE)
    Value 0 means unlimited (no limit enforced).
    """
    env_key = f"{service.upper()}_DAILY_LIMIT_{tier.upper()}"
    env_val = os.getenv(env_key)
    if env_val is not None:
        try:
            return int(env_val)
        except ValueError:
            logger.warning("Invalid limit env var %s=%r, using default", env_key, env_val)
    return _DEFAULT_LIMITS.get((service, tier), 50)


class UsageRepository:
    """Atomic usage counter with dialect-aware upsert and limit checking."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # -- Timezone helpers ------------------------------------------------------

    @staticmethod
    def _get_pt_today_start_utc() -> datetime:
        """Start of today in PT timezone, converted to naive UTC for DB storage."""
        now_pt = datetime.now(ZoneInfo("America/Los_Angeles"))
        start_of_day_pt = datetime.combine(
            now_pt.date(), time.min, tzinfo=ZoneInfo("America/Los_Angeles")
        )
        return start_of_day_pt.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)

    @staticmethod
    def _next_pt_midnight_iso() -> str:
        """Tomorrow at midnight PT as ISO 8601 string for resets_at."""
        from datetime import timedelta

        now_pt = datetime.now(ZoneInfo("America/Los_Angeles"))
        tomorrow_pt = datetime.combine(
            now_pt.date() + timedelta(days=1),
            time.min,
            tzinfo=ZoneInfo("America/Los_Angeles"),
        )
        return tomorrow_pt.isoformat()

    # -- Core operations -------------------------------------------------------

    async def increment(
        self,
        user_id: int,
        service: str,
        tier: str,
        status: str = "success",
        cost_usd: float = 0.0,
    ) -> int:
        """Atomically increment usage counter. Returns new count.

        Uses dialect-specific upsert:
        - MySQL: INSERT ... ON DUPLICATE KEY UPDATE
        - SQLite: INSERT ... ON CONFLICT DO UPDATE
        """
        today_utc = self._get_pt_today_start_utc()
        values = dict(
            user_id=user_id,
            service=service,
            tier=tier,
            date=today_utc,
            usage_count=1,
            cost_usd=cost_usd,
            status=status,
        )

        if _is_sqlite():
            from sqlalchemy.dialects.sqlite import insert as sqlite_insert

            stmt = sqlite_insert(ApiUsage).values(**values)
            stmt = stmt.on_conflict_do_update(
                index_elements=["user_id", "service", "tier", "date"],
                set_={
                    "usage_count": ApiUsage.usage_count + 1,
                    "cost_usd": ApiUsage.cost_usd + cost_usd,
                },
            )
        else:
            from sqlalchemy.dialects.mysql import insert as mysql_insert

            stmt = mysql_insert(ApiUsage).values(**values)
            stmt = stmt.on_duplicate_key_update(
                usage_count=ApiUsage.usage_count + 1,
                cost_usd=ApiUsage.cost_usd + cost_usd,
            )

        await self.session.execute(stmt)
        await self.session.flush()

        # Read back current count
        current = await self._get_current_count(user_id, service, tier, today_utc)
        return current

    async def _get_current_count(
        self,
        user_id: int,
        service: str,
        tier: str,
        today_utc: datetime,
    ) -> int:
        """SELECT current usage_count for the given user/service/tier/date bucket."""
        result = await self.session.execute(
            select(ApiUsage.usage_count).where(
                ApiUsage.user_id == user_id,
                ApiUsage.service == service,
                ApiUsage.tier == tier,
                ApiUsage.date == today_utc,
                ApiUsage.status == "success",
            )
        )
        row = result.scalar_one_or_none()
        return row if row is not None else 0

    async def check_limit(
        self,
        user_id: int,
        service: str,
        tier: str,
    ) -> tuple[bool, dict]:
        """Check if user is within daily limit for service/tier.

        Returns (allowed, info_dict).
        If rejected, inserts a status='rejected' row (D-03).
        """
        today_utc = self._get_pt_today_start_utc()
        current = await self._get_current_count(user_id, service, tier, today_utc)
        limit = get_daily_limit(service, tier)
        resets_at = self._next_pt_midnight_iso()

        # 0 = unlimited
        if limit == 0:
            return (True, {
                "used": current,
                "limit": 0,
                "remaining": -1,
                "resets_at": resets_at,
            })

        if current >= limit:
            # Insert rejected row with full timestamp (not bucketed) to avoid
            # unique constraint collision — uses plain INSERT, not upsert.
            rejected_row = ApiUsage(
                user_id=user_id,
                service=service,
                tier=tier,
                date=datetime.now(ZoneInfo("UTC")).replace(tzinfo=None),  # full timestamp, not bucketed
                usage_count=1,
                status="rejected",
            )
            self.session.add(rejected_row)
            await self.session.flush()

            return (False, {
                "used": current,
                "limit": limit,
                "remaining": 0,
                "resets_at": resets_at,
            })

        return (True, {
            "used": current,
            "limit": limit,
            "remaining": limit - current,
            "resets_at": resets_at,
        })

    async def get_user_usage(self, user_id: int) -> dict:
        """Get per-service usage breakdown for today.

        Returns dict matching UsageResponse schema:
        {"services": [...], "resets_at": "..."}
        """
        today_utc = self._get_pt_today_start_utc()
        resets_at = self._next_pt_midnight_iso()

        # Query all success rows for today
        result = await self.session.execute(
            select(ApiUsage).where(
                ApiUsage.user_id == user_id,
                ApiUsage.date == today_utc,
                ApiUsage.status == "success",
            )
        )
        rows = result.scalars().all()
        usage_map: dict[tuple[str, str], int] = {}
        for row in rows:
            usage_map[(row.service, row.tier)] = row.usage_count

        # Build services list — always include known services
        services = []
        seen: set[tuple[str, str]] = set()
        for svc, tier in _KNOWN_SERVICES:
            used = usage_map.get((svc, tier), 0)
            limit = get_daily_limit(svc, tier)
            remaining = limit - used if limit > 0 else -1
            services.append({
                "service": svc,
                "tier": tier,
                "used": used,
                "limit": limit,
                "remaining": remaining,
            })
            seen.add((svc, tier))

        # Include any extra services from actual usage
        for (svc, tier), used in usage_map.items():
            if (svc, tier) not in seen:
                limit = get_daily_limit(svc, tier)
                remaining = limit - used if limit > 0 else -1
                services.append({
                    "service": svc,
                    "tier": tier,
                    "used": used,
                    "limit": limit,
                    "remaining": remaining,
                })

        return {"services": services, "resets_at": resets_at}

    async def get_cost_stats(self, user_id: int) -> dict:
        """Get cumulative Gemini Image cost statistics for a user.

        Returns dict with total_cost_usd, total_images, avg_cost_per_image, days_tracked.
        """
        result = await self.session.execute(
            select(
                func.sum(ApiUsage.cost_usd),
                func.sum(ApiUsage.usage_count),
                func.count(),
            ).where(
                ApiUsage.user_id == user_id,
                ApiUsage.service == "gemini_image",
                ApiUsage.status == "success",
            )
        )
        row = result.one()
        total_cost = row[0] or 0.0
        total_images = row[1] or 0
        days_tracked = row[2] or 0
        avg_cost = total_cost / total_images if total_images > 0 else 0.0
        return {
            "total_cost_usd": round(total_cost, 6),
            "total_images": total_images,
            "avg_cost_per_image": round(avg_cost, 6),
            "days_tracked": days_tracked,
        }

    async def get_daily_cost(self, user_id: int, service: str) -> float:
        """Get total cost_usd spent today for a specific service.

        Used by video budget enforcement (D-09) to check daily spend
        against VIDEO_DAILY_BUDGET_USD before allowing new generation.

        Returns sum of cost_usd for all successful usage rows matching
        user_id + service for today's date bucket (PT timezone).
        """
        today_utc = self._get_pt_today_start_utc()
        result = await self.session.execute(
            select(func.sum(ApiUsage.cost_usd)).where(
                ApiUsage.user_id == user_id,
                ApiUsage.service == service,
                ApiUsage.date == today_utc,
                ApiUsage.status == "success",
            )
        )
        total = result.scalar_one_or_none()
        return float(total) if total is not None else 0.0

    # -- Dashboard analytics (Phase 16) ----------------------------------------

    async def get_usage_history(self, user_id: int, days: int = 30) -> list[dict]:
        """Get daily usage counts grouped by service for the last N days.

        Returns list of dicts sorted by date ascending, with zero-filled
        missing dates:
            [{"date": "2026-03-01", "gemini_text": 45, "gemini_image": 3, ...}, ...]
        """
        today_utc = self._get_pt_today_start_utc()
        start_date = today_utc - timedelta(days=days)

        result = await self.session.execute(
            select(
                ApiUsage.date,
                ApiUsage.service,
                func.sum(ApiUsage.usage_count).label("count"),
            )
            .where(
                ApiUsage.user_id == user_id,
                ApiUsage.status == "success",
                ApiUsage.date >= start_date,
            )
            .group_by(ApiUsage.date, ApiUsage.service)
        )
        rows = result.all()

        # Collect all services seen
        services_seen: set[str] = set()
        date_service_map: dict[str, dict[str, int]] = {}
        for row in rows:
            d = row.date
            date_str = d.strftime("%Y-%m-%d") if isinstance(d, datetime) else str(d)[:10]
            service = row.service
            count = int(row.count)
            services_seen.add(service)
            if date_str not in date_service_map:
                date_service_map[date_str] = {}
            date_service_map[date_str][service] = count

        # Always include common services
        for svc in ("gemini_text", "gemini_image", "kie_video"):
            services_seen.add(svc)

        # Generate all dates in range, fill zeros
        history: list[dict] = []
        for i in range(days + 1):
            d = start_date + timedelta(days=i)
            date_str = d.strftime("%Y-%m-%d")
            entry: dict = {"date": date_str}
            svc_data = date_service_map.get(date_str, {})
            for svc in sorted(services_seen):
                entry[svc] = svc_data.get(svc, 0)
            history.append(entry)

        return history

    async def get_cost_breakdown(self, user_id: int, days: int = 30) -> list[dict]:
        """Get cost aggregation by service for the last N days.

        Returns list of dicts:
            [{"service": "gemini_text", "cost_usd": 0.45, "calls": 120}, ...]
        Only includes services with cost > 0 or calls > 0.
        """
        today_utc = self._get_pt_today_start_utc()
        start_date = today_utc - timedelta(days=days)

        result = await self.session.execute(
            select(
                ApiUsage.service,
                func.sum(ApiUsage.cost_usd).label("total_cost"),
                func.sum(ApiUsage.usage_count).label("total_calls"),
            )
            .where(
                ApiUsage.user_id == user_id,
                ApiUsage.status == "success",
                ApiUsage.date >= start_date,
            )
            .group_by(ApiUsage.service)
        )
        rows = result.all()

        breakdown: list[dict] = []
        for row in rows:
            cost = float(row.total_cost or 0)
            calls = int(row.total_calls or 0)
            if cost > 0 or calls > 0:
                breakdown.append({
                    "service": row.service,
                    "cost_usd": round(cost, 6),
                    "calls": calls,
                })

        return breakdown
