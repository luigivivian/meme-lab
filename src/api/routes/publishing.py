"""Rotas de publishing — fila de publicacao, agendamento, calendario."""

from collections import defaultdict
from datetime import datetime, date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import db_session, get_current_user
from src.api.models import SchedulePostRequest
from src.api.serializers import scheduled_post_to_dict, scheduled_post_calendar_item

router = APIRouter(prefix="/publishing", tags=["Publishing"])


# ── Agendar post ────────────────────────────────────────────────────────────

@router.post("/schedule", summary="Agendar content package para publicacao")
async def schedule_post(
    req: SchedulePostRequest,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
    from src.services.publisher import PublishingService

    service = PublishingService(session)
    try:
        post = await service.schedule_post(
            content_package_id=req.content_package_id,
            platform=req.platform,
            scheduled_at=req.scheduled_at,
            character_id=req.character_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return scheduled_post_to_dict(post)


# ── Listar fila ─────────────────────────────────────────────────────────────

@router.get("/queue", summary="Lista posts agendados com filtros")
async def list_queue(
    status: str | None = Query(default=None, description="Filtrar por status (queued, published, failed, cancelled)"),
    platform: str | None = Query(default=None, description="Filtrar por plataforma"),
    character_id: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
    from src.database.repositories.schedule_repo import ScheduledPostRepository

    repo = ScheduledPostRepository(session)
    posts = await repo.list_posts(
        limit=limit, offset=offset,
        status=status, platform=platform, character_id=character_id,
        user=current_user,
    )
    total = await repo.count(status=status, platform=platform, user=current_user)
    items = [scheduled_post_to_dict(p) for p in posts]
    return {"total": total, "offset": offset, "limit": limit, "items": items}


# ── Resumo da fila ──────────────────────────────────────────────────────────

@router.get("/queue/summary", summary="Contagem por status e plataforma")
async def queue_summary(current_user=Depends(get_current_user), session: AsyncSession = Depends(db_session)):
    from src.services.publisher import PublishingService

    service = PublishingService(session)
    raw = await service.get_queue()  # {platform: {status: count}}

    # Transformar para formato esperado pelo frontend
    by_status: dict[str, int] = {}
    by_platform: dict[str, int] = {}
    total = 0
    for platform, statuses in raw.items():
        platform_total = 0
        for status, count in statuses.items():
            by_status[status] = by_status.get(status, 0) + count
            platform_total += count
            total += count
        by_platform[platform] = platform_total

    return {"total": total, "by_status": by_status, "by_platform": by_platform}


# ── Detalhe de post agendado ────────────────────────────────────────────────

@router.get("/queue/{post_id}", summary="Detalhes de um post agendado")
async def get_scheduled_post(post_id: int, current_user=Depends(get_current_user), session: AsyncSession = Depends(db_session)):
    from src.database.repositories.schedule_repo import ScheduledPostRepository

    repo = ScheduledPostRepository(session)
    try:
        post = await repo.get_by_id(post_id, user=current_user)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Forbidden")
    if not post:
        raise HTTPException(status_code=404, detail=f"Post agendado {post_id} nao encontrado")
    return scheduled_post_to_dict(post)


# ── Cancelar post ───────────────────────────────────────────────────────────

@router.post("/queue/{post_id}/cancel", summary="Cancelar post agendado")
async def cancel_scheduled_post(post_id: int, current_user=Depends(get_current_user), session: AsyncSession = Depends(db_session)):
    from src.services.publisher import PublishingService

    service = PublishingService(session)
    post = await service.cancel_scheduled(post_id)
    if not post:
        raise HTTPException(
            status_code=400,
            detail=f"Post {post_id} nao encontrado ou nao pode ser cancelado (status deve ser queued ou failed)",
        )
    return scheduled_post_to_dict(post)


# ── Retry post falho ────────────────────────────────────────────────────────

@router.post("/queue/{post_id}/retry", summary="Recolocar post falho na fila")
async def retry_scheduled_post(post_id: int, current_user=Depends(get_current_user), session: AsyncSession = Depends(db_session)):
    from src.services.publisher import PublishingService

    service = PublishingService(session)
    post = await service.retry_post(post_id)
    if not post:
        raise HTTPException(
            status_code=400,
            detail=f"Post {post_id} nao encontrado ou nao esta com status 'failed'",
        )
    return scheduled_post_to_dict(post)


# ── Calendario ──────────────────────────────────────────────────────────────

@router.get("/calendar", summary="Posts agrupados por data (para calendar view)")
async def publishing_calendar(
    start_date: date = Query(description="Data inicio (YYYY-MM-DD)"),
    end_date: date = Query(description="Data fim (YYYY-MM-DD)"),
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
    from src.database.repositories.schedule_repo import ScheduledPostRepository

    repo = ScheduledPostRepository(session)

    # Converter date para datetime (inicio do dia / fim do dia)
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())

    posts = await repo.get_posts_by_date_range(start_dt, end_dt, user=current_user)

    # Agrupar por data
    dates: dict[str, list] = defaultdict(list)
    for post in posts:
        date_str = post.scheduled_at.strftime("%Y-%m-%d")
        dates[date_str].append(scheduled_post_calendar_item(post))

    return {"dates": dict(dates)}


# ── Melhores horarios ──────────────────────────────────────────────────────

# ── Health check do scheduler ─────────────────────────────────────────────

@router.get("/scheduler/health", summary="Status do scheduler de publicacao")
async def scheduler_health():
    """Retorna se o scheduler esta rodando e seus jobs ativos."""
    from src.services.scheduler_worker import get_scheduler_status

    return get_scheduler_status()


# ── Melhores horarios ──────────────────────────────────────────────────────

@router.get("/best-times", summary="Melhores horarios para postar (estatico)")
async def best_times():
    """Retorna horarios sugeridos por dia da semana.

    Baseado em dados gerais de engajamento Instagram Brasil.
    TODO: Integrar com Instagram Insights para dados reais.
    """
    return {
        "monday": ["09:00", "12:00", "19:00"],
        "tuesday": ["09:00", "12:00", "19:00"],
        "wednesday": ["09:00", "12:00", "19:00", "21:00"],
        "thursday": ["09:00", "12:00", "19:00"],
        "friday": ["09:00", "12:00", "18:00", "21:00"],
        "saturday": ["10:00", "14:00", "20:00"],
        "sunday": ["10:00", "14:00", "19:00"],
    }
