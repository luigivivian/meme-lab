"""Dashboard analytics endpoints (Phase 16 — DASH-01 through DASH-04).

Provides 4 GET endpoints for dashboard charts:
  - /dashboard/usage-history   — daily API usage by service (30 days)
  - /dashboard/cost-breakdown  — cost aggregation by service (30 days)
  - /dashboard/pipeline-activity — daily pipeline runs & packages (30 days)
  - /dashboard/publishing-stats  — published/queued/failed/cancelled counts
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import db_session, get_current_user
from src.database.models import Character, PipelineRun, ScheduledPost

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


# ── Usage History ─────────────────────────────────────────────────────────────

@router.get("/usage-history", summary="Historico de uso diario por servico (30 dias)")
async def usage_history(
    days: int = Query(default=30, ge=1, le=90),
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
    """Return daily usage array for last N days grouped by service (DASH-01)."""
    from src.database.repositories.usage_repo import UsageRepository

    days = min(max(days, 1), 90)
    repo = UsageRepository(session)
    history = await repo.get_usage_history(current_user.id, days)
    return {"days": days, "history": history}


# ── Cost Breakdown ────────────────────────────────────────────────────────────

@router.get("/cost-breakdown", summary="Custos agregados por servico (30 dias)")
async def cost_breakdown(
    days: int = Query(default=30, ge=1, le=90),
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
    """Return cost_usd aggregated by service for last N days (DASH-02)."""
    from src.database.repositories.usage_repo import UsageRepository

    days = min(max(days, 1), 90)
    repo = UsageRepository(session)
    services = await repo.get_cost_breakdown(current_user.id, days)
    total_cost = sum(s["cost_usd"] for s in services)
    return {
        "days": days,
        "services": services,
        "total_cost_usd": round(total_cost, 6),
    }


# ── Pipeline Activity ─────────────────────────────────────────────────────────

@router.get("/pipeline-activity", summary="Atividade do pipeline por dia (30 dias)")
async def pipeline_activity(
    days: int = Query(default=30, ge=1, le=90),
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
    """Return daily pipeline run counts and packages produced (DASH-03).

    Tenant-scoped: only shows runs linked to characters owned by the
    current user (via Character.user_id join), plus legacy runs where
    character_id IS NULL.
    """
    days = min(max(days, 1), 90)
    cutoff = datetime.utcnow() - timedelta(days=days)

    # Aggregate pipeline runs by day, tenant-scoped
    stmt = (
        select(
            func.date(PipelineRun.started_at).label("day"),
            func.count().label("runs"),
            func.coalesce(func.sum(PipelineRun.packages_produced), 0).label("packages"),
        )
        .outerjoin(Character, PipelineRun.character_id == Character.id)
        .where(
            PipelineRun.started_at >= cutoff,
            # Tenant scope: user's characters OR legacy runs (no character)
            (Character.user_id == current_user.id) | (PipelineRun.character_id.is_(None)),
        )
        .group_by(func.date(PipelineRun.started_at))
        .order_by(func.date(PipelineRun.started_at).asc())
    )
    result = await session.execute(stmt)
    rows = result.all()

    # Build date->data map
    day_map: dict[str, dict] = {}
    for row in rows:
        d = row.day
        date_str = d.strftime("%Y-%m-%d") if isinstance(d, datetime) else str(d)[:10]
        day_map[date_str] = {"runs": int(row.runs), "packages": int(row.packages)}

    # Fill missing dates
    activity: list[dict] = []
    for i in range(days + 1):
        d = cutoff + timedelta(days=i)
        date_str = d.strftime("%Y-%m-%d")
        data = day_map.get(date_str, {"runs": 0, "packages": 0})
        activity.append({"date": date_str, **data})

    return {"days": days, "activity": activity}


# ── Publishing Stats ──────────────────────────────────────────────────────────

@router.get("/publishing-stats", summary="Contagem de posts por status")
async def publishing_stats(
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
    """Return published/queued/failed/cancelled counts (DASH-04).

    Tenant-scoped via Character.user_id join (same pattern as schedule_repo).
    """
    stmt = (
        select(
            ScheduledPost.status,
            func.count().label("cnt"),
        )
        .outerjoin(Character, ScheduledPost.character_id == Character.id)
        .where(
            (Character.user_id == current_user.id) | (ScheduledPost.character_id.is_(None)),
        )
        .group_by(ScheduledPost.status)
    )
    result = await session.execute(stmt)
    rows = result.all()

    counts: dict[str, int] = {}
    for row in rows:
        counts[row.status] = int(row.cnt)

    total = sum(counts.values())
    return {
        "total": total,
        "published": counts.get("published", 0),
        "queued": counts.get("queued", 0),
        "failed": counts.get("failed", 0),
        "cancelled": counts.get("cancelled", 0),
    }


# -- Business Metrics (Phase 21 -- DASH-05, DASH-06, DASH-07) ----------------

@router.get("/business-metrics", summary="Metricas de negocio consolidadas")
async def business_metrics(
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
    """Return consolidated business metrics with 7d period comparison (DASH-06, DASH-07).

    All cost values are in BRL (DASH-05).
    """
    from src.database.repositories.usage_repo import UsageRepository

    repo = UsageRepository(session)
    metrics = await repo.get_business_metrics(current_user.id)
    return metrics
