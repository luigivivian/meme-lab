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

            # Determine theme_key from image_metadata or work_order
            theme_key = "generico"
            if pkg.image_metadata and isinstance(pkg.image_metadata, dict):
                theme_key = pkg.image_metadata.get("theme_key", theme_key)
                theme_key = pkg.image_metadata.get("situacao_key", theme_key)

            # Build motion prompt (per D-02)
            prompt_builder = VideoPromptBuilder()
            motion_prompt = prompt_builder.build_motion_prompt(
                theme_key=theme_key,
                phrase_context=pkg.phrase or "",
                video_prompt_notes=theme_notes,
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
            blob_name = f"video-inputs/{Path(bg_path).name}"
            signed_url = uploader.upload_image(bg_path, blob_name)

            # Generate video via Kie.ai Sora 2
            client = KieSora2Client()
            gen_result = await client.generate_video(
                image_url=signed_url,
                prompt=motion_prompt,
                duration=duration,
                character_ids=character_ids if character_ids else None,
                output_dir=str(GENERATED_VIDEOS_DIR),
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

                # Track cost (per D-09)
                repo = UsageRepository(session)
                await repo.increment(
                    user_id=user_id,
                    service="kie_video",
                    tier="standard",
                    cost_usd=gen_result.cost_usd,
                )

                logger.info(
                    "Video generated for package %d: task=%s cost=$%.3f",
                    content_package_id, gen_result.task_id, gen_result.cost_usd,
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

    # Validate duration (per D-08)
    if req.duration not in (10, 15):
        raise HTTPException(status_code=400, detail="Duration must be 10 or 15 seconds")

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

    if req.duration not in (10, 15):
        raise HTTPException(status_code=400, detail="Duration must be 10 or 15 seconds")

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
