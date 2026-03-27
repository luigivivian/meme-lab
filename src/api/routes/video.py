"""Video generation routes -- Kie.ai Sora 2 image-to-video (Phase 999.1).

Per D-05: Opt-in per content package (no auto-generation).
Per D-06: Background async processing with status polling.
Per D-09: Hard daily cap via VIDEO_DAILY_BUDGET_USD.
"""

import asyncio
import logging
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import (
    VIDEO_ENABLED,
    VIDEO_DURATION,
    VIDEO_COST_PER_SECOND,
    VIDEO_DAILY_BUDGET_USD,
    VIDEO_LEGEND_ENABLED,
    VIDEO_LEGEND_MODE,
    VIDEO_MODEL,
    VIDEO_MODELS,
    KIE_API_KEY,
    GENERATED_VIDEOS_DIR,
)
from src.api.deps import get_current_user, db_session
from src.api.models import (
    VideoGenerateRequest,
    VideoBatchRequest,
    VideoStatusResponse,
    VideoBudgetResponse,
    VideoProgressDetailResponse,
    VideoCreditsResponse,
    LegendRequest,
    LegendBatchRequest,
)
from src.database.models import ContentPackage, Theme

logger = logging.getLogger("clip-flow.api.video")

router = APIRouter(prefix="/generate/video", tags=["Video Generation"])

# Step label mapping: Kie.ai state -> Portuguese UI label (Phase 18)
STEP_LABELS = {
    "waiting": "Na fila...",
    "queuing": "Na fila...",
    "generating": "Gerando...",
    "success": "Concluido",
    "fail": "Falhou",
}


@router.get("/models", summary="List available video generation models")
async def list_video_models():
    """Return available Kie.ai models with pricing and default selection."""
    from config import VIDEO_USD_TO_BRL
    models = []
    for model_id, info in VIDEO_MODELS.items():
        models.append({
            "id": model_id,
            "name": info["name"],
            "resolution": info.get("resolution", "720p"),
            "tier": info.get("tier", "standard"),
            "durations": info.get("durations", [5, 10]),
            "prices_brl": info.get("prices_brl", {}),
            "speed": info.get("speed", 3),
            "notes": info.get("notes", ""),
            "is_default": model_id == VIDEO_MODEL,
        })
    return {"models": models, "default": VIDEO_MODEL, "usd_to_brl": VIDEO_USD_TO_BRL}


@router.get(
    "/credits/summary",
    summary="Get video credits summary",
    response_model=VideoCreditsResponse,
)
async def credits_summary(
    days: int = 30,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
    """Return BRL cost summary for video generation with per-model breakdown.

    Per CRED-03: total spent, per-model breakdown, failed count, daily budget in BRL.
    """
    from src.database.repositories.usage_repo import UsageRepository

    repo = UsageRepository(session)
    data = await repo.get_credits_summary(user_id=current_user.id, days=days)
    return VideoCreditsResponse(**data)


@router.post("/preview-prompt", summary="Preview video prompt without calling Kie.ai (free)")
async def preview_prompt(
    req: VideoGenerateRequest,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
    """Generate and return the motion prompt that would be sent to Kie.ai — no API call, no cost."""
    result = await session.execute(
        select(ContentPackage).where(ContentPackage.id == req.content_package_id)
    )
    pkg = result.scalar_one_or_none()
    if not pkg:
        raise HTTPException(status_code=404, detail="Content package not found")

    meta = pkg.image_metadata if isinstance(pkg.image_metadata, dict) else {}
    theme_key = meta.get("theme_key") or meta.get("situacao_key") or "generico"
    scene = meta.get("scene") or ""
    pose = meta.get("pose") or ""

    if not scene:
        bg = pkg.background_path or pkg.image_path or ""
        if bg:
            scene = Path(bg).stem.replace("_", " ").split("2026")[0].strip()

    if theme_key == "generico" and scene:
        from src.video_gen.video_prompt_builder import _get_templates
        for key in _get_templates().keys():
            if key in scene.lower().replace(" ", "_") or key in scene.lower():
                theme_key = key
                break

    from src.video_gen.video_prompt_builder import VideoPromptBuilder
    try:
        prompt_builder = VideoPromptBuilder()
        if req.custom_prompt:
            prompt = prompt_builder.enhance_user_prompt(req.custom_prompt, theme_key)
        else:
            prompt = prompt_builder.build_motion_prompt(
                theme_key=theme_key, phrase_context=pkg.phrase or "",
                pose=pose, scene=scene,
            )
    except Exception as e:
        logger.error("Preview prompt generation failed: %s", e, exc_info=True)
        prompt = VideoPromptBuilder().get_fallback_prompt(theme_key)

    model_info = VIDEO_MODELS.get(req.model or VIDEO_MODEL, {})
    valid_durations = model_info.get("durations", [5, 10])
    snapped_duration = min(valid_durations, key=lambda d: abs(d - req.duration))

    return {
        "prompt": prompt,
        "prompt_length": len(prompt),
        "theme_key": theme_key,
        "scene": scene,
        "pose": pose,
        "model": req.model or VIDEO_MODEL,
        "duration": snapped_duration,
        "valid": len(prompt) >= 20,
    }


# -- Helper functions ---------------------------------------------------------


def _check_video_enabled():
    """Raise HTTPException if video generation is not enabled/configured."""
    if not VIDEO_ENABLED:
        raise HTTPException(
            status_code=400,
            detail="Video generation is disabled. Set VIDEO_ENABLED=true in .env",
        )
    if not KIE_API_KEY:
        raise HTTPException(
            status_code=400,
            detail="KIE_API_KEY not configured",
        )


async def _check_budget(
    session: AsyncSession, user_id: int, duration: int,
) -> float:
    """Check daily budget and return estimated cost. Raises 429 if exhausted.

    Per D-09: Hard daily cap via VIDEO_DAILY_BUDGET_USD.
    """
    from src.database.repositories.usage_repo import UsageRepository

    estimated_cost = duration * VIDEO_COST_PER_SECOND
    repo = UsageRepository(session)
    spent_today = await repo.get_daily_cost(user_id, "kie_video")

    if spent_today + estimated_cost > VIDEO_DAILY_BUDGET_USD:
        raise HTTPException(
            status_code=429,
            detail=(
                f"Daily video budget exhausted. "
                f"Spent ${spent_today:.2f} of ${VIDEO_DAILY_BUDGET_USD:.2f}"
            ),
        )
    return estimated_cost


async def _generate_video_task(
    content_package_id: int,
    duration: int,
    character_ids: list[str],
    user_id: int,
    custom_prompt: str = "",
    model: str = "",
):
    """Background task: generate video for a content package.

    Creates its own DB session (cannot reuse request session in background).
    Per D-06: Runs after HTTP response returns.
    """
    from src.database.session import get_session_factory
    from src.database.repositories.usage_repo import UsageRepository
    from src.video_gen.kie_client import KieSora2Client
    from src.video_gen.gcs_uploader import GCSUploader
    from src.video_gen.video_prompt_builder import VideoPromptBuilder

    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            # Load content package
            result = await session.execute(
                select(ContentPackage).where(ContentPackage.id == content_package_id)
            )
            pkg = result.scalar_one_or_none()
            if not pkg:
                logger.error("Video task: ContentPackage %d not found", content_package_id)
                return

            # Resolve theme for video_prompt_notes (per D-03)
            theme_notes = ""
            if pkg.work_order_id:
                from src.database.models import WorkOrder
                wo_result = await session.execute(
                    select(WorkOrder).where(WorkOrder.id == pkg.work_order_id)
                )
                wo = wo_result.scalar_one_or_none()
                if wo:
                    theme_result = await session.execute(
                        select(Theme).where(Theme.key == wo.situacao_key)
                    )
                    theme = theme_result.scalar_one_or_none()
                    if theme and theme.video_prompt_notes:
                        theme_notes = theme.video_prompt_notes

            # ── Extract scene context from metadata, phrase, or filename ──
            meta = pkg.image_metadata if isinstance(pkg.image_metadata, dict) else {}

            theme_key = meta.get("theme_key") or meta.get("situacao_key") or "generico"
            scene = meta.get("scene") or ""
            pose = meta.get("pose") or ""

            # Fallback: derive scene from filename if metadata is empty
            if not scene:
                bg_path_str = pkg.background_path or pkg.image_path or ""
                if bg_path_str:
                    fname = Path(bg_path_str).stem
                    scene = fname.replace("_", " ").split("2026")[0].strip()

            # Infer theme_key from scene if still generic
            if theme_key == "generico" and scene:
                from src.video_gen.video_prompt_builder import _get_templates
                for key in _get_templates().keys():
                    if key in scene.lower().replace(" ", "_") or key in scene.lower():
                        theme_key = key
                        break

            # ── Build motion prompt ──
            prompt_builder = VideoPromptBuilder()
            if custom_prompt:
                motion_prompt = prompt_builder.enhance_user_prompt(custom_prompt, theme_key)
            else:
                motion_prompt = prompt_builder.build_motion_prompt(
                    theme_key=theme_key,
                    phrase_context=pkg.phrase or "",
                    pose=pose,
                    scene=scene,
                    video_prompt_notes=theme_notes,
                )

            # ── Validate prompt before calling paid API ──
            if not motion_prompt or len(motion_prompt) < 20:
                logger.error("Video task %d: prompt too short (%d chars), aborting",
                             content_package_id, len(motion_prompt or ""))
                pkg.video_status = "failed"
                pkg.video_metadata = {"error": "Generated prompt too short"}
                await session.commit()
                return

            if len(motion_prompt) > 5000:
                motion_prompt = motion_prompt[:5000]

            logger.info(
                "Video task %d: model=%s duration=%ds theme=%s scene='%s' prompt='%s'",
                content_package_id, model or "default", duration,
                theme_key, scene[:40], motion_prompt[:80],
            )

            # Upload background image to GCS for public URL (per D-04)
            bg_path = pkg.background_path or pkg.image_path
            if not bg_path or not Path(bg_path).exists():
                logger.error(
                    "Video task: no valid background for package %d (path=%s)",
                    content_package_id, bg_path,
                )
                pkg.video_status = "failed"
                pkg.video_metadata = {"error": f"Background image not found: {bg_path}"}
                await session.commit()
                return

            uploader = GCSUploader()
            # Unique blob name per upload — prevents stale signed URL issues
            import time as _time
            ts = int(_time.time())
            stem = Path(bg_path).stem
            blob_name = f"video-inputs/{stem}_{ts}{Path(bg_path).suffix}"
            signed_url = uploader.upload_image(bg_path, blob_name)

            # Generate video via Kie.ai Sora 2
            client = KieSora2Client()
            gen_result = await client.generate_video(
                image_url=signed_url,
                prompt=motion_prompt,
                duration=duration,
                character_ids=character_ids if character_ids else None,
                output_dir=str(GENERATED_VIDEOS_DIR),
                model=model or None,
            )

            if gen_result:
                # Success
                pkg.video_status = "success"
                pkg.video_path = gen_result.local_path
                pkg.video_source = "kie_sora2"
                pkg.video_prompt_used = gen_result.prompt_used
                pkg.video_task_id = gen_result.task_id
                pkg.video_metadata = {
                    "cost_usd": gen_result.cost_usd,
                    "duration": duration,
                    "model": gen_result.model,
                    "generation_time_ms": gen_result.generation_time_ms,
                }

                # Track cost (per D-09, CRED-01/02: BRL from prices_brl, success-only)
                from config import compute_video_cost_brl
                model_id = model or VIDEO_MODEL
                cost_brl = compute_video_cost_brl(model_id, duration)
                repo = UsageRepository(session)
                await repo.increment(
                    user_id=user_id,
                    service="kie_video",
                    tier=model_id,
                    cost_usd=gen_result.cost_usd,
                    cost_brl=cost_brl,
                    model=model_id,
                )

                logger.info(
                    "Video generated for package %d: task=%s cost=$%.3f R$%.2f",
                    content_package_id, gen_result.task_id, gen_result.cost_usd, cost_brl,
                )
            else:
                # Failure
                pkg.video_status = "failed"
                pkg.video_metadata = {"error": "Video generation returned None"}
                logger.error("Video generation failed for package %d", content_package_id)

            await session.commit()

            # Cleanup GCS blob (non-blocking, best-effort)
            try:
                uploader.delete_blob(blob_name)
            except Exception as cleanup_err:
                logger.warning("GCS cleanup failed for %s: %s", blob_name, cleanup_err)

        except Exception as e:
            logger.error(
                "Video task error for package %d: %s", content_package_id, e,
                exc_info=True,
            )
            try:
                pkg.video_status = "failed"
                pkg.video_metadata = {"error": str(e)}
                await session.commit()
            except Exception:
                await session.rollback()


def _check_legend_enabled():
    """Raise HTTPException if legend rendering is not enabled."""
    if not VIDEO_LEGEND_ENABLED:
        raise HTTPException(
            status_code=400,
            detail="Video legend rendering is disabled. Set VIDEO_LEGEND_ENABLED=true and install FFmpeg.",
        )


async def _generate_legend_task(content_package_id: int, mode: str = "static"):
    """Background task: render legend overlay for a content package.

    Creates its own DB session (cannot reuse request session in background).
    Per D-11: Graceful fallback on failure.
    """
    from src.database.session import get_session_factory
    from src.pipeline.workers.legend_worker import LegendWorker

    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            result = await session.execute(
                select(ContentPackage).where(ContentPackage.id == content_package_id)
            )
            pkg = result.scalar_one_or_none()
            if not pkg:
                logger.error("Legend task: ContentPackage %d not found", content_package_id)
                return

            worker = LegendWorker(mode=mode)
            legend_path = await worker.process(
                video_path=pkg.video_path,
                phrase=pkg.phrase,
                mode=mode,
            )

            if legend_path:
                pkg.legend_status = "success"
                pkg.legend_path = legend_path
                logger.info("Legend rendered for package %d: %s", content_package_id, legend_path)
            else:
                pkg.legend_status = "failed"
                logger.warning("Legend render returned None for package %d (graceful fallback)", content_package_id)

            await session.commit()

        except Exception as e:
            logger.error("Legend task error for package %d: %s", content_package_id, e, exc_info=True)
            try:
                pkg.legend_status = "failed"
                await session.commit()
            except Exception:
                await session.rollback()


# -- Endpoints ----------------------------------------------------------------


@router.post("", summary="Generate video for an approved content package")
async def generate_video(
    req: VideoGenerateRequest,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
    """Trigger video generation for a single approved content package.

    Per D-05: Only approved packages can have videos generated.
    Per D-06: Processing runs in background; returns immediately with status=generating.
    Per D-08: Duration must be 10 or 15 seconds.
    Per D-09: Daily budget cap enforced before starting.
    Per D-10: character_ids passed to Kie.ai for visual consistency.
    """
    _check_video_enabled()

    # Validate duration against model's supported range (kie_client snaps to nearest valid)
    if req.duration < 1 or req.duration > 15:
        raise HTTPException(status_code=400, detail="Duration must be between 1 and 15 seconds")

    # Load and verify content package
    result = await session.execute(
        select(ContentPackage).where(ContentPackage.id == req.content_package_id)
    )
    pkg = result.scalar_one_or_none()
    if not pkg:
        raise HTTPException(status_code=404, detail="Content package not found")

    # Verify ownership (user_id via pipeline_run -> character -> user_id, or admin bypass)
    if current_user.role != "admin":
        if pkg.character_id:
            from src.database.models import Character
            char_result = await session.execute(
                select(Character).where(Character.id == pkg.character_id)
            )
            char = char_result.scalar_one_or_none()
            if char and char.user_id != current_user.id:
                raise HTTPException(status_code=403, detail="Forbidden")

    # Only approved packages (per D-05)
    if pkg.approval_status != "approved":
        raise HTTPException(
            status_code=400,
            detail="Only approved content packages can have videos generated",
        )

    # Check if already generating
    if pkg.video_status == "generating":
        raise HTTPException(
            status_code=409,
            detail="Video generation already in progress",
        )

    # Check budget (per D-09)
    await _check_budget(session, current_user.id, req.duration)

    # Mark as generating and commit
    pkg.video_status = "generating"
    await session.commit()

    # Schedule background task (per D-06)
    background_tasks.add_task(
        _generate_video_task,
        content_package_id=req.content_package_id,
        duration=req.duration,
        character_ids=req.character_ids,
        user_id=current_user.id,
        custom_prompt=req.custom_prompt,
        model=req.model,
    )

    return VideoStatusResponse(
        content_package_id=pkg.id,
        video_status="generating",
        video_task_id=pkg.video_task_id,
        video_path=pkg.video_path,
        video_source=pkg.video_source,
        video_metadata=pkg.video_metadata,
    )


@router.post("/batch", summary="Generate videos for multiple content packages")
async def generate_video_batch(
    req: VideoBatchRequest,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
    """Trigger video generation for multiple approved content packages.

    Per D-09: Budget checked for total estimated cost before starting any.
    """
    _check_video_enabled()

    if req.duration < 1 or req.duration > 15:
        raise HTTPException(status_code=400, detail="Duration must be between 1 and 15 seconds")

    if not req.content_package_ids:
        raise HTTPException(status_code=400, detail="No content package IDs provided")

    # Load all packages
    result = await session.execute(
        select(ContentPackage).where(
            ContentPackage.id.in_(req.content_package_ids)
        )
    )
    packages = result.scalars().all()

    if len(packages) != len(req.content_package_ids):
        found_ids = {p.id for p in packages}
        missing = [pid for pid in req.content_package_ids if pid not in found_ids]
        raise HTTPException(
            status_code=404,
            detail=f"Content packages not found: {missing}",
        )

    # Verify all packages are approved and not already generating
    for pkg in packages:
        if pkg.approval_status != "approved":
            raise HTTPException(
                status_code=400,
                detail=f"Package {pkg.id} is not approved (status={pkg.approval_status})",
            )
        if pkg.video_status == "generating":
            raise HTTPException(
                status_code=409,
                detail=f"Package {pkg.id} already has video generation in progress",
            )

    # Verify ownership for non-admin users
    if current_user.role != "admin":
        from src.database.models import Character
        char_ids = {pkg.character_id for pkg in packages if pkg.character_id}
        if char_ids:
            char_result = await session.execute(
                select(Character).where(Character.id.in_(char_ids))
            )
            chars = {c.id: c for c in char_result.scalars().all()}
            for pkg in packages:
                if pkg.character_id and pkg.character_id in chars:
                    if chars[pkg.character_id].user_id != current_user.id:
                        raise HTTPException(status_code=403, detail="Forbidden")

    # Check total budget (per D-09)
    from src.database.repositories.usage_repo import UsageRepository
    total_estimated = len(packages) * req.duration * VIDEO_COST_PER_SECOND
    repo = UsageRepository(session)
    spent_today = await repo.get_daily_cost(current_user.id, "kie_video")

    if spent_today + total_estimated > VIDEO_DAILY_BUDGET_USD:
        raise HTTPException(
            status_code=429,
            detail=(
                f"Daily video budget insufficient for batch. "
                f"Need ${total_estimated:.2f}, remaining ${VIDEO_DAILY_BUDGET_USD - spent_today:.2f}"
            ),
        )

    # Mark all as generating
    responses = []
    for pkg in packages:
        pkg.video_status = "generating"
        responses.append(
            VideoStatusResponse(
                content_package_id=pkg.id,
                video_status="generating",
                video_task_id=pkg.video_task_id,
                video_path=pkg.video_path,
                video_source=pkg.video_source,
                video_metadata=pkg.video_metadata,
            )
        )
    await session.commit()

    # Schedule one background task per package
    for pkg in packages:
        background_tasks.add_task(
            _generate_video_task,
            content_package_id=pkg.id,
            duration=req.duration,
            character_ids=req.character_ids,
            user_id=current_user.id,
            model=req.model,
        )

    return responses


@router.get(
    "/status/{content_package_id}",
    summary="Check video generation status",
    response_model=VideoStatusResponse,
)
async def get_video_status(
    content_package_id: int,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
    """Get current video generation status for a content package."""
    result = await session.execute(
        select(ContentPackage).where(ContentPackage.id == content_package_id)
    )
    pkg = result.scalar_one_or_none()
    if not pkg:
        raise HTTPException(status_code=404, detail="Content package not found")

    # Verify ownership for non-admin
    if current_user.role != "admin":
        if pkg.character_id:
            from src.database.models import Character
            char_result = await session.execute(
                select(Character).where(Character.id == pkg.character_id)
            )
            char = char_result.scalar_one_or_none()
            if char and char.user_id != current_user.id:
                raise HTTPException(status_code=403, detail="Forbidden")

    return VideoStatusResponse(
        content_package_id=pkg.id,
        video_status=pkg.video_status,
        video_task_id=pkg.video_task_id,
        video_path=pkg.video_path,
        video_source=pkg.video_source,
        video_metadata=pkg.video_metadata,
    )


@router.get("/progress/{content_package_id}", summary="Live Kie.ai task progress")
async def get_video_progress(
    content_package_id: int,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
    """Query Kie.ai for real-time task progress (state + percentage)."""
    result = await session.execute(
        select(ContentPackage).where(ContentPackage.id == content_package_id)
    )
    pkg = result.scalar_one_or_none()
    if not pkg:
        raise HTTPException(status_code=404, detail="Content package not found")

    if not pkg.video_task_id or pkg.video_status != "generating":
        return {
            "content_package_id": pkg.id,
            "state": pkg.video_status or "none",
            "progress": 100 if pkg.video_status == "success" else 0,
        }

    try:
        from src.video_gen.kie_client import KieSora2Client
        client = KieSora2Client()
        task_data = await client.get_task_status(pkg.video_task_id)
        return {
            "content_package_id": pkg.id,
            "state": task_data.get("state", "unknown"),
            "progress": int(str(task_data.get("progress", "0")).replace("%", "")),
        }
    except Exception as e:
        logger.warning("Failed to get Kie.ai progress for %s: %s", pkg.video_task_id, e)
        return {
            "content_package_id": pkg.id,
            "state": "generating",
            "progress": -1,
        }


@router.get("/list", summary="List content packages with video status")
async def list_videos(
    status: str | None = None,
    model: str | None = None,
    sort: str = "newest",
    limit: int = 50,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
    """List content packages that have video generation activity.

    Supports filtering by status, model (from video_metadata JSON), and sort order.
    """
    from sqlalchemy import desc, asc

    stmt = select(ContentPackage).where(ContentPackage.video_status.isnot(None))
    if status:
        stmt = stmt.where(ContentPackage.video_status == status)
    if model:
        # Filter by model stored in video_metadata JSON field (MySQL compatible)
        stmt = stmt.where(
            ContentPackage.video_metadata.like(f'%"model": "{model}"%')
        )
    if sort == "oldest":
        stmt = stmt.order_by(asc(ContentPackage.created_at)).limit(limit)
    else:
        stmt = stmt.order_by(desc(ContentPackage.created_at)).limit(limit)

    result = await session.execute(stmt)
    packages = result.scalars().all()

    return {
        "total": len(packages),
        "videos": [
            {
                "content_package_id": pkg.id,
                "phrase": pkg.phrase,
                "topic": pkg.topic,
                "image_path": pkg.image_path,
                "video_status": pkg.video_status,
                "video_path": pkg.video_path,
                "video_task_id": pkg.video_task_id,
                "video_source": pkg.video_source,
                "video_metadata": pkg.video_metadata,
                "video_prompt_used": pkg.video_prompt_used,
                "legend_status": pkg.legend_status,
                "legend_path": pkg.legend_path,
                "created_at": pkg.created_at.isoformat() if pkg.created_at else None,
                "is_published": pkg.is_published,
            }
            for pkg in packages
        ],
    }


@router.get("/file/{content_package_id}", summary="Serve generated video file")
async def serve_video_file(
    content_package_id: int,
    session: AsyncSession = Depends(db_session),
):
    """Serve the generated video file for playback/download. No auth required (like image serving)."""
    from fastapi.responses import FileResponse

    result = await session.execute(
        select(ContentPackage).where(ContentPackage.id == content_package_id)
    )
    pkg = result.scalar_one_or_none()
    if not pkg or not pkg.video_path:
        raise HTTPException(status_code=404, detail="Video not found")

    video_path = Path(pkg.video_path)
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video file missing from disk")

    return FileResponse(
        str(video_path),
        media_type="video/mp4",
        filename=f"memelab_video_{content_package_id}.mp4",
    )


@router.delete("/{content_package_id}", summary="Delete generated video from a content package")
async def delete_video(
    content_package_id: int,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
    """Delete a generated video, clearing video fields on the content package."""
    result = await session.execute(
        select(ContentPackage).where(ContentPackage.id == content_package_id)
    )
    pkg = result.scalar_one_or_none()
    if not pkg:
        raise HTTPException(status_code=404, detail="Content package not found")

    if not pkg.video_status:
        raise HTTPException(status_code=400, detail="No video to delete")

    # Delete file from disk
    if pkg.video_path:
        video_file = Path(pkg.video_path)
        if video_file.exists():
            video_file.unlink()
            logger.info("Deleted video file: %s", video_file)

    # Clear video fields
    pkg.video_status = None
    pkg.video_path = None
    pkg.video_task_id = None
    pkg.video_metadata = None
    pkg.video_source = None
    pkg.video_prompt_used = None
    await session.commit()

    return {"deleted": True, "content_package_id": content_package_id}


@router.patch(
    "/{content_package_id}/approve",
    summary="Toggle video approval status",
)
async def approve_video(
    content_package_id: int,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
    """Toggle the approved state of a video in video_metadata.

    If video_metadata.approved is truthy, sets to False. If falsy or missing, sets to True.
    If video_metadata is None, initializes as {"approved": True}.
    """
    result = await session.execute(
        select(ContentPackage).where(ContentPackage.id == content_package_id)
    )
    pkg = result.scalar_one_or_none()
    if not pkg:
        raise HTTPException(status_code=404, detail="Content package not found")

    # Verify ownership (same pattern as delete_video)
    if current_user.role != "admin":
        if pkg.character_id:
            from src.database.models import Character
            char_result = await session.execute(
                select(Character).where(Character.id == pkg.character_id)
            )
            char = char_result.scalar_one_or_none()
            if char and char.user_id != current_user.id:
                raise HTTPException(status_code=403, detail="Forbidden")

    # Toggle approved in video_metadata
    if pkg.video_metadata is None:
        pkg.video_metadata = {"approved": True}
    elif isinstance(pkg.video_metadata, dict):
        current = pkg.video_metadata.get("approved", False)
        # Create a new dict to trigger SQLAlchemy change detection on JSON column
        pkg.video_metadata = {**pkg.video_metadata, "approved": not current}
    else:
        pkg.video_metadata = {"approved": True}

    await session.commit()

    return {
        "content_package_id": content_package_id,
        "approved": pkg.video_metadata.get("approved", False),
    }


# -- Legend endpoints (Phase 999.2) -------------------------------------------


@router.post("/legend", summary="Add text legend overlay to a generated video")
async def generate_legend(
    req: LegendRequest,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
    """Add burned-in text overlay (phrase + watermark) to a video.

    Per D-05: Default mode is "static" (full duration visibility).
    Per D-08: Mode override via request parameter.
    Per D-09: Auto-triggers after video generation, but also available manually.
    Per D-10: Creates new file with _legend suffix, preserving original.
    Per D-11: Graceful fallback -- failure logged, original video intact.
    """
    _check_legend_enabled()

    # Validate mode
    if req.mode not in ("static", "fade", "typewriter"):
        raise HTTPException(status_code=400, detail="Mode must be 'static', 'fade', or 'typewriter'")

    # Load content package
    result = await session.execute(
        select(ContentPackage).where(ContentPackage.id == req.content_package_id)
    )
    pkg = result.scalar_one_or_none()
    if not pkg:
        raise HTTPException(status_code=404, detail="Content package not found")

    # Verify ownership (same pattern as generate_video)
    if current_user.role != "admin":
        if pkg.character_id:
            from src.database.models import Character
            char_result = await session.execute(
                select(Character).where(Character.id == pkg.character_id)
            )
            char = char_result.scalar_one_or_none()
            if char and char.user_id != current_user.id:
                raise HTTPException(status_code=403, detail="Forbidden")

    # Must have a completed video
    if not pkg.video_path or pkg.video_status != "success":
        raise HTTPException(
            status_code=400,
            detail="Content package must have a completed video (video_status='success')",
        )

    # Check if already processing
    if pkg.legend_status == "processing":
        raise HTTPException(status_code=409, detail="Legend rendering already in progress")

    # Mark as processing
    pkg.legend_status = "processing"
    await session.commit()

    # Schedule background task
    background_tasks.add_task(
        _generate_legend_task,
        content_package_id=req.content_package_id,
        mode=req.mode,
    )

    return {
        "content_package_id": pkg.id,
        "legend_status": "processing",
        "mode": req.mode,
    }


@router.post("/legend/batch", summary="Add text legend overlay to multiple videos")
async def generate_legend_batch(
    req: LegendBatchRequest,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
    """Add burned-in text overlays to multiple videos.

    Per D-08: Single mode applied to all videos in batch.
    """
    _check_legend_enabled()

    if req.mode not in ("static", "fade", "typewriter"):
        raise HTTPException(status_code=400, detail="Mode must be 'static', 'fade', or 'typewriter'")

    if not req.content_package_ids:
        raise HTTPException(status_code=400, detail="No content package IDs provided")

    # Load all packages
    result = await session.execute(
        select(ContentPackage).where(
            ContentPackage.id.in_(req.content_package_ids)
        )
    )
    packages = result.scalars().all()

    if len(packages) != len(req.content_package_ids):
        found_ids = {p.id for p in packages}
        missing = [pid for pid in req.content_package_ids if pid not in found_ids]
        raise HTTPException(status_code=404, detail=f"Content packages not found: {missing}")

    # Verify all have completed videos
    for pkg in packages:
        if not pkg.video_path or pkg.video_status != "success":
            raise HTTPException(
                status_code=400,
                detail=f"Package {pkg.id} does not have a completed video",
            )
        if pkg.legend_status == "processing":
            raise HTTPException(
                status_code=409,
                detail=f"Package {pkg.id} already has legend rendering in progress",
            )

    # Mark all as processing
    responses = []
    for pkg in packages:
        pkg.legend_status = "processing"
        responses.append({
            "content_package_id": pkg.id,
            "legend_status": "processing",
            "mode": req.mode,
        })
    await session.commit()

    # Schedule one background task per package
    for pkg in packages:
        background_tasks.add_task(
            _generate_legend_task,
            content_package_id=pkg.id,
            mode=req.mode,
        )

    return responses


@router.post("/enhance-prompt", summary="Enhance user animation description into Sora 2 prompt")
async def enhance_video_prompt(
    req: dict,
    current_user=Depends(get_current_user),
):
    """Take user's brief animation description and enhance it for Sora 2."""
    from src.video_gen.video_prompt_builder import VideoPromptBuilder

    user_input = req.get("user_input", "").strip()
    theme_key = req.get("theme_key", "")
    if not user_input:
        raise HTTPException(status_code=400, detail="user_input is required")

    builder = VideoPromptBuilder()
    enhanced = builder.enhance_user_prompt(user_input, theme_key)
    return {"original": user_input, "enhanced": enhanced}


@router.get(
    "/budget",
    summary="Check remaining daily video budget",
    response_model=VideoBudgetResponse,
)
async def get_video_budget(
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
    """Get today's video generation budget status.

    Per D-09: Shows remaining budget before user confirms video generation.
    """
    from src.database.repositories.usage_repo import UsageRepository

    repo = UsageRepository(session)
    spent_today = await repo.get_daily_cost(current_user.id, "kie_video")
    remaining = max(0.0, VIDEO_DAILY_BUDGET_USD - spent_today)

    # Estimate videos remaining at current duration
    cost_per_video = VIDEO_DURATION * VIDEO_COST_PER_SECOND
    videos_remaining = int(remaining / cost_per_video) if cost_per_video > 0 else 0

    return VideoBudgetResponse(
        daily_budget_usd=VIDEO_DAILY_BUDGET_USD,
        spent_today_usd=round(spent_today, 4),
        remaining_usd=round(remaining, 4),
        videos_remaining_estimate=videos_remaining,
    )


@router.post("/retry/{content_package_id}", summary="Retry a failed video generation")
async def retry_video_generation(
    content_package_id: int,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
    """Retry a failed video generation job.

    Resubmits the same prompt/model/image to Kie.ai.
    Only jobs with video_status='failed' can be retried.
    Phase 18: One-click retry for failed jobs.
    """
    _check_video_enabled()

    # Load content package
    result = await session.execute(
        select(ContentPackage).where(ContentPackage.id == content_package_id)
    )
    pkg = result.scalar_one_or_none()
    if not pkg:
        raise HTTPException(status_code=404, detail="Content package not found")

    # Verify ownership
    if current_user.role != "admin":
        if pkg.character_id:
            from src.database.models import Character
            char_result = await session.execute(
                select(Character).where(Character.id == pkg.character_id)
            )
            char = char_result.scalar_one_or_none()
            if char and char.user_id != current_user.id:
                raise HTTPException(status_code=403, detail="Forbidden")

    # Only failed videos can be retried
    if pkg.video_status != "failed":
        raise HTTPException(
            status_code=400,
            detail="Only failed videos can be retried",
        )

    # Extract previous params from video_metadata
    duration = (
        pkg.video_metadata.get("duration", VIDEO_DURATION)
        if pkg.video_metadata
        else VIDEO_DURATION
    )
    model = (
        pkg.video_metadata.get("model", "")
        if pkg.video_metadata
        else ""
    )
    prompt = pkg.video_prompt_used or ""

    # Check budget
    await _check_budget(session, current_user.id, duration)

    # Reset status for retry
    pkg.video_status = "generating"
    pkg.video_task_id = None
    pkg.video_metadata = None
    await session.commit()

    # Schedule background task
    character_ids = (
        pkg.video_metadata.get("character_ids", [])
        if pkg.video_metadata
        else []
    )
    background_tasks.add_task(
        _generate_video_task,
        content_package_id=content_package_id,
        duration=duration,
        character_ids=character_ids,
        user_id=current_user.id,
    )

    return VideoStatusResponse(
        content_package_id=pkg.id,
        video_status="generating",
        video_task_id=None,
        video_path=pkg.video_path,
        video_source=pkg.video_source,
        video_metadata=None,
    )


@router.get(
    "/progress/{content_package_id}",
    summary="Get detailed video generation progress",
    response_model=VideoProgressDetailResponse,
)
async def get_video_progress(
    content_package_id: int,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
    """Get real-time video generation progress with human-readable step labels.

    Phase 18: Enhanced progress with step labels mapped from Kie.ai task state.
    Queries Kie.ai live for jobs in 'generating' state.
    """
    result = await session.execute(
        select(ContentPackage).where(ContentPackage.id == content_package_id)
    )
    pkg = result.scalar_one_or_none()
    if not pkg:
        raise HTTPException(status_code=404, detail="Content package not found")

    # Verify ownership for non-admin
    if current_user.role != "admin":
        if pkg.character_id:
            from src.database.models import Character
            char_result = await session.execute(
                select(Character).where(Character.id == pkg.character_id)
            )
            char = char_result.scalar_one_or_none()
            if char and char.user_id != current_user.id:
                raise HTTPException(status_code=403, detail="Forbidden")

    # Non-generating states: return from DB directly
    if pkg.video_status != "generating":
        if pkg.video_status == "success":
            return VideoProgressDetailResponse(
                content_package_id=pkg.id,
                state="success",
                progress=100,
                step_label="Concluido",
            )
        if pkg.video_status == "failed":
            return VideoProgressDetailResponse(
                content_package_id=pkg.id,
                state="fail",
                progress=0,
                step_label="Falhou",
            )
        # No video / null status
        return VideoProgressDetailResponse(
            content_package_id=pkg.id,
            state="none",
            progress=0,
            step_label="Sem video",
        )

    # Generating: query Kie.ai for live status
    if pkg.video_task_id:
        try:
            from src.video_gen.kie_client import KieSora2Client

            client = KieSora2Client()
            task_data = await client.get_task_status(pkg.video_task_id)
            state = task_data.get("state", "")
            progress = task_data.get("progress", 0)
            step_label = STEP_LABELS.get(state, "Processando...")

            return VideoProgressDetailResponse(
                content_package_id=pkg.id,
                state=state,
                progress=progress,
                step_label=step_label,
            )
        except Exception as e:
            logger.warning(
                "Failed to get Kie.ai progress for package %d: %s",
                pkg.id, e,
            )

    # Fallback: generating but no task_id yet (submission in progress)
    return VideoProgressDetailResponse(
        content_package_id=pkg.id,
        state="generating",
        progress=0,
        step_label="Enviando...",
    )
