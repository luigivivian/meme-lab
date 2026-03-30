"""Product Ad pipeline API routes -- wizard create, step execution, approve, regenerate.

Per D-20: Same approve/regenerate pattern as reels.
Per D-21: 8 steps: analysis, scene, prompt, video, copy, audio, assembly, export.
Per D-22: Export is auto-complete (no approval needed).
Per D-23: Separate /ads section.
"""

import asyncio
import logging
import os
import shutil
import traceback
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from src.api.deps import get_current_user, db_session
from src.database.models import ProductAdJob
from src.product_studio.config import ADS_STEP_ORDER, ADS_OUTPUT_DIR
from src.product_studio.models import (
    AdCreateRequest,
    AdJobResponse,
    AdStepStateResponse,
    AdCostEstimate,
)

logger = logging.getLogger("clip-flow.api.ads")

router = APIRouter(prefix="/ads", tags=["Product Ads"])


# ── Helpers ──────────────────────────────────────────────────────────────────


def _init_step_state() -> dict:
    """Create initial step_state for an ad job with all 8 steps pending."""
    state = {}
    for step in ADS_STEP_ORDER:
        state[step] = {"status": "pending"}
    return state


def _calc_progress(step_state: dict) -> tuple[str, int]:
    """Calculate current_step and progress_pct from step_state."""
    completed = 0
    current = ADS_STEP_ORDER[0]
    for step in ADS_STEP_ORDER:
        s = step_state.get(step, {})
        if s.get("status") in ("approved", "complete"):
            completed += 1
        elif s.get("status") in ("generating", "pending", "error"):
            current = step
            break
    pct = int((completed / len(ADS_STEP_ORDER)) * 100)
    return current, pct


async def _get_user_job(
    job_id: str, user_id: int, db: AsyncSession
) -> ProductAdJob:
    """Fetch a ProductAdJob owned by user_id, or raise 404."""
    result = await db.execute(
        select(ProductAdJob).where(
            ProductAdJob.job_id == job_id,
            ProductAdJob.user_id == user_id,
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


def _job_to_response(job: ProductAdJob) -> AdJobResponse:
    """Convert ORM model to response."""
    return AdJobResponse(
        job_id=job.job_id,
        status=job.status,
        style=job.style,
        product_name=job.product_name,
        step_state=job.step_state,
        cost_brl=job.cost_brl,
        outputs=job.outputs,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


# ── Background task for step execution ───────────────────────────────────────


async def _execute_ad_step_task(
    job_id: str,
    step_name: str,
    session_factory,
):
    """Background task: execute a single pipeline step for an ad job.

    Uses get_session_factory() pattern for independent DB session (same as reels).
    """
    from src.product_studio.pipeline import ProductAdPipeline

    async with session_factory() as session:
        try:
            result = await session.execute(
                select(ProductAdJob).where(ProductAdJob.job_id == job_id)
            )
            job = result.scalar_one_or_none()
            if not job:
                logger.error("Ad step task: job %s not found", job_id)
                return

            step_state = dict(job.step_state or {})
            step_data = step_state.get(step_name, {})
            step_data["status"] = "generating"
            step_state[step_name] = step_data
            job.step_state = step_state
            flag_modified(job, "step_state")
            await session.commit()

            config = dict(job.config or {})
            pipeline = ProductAdPipeline(config=config)
            job_dir = config.get("job_dir", "")

            # Create job_dir if not set
            if not job_dir:
                job_dir = pipeline._make_job_dir(job.product_name)
                config["job_dir"] = job_dir
                job.config = config
                flag_modified(job, "config")

            if step_name == "analysis":
                product_image = (job.product_images or [None])[0]
                if product_image:
                    result_data = await pipeline.run_step_analysis(
                        product_image_path=product_image,
                    )
                else:
                    # Text-only analysis when no product image uploaded
                    from src.llm_client import _get_client, _extract_text
                    import json as _json
                    client = _get_client()
                    prompt = (
                        f"Analyze the product '{job.product_name}' for a video ad. "
                        "Return ONLY valid JSON with: niche, tone, audience, "
                        "scene_suggestions (array of 3 BACKGROUND-ONLY descriptions in English — "
                        "describe ONLY the surface/backdrop/lighting, NOT people, NOT hands, NOT humans. "
                        "Examples: 'dark gradient with soft rim lighting', 'white marble with natural sunlight'), "
                        "product_description (Portuguese). No markdown."
                    )
                    resp = await asyncio.to_thread(
                        client.models.generate_content,
                        model="gemini-2.5-flash",
                        contents=prompt,
                    )
                    text = _extract_text(resp)
                    clean = text.strip().removeprefix("```json").removesuffix("```").strip()
                    result_data = _json.loads(clean)
                step_data["result"] = result_data
                step_data["status"] = "complete"

            elif step_name == "scene":
                analysis = step_state.get("analysis", {}).get("result", {})
                raw_scene = job.scene_description or analysis.get("scene_suggestions", [""])[0]
                # Sanitize: strip any human/hand references from scene prompt
                _BANNED = ["hand", "hands", "finger", "person", "people", "human",
                           "family", "child", "couple", "adult", "woman", "man"]
                scene_desc = raw_scene
                for word in _BANNED:
                    if word.lower() in scene_desc.lower():
                        scene_desc = "Clean product photography on elegant surface with soft studio lighting"
                        break
                product_image = (job.product_images or [None])[0]
                scene_params = config.get("step_params_scene", {})
                scene_mode = scene_params.get("scene_mode", "cutout")
                scene_path = await pipeline.run_step_scene(
                    product_image_path=product_image or "",
                    scene_prompt=scene_desc,
                    job_dir=job_dir,
                    scene_mode=scene_mode,
                )
                step_data["result"] = {"scene_image_path": scene_path}
                step_data["status"] = "complete"

            elif step_name == "prompt":
                analysis = step_state.get("analysis", {}).get("result", {})
                # Use the scene description text (from wizard or analysis), not the file path
                scene_desc_for_prompt = (
                    job.scene_description
                    or analysis.get("scene_suggestions", ["product on clean background"])[0]
                )
                # Build rich product description — name + analysis description
                prod_desc = analysis.get("product_description", "")
                if prod_desc:
                    prod_desc = f"{job.product_name}: {prod_desc}"
                else:
                    prod_desc = job.product_name
                prompt_text = await pipeline.run_step_prompt(
                    product_description=prod_desc,
                    scene_description=scene_desc_for_prompt,
                    style=job.style,
                    video_model=job.video_model or "wan/2-6-flash-image-to-video",
                    tone=job.tone or "premium",
                )
                step_data["result"] = {"prompt": prompt_text}
                step_data["status"] = "complete"

            elif step_name == "video":
                scene_data = step_state.get("scene", {}).get("result", {})
                prompt_data = step_state.get("prompt", {}).get("result", {})
                video_path = await pipeline.run_step_video(
                    scene_image_path=scene_data.get("scene_image_path", ""),
                    prompt=prompt_data.get("prompt", ""),
                    style=job.style,
                    video_model=job.video_model or "wan/2-6-flash-image-to-video",
                    job_dir=job_dir,
                )
                step_data["result"] = {"video_path": video_path}
                step_data["status"] = "complete"

            elif step_name == "copy":
                analysis = step_state.get("analysis", {}).get("result", {})
                copy_result = await pipeline.run_step_copy(
                    product_name=job.product_name,
                    product_description=analysis.get("product_description", ""),
                    niche=job.niche or "",
                    tone=job.tone or "premium",
                    audience=job.audience or "",
                    style=job.style,
                )
                step_data["result"] = copy_result
                step_data["status"] = "complete"

            elif step_name == "audio":
                audio_result = await pipeline.run_step_audio(
                    tone=job.tone or "premium",
                    audio_mode=job.audio_mode or "music",
                    job_dir=job_dir,
                    video_duration=job.target_duration or 15.0,
                )
                step_data["result"] = audio_result
                step_data["status"] = "complete"

            elif step_name == "assembly":
                video_data = step_state.get("video", {}).get("result", {})
                copy_data = step_state.get("copy", {}).get("result", {})
                audio_data = step_state.get("audio", {}).get("result", {})
                assembled_path = await pipeline.run_step_assembly(
                    video_path=video_data.get("video_path", ""),
                    headline=copy_data.get("headline"),
                    cta=copy_data.get("cta"),
                    audio_path=audio_data.get("mixed_path"),
                    style=job.style,
                    job_dir=job_dir,
                )
                step_data["result"] = {"assembled_path": assembled_path}
                step_data["status"] = "complete"

            elif step_name == "export":
                assembly_data = step_state.get("assembly", {}).get("result", {})
                export_paths = await pipeline.run_step_export(
                    assembled_path=assembly_data.get("assembled_path", ""),
                    job_dir=job_dir,
                    formats=job.output_formats or ["9:16"],
                )
                step_data["result"] = {"export_paths": export_paths}
                step_data["status"] = "complete"
                # Per D-22: Export auto-approves
                step_data["status"] = "approved"
                job.outputs = {"export_paths": export_paths}

            step_state[step_name] = step_data
            current_step, progress_pct = _calc_progress(step_state)
            job.step_state = step_state
            job.current_step = current_step
            job.progress_pct = progress_pct
            flag_modified(job, "step_state")
            await session.commit()

            logger.info("Ad step %s complete for job %s", step_name, job_id)

        except Exception as e:
            logger.error("Ad step %s failed for job %s: %s", step_name, job_id, str(e))
            logger.error(traceback.format_exc())
            try:
                step_state = dict(job.step_state or {})
                step_data = step_state.get(step_name, {})
                step_data["status"] = "error"
                step_data["error"] = str(e)[:500]
                step_state[step_name] = step_data
                job.step_state = step_state
                job.error_message = str(e)[:500]
                flag_modified(job, "step_state")
                await session.commit()
            except Exception:
                pass


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.post("/upload-image")
async def upload_product_image(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
):
    """Upload a product reference image. Returns the saved file path."""
    upload_dir = os.path.join(ADS_OUTPUT_DIR, "uploads")
    os.makedirs(upload_dir, exist_ok=True)

    ext = os.path.splitext(file.filename or "img.jpg")[1] or ".jpg"
    filename = f"{uuid.uuid4().hex[:12]}{ext}"
    filepath = os.path.join(upload_dir, filename)

    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    return {"filename": filename, "path": filepath, "size_bytes": len(content)}


@router.post("/analyze")
async def analyze_product(
    req: dict,
    current_user=Depends(get_current_user),
):
    """Quick AI analysis of product name — returns niche, tone, audience, scene suggestions."""
    from src.llm_client import _get_client, _extract_text

    product_name = req.get("product_name", "")
    if not product_name:
        raise HTTPException(status_code=400, detail="product_name required")

    prompt = (
        f"Analyze the product '{product_name}' for a video ad. "
        "Return ONLY valid JSON with keys: niche (string), tone (string), "
        "audience (string), scene_suggestions (array of 3 short scene descriptions in English). "
        "No text outside the JSON."
    )
    try:
        client = _get_client()
        resp = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.5-flash",
            contents=prompt,
        )
        text = _extract_text(resp)
        import json as _json
        clean = text.strip().removeprefix("```json").removesuffix("```").strip()
        result = _json.loads(clean)
        return result
    except Exception as e:
        logger.warning("analyze_product failed: %s", e)
        return {
            "niche": "",
            "tone": "professional",
            "audience": "general",
            "scene_suggestions": [],
        }


@router.post("/create", response_model=AdJobResponse)
async def create_ad_job(
    req: AdCreateRequest,
    db: AsyncSession = Depends(db_session),
    current_user=Depends(get_current_user),
):
    """Create a new product ad job with wizard config."""
    from src.product_studio.pipeline import ProductAdPipeline

    job_id = str(uuid.uuid4())
    step_state = _init_step_state()

    config = req.model_dump()
    pipeline = ProductAdPipeline(config=config)
    cost = pipeline.estimate_cost(
        style=req.style,
        audio_mode=req.audio_mode,
        formats=req.output_formats,
    )

    job = ProductAdJob(
        job_id=job_id,
        user_id=current_user.id,
        product_name=req.product_name,
        product_images=[req.product_image_url] if req.product_image_url else [],
        config=config,
        style=req.style,
        video_model=req.video_model,
        audio_mode=req.audio_mode,
        output_formats=req.output_formats,
        target_duration=req.target_duration,
        tone=req.tone,
        niche=req.niche,
        audience=req.audience,
        scene_description=req.scene_description,
        step_state=step_state,
        status="draft",
        cost_brl=cost.get("total_brl", 0),
    )

    db.add(job)
    await db.commit()
    await db.refresh(job)

    return _job_to_response(job)


@router.get("/jobs", response_model=list[AdJobResponse])
async def list_ad_jobs(
    status: str | None = Query(default=None),
    db: AsyncSession = Depends(db_session),
    current_user=Depends(get_current_user),
):
    """List user's ad jobs, optionally filtered by status."""
    query = select(ProductAdJob).where(
        ProductAdJob.user_id == current_user.id
    ).order_by(desc(ProductAdJob.created_at))

    if status:
        query = query.where(ProductAdJob.status == status)

    result = await db.execute(query)
    jobs = result.scalars().all()
    return [_job_to_response(j) for j in jobs]


@router.get("/{job_id}", response_model=AdJobResponse)
async def get_ad_job(
    job_id: str,
    db: AsyncSession = Depends(db_session),
    current_user=Depends(get_current_user),
):
    """Get ad job detail with full step_state."""
    job = await _get_user_job(job_id, current_user.id, db)
    return _job_to_response(job)


@router.get("/{job_id}/steps")
async def get_ad_steps(
    job_id: str,
    db: AsyncSession = Depends(db_session),
    current_user=Depends(get_current_user),
):
    """Get step state as array with current_step and progress_pct."""
    job = await _get_user_job(job_id, current_user.id, db)
    step_state = job.step_state or {}
    current_step, progress_pct = _calc_progress(step_state)
    # Build steps array for frontend consumption
    steps = []
    for step_name in ADS_STEP_ORDER:
        data = step_state.get(step_name, {})
        steps.append({
            "step_name": step_name,
            "status": data.get("status", "pending"),
            "result": data.get("result"),
            "error": data.get("error"),
        })
    return {
        "steps": steps,
        "current_step": current_step,
        "progress_pct": progress_pct,
    }


@router.post("/{job_id}/step/{step_name}/execute")
async def execute_ad_step(
    job_id: str,
    step_name: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(db_session),
    current_user=Depends(get_current_user),
    body: dict | None = None,
):
    """Execute a pipeline step in background.

    Optional body params per step:
    - scene: scene_mode ("raw" | "cutout" | "compose")
    """
    if step_name not in ADS_STEP_ORDER:
        raise HTTPException(status_code=400, detail=f"Invalid step: {step_name}")

    job = await _get_user_job(job_id, current_user.id, db)
    step_state = job.step_state or {}

    # Guard: prevent duplicate execution if step is already running
    current_status = step_state.get(step_name, {}).get("status")
    if current_status == "generating":
        return {"message": f"Step '{step_name}' is already running", "job_id": job_id}

    # Validate previous step is approved (or this is the first step)
    step_idx = ADS_STEP_ORDER.index(step_name)
    if step_idx > 0:
        prev_step = ADS_STEP_ORDER[step_idx - 1]
        prev_status = step_state.get(prev_step, {}).get("status")
        if prev_status not in ("approved", "complete"):
            raise HTTPException(
                status_code=400,
                detail=f"Previous step '{prev_step}' must be completed or approved first",
            )

    # Store step params in config for the background task to read
    step_params = body or {}
    if step_params:
        config = dict(job.config or {})
        config[f"step_params_{step_name}"] = step_params
        job.config = config
        flag_modified(job, "config")
        await db.commit()

    from src.database.session import get_session_factory
    session_factory = get_session_factory()

    background_tasks.add_task(
        _execute_ad_step_task,
        job_id=job_id,
        step_name=step_name,
        session_factory=session_factory,
    )

    return {"message": f"Step '{step_name}' execution started", "job_id": job_id}


@router.post("/{job_id}/step/{step_name}/approve")
async def approve_ad_step(
    job_id: str,
    step_name: str,
    db: AsyncSession = Depends(db_session),
    current_user=Depends(get_current_user),
):
    """Approve a completed step."""
    if step_name not in ADS_STEP_ORDER:
        raise HTTPException(status_code=400, detail=f"Invalid step: {step_name}")

    job = await _get_user_job(job_id, current_user.id, db)
    step_state = dict(job.step_state or {})
    step_data = step_state.get(step_name, {})

    if step_data.get("status") != "complete":
        raise HTTPException(
            status_code=400,
            detail=f"Step '{step_name}' is not complete (status: {step_data.get('status')})",
        )

    step_data["status"] = "approved"
    step_state[step_name] = step_data
    job.step_state = step_state
    flag_modified(job, "step_state")
    await db.commit()

    return {"step_state": step_state}


@router.post("/{job_id}/step/{step_name}/regenerate")
async def regenerate_ad_step(
    job_id: str,
    step_name: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(db_session),
    current_user=Depends(get_current_user),
    body: dict | None = None,
):
    """Regenerate a step: clears this step and all downstream, then re-executes.

    Optional body params: video_model, target_duration, audio_mode — updates job before re-running.
    """
    if step_name not in ADS_STEP_ORDER:
        raise HTTPException(status_code=400, detail=f"Invalid step: {step_name}")

    job = await _get_user_job(job_id, current_user.id, db)

    # Apply overrides from body if provided
    if body:
        if "video_model" in body and body["video_model"]:
            job.video_model = body["video_model"]
        if "target_duration" in body and body["target_duration"]:
            job.target_duration = int(body["target_duration"])
        if "audio_mode" in body and body["audio_mode"]:
            job.audio_mode = body["audio_mode"]

    step_state = dict(job.step_state or {})

    # Clear this step and all downstream steps
    step_idx = ADS_STEP_ORDER.index(step_name)
    for i in range(step_idx, len(ADS_STEP_ORDER)):
        step_state[ADS_STEP_ORDER[i]] = {"status": "pending"}

    job.step_state = step_state
    flag_modified(job, "step_state")
    await db.commit()

    # Trigger execution for this step
    from src.database.session import get_session_factory
    session_factory = get_session_factory()

    background_tasks.add_task(
        _execute_ad_step_task,
        job_id=job_id,
        step_name=step_name,
        session_factory=session_factory,
    )

    return {"message": f"Step '{step_name}' regeneration started", "job_id": job_id}


@router.get("/{job_id}/cost-estimate", response_model=AdCostEstimate)
async def get_cost_estimate(
    job_id: str,
    db: AsyncSession = Depends(db_session),
    current_user=Depends(get_current_user),
):
    """Get cost breakdown for an ad job."""
    from src.product_studio.pipeline import ProductAdPipeline

    job = await _get_user_job(job_id, current_user.id, db)
    config = job.config or {}
    pipeline = ProductAdPipeline(config=config)
    cost = pipeline.estimate_cost(
        style=job.style,
        audio_mode=job.audio_mode or "music",
        formats=job.output_formats or ["9:16"],
    )

    return AdCostEstimate(
        video_cost_brl=cost.get("video_brl", 0),
        audio_cost_brl=cost.get("audio_brl", 0),
        image_cost_brl=cost.get("image_brl", 0),
        total_brl=cost.get("total_brl", 0),
    )


@router.get("/{job_id}/file/{filename}")
async def serve_ad_file(
    job_id: str,
    filename: str,
    db: AsyncSession = Depends(db_session),
):
    """Serve artifact file from job output directory. No auth — UUID is unguessable."""
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    result = await db.execute(
        select(ProductAdJob).where(ProductAdJob.job_id == job_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    config = job.config or {}
    job_dir = config.get("job_dir", "")

    if not job_dir:
        raise HTTPException(status_code=404, detail="No output directory for this job")

    file_path = os.path.join(job_dir, filename)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_path)


@router.delete("/{job_id}")
async def delete_ad_job(
    job_id: str,
    db: AsyncSession = Depends(db_session),
    current_user=Depends(get_current_user),
):
    """Delete an ad job and its output directory."""
    job = await _get_user_job(job_id, current_user.id, db)

    # Remove output directory if exists
    config = job.config or {}
    job_dir = config.get("job_dir", "")
    if job_dir and os.path.isdir(job_dir):
        shutil.rmtree(job_dir, ignore_errors=True)

    await db.delete(job)
    await db.commit()

    return {"message": "Job deleted", "job_id": job_id}
