"""Reels pipeline API routes — generate, status polling, job listing, config CRUD, interactive step API.

Per D-01: Expose reels pipeline via /reels/* routes.
Per D-02/D-03: Step-based endpoints for interactive pipeline execution.
Per Phase 999.1 pattern: background tasks use get_session_factory() for independent DB sessions.

Phase 999.4/999.5 — Instagram Reels Pipeline
"""

import asyncio
import json
import logging
import os
import traceback
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from src.api.deps import get_current_user, db_session
from src.database.models import ReelsConfig, ReelsJob
from src.reels_pipeline.models import (
    ReelGenerateRequest,
    ReelStatusResponse,
    ReelJobResponse,
    ReelsConfigRequest,
    ReelsConfigResponse,
    StepStateResponse,
    StepApproveResponse,
    StepEditRequest,
    ReelCreateInteractiveRequest,
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


# ── Step order for interactive pipeline ────────────────────────────────────

STEP_ORDER = ["prompt", "script", "images", "tts", "srt", "video"]


async def _mark_tema_used(db: AsyncSession, user_id: int, tema: str):
    """Check if tema matches any cached suggestion for this user; if so, add to used_suggestions."""
    from src.database.models import EnhanceThemeCache

    result = await db.execute(
        select(EnhanceThemeCache).where(EnhanceThemeCache.user_id == user_id)
    )
    for cache_row in result.scalars().all():
        suggestions = cache_row.suggestions or []
        if tema in suggestions:
            used = list(cache_row.used_suggestions or [])
            if tema not in used:
                used.append(tema)
                cache_row.used_suggestions = used
                flag_modified(cache_row, "used_suggestions")
                await db.commit()
            break


def _init_step_state(tema: str) -> dict:
    """Create initial step_state for an interactive job."""
    return {
        "current_step": 0,
        "prompt": {"text": tema, "approved": False},
        "images": {"paths": [], "approved": False},
        "script": {"json": {}, "approved": False},
        "tts": {"path": "", "approved": False},
        "srt": {"path": "", "approved": False},
        "video": {"path": "", "approved": False},
    }


async def _get_user_job(
    job_id: str, user_id: int, db: AsyncSession
) -> ReelsJob:
    """Fetch a ReelsJob owned by user_id, or raise 404."""
    result = await db.execute(
        select(ReelsJob).where(
            ReelsJob.job_id == job_id,
            ReelsJob.user_id == user_id,
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


# ── Background task for step execution ─────────────────────────────────────

async def _execute_step_task(
    job_id: str,
    step_name: str,
    config_override: dict,
    session_factory,
):
    """Background task: execute a single pipeline step for an interactive job.

    Uses get_session_factory() pattern for independent DB session.
    """
    from src.reels_pipeline.main import ReelsPipeline

    async with session_factory() as session:
        try:
            result = await session.execute(
                select(ReelsJob).where(ReelsJob.job_id == job_id)
            )
            job = result.scalar_one_or_none()
            if not job:
                logger.error("Step task: job %s not found", job_id)
                return

            step_state = dict(job.step_state or {})
            step_data = step_state.get(step_name, {})
            step_data["status"] = "generating"
            step_state[step_name] = step_data
            job.step_state = step_state
            flag_modified(job, "step_state")
            await session.commit()

            # Inject job-level language into config for pipeline steps
            if job.language:
                config_override["script_language"] = job.language

            pipeline = ReelsPipeline(config_override=config_override)
            job_dir = step_state.get("prompt", {}).get("job_dir", "")

            if step_name == "images":
                script_json = step_state.get("script", {}).get("json", {})
                logger.info("Images step: script_json keys=%s, has_cenas=%s, n_cenas=%d",
                            list(script_json.keys()) if script_json else "None",
                            bool(script_json.get("cenas")),
                            len(script_json.get("cenas", [])))
                if script_json and script_json.get("cenas"):
                    # v2: per-cena image generation using script context + asset reuse
                    paths, reuse_info = await pipeline.run_step_images_per_cena(
                        script=script_json,
                        character_id=job.character_id,
                        job_dir=job_dir,
                        images_dir=os.path.join(job_dir, "images") if job_dir else "",
                        user_id=job.user_id,
                    )
                    step_data["reuse_info"] = {str(k): v for k, v in reuse_info.items()}
                else:
                    # Fallback: generic image generation (no script available)
                    paths = await pipeline.run_step_images(
                        tema=job.tema,
                        character_id=job.character_id,
                        job_dir=job_dir,
                        images_dir=os.path.join(job_dir, "images") if job_dir else "",
                    )
                step_data["paths"] = paths
                step_data["status"] = "complete"

            elif step_name == "script":
                script_result = await pipeline.run_step_script(
                    image_paths=None,  # v2: text-only script gen (before images)
                    tema=job.tema,
                    job_dir=job_dir,
                    character_id=job.character_id,
                )
                step_data["json"] = script_result
                step_data["status"] = "complete"
                job.script_json = script_result

            elif step_name == "tts":
                script_json = step_state.get("script", {}).get("json", {})
                narration = script_json.get("narracao_completa", "")
                audio_path, duration = await pipeline.run_step_tts(
                    narration_text=narration,
                    job_dir=job_dir,
                )
                step_data["path"] = audio_path
                step_data["duration"] = duration
                step_data["status"] = "complete"
                job.audio_path = audio_path

            elif step_name == "srt":
                audio_path = step_state.get("tts", {}).get("path", "")
                srt_path, duration = await pipeline.run_step_srt(
                    audio_path=audio_path,
                    job_dir=job_dir,
                )
                step_data["path"] = srt_path
                step_data["duration"] = duration
                step_data["status"] = "complete"
                job.srt_path = srt_path

            elif step_name == "video":
                image_paths = step_state.get("images", {}).get("paths", [])
                audio_path = step_state.get("tts", {}).get("path", "")
                srt_path = step_state.get("srt", {}).get("path", "")
                script_json = step_state.get("script", {}).get("json", {})

                # Per-scene status callback — uses independent session to avoid
                # concurrent commit on the parent session (which is mid-transaction)
                _scene_lock = asyncio.Lock()

                async def _scene_update(scenes_list):
                    from src.database.session import get_session_factory
                    async with _scene_lock:
                        try:
                            sf = get_session_factory()
                            async with sf() as s:
                                result = await s.execute(
                                    select(ReelsJob).where(ReelsJob.job_id == job_id)
                                )
                                j = result.scalar_one_or_none()
                                if j and j.step_state:
                                    j.step_state["video"]["scenes"] = scenes_list
                                    flag_modified(j, "step_state")
                                    await s.commit()
                        except Exception as e:
                            logger.warning("Scene update commit failed (non-fatal): %s", e)

                def on_scene_update(scenes_list):
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(_scene_update(scenes_list))
                    except RuntimeError:
                        pass

                video_path = await pipeline.run_step_video_kie(
                    image_paths=image_paths,
                    audio_path=audio_path,
                    srt_path=srt_path,
                    job_dir=job_dir,
                    script=script_json,
                    on_scene_update=on_scene_update,
                    user_id=job.user_id,
                    character_id=job.character_id,
                )
                step_data["path"] = video_path
                step_data["status"] = "complete"
                job.video_path = video_path

                # Generate platform metadata after video completes
                platforms = job.platforms or ["instagram"]
                if platforms:
                    try:
                        from src.reels_pipeline.platform_metadata import generate_platform_metadata
                        platform_outputs = await generate_platform_metadata(
                            script_json=script_json,
                            platforms=platforms,
                            video_url=job.video_url,
                        )
                        job.platform_outputs = platform_outputs
                        flag_modified(job, "platform_outputs")
                    except Exception as plat_err:
                        logger.error("Platform metadata generation failed: %s", plat_err)

            step_state[step_name] = step_data
            job.step_state = step_state
            flag_modified(job, "step_state")
            await session.commit()

            logger.info("Step %s complete for job %s", step_name, job_id)

        except Exception as e:
            logger.error("Step %s failed for job %s: %s", step_name, job_id, str(e))
            logger.error(traceback.format_exc())
            try:
                step_state = dict(job.step_state or {})
                step_data = step_state.get(step_name, {})
                step_data["status"] = "error"
                step_data["error"] = str(e)[:500]
                step_state[step_name] = step_data
                job.step_state = step_state
                flag_modified(job, "step_state")
                await session.commit()
            except Exception:
                pass


# ── Background task (full pipeline) ────────────────────────────────────────

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
                "video_model": config.video_model,
            }

    # Resolve character_id: explicit id > slug > auto-detect > none
    from src.database.models import Character
    character_id = req.character_id
    if not character_id and req.character_slug:
        slug_result = await db.execute(
            select(Character).where(
                Character.slug == req.character_slug,
                Character.user_id == current_user.id,
            )
        )
        slug_char = slug_result.scalar_one_or_none()
        if slug_char:
            character_id = slug_char.id
    if not req.no_character and character_id is None:
        # Auto-detect: use user's first character
        char_result = await db.execute(
            select(Character).where(
                Character.user_id == current_user.id,
                Character.is_deleted == False,
            ).limit(1)
        )
        default_char = char_result.scalar_one_or_none()
        if default_char:
            character_id = default_char.id
    elif req.no_character:
        character_id = None

    # Merge request params into config (request takes priority)
    if req.tone != "inspiracional":
        config_override["tone"] = req.tone
    if req.target_duration != 30:
        config_override["target_duration"] = req.target_duration
    if req.niche != "lifestyle":
        config_override["niche"] = req.niche
    if req.keywords:
        config_override["keywords"] = req.keywords

    # Update request character_id for pipeline
    req.character_id = character_id

    # Thread language into config_override for pipeline
    language = req.language or config_override.get("script_language", "pt-BR")
    config_override["script_language"] = language

    # Create job in DB
    job = ReelsJob(
        job_id=job_id,
        user_id=current_user.id,
        character_id=character_id,
        config_id=req.config_id,
        tema=req.tema,
        language=language,
        status="queued",
        platforms=req.platforms or ["instagram"],
    )
    db.add(job)
    await db.commit()

    # Mark tema as used in enhance cache (Phase 999.8-A)
    await _mark_tema_used(db, current_user.id, req.tema)

    # Start background task
    session_factory = get_session_factory()
    background_tasks.add_task(
        _generate_reel_task, job_id, req, config_override, session_factory
    )

    return {"job_id": job_id, "status": "queued"}


# ── Interactive step endpoints ─────────────────────────────────────────────

@router.post("/interactive", summary="Create interactive reel job (step-by-step)")
async def create_interactive_reel(
    req: ReelCreateInteractiveRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(db_session),
):
    """Create an interactive reel job with step_state initialized.

    Returns job_id and step_state for frontend to drive step-by-step.
    """
    from src.database.models import Character

    job_id = uuid.uuid4().hex[:16]

    # Resolve character_id: explicit id > slug > auto-detect > none
    character_id = req.character_id
    if not character_id and req.character_slug:
        slug_result = await db.execute(
            select(Character).where(
                Character.slug == req.character_slug,
                Character.user_id == current_user.id,
            )
        )
        slug_char = slug_result.scalar_one_or_none()
        if slug_char:
            character_id = slug_char.id
    if not req.no_character and character_id is None:
        char_result = await db.execute(
            select(Character).where(
                Character.user_id == current_user.id,
                Character.is_deleted == False,
            ).limit(1)
        )
        default_char = char_result.scalar_one_or_none()
        if default_char:
            character_id = default_char.id
    elif req.no_character:
        character_id = None

    step_state = _init_step_state(req.tema)

    # Load config to persist video_model in step_state for downstream steps
    if req.config_id:
        cfg_result = await db.execute(
            select(ReelsConfig).where(
                ReelsConfig.id == req.config_id,
                ReelsConfig.user_id == current_user.id,
            )
        )
        cfg = cfg_result.scalar_one_or_none()
        if cfg:
            step_state["config"] = {"video_model": cfg.video_model}

    # Per-reel image_count override (independent of saved config)
    if req.image_count is not None:
        step_state.setdefault("config", {})["image_count"] = req.image_count

    # Create job_dir immediately so all subsequent steps can use it
    from src.reels_pipeline.main import ReelsPipeline
    pipeline = ReelsPipeline()
    prompt_result = await pipeline.run_step_prompt(
        tema=req.tema,
        character_id=character_id,
    )
    step_state["prompt"]["job_dir"] = prompt_result.get("job_dir", "")
    step_state["prompt"]["status"] = "complete"

    job = ReelsJob(
        job_id=job_id,
        user_id=current_user.id,
        character_id=character_id,
        config_id=req.config_id,
        tema=req.tema,
        language=req.language,
        status="interactive",
        step_state=step_state,
        platforms=req.platforms or ["instagram"],
    )
    db.add(job)
    await db.commit()

    # Mark tema as used in enhance cache (Phase 999.8-A)
    await _mark_tema_used(db, current_user.id, req.tema)

    return {"job_id": job_id, "step_state": step_state}


@router.get("/{job_id}/step-state", summary="Get interactive job step state")
async def get_step_state(
    job_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(db_session),
):
    """Return full step_state JSON for an interactive job. Tenant-isolated."""
    job = await _get_user_job(job_id, current_user.id, db)
    step_state = job.step_state or {}
    return StepStateResponse(
        job_id=job.job_id,
        current_step=step_state.get("current_step", 0),
        prompt=step_state.get("prompt"),
        images=step_state.get("images"),
        script=step_state.get("script"),
        tts=step_state.get("tts"),
        srt=step_state.get("srt"),
        video=step_state.get("video"),
    )


@router.post("/{job_id}/step/{step_name}", summary="Execute a pipeline step")
async def execute_step(
    job_id: str,
    step_name: str,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(db_session),
):
    """Execute a specific pipeline step. Runs in background for heavy steps."""
    from src.database.session import get_session_factory
    from src.reels_pipeline.main import ReelsPipeline

    if step_name not in STEP_ORDER:
        raise HTTPException(status_code=400, detail=f"Invalid step: {step_name}")

    job = await _get_user_job(job_id, current_user.id, db)
    step_state = dict(job.step_state or _init_step_state(job.tema))

    if step_name == "prompt":
        # Prompt step: lightweight, no background task needed
        # Run step_prompt to set up job directory
        config_override = {}
        if job.config_id:
            cfg_result = await db.execute(
                select(ReelsConfig).where(
                    ReelsConfig.id == job.config_id,
                    ReelsConfig.user_id == current_user.id,
                )
            )
            cfg = cfg_result.scalar_one_or_none()
            if cfg:
                config_override = {"target_duration": cfg.target_duration}

        pipeline = ReelsPipeline(config_override=config_override)
        prompt_result = await pipeline.run_step_prompt(
            tema=job.tema,
            character_id=job.character_id,
        )
        step_state["prompt"]["job_dir"] = prompt_result.get("job_dir", "")
        step_state["prompt"]["text"] = job.tema
        step_state["prompt"]["status"] = "complete"
        job.step_state = step_state
        flag_modified(job, "step_state")
        await db.commit()
        return {"step": "prompt", "status": "complete", "step_state": step_state}

    # Heavy steps: run in background
    config_override = {}
    if job.config_id:
        cfg_result = await db.execute(
            select(ReelsConfig).where(
                ReelsConfig.id == job.config_id,
                ReelsConfig.user_id == current_user.id,
            )
        )
        cfg = cfg_result.scalar_one_or_none()
        if cfg:
            config_override = {
                "image_count": cfg.image_count,
                "image_style": cfg.image_style,
                "tone": cfg.tone,
                "target_duration": cfg.target_duration,
                "tts_provider": cfg.tts_provider,
                "tts_voice": cfg.tts_voice,
                "tts_speed": cfg.tts_speed,
                "transcription_provider": cfg.transcription_provider,
                "image_duration": cfg.image_duration,
                "transition_type": cfg.transition_type,
                "transition_duration": cfg.transition_duration,
                "subtitle_font_size": cfg.subtitle_font_size,
                "subtitle_color": cfg.subtitle_color,
                "video_model": cfg.video_model,
            }

    # Merge per-job overrides from step_state (e.g. image_count set at creation)
    job_config = step_state.get("config", {})
    for key in ("image_count",):
        if key in job_config and key not in config_override:
            config_override[key] = job_config[key]

    # Mark step as generating
    step_data = step_state.get(step_name, {})
    step_data["status"] = "generating"
    step_state[step_name] = step_data
    job.step_state = step_state
    flag_modified(job, "step_state")
    await db.commit()

    session_factory = get_session_factory()
    background_tasks.add_task(
        _execute_step_task, job_id, step_name, config_override, session_factory
    )

    return {"step": step_name, "status": "generating"}


@router.post("/{job_id}/approve/{step_name}", summary="Approve a step and advance")
async def approve_step(
    job_id: str,
    step_name: str,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(db_session),
):
    """Mark a step as approved and advance current_step to the next index.

    Per D-02: only advances forward.
    """
    if step_name not in STEP_ORDER:
        raise HTTPException(status_code=400, detail=f"Invalid step: {step_name}")

    job = await _get_user_job(job_id, current_user.id, db)
    step_state = dict(job.step_state or {})

    step_idx = STEP_ORDER.index(step_name)
    step_data = step_state.get(step_name, {})

    # Idempotent: if already approved, return without re-triggering next step
    if step_data.get("approved"):
        return StepApproveResponse(
            step=step_name,
            approved=True,
            current_step=step_state.get("current_step", 0),
        )

    step_data["approved"] = True
    step_state[step_name] = step_data

    # Advance current_step to next (only forward)
    next_step = step_idx + 1
    if next_step > step_state.get("current_step", 0):
        step_state["current_step"] = next_step

    job.step_state = step_state
    flag_modified(job, "step_state")

    # If all steps approved, mark job complete
    if next_step >= len(STEP_ORDER):
        job.status = "complete"

    await db.commit()

    # Auto-trigger next step execution (eliminates frontend race condition)
    if next_step < len(STEP_ORDER):
        next_step_name = STEP_ORDER[next_step]
        config_override = {}
        if job.config_id:
            cfg_result = await db.execute(
                select(ReelsConfig).where(
                    ReelsConfig.id == job.config_id,
                    ReelsConfig.user_id == current_user.id,
                )
            )
            cfg = cfg_result.scalar_one_or_none()
            if cfg:
                config_override = {
                    "target_duration": cfg.target_duration,
                    "tone": cfg.tone,
                    "niche": cfg.niche,
                    "cta_default": cfg.cta_default,
                }
        # Merge per-job overrides from step_state
        job_config = step_state.get("config", {})
        for key in ("image_count",):
            if key in job_config and key not in config_override:
                config_override[key] = job_config[key]
        from src.database.session import get_session_factory
        session_factory = get_session_factory()
        background_tasks.add_task(
            _execute_step_task, job.job_id, next_step_name, config_override, session_factory
        )

    return StepApproveResponse(
        step=step_name,
        approved=True,
        current_step=step_state["current_step"],
    )


@router.post("/{job_id}/regenerate/{step_name}", summary="Regenerate a step and clear downstream")
async def regenerate_step(
    job_id: str,
    step_name: str,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(db_session),
):
    """Re-run a step and clear all downstream step artifacts.

    Per D-02 / Research Pitfall 4: marks downstream steps as unapproved and clears artifacts.
    """
    from src.database.session import get_session_factory

    if step_name not in STEP_ORDER:
        raise HTTPException(status_code=400, detail=f"Invalid step: {step_name}")

    job = await _get_user_job(job_id, current_user.id, db)
    step_state = dict(job.step_state or {})

    step_idx = STEP_ORDER.index(step_name)

    # Clear downstream steps (step_name+1 through video)
    for downstream_name in STEP_ORDER[step_idx + 1:]:
        ds = step_state.get(downstream_name, {})
        ds["approved"] = False
        # Clear artifact fields
        for key in ["paths", "path", "json", "duration", "status", "error"]:
            ds.pop(key, None)
        step_state[downstream_name] = ds

    # Reset current_step to this step's index
    step_state["current_step"] = step_idx

    # Clear current step approval
    current_data = step_state.get(step_name, {})
    current_data["approved"] = False
    step_state[step_name] = current_data

    job.step_state = step_state
    flag_modified(job, "step_state")
    await db.commit()

    # Trigger step execution (same as POST /step/{step_name})
    config_override = {}
    if job.config_id:
        cfg_result = await db.execute(
            select(ReelsConfig).where(
                ReelsConfig.id == job.config_id,
                ReelsConfig.user_id == current_user.id,
            )
        )
        cfg = cfg_result.scalar_one_or_none()
        if cfg:
            config_override = {
                "image_count": cfg.image_count,
                "image_style": cfg.image_style,
                "tone": cfg.tone,
                "target_duration": cfg.target_duration,
                "tts_provider": cfg.tts_provider,
                "tts_voice": cfg.tts_voice,
                "tts_speed": cfg.tts_speed,
                "transcription_provider": cfg.transcription_provider,
            }

    # Merge per-job overrides from step_state
    job_config = step_state.get("config", {})
    for key in ("image_count",):
        if key in job_config and key not in config_override:
            config_override[key] = job_config[key]

    session_factory = get_session_factory()
    background_tasks.add_task(
        _execute_step_task, job_id, step_name, config_override, session_factory
    )

    return {"step": step_name, "status": "regenerating", "cleared_downstream": STEP_ORDER[step_idx + 1:]}


@router.put("/{job_id}/edit/{step_name}", summary="Edit step artifacts inline")
async def edit_step(
    job_id: str,
    step_name: str,
    req: StepEditRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(db_session),
):
    """Update editable step artifacts inline.

    Per D-03: prompt, script, and srt are editable. Other steps return 400.
    """
    editable_steps = {"prompt", "script", "srt"}
    if step_name not in editable_steps:
        raise HTTPException(
            status_code=400,
            detail=f"Step '{step_name}' is not editable. Editable steps: {', '.join(editable_steps)}",
        )

    job = await _get_user_job(job_id, current_user.id, db)
    step_state = dict(job.step_state or {})

    if step_name == "prompt":
        if req.text is None:
            raise HTTPException(status_code=400, detail="'text' field required for prompt edit")
        step_state["prompt"]["text"] = req.text

    elif step_name == "script":
        if req.script_json is None:
            raise HTTPException(status_code=400, detail="'script_json' field required for script edit")
        # Rebuild narracao_completa from edited cenas
        cenas = req.script_json.get("cenas", [])
        if cenas:
            req.script_json["narracao_completa"] = " ".join(
                c.get("narracao", "") for c in cenas if c.get("narracao")
            )
        step_state["script"]["json"] = req.script_json
        job.script_json = req.script_json

    elif step_name == "srt":
        if req.srt_entries is None:
            raise HTTPException(status_code=400, detail="'srt_entries' field required for srt edit")
        # Reconstruct SRT file from entries
        srt_path = step_state.get("srt", {}).get("path", "")
        if srt_path:
            srt_content = ""
            for entry in req.srt_entries:
                idx = entry.get("index", 0)
                start = entry.get("start", "00:00:00,000")
                end = entry.get("end", "00:00:00,000")
                text = entry.get("text", "")
                srt_content += f"{idx}\n{start} --> {end}\n{text}\n\n"
            with open(srt_path, "w", encoding="utf-8") as f:
                f.write(srt_content.strip())
            step_state["srt"]["entries"] = req.srt_entries

    job.step_state = step_state
    flag_modified(job, "step_state")
    await db.commit()

    return {"step": step_name, "status": "edited", "step_state": step_state}


@router.post("/{job_id}/regenerate-image/{scene_index}", summary="Regenerate a single scene image")
async def regenerate_single_image(
    job_id: str,
    scene_index: int,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(db_session),
    prompt: str | None = None,
):
    """Force-regenerate a single scene image (bypass cache). Runs in background.

    Optional prompt query param overrides the scene description for this generation.
    """
    from src.database.session import get_session_factory

    job = await _get_user_job(job_id, current_user.id, db)
    step_state = dict(job.step_state or {})
    images_data = step_state.get("images", {})
    paths = images_data.get("paths", [])

    if scene_index < 0 or scene_index >= len(paths):
        raise HTTPException(status_code=400, detail=f"Invalid scene index: {scene_index}")

    # Mark this image as generating so frontend can poll
    reuse_info = dict(images_data.get("reuse_info", {}))
    reuse_info[str(scene_index)] = {"reused": False, "generating": True}
    images_data["reuse_info"] = reuse_info
    step_state["images"] = images_data
    job.step_state = step_state
    flag_modified(job, "step_state")
    await db.commit()

    session_factory = get_session_factory()
    background_tasks.add_task(
        _regenerate_single_image_task, job_id, scene_index, session_factory, prompt
    )

    return {"scene_index": scene_index, "status": "generating"}


async def _regenerate_single_image_task(
    job_id: str,
    scene_index: int,
    session_factory,
    custom_prompt: str | None = None,
):
    """Background task: regenerate a single scene image via Gemini, register as new asset."""
    from src.reels_pipeline.image_gen import generate_reel_images_per_cena

    async with session_factory() as session:
        try:
            result = await session.execute(
                select(ReelsJob).where(ReelsJob.job_id == job_id)
            )
            job = result.scalar_one_or_none()
            if not job:
                return

            step_state = dict(job.step_state or {})
            job_dir = step_state.get("prompt", {}).get("job_dir", "")
            images_dir = os.path.join(job_dir, "images") if job_dir else ""
            script_json = step_state.get("script", {}).get("json", {})
            cenas = script_json.get("cenas", [])

            if scene_index >= len(cenas):
                logger.error("Regenerate image: scene_index %d >= cenas count %d", scene_index, len(cenas))
                return

            # Generate single cena image — use custom prompt if provided
            single_cena = dict(cenas[scene_index])
            if custom_prompt:
                single_cena["legenda_overlay"] = custom_prompt
            new_paths = await generate_reel_images_per_cena(
                cenas=[single_cena],
                character_id=job.character_id,
                output_dir=images_dir,
            )

            if new_paths:
                import shutil
                target_path = os.path.join(images_dir, f"cena_{scene_index:02d}.jpg")
                if new_paths[0] != target_path and os.path.isfile(new_paths[0]):
                    shutil.copy2(new_paths[0], target_path)

                # Update paths in step_state
                images_data = step_state.get("images", {})
                paths = list(images_data.get("paths", []))
                if scene_index < len(paths):
                    paths[scene_index] = target_path
                images_data["paths"] = paths

                # Update reuse_info — clear generating flag, add version for cache busting
                import time
                reuse_info = images_data.get("reuse_info", {})
                reuse_info[str(scene_index)] = {"reused": False, "generating": False, "version": int(time.time())}
                images_data["reuse_info"] = reuse_info

                step_state["images"] = images_data
                job.step_state = step_state
                flag_modified(job, "step_state")

                # Register as new asset
                try:
                    from src.reels_pipeline.asset_registry import register_asset, generate_embedding
                    desc = f"{single_cena.get('legenda_overlay', '')} {single_cena.get('narracao', '')}".strip()
                    if desc:
                        emb = await generate_embedding(desc)
                        await register_asset(
                            user_id=job.user_id,
                            character_id=job.character_id,
                            asset_type="image",
                            description=desc,
                            file_path=target_path,
                            embedding=emb,
                            model_used="gemini",
                        )
                except Exception as reg_err:
                    logger.warning("Asset registration failed for regenerated image %d: %s", scene_index, reg_err)

                await session.commit()
                logger.info("Regenerated image %d for job %s", scene_index, job_id)

        except Exception as e:
            logger.error("Regenerate image %d for job %s failed: %s", scene_index, job_id, e)
            # Clear generating flag on failure
            try:
                result2 = await session.execute(
                    select(ReelsJob).where(ReelsJob.job_id == job_id)
                )
                job2 = result2.scalar_one_or_none()
                if job2:
                    ss = dict(job2.step_state or {})
                    ri = ss.get("images", {}).get("reuse_info", {})
                    if str(scene_index) in ri:
                        ri[str(scene_index)]["generating"] = False
                        ss["images"]["reuse_info"] = ri
                        job2.step_state = ss
                        flag_modified(job2, "step_state")
                        await session.commit()
            except Exception:
                pass


@router.post("/{job_id}/regenerate-scene-video/{scene_index}", summary="Regenerate a single scene video")
async def regenerate_scene_video(
    job_id: str,
    scene_index: int,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(db_session),
    prompt: str | None = None,
):
    """Force-regenerate a single scene video (no status restriction, allows re-doing reused scenes).

    Unlike retry-scene, this works on scenes in any status including 'success'.
    """
    from src.database.session import get_session_factory

    job = await _get_user_job(job_id, current_user.id, db)
    step_state = dict(job.step_state or {})
    video_data = step_state.get("video", {})
    scenes = video_data.get("scenes", [])

    if scene_index < 0 or scene_index >= len(scenes):
        raise HTTPException(status_code=400, detail=f"Invalid scene index: {scene_index}")

    # Mark scene as generating
    scene = scenes[scene_index]
    scene["status"] = "generating"
    scene["error"] = None
    scene.pop("reused", None)
    scene.pop("source_asset_id", None)
    scenes[scene_index] = scene
    video_data["scenes"] = scenes
    step_state["video"] = video_data
    job.step_state = step_state
    flag_modified(job, "step_state")
    await db.commit()

    config_override = {}
    if job.config_id:
        cfg_result = await db.execute(
            select(ReelsConfig).where(
                ReelsConfig.id == job.config_id,
                ReelsConfig.user_id == current_user.id,
            )
        )
        cfg = cfg_result.scalar_one_or_none()
        if cfg:
            config_override = {"video_model": cfg.video_model}

    session_factory = get_session_factory()
    background_tasks.add_task(
        _retry_scene_task, job_id, scene_index, prompt, config_override, session_factory
    )

    return {"scene_index": scene_index, "status": "generating"}


@router.post("/{job_id}/retry-scene/{scene_index}", summary="Retry a single failed scene")
async def retry_scene(
    job_id: str,
    scene_index: int,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(db_session),
    prompt: str | None = None,
):
    """Re-run Kie.ai for a single scene. Accepts optional custom prompt in query param.

    If all scenes have clips after retry, auto-reassembles the final video.
    """
    from src.database.session import get_session_factory

    job = await _get_user_job(job_id, current_user.id, db)
    step_state = dict(job.step_state or {})
    video_data = step_state.get("video", {})
    scenes = video_data.get("scenes", [])

    if scene_index < 0 or scene_index >= len(scenes):
        raise HTTPException(status_code=400, detail=f"Invalid scene index: {scene_index}")

    scene = scenes[scene_index]
    if scene.get("status") not in ("failed", "static_fallback"):
        raise HTTPException(status_code=400, detail="Scene is not in a retryable state")

    # Mark scene as generating
    scene["status"] = "generating"
    scene["error"] = None
    scenes[scene_index] = scene
    video_data["scenes"] = scenes
    step_state["video"] = video_data
    job.step_state = step_state
    flag_modified(job, "step_state")
    await db.commit()

    # Build config_override
    config_override = {}
    if job.config_id:
        cfg_result = await db.execute(
            select(ReelsConfig).where(
                ReelsConfig.id == job.config_id,
                ReelsConfig.user_id == current_user.id,
            )
        )
        cfg = cfg_result.scalar_one_or_none()
        if cfg:
            config_override = {"video_model": cfg.video_model}

    session_factory = get_session_factory()
    background_tasks.add_task(
        _retry_scene_task, job_id, scene_index, prompt, config_override, session_factory
    )

    return {"scene_index": scene_index, "status": "generating"}


async def _retry_scene_task(
    job_id: str,
    scene_index: int,
    custom_prompt: str | None,
    config_override: dict,
    session_factory,
):
    """Background task: retry a single scene via Kie.ai."""
    from src.reels_pipeline.main import ReelsPipeline
    from src.reels_pipeline.video_builder import concat_clips_with_audio

    async with session_factory() as session:
        try:
            result = await session.execute(
                select(ReelsJob).where(ReelsJob.job_id == job_id)
            )
            job = result.scalar_one_or_none()
            if not job:
                return

            step_state = dict(job.step_state or {})
            video_data = step_state.get("video", {})
            scenes = video_data.get("scenes", [])
            if scene_index >= len(scenes):
                return

            scene = scenes[scene_index]
            job_dir = step_state.get("prompt", {}).get("job_dir", "")

            # Determine prompt and image URL
            retry_prompt = custom_prompt or scene.get("prompt", "")
            # Use latest image from images.paths (may have been regenerated)
            images_paths = step_state.get("images", {}).get("paths", [])
            if scene_index < len(images_paths) and os.path.isfile(images_paths[scene_index]):
                img_path = images_paths[scene_index]
            else:
                img_path = scene.get("img_path", "")
            duration = scene.get("duration", 6)

            # Upload image to GCS for retry
            from src.video_gen.gcs_uploader import GCSUploader
            gcs = GCSUploader()
            gcs_key = f"reels/{os.path.basename(job_dir)}/scene_{scene_index}_retry.jpg"
            image_url = gcs.upload_image(img_path, gcs_key)

            pipeline = ReelsPipeline(config_override=config_override)
            retry_result = await pipeline.retry_single_scene(
                job_dir=job_dir,
                scene_index=scene_index,
                image_path=img_path,
                image_url=image_url,
                prompt=retry_prompt,
                duration=duration,
            )

            # Update scene in step_state
            scenes[scene_index] = {**scene, **retry_result}
            video_data["scenes"] = scenes
            step_state["video"] = video_data

            # Check if all scenes now have clips — auto-reassemble
            all_have_clips = all(
                s.get("status") in ("success", "static_fallback")
                for s in scenes
            )
            if all_have_clips:
                clips_dir = os.path.join(job_dir, "clips")
                clip_paths = []
                for s in scenes:
                    cp = s.get("clip_path", "")
                    if cp and os.path.isfile(cp):
                        clip_paths.append(cp)
                    else:
                        # Fallback to expected path
                        expected = os.path.join(clips_dir, f"clip_{s['index']:02d}.mp4")
                        if os.path.isfile(expected):
                            clip_paths.append(expected)

                if clip_paths:
                    audio_path = step_state.get("tts", {}).get("path", "")
                    srt_path = step_state.get("srt", {}).get("path", "")
                    video_path = os.path.join(job_dir, "final.mp4")
                    concat_clips_with_audio(
                        clip_paths=clip_paths,
                        audio_path=audio_path,
                        srt_path=srt_path,
                        output_path=video_path,
                        transition_duration=0.3,
                    )
                    video_data["path"] = video_path
                    job.video_path = video_path
                    logger.info(f"Auto-reassembled video after retry: {video_path}")

            job.step_state = step_state
            flag_modified(job, "step_state")
            await session.commit()

        except Exception as e:
            logger.error(f"Retry scene {scene_index} for job {job_id} failed: {e}")
            try:
                step_state = dict(job.step_state or {})
                scenes = step_state.get("video", {}).get("scenes", [])
                if scene_index < len(scenes):
                    scenes[scene_index]["status"] = "failed"
                    scenes[scene_index]["error"] = str(e)[:300]
                    step_state["video"]["scenes"] = scenes
                    job.step_state = step_state
                    flag_modified(job, "step_state")
                    await session.commit()
            except Exception:
                pass


@router.post("/{job_id}/reassemble-video", summary="Reassemble final video from existing clips")
async def reassemble_video(
    job_id: str,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(db_session),
):
    """Reassemble the final video from existing scene clips WITHOUT re-calling Kie.ai.

    Use this after editing/regenerating individual scenes to rebuild the final video.
    """
    from src.database.session import get_session_factory

    job = await _get_user_job(job_id, current_user.id, db)
    step_state = dict(job.step_state or {})
    video_data = step_state.get("video", {})
    scenes = video_data.get("scenes", [])

    if not scenes:
        raise HTTPException(status_code=400, detail="No scene clips available to reassemble")

    clips_with_success = [s for s in scenes if s.get("status") in ("success", "static_fallback")]
    if not clips_with_success:
        raise HTTPException(status_code=400, detail="No completed scene clips to assemble")

    # Mark as reassembling
    video_data["status"] = "generating"
    video_data.pop("path", None)
    step_state["video"] = video_data
    job.step_state = step_state
    flag_modified(job, "step_state")
    await db.commit()

    session_factory = get_session_factory()
    background_tasks.add_task(
        _reassemble_video_task, job_id, session_factory
    )

    return {"status": "reassembling"}


async def _reassemble_video_task(job_id: str, session_factory):
    """Background task: reassemble final video from existing clips."""
    from src.reels_pipeline.video_builder import concat_clips_with_audio

    async with session_factory() as session:
        try:
            result = await session.execute(
                select(ReelsJob).where(ReelsJob.job_id == job_id)
            )
            job = result.scalar_one_or_none()
            if not job:
                return

            step_state = dict(job.step_state or {})
            video_data = step_state.get("video", {})
            scenes = video_data.get("scenes", [])
            job_dir = step_state.get("prompt", {}).get("job_dir", "")
            clips_dir = os.path.join(job_dir, "clips")

            clip_paths = []
            for s in scenes:
                cp = s.get("clip_path", "")
                if cp and os.path.isfile(cp):
                    clip_paths.append(cp)
                else:
                    expected = os.path.join(clips_dir, f"clip_{s['index']:02d}.mp4")
                    if os.path.isfile(expected):
                        clip_paths.append(expected)

            if not clip_paths:
                video_data["status"] = "error"
                video_data["error"] = "No clip files found on disk"
                step_state["video"] = video_data
                job.step_state = step_state
                flag_modified(job, "step_state")
                await session.commit()
                return

            audio_path = step_state.get("tts", {}).get("path", "")
            srt_path = step_state.get("srt", {}).get("path", "")
            script_json = step_state.get("script", {}).get("json", {})
            video_path = os.path.join(job_dir, "final.mp4")

            concat_clips_with_audio(
                clip_paths=clip_paths,
                audio_path=audio_path,
                srt_path=srt_path,
                output_path=video_path,
                transition_duration=0.3,
                script_json=script_json,
            )

            video_data["path"] = video_path
            video_data["status"] = "complete"
            step_state["video"] = video_data
            job.step_state = step_state
            job.video_path = video_path
            flag_modified(job, "step_state")

            # Re-generate platform metadata
            platforms = job.platforms or ["instagram"]
            if platforms:
                try:
                    from src.reels_pipeline.platform_metadata import generate_platform_metadata
                    platform_outputs = await generate_platform_metadata(
                        script_json=script_json,
                        platforms=platforms,
                        video_url=job.video_url,
                    )
                    job.platform_outputs = platform_outputs
                    flag_modified(job, "platform_outputs")
                except Exception as pm_err:
                    logger.warning("Platform metadata failed on reassemble: %s", pm_err)

            await session.commit()
            logger.info("Reassembled video for job %s: %s", job_id, video_path)

        except Exception as e:
            logger.error("Reassemble video for job %s failed: %s", job_id, e)
            try:
                step_state = dict(job.step_state or {})
                step_state.setdefault("video", {})["status"] = "error"
                step_state["video"]["error"] = str(e)[:300]
                job.step_state = step_state
                flag_modified(job, "step_state")
                await session.commit()
            except Exception:
                pass


@router.get("/{job_id}/file/{filename:path}", summary="Serve artifact files for preview")
async def serve_artifact_file(
    job_id: str,
    filename: str,
    db: AsyncSession = Depends(db_session),
):
    """Serve artifact files (images, audio, video) via FileResponse.

    No auth required — <img> tags can't send Authorization headers.
    Security: job_id is opaque UUID + path restricted to output/reels.
    """
    result = await db.execute(
        select(ReelsJob).where(ReelsJob.job_id == job_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    step_state = job.step_state or {}

    job_dir = step_state.get("prompt", {}).get("job_dir", "")
    if not job_dir:
        raise HTTPException(status_code=400, detail="Job directory not initialized")

    # If filename is an absolute path or starts with the output dir, use directly
    if os.path.isabs(filename) or filename.startswith("output/"):
        resolved = os.path.realpath(filename)
    else:
        resolved = os.path.realpath(os.path.join(job_dir, filename))

    # Security: ensure the resolved path is under job_dir or output/reels
    job_dir_real = os.path.realpath(job_dir)
    output_real = os.path.realpath("output/reels")
    if not (resolved.startswith(job_dir_real) or resolved.startswith(output_real)):
        raise HTTPException(status_code=403, detail="Access denied")

    if not os.path.isfile(resolved):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(resolved)


# ── Existing endpoints ─────────────────────────────────────────────────────

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
            platforms=j.platforms,
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
            video_model=c.video_model,
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
            "video_model",
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
        video_model=config.video_model,
    )


@router.get("/config/transitions", summary="List available video transitions")
async def list_transitions():
    """Return available FFmpeg xfade transition types for config panel."""
    from src.reels_pipeline.config import REELS_AVAILABLE_TRANSITIONS
    return {"transitions": REELS_AVAILABLE_TRANSITIONS}


@router.get("/{job_id}/platforms", summary="Get platform-specific metadata")
async def get_platform_outputs(
    job_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(db_session),
):
    """Return platform_outputs for a reel job. Tenant-isolated."""
    job = await _get_user_job(job_id, current_user.id, db)
    return {
        "job_id": job.job_id,
        "platforms": job.platforms or ["instagram"],
        "platform_outputs": job.platform_outputs or {},
    }


@router.get("/config/presets", summary="List available config presets")
async def list_presets():
    """Return static preset configurations. Per D-04: pre-configured, editable."""
    return {"presets": PRESETS}


# ── Enhance Theme (Phase 999.8-A) ─────────────────────────────────────────

ENHANCE_REELS_SYSTEM_PROMPT = """Voce e um estrategista de conteudo informativo para Instagram Reels no Brasil.
Seu objetivo: criar sugestoes de video que entreguem VALOR REAL ao espectador — dicas praticas, informacoes uteis, hacks aplicaveis no dia a dia.

## REGRAS INVIOLAVEIS

1. FOCO ABSOLUTO: Toda sugestao DEVE ser sobre o SUB-TEMA dentro do NICHO informado. Nao desvie. Nao generalize. Nao misture sub-temas.
2. CONTEUDO SOLIDO: Cada topico DEVE ser uma dica pratica, informacao util ou insight aplicavel IMEDIATAMENTE pelo espectador. Sem frases vagas como "melhore sua vida" ou "tenha disciplina".
3. GANCHO INFORMATIVO: O titulo deve criar curiosidade sobre informacao util — use numeros, "como fazer", contrastes ou revelacoes. Exemplos: "3 erros que...", "O metodo que...", "Por que voce nao deveria...".
4. TOPICOS SAO CENAS: Cada topico vira uma cena do video com narracao propria. Escreva como se fosse o roteiro resumido daquela cena — concreto, especifico, com a dica completa.
5. PT-BR NATURAL: Tom coloquial brasileiro, como se estivesse explicando para um amigo.

## FORMATO DE SAIDA

Retorne APENAS um JSON array valido. Cada objeto:
- "title": gancho informativo (max 80 chars) — cria curiosidade sobre algo util
- "outline": 2-3 frases descrevendo o angulo do video, publico-alvo e por que o espectador vai se beneficiar
- "topics": array de 3-5 dicas concretas. Cada uma DEVE conter: a dica em si + por que funciona ou como aplicar (20-50 palavras cada)

## EXEMPLOS

Niche: "Financas Pessoais" | Sub-theme: "como sair das dividas"
[
  {
    "title": "4 passos para zerar suas dividas esse ano",
    "outline": "Guia pratico com metodo bola de neve adaptado para a realidade brasileira. Para quem ganha ate 5 mil e quer sair do vermelho sem cortar tudo.",
    "topics": [
      "Liste TODAS as dividas em uma planilha com valor, juros e parcelas — voce precisa enxergar o monstro inteiro antes de atacar",
      "Priorize a divida com maior juros (geralmente cartao de credito a 15% ao mes) — renegocie direto com o banco, nunca com intermediarios",
      "Crie uma reserva minima de R$500 antes de pagar dividas extras — sem colchao financeiro voce volta a se endividar no primeiro imprevisto",
      "Use a regra 50-30-20 adaptada: 50% essenciais, 30% quitar dividas, 20% fundo de emergencia ate ter 3 meses de gastos guardados"
    ]
  }
]

Niche: "Desenvolvimento Pessoal" | Sub-theme: "foco"
[
  {
    "title": "3 tecnicas de foco que neurocientistas recomendam",
    "outline": "Video baseado em estudos de neurociencia sobre como o cerebro mantem atencao. Para quem se distrai facilmente e quer produzir mais em menos tempo.",
    "topics": [
      "Tecnica Pomodoro invertida: trabalhe 25min e descanse 5, mas no descanso faca algo fisico (levantar, alongar) — ativa o cortex pre-frontal e renova o foco",
      "Regra dos 2 minutos: se uma tarefa leva menos de 2 minutos, faca agora — tarefas pendentes ocupam espaco mental e drenam concentracao",
      "Ambiente de foco: tire notificacoes, coloque o celular em outro comodo e use fones — o cerebro leva 23 minutos para recuperar foco apos uma interrupcao"
    ]
  }
]"""


@router.post("/enhance-theme", summary="AI structured topic suggestions for reels (cached)")
async def enhance_theme(
    niche_id: str = Query(..., description="Niche identifier"),
    sub_theme: str = Query("", description="Optional sub-theme"),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(db_session),
):
    """Generate structured AI topic suggestions for a niche, with persistent cache.

    Returns all suggestions for the niche+sub-theme, accumulating across calls.
    New suggestions are appended to the existing list (not replaced).
    """
    from datetime import datetime, timezone
    from src.database.models import EnhanceThemeCache
    from src.llm_client import _get_client, _extract_text

    sub = sub_theme.strip() or ""

    # Load existing cache row (persistent, no TTL — accumulates over time)
    result = await db.execute(
        select(EnhanceThemeCache).where(
            EnhanceThemeCache.user_id == current_user.id,
            EnhanceThemeCache.niche_id == niche_id,
            EnhanceThemeCache.sub_theme == sub,
        )
    )
    cached = result.scalar_one_or_none()

    existing = cached.suggestions if cached else []
    used_titles = set(cached.used_suggestions or []) if cached else set()

    # Generate new batch via Gemini
    existing_titles = [s["title"] for s in existing if isinstance(s, dict)] if existing else []
    avoid_clause = ""
    if existing_titles:
        avoid_clause = f"\n\nAVOID repeating these already-generated topics:\n" + "\n".join(f"- {t}" for t in existing_titles[-12:])

    prompt = (
        f"NICHO: {niche_id}\n"
        f"SUB-TEMA: {sub or niche_id}\n"
        f"\nGere 6 sugestoes de video INFORMATIVO sobre \"{sub or niche_id}\"."
        f"\nCada sugestao deve entregar dicas praticas, informacoes uteis e conteudo aplicavel no dia a dia."
        f"\nOs topicos devem ser dicas completas com explicacao — nao apenas titulos."
        f"\nFoque 100% no sub-tema \"{sub or niche_id}\" dentro do nicho \"{niche_id}\"."
        f"{avoid_clause}"
    )

    try:
        client = _get_client()
        resp = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.5-flash",
            contents=[
                {"role": "user", "parts": [{"text": ENHANCE_REELS_SYSTEM_PROMPT}]},
                {"role": "user", "parts": [{"text": prompt}]},
            ],
        )
        text = _extract_text(resp)
        clean = text.strip().removeprefix("```json").removesuffix("```").strip()
        new_suggestions = json.loads(clean)

        if isinstance(new_suggestions, dict):
            new_suggestions = new_suggestions.get("suggestions", [])
        if not isinstance(new_suggestions, list):
            new_suggestions = []

        # Validate structure
        validated = []
        for s in new_suggestions:
            if isinstance(s, dict) and "title" in s:
                validated.append({
                    "title": str(s["title"])[:100],
                    "outline": str(s.get("outline", ""))[:500],
                    "topics": [str(t)[:200] for t in s.get("topics", [])][:7],
                })
            elif isinstance(s, str):
                # Backward compat: plain string → wrap in structure
                validated.append({"title": s[:100], "outline": "", "topics": []})
        new_suggestions = validated[:6]

    except Exception as e:
        logger.error("Enhance theme Gemini error: %s", e)
        raise HTTPException(status_code=502, detail=f"Erro ao gerar sugestoes: {e}")

    if not new_suggestions:
        raise HTTPException(status_code=502, detail="Gemini nao gerou sugestoes validas")

    # Append new suggestions to existing (accumulate)
    all_suggestions = list(existing) + new_suggestions

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if cached:
        cached.suggestions = all_suggestions
        cached.created_at = now
        flag_modified(cached, "suggestions")
    else:
        cached = EnhanceThemeCache(
            user_id=current_user.id,
            niche_id=niche_id,
            sub_theme=sub,
            suggestions=all_suggestions,
            used_suggestions=list(used_titles),
        )
        db.add(cached)
    await db.commit()

    # Return all available (not used)
    available = [s for s in all_suggestions if isinstance(s, dict) and s.get("title") not in used_titles]
    return {"suggestions": available, "cached": len(existing) > 0, "total": len(all_suggestions)}


@router.get("/enhance-theme/suggestions", summary="Load cached suggestions without generating")
async def get_cached_suggestions(
    niche_id: str = Query(..., description="Niche identifier"),
    sub_theme: str = Query("", description="Optional sub-theme"),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(db_session),
):
    """Return existing cached suggestions for a niche+sub-theme (no Gemini call)."""
    from src.database.models import EnhanceThemeCache

    sub = sub_theme.strip() or ""
    result = await db.execute(
        select(EnhanceThemeCache).where(
            EnhanceThemeCache.user_id == current_user.id,
            EnhanceThemeCache.niche_id == niche_id,
            EnhanceThemeCache.sub_theme == sub,
        )
    )
    cached = result.scalar_one_or_none()
    if not cached:
        return {"suggestions": [], "total": 0}

    used_titles = set(cached.used_suggestions or [])
    available = [s for s in (cached.suggestions or []) if isinstance(s, dict) and s.get("title") not in used_titles]
    return {"suggestions": available, "total": len(cached.suggestions or [])}


@router.delete("/enhance-theme/cache", summary="Clear cached suggestions for a niche+sub-theme")
async def clear_enhance_cache(
    niche_id: str = Query(..., description="Niche identifier"),
    sub_theme: str = Query("", description="Optional sub-theme"),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(db_session),
):
    """Delete cache row so next enhance-theme call regenerates suggestions."""
    from src.database.models import EnhanceThemeCache

    sub = sub_theme.strip() or ""
    result = await db.execute(
        select(EnhanceThemeCache).where(
            EnhanceThemeCache.user_id == current_user.id,
            EnhanceThemeCache.niche_id == niche_id,
            EnhanceThemeCache.sub_theme == sub,
        )
    )
    cached = result.scalar_one_or_none()
    if cached:
        await db.delete(cached)
        await db.commit()
    return {"cleared": True}


@router.get("/config/models", summary="List available Kie.ai video models")
async def list_video_models():
    """Return available video models for reels with label, price, durations, resolution."""
    from src.reels_pipeline.config import REELS_AVAILABLE_MODELS
    return {"models": REELS_AVAILABLE_MODELS}
