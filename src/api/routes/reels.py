"""Reels pipeline API routes — generate, status polling, job listing, config CRUD.

Per D-01: Expose reels pipeline via /reels/* routes.
Per Phase 999.1 pattern: background tasks use get_session_factory() for independent DB sessions.

Phase 999.4 — Instagram Reels Pipeline
"""

import json
import logging
import traceback
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user, db_session
from src.database.models import ReelsConfig, ReelsJob
from src.reels_pipeline.models import (
    ReelGenerateRequest,
    ReelStatusResponse,
    ReelJobResponse,
    ReelsConfigRequest,
    ReelsConfigResponse,
)

logger = logging.getLogger("clip-flow.api.reels")

router = APIRouter(prefix="/reels", tags=["Reels Pipeline"])

# ── Presets (per D-04) ──────────────────────────────────────────────────────

PRESETS = {
    "clean": {
        "name": "Clean",
        "description": "Minimal style, fast cuts, small subtitles",
        "image_duration": 3.0,
        "transition_type": "cut",
        "transition_duration": 0.2,
        "subtitle_font_size": 40,
        "subtitle_color": "#FFFFFF",
        "bg_music_enabled": False,
    },
    "bold": {
        "name": "Bold",
        "description": "Large subtitles, slow transitions, dramatic",
        "image_duration": 5.0,
        "transition_type": "fade",
        "transition_duration": 1.0,
        "subtitle_font_size": 64,
        "subtitle_color": "#FFD700",
        "bg_music_enabled": True,
        "bg_music_volume": 0.2,
    },
    "minimal": {
        "name": "Minimal",
        "description": "Default settings, balanced for most content",
        "image_duration": 4.0,
        "transition_type": "fade",
        "transition_duration": 0.5,
        "subtitle_font_size": 52,
        "subtitle_color": "#FFFFFF",
        "bg_music_enabled": False,
    },
}


# ── Background task ─────────────────────────────────────────────────────────

async def _generate_reel_task(
    job_id: str,
    req: ReelGenerateRequest,
    config_override: dict,
    session_factory,
):
    """Background task: run full reels pipeline for a job.

    Creates its own DB session (cannot reuse request session in background).
    Per Phase 999.1 pattern: uses get_session_factory().
    """
    from src.reels_pipeline.main import ReelsPipeline

    async with session_factory() as session:
        try:
            # Load job
            result = await session.execute(
                select(ReelsJob).where(ReelsJob.job_id == job_id)
            )
            job = result.scalar_one_or_none()
            if not job:
                logger.error("Reel task: job %s not found", job_id)
                return

            # Update status to generating
            job.status = "generating"
            job.current_step = "images"
            job.progress_pct = 0
            await session.commit()

            # Define progress callback
            async def on_progress(step: str, pct: int):
                job.current_step = step
                job.progress_pct = pct
                await session.commit()

            # Sync wrapper for the progress callback (pipeline uses sync callback)
            def on_progress_sync(step: str, pct: int):
                job.current_step = step
                job.progress_pct = pct

            # Run pipeline
            pipeline = ReelsPipeline(config_override=config_override)
            pipeline_result = await pipeline.run(
                tema=req.tema,
                character_id=req.character_id,
                on_progress=on_progress_sync,
            )

            # Update job with results
            job.status = "complete"
            job.current_step = "complete"
            job.progress_pct = 100
            job.video_path = pipeline_result.video_path
            job.image_paths = pipeline_result.image_paths
            job.script_json = pipeline_result.script
            job.audio_path = pipeline_result.audio_path
            job.srt_path = pipeline_result.srt_path
            job.cost_usd = pipeline_result.cost_usd
            job.cost_brl = pipeline_result.cost_brl
            job.caption = pipeline_result.script.get("caption_instagram", "")
            job.hashtags = pipeline_result.script.get("hashtags", [])
            await session.commit()

            logger.info(
                "Reel generated: job=%s video=%s cost=$%.4f",
                job_id, pipeline_result.video_path, pipeline_result.cost_usd,
            )

        except Exception as e:
            logger.error("Reel task failed: job=%s error=%s", job_id, str(e))
            logger.error(traceback.format_exc())
            try:
                job.status = "failed"
                job.error_message = str(e)[:500]
                await session.commit()
            except Exception:
                pass


# ── Endpoints ───────────────────────────────────────────────────────────────

@router.post("/generate", summary="Start reel generation as background task")
async def generate_reel(
    req: ReelGenerateRequest,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(db_session),
):
    """Create a reel generation job and start pipeline in background.

    Returns job_id immediately for status polling.
    """
    from src.database.session import get_session_factory

    job_id = uuid.uuid4().hex[:16]

    # Load config if config_id provided
    config_override = {}
    if req.config_id:
        result = await db.execute(
            select(ReelsConfig).where(
                ReelsConfig.id == req.config_id,
                ReelsConfig.user_id == current_user.id,
            )
        )
        config = result.scalar_one_or_none()
        if config:
            config_override = {
                "image_count": config.image_count,
                "image_style": config.image_style,
                "tone": config.tone,
                "target_duration": config.target_duration,
                "niche": config.niche,
                "cta_default": config.cta_default,
                "keywords": config.keywords or [],
                "script_language": config.script_language,
                "script_system_prompt": config.script_system_prompt,
                "tts_provider": config.tts_provider,
                "tts_voice": config.tts_voice,
                "tts_speed": config.tts_speed,
                "transcription_provider": config.transcription_provider,
                "image_duration": config.image_duration,
                "transition_type": config.transition_type,
                "transition_duration": config.transition_duration,
                "bg_music_enabled": config.bg_music_enabled,
                "bg_music_volume": config.bg_music_volume,
                "subtitle_position": config.subtitle_position,
                "subtitle_font_size": config.subtitle_font_size,
                "subtitle_color": config.subtitle_color,
                "logo_enabled": config.logo_enabled,
            }

    # Merge request params into config (request takes priority)
    if req.tone != "inspiracional":
        config_override["tone"] = req.tone
    if req.target_duration != 30:
        config_override["target_duration"] = req.target_duration
    if req.niche != "lifestyle":
        config_override["niche"] = req.niche
    if req.keywords:
        config_override["keywords"] = req.keywords

    # Create job in DB
    job = ReelsJob(
        job_id=job_id,
        user_id=current_user.id,
        character_id=req.character_id,
        config_id=req.config_id,
        tema=req.tema,
        status="queued",
    )
    db.add(job)
    await db.commit()

    # Start background task
    session_factory = get_session_factory()
    background_tasks.add_task(
        _generate_reel_task, job_id, req, config_override, session_factory
    )

    return {"job_id": job_id, "status": "queued"}


@router.get("/status/{job_id}", summary="Poll reel generation status", response_model=ReelStatusResponse)
async def get_reel_status(
    job_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(db_session),
):
    """Get current status of a reel generation job. Tenant-isolated by user_id."""
    result = await db.execute(
        select(ReelsJob).where(
            ReelsJob.job_id == job_id,
            ReelsJob.user_id == current_user.id,
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return ReelStatusResponse(
        job_id=job.job_id,
        status=job.status,
        current_step=job.current_step,
        progress_pct=job.progress_pct,
        video_url=job.video_url,
        error_message=job.error_message,
    )


@router.get("/jobs", summary="List user's reel jobs")
async def list_reel_jobs(
    status: str | None = Query(default=None, description="Filter by status"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(db_session),
):
    """List reel generation jobs for the current user, ordered by newest first."""
    query = select(ReelsJob).where(ReelsJob.user_id == current_user.id)
    if status:
        query = query.where(ReelsJob.status == status)
    query = query.order_by(desc(ReelsJob.created_at)).limit(limit).offset(offset)

    result = await db.execute(query)
    jobs = result.scalars().all()

    return [
        ReelJobResponse(
            job_id=j.job_id,
            status=j.status,
            tema=j.tema,
            video_url=j.video_url,
            caption=j.caption,
            hashtags=j.hashtags,
            cost_brl=j.cost_brl,
            created_at=j.created_at,
        )
        for j in jobs
    ]


@router.get("/config", summary="Get user's reels configs")
async def get_reels_configs(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(db_session),
):
    """Return all reels configs for the current user."""
    result = await db.execute(
        select(ReelsConfig).where(ReelsConfig.user_id == current_user.id)
    )
    configs = result.scalars().all()

    return [
        ReelsConfigResponse(
            id=c.id,
            name=c.name,
            character_id=c.character_id,
            image_count=c.image_count,
            image_style=c.image_style,
            tone=c.tone,
            target_duration=c.target_duration,
            niche=c.niche,
            cta_default=c.cta_default,
            keywords=c.keywords or [],
            script_language=c.script_language,
            script_system_prompt=c.script_system_prompt,
            tts_provider=c.tts_provider,
            tts_voice=c.tts_voice,
            tts_speed=c.tts_speed,
            transcription_provider=c.transcription_provider,
            image_duration=c.image_duration,
            transition_type=c.transition_type,
            transition_duration=c.transition_duration,
            bg_music_enabled=c.bg_music_enabled,
            bg_music_volume=c.bg_music_volume,
            subtitle_position=c.subtitle_position,
            subtitle_font_size=c.subtitle_font_size,
            subtitle_color=c.subtitle_color,
            logo_enabled=c.logo_enabled,
            preset=c.preset,
        )
        for c in configs
    ]


@router.post("/config", summary="Create or update reels config")
async def upsert_reels_config(
    req: ReelsConfigRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(db_session),
):
    """Create or update a reels config. Upserts by user_id + character_id + name."""
    # Check for existing config
    query = select(ReelsConfig).where(
        ReelsConfig.user_id == current_user.id,
        ReelsConfig.name == (req.name or "default"),
    )
    if req.character_id is not None:
        query = query.where(ReelsConfig.character_id == req.character_id)
    else:
        query = query.where(ReelsConfig.character_id.is_(None))

    result = await db.execute(query)
    config = result.scalar_one_or_none()

    if config:
        # Update existing
        for field_name in [
            "image_count", "image_style", "tone", "target_duration", "niche",
            "cta_default", "keywords", "script_language", "script_system_prompt",
            "tts_provider", "tts_voice", "tts_speed", "transcription_provider",
            "image_duration", "transition_type", "transition_duration",
            "bg_music_enabled", "bg_music_volume", "subtitle_position",
            "subtitle_font_size", "subtitle_color", "logo_enabled", "preset",
        ]:
            val = getattr(req, field_name, None)
            if val is not None:
                setattr(config, field_name, val)
    else:
        # Create new
        config = ReelsConfig(
            user_id=current_user.id,
            character_id=req.character_id,
            name=req.name or "default",
            image_count=req.image_count or 5,
            image_style=req.image_style or "photographic",
            tone=req.tone or "inspiracional",
            target_duration=req.target_duration or 30,
            niche=req.niche or "lifestyle",
            cta_default=req.cta_default or "salve esse post",
            keywords=req.keywords or [],
            script_language=req.script_language or "pt-BR",
            script_system_prompt=req.script_system_prompt,
            tts_provider=req.tts_provider or "gemini",
            tts_voice=req.tts_voice or "Puck",
            tts_speed=req.tts_speed or 1.1,
            transcription_provider=req.transcription_provider or "gemini",
            image_duration=req.image_duration or 4.0,
            transition_type=req.transition_type or "fade",
            transition_duration=req.transition_duration or 0.5,
            bg_music_enabled=req.bg_music_enabled or False,
            bg_music_volume=req.bg_music_volume or 0.15,
            subtitle_position=req.subtitle_position or "bottom",
            subtitle_font_size=req.subtitle_font_size or 52,
            subtitle_color=req.subtitle_color or "#FFFFFF",
            logo_enabled=req.logo_enabled or False,
            preset=req.preset,
        )
        db.add(config)

    await db.commit()
    await db.refresh(config)

    return ReelsConfigResponse(
        id=config.id,
        name=config.name,
        character_id=config.character_id,
        image_count=config.image_count,
        image_style=config.image_style,
        tone=config.tone,
        target_duration=config.target_duration,
        niche=config.niche,
        cta_default=config.cta_default,
        keywords=config.keywords or [],
        script_language=config.script_language,
        script_system_prompt=config.script_system_prompt,
        tts_provider=config.tts_provider,
        tts_voice=config.tts_voice,
        tts_speed=config.tts_speed,
        transcription_provider=config.transcription_provider,
        image_duration=config.image_duration,
        transition_type=config.transition_type,
        transition_duration=config.transition_duration,
        bg_music_enabled=config.bg_music_enabled,
        bg_music_volume=config.bg_music_volume,
        subtitle_position=config.subtitle_position,
        subtitle_font_size=config.subtitle_font_size,
        subtitle_color=config.subtitle_color,
        logo_enabled=config.logo_enabled,
        preset=config.preset,
    )


@router.get("/config/presets", summary="List available config presets")
async def list_presets():
    """Return static preset configurations. Per D-04: pre-configured, editable."""
    return {"presets": PRESETS}
