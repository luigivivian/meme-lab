"""Reels pipeline API routes — generate, status polling, job listing, config CRUD, interactive step API.

Per D-01: Expose reels pipeline via /reels/* routes.
Per D-02/D-03: Step-based endpoints for interactive pipeline execution.
Per Phase 999.1 pattern: background tasks use get_session_factory() for independent DB sessions.

Phase 999.4/999.5 — Instagram Reels Pipeline
"""

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

            pipeline = ReelsPipeline(config_override=config_override)
            job_dir = step_state.get("prompt", {}).get("job_dir", "")

            if step_name == "images":
                script_json = step_state.get("script", {}).get("json", {})
                logger.info("Images step: script_json keys=%s, has_cenas=%s, n_cenas=%d",
                            list(script_json.keys()) if script_json else "None",
                            bool(script_json.get("cenas")),
                            len(script_json.get("cenas", [])))
                if script_json and script_json.get("cenas"):
                    # v2: per-cena image generation using script context
                    paths = await pipeline.run_step_images_per_cena(
                        script=script_json,
                        character_id=job.character_id,
                        job_dir=job_dir,
                        images_dir=os.path.join(job_dir, "images") if job_dir else "",
                    )
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
                video_path = await pipeline.run_step_video_hailuo(
                    image_paths=image_paths,
                    audio_path=audio_path,
                    srt_path=srt_path,
                    job_dir=job_dir,
                    script=script_json,
                )
                step_data["path"] = video_path
                step_data["status"] = "complete"
                job.video_path = video_path

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

    # Create job in DB
    job = ReelsJob(
        job_id=job_id,
        user_id=current_user.id,
        character_id=character_id,
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
        status="interactive",
        step_state=step_state,
    )
    db.add(job)
    await db.commit()

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
            }

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


@router.get("/{job_id}/file/{filename:path}", summary="Serve artifact files for preview")
async def serve_artifact_file(
    job_id: str,
    filename: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(db_session),
):
    """Serve artifact files (images, audio, video) via FileResponse.

    Per Research Pitfall 3: enables frontend previews.
    Accepts both relative-to-job_dir and absolute paths stored in step_state.
    """
    job = await _get_user_job(job_id, current_user.id, db)
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
