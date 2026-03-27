"""Scheduler Worker — executa process_due_posts() a cada 60 segundos.

Pode ser executado standalone:
    python -m src.services.scheduler_worker

Ou integrado ao lifespan do FastAPI (ver start/stop_scheduler).
"""

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger("clip-flow.scheduler")

# Singleton do scheduler
_scheduler: AsyncIOScheduler | None = None


async def _process_due_posts_job():
    """Job executado pelo APScheduler — processa posts pendentes."""
    from src.database.session import get_session_factory

    factory = get_session_factory()
    async with factory() as session:
        try:
            from src.services.publisher import PublishingService

            service = PublishingService(session)
            results = await service.process_due_posts()

            if results:
                published = sum(1 for r in results if r["status"] == "published")
                failed = sum(1 for r in results if r["status"] == "failed")
                logger.info(f"Scheduler: {published} publicados, {failed} falhas")

            await session.commit()
        except Exception as e:
            logger.error(f"Erro no scheduler job: {e}")
            await session.rollback()


async def _refresh_instagram_tokens():
    """Check and refresh Instagram tokens expiring within 7 days (per D-05).

    Runs every 12 hours via APScheduler. Uses independent session
    (same pattern as _process_due_posts_job).
    """
    from src.database.session import get_session_factory
    from src.services.instagram_oauth import InstagramOAuthService

    try:
        factory = get_session_factory()
        async with factory() as session:
            service = InstagramOAuthService(session)
            refreshed = await service.refresh_expiring_tokens(days_before_expiry=7)
            if refreshed > 0:
                logger.info(f"Instagram tokens refreshed: {refreshed}")
            await session.commit()
    except Exception as e:
        logger.error(f"Instagram token refresh failed: {e}")


def get_scheduler() -> AsyncIOScheduler:
    """Retorna instancia singleton do scheduler."""
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()
    return _scheduler


def start_scheduler(interval_seconds: int = 60) -> AsyncIOScheduler:
    """Inicia o scheduler com intervalo configuravel.

    Args:
        interval_seconds: Intervalo entre execucoes (padrao: 60s).

    Returns:
        Instancia do AsyncIOScheduler.
    """
    scheduler = get_scheduler()

    if scheduler.running:
        logger.warning("Scheduler ja esta rodando")
        return scheduler

    scheduler.add_job(
        _process_due_posts_job,
        trigger=IntervalTrigger(seconds=interval_seconds),
        id="process_due_posts",
        name="Processar posts agendados",
        replace_existing=True,
    )

    # Instagram token refresh — every 12 hours (per D-05)
    scheduler.add_job(
        _refresh_instagram_tokens,
        trigger=IntervalTrigger(hours=12),
        id="instagram_token_refresh",
        name="Refresh Instagram tokens expiring within 7 days",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    scheduler.start()
    logger.info(f"Scheduler iniciado — intervalo: {interval_seconds}s")
    logger.info("Instagram token refresh job scheduled (every 12h)")
    return scheduler


def get_scheduler_status() -> dict:
    """Retorna status do scheduler para health check.

    Returns:
        Dict com running (bool), jobs (list), e uptime info.
    """
    scheduler = _scheduler
    if not scheduler:
        return {"running": False, "jobs": [], "message": "Scheduler nao inicializado"}

    jobs = []
    if scheduler.running:
        for job in scheduler.get_jobs():
            next_run = job.next_run_time
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": next_run.isoformat() if next_run else None,
            })

    return {
        "running": scheduler.running,
        "jobs": jobs,
        "jobs_count": len(jobs),
    }


def stop_scheduler():
    """Para o scheduler se estiver rodando."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler parado")
    _scheduler = None


# ── Standalone ──────────────────────────────────────────────────────────────

async def _main():
    """Execucao standalone do scheduler worker."""
    from src.database.session import init_db

    # Inicializar banco
    await init_db()
    logger.info("Banco de dados inicializado")

    # Iniciar scheduler
    start_scheduler(interval_seconds=60)
    logger.info("Scheduler worker rodando. Ctrl+C para parar.")

    try:
        # Manter vivo
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, asyncio.CancelledError):
        stop_scheduler()
        logger.info("Scheduler worker encerrado")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    asyncio.run(_main())
