"""Rotas de pipeline multi-agente."""

import asyncio
import logging
import random
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import db_session, get_current_user, get_user_character
from src.api.models import PipelineRunRequest, ManualRunRequest, ApprovalRequest
from src.api.serializers import pipeline_run_to_dict, pipeline_run_list_item, content_package_summary

logger = logging.getLogger("clip-flow.api")

router = APIRouter(prefix="/pipeline", tags=["Pipeline"])

# Cache in-memory para layer updates em tempo real
_pipeline_layers: dict[str, dict] = {}


async def _run_pipeline_task(run_id: str, request: PipelineRunRequest):
    """Executa pipeline multi-agente em background e persiste no DB."""
    from src.pipeline.async_orchestrator import AsyncPipelineOrchestrator
    from src.database.session import get_session_factory
    from src.database.repositories.pipeline_repo import PipelineRunRepository
    from src.database.repositories.content_repo import ContentPackageRepository

    _pipeline_layers[run_id] = {
        "L1": {"status": "idle", "detail": "", "steps": {}},
        "L2": {"status": "idle", "detail": "", "steps": {}},
        "L3": {"status": "idle", "detail": "", "steps": {}},
        "L4": {"status": "idle", "detail": "", "steps": {}},
        "L5": {"status": "idle", "detail": "", "steps": {}},
        "current_layer": None,
    }

    def on_layer_update(layer: str, status: str, detail: str = "", step: str = ""):
        layers = _pipeline_layers.get(run_id)
        if not layers:
            return
        if step:
            layers[layer]["steps"][step] = {"status": status, "detail": detail}
        else:
            layers[layer]["status"] = status
            layers[layer]["detail"] = detail
            if status == "running":
                layers["current_layer"] = layer

    factory = get_session_factory()
    async with factory() as session:
        repo = PipelineRunRepository(session)
        await repo.update_run(run_id, {"status": "running", "started_at": datetime.now()})
        await session.commit()

    try:
        # Aplicar cost_mode por request (override temporario do config global)
        import config as _cfg
        original_cost_mode = _cfg.COST_MODE
        effective_cost_mode = request.cost_mode or _cfg.COST_MODE
        if request.cost_mode:
            _cfg.COST_MODE = request.cost_mode
            logger.info(f"Pipeline cost_mode override: {request.cost_mode}")

        # Carregar contexto do personagem
        char_kwargs = {}
        char_id = None
        if request.character_slug:
            try:
                from src.database.repositories.character_repo import CharacterRepository
                from src.database.converters import orm_to_character_config
                async with factory() as session:
                    char_repo = CharacterRepository(session)
                    char = await char_repo.get_by_slug(request.character_slug)
                    if char:
                        config = orm_to_character_config(char)
                        char_id = char.id
                        char_kwargs = {
                            "character_system_prompt": char.system_prompt or None,
                            "character_max_chars": char.rules_max_chars or None,
                            "character_dna": char.character_dna or None,
                            "character_negative_traits": char.negative_traits or None,
                            "character_composition": char.composition or None,
                            "character_rendering": char.rendering or None,
                            "character_refs_priority": config.refs_priority or None,
                            "character_watermark": char.watermark or char.handle or None,
                            "character_name": char.name or None,
                            "character_handle": char.handle or None,
                            "character_branded_hashtags": config.branded_hashtags or None,
                            "character_caption_prompt": config.caption_prompt or None,
                        }
                        if config.approved_refs_dir.exists() and any(config.approved_refs_dir.iterdir()):
                            char_kwargs["character_reference_dir"] = str(config.approved_refs_dir)
                        logger.info(f"Pipeline usando personagem: {char.name} (slug={request.character_slug})")
                    else:
                        logger.warning(f"Personagem nao encontrado: {request.character_slug}")
            except Exception as e:
                logger.warning(f"Erro ao carregar personagem: {e}, usando padrao")

        # Dedup cross-run: buscar temas recentes para excluir
        exclude_topics = None
        from config import DEDUP_CROSS_RUN_ENABLED, DEDUP_CROSS_RUN_DAYS
        if DEDUP_CROSS_RUN_ENABLED:
            try:
                async with factory() as session:
                    content_repo_dedup = ContentPackageRepository(session)
                    exclude_topics = await content_repo_dedup.get_recent_topics(
                        days=DEDUP_CROSS_RUN_DAYS
                    )
                    if exclude_topics:
                        logger.info(f"Dedup cross-run: {len(exclude_topics)} temas recentes excluidos")
            except Exception as e:
                logger.warning(f"Dedup cross-run falhou (continuando sem): {e}")

        # Converter TopicInput para dicts para o orchestrator
        manual_topics = None
        if request.topics:
            manual_topics = [{"topic": t.topic, "humor_angle": t.humor_angle} for t in request.topics]

        orchestrator = AsyncPipelineOrchestrator(
            images_per_run=request.count,
            phrases_per_topic=request.phrases_per_topic,
            use_comfyui=request.use_comfyui,
            use_gemini_image=request.use_gemini_image,
            use_phrase_context=request.use_phrase_context,
            on_layer_update=on_layer_update,
            theme_tags=request.theme_tags or None,
            exclude_topics=exclude_topics,
            carousel_count=request.carousel_count,
            cost_mode=effective_cost_mode,
            background_mode=request.background_mode,
            manual_topics=manual_topics,
            character_slug=request.character_slug or "mago-mestre",
            **char_kwargs,
        )
        result = await orchestrator.run()

        # Persistir resultado
        async with factory() as session:
            repo = PipelineRunRepository(session)
            content_repo = ContentPackageRepository(session)

            duration = None
            if result.finished_at and result.started_at:
                duration = (result.finished_at - result.started_at).total_seconds()

            layers_snapshot = _pipeline_layers.get(run_id, {})
            layers_data = {k: v for k, v in layers_snapshot.items() if k != "current_layer"}

            await repo.finish_run(run_id, status="completed", results={
                "trends_fetched": result.trends_fetched,
                "trend_events_queued": getattr(result, "trend_events_queued", 0),
                "work_orders_emitted": result.work_orders_emitted,
                "images_generated": result.images_generated,
                "packages_produced": result.packages_produced,
                "errors": result.errors,
                "layers_snapshot": layers_data,
            })

            run_obj = await repo.get_by_run_id(run_id)
            for pkg in result.content:
                source_val = getattr(pkg, "source", "")
                if hasattr(source_val, "value"):
                    source_val = source_val.value

                pkg_data = {
                    "pipeline_run_id": run_obj.id,
                    "phrase": pkg.phrase,
                    "topic": pkg.topic,
                    "image_path": pkg.image_path,
                    "background_path": getattr(pkg, "background_path", None),
                    "background_source": getattr(pkg, "background_source", "static"),
                    "caption": pkg.caption,
                    "hashtags": pkg.hashtags,
                    "quality_score": pkg.quality_score,
                    "source": source_val,
                    "image_metadata": getattr(pkg, "image_metadata", {}),
                    "phrase_alternatives": getattr(pkg, "phrase_alternatives", []),
                    "carousel_slides": getattr(pkg, "carousel_slides", []),
                }
                if char_id:
                    pkg_data["character_id"] = char_id

                content_pkg_orm = await content_repo.create(pkg_data)

                from src.database.models import GeneratedImage as GeneratedImageModel
                img_path = Path(pkg.image_path)
                metadata = getattr(pkg, "image_metadata", {})
                gen_img = GeneratedImageModel(
                    character_id=char_id if char_id else None,
                    content_package_id=content_pkg_orm.id,
                    filename=img_path.name,
                    file_path=str(img_path),
                    image_type="composed",
                    source=getattr(pkg, "background_source", "static"),
                    width=1080, height=1350,
                    theme_key=metadata.get("theme_key", ""),
                    prompt_used=metadata.get("prompt_used", "")[:4000],
                    image_metadata=metadata,
                )
                session.add(gen_img)

            await session.commit()

        logger.info(f"Pipeline {run_id} concluido: {result.packages_produced} packages")

    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        try:
            async with factory() as session:
                repo = PipelineRunRepository(session)
                await repo.finish_run(run_id, status="failed", results={
                    "errors": [str(e)],
                    "exception_type": type(e).__name__,
                    "traceback": tb,
                })
                await session.commit()
        except Exception:
            pass
        logger.error(f"Pipeline {run_id} falhou: {type(e).__name__}: {e}")
        logger.error(f"Pipeline {run_id} traceback:\n{tb}")
    finally:
        # Restaurar cost_mode original
        _cfg.COST_MODE = original_cost_mode
        async def _cleanup_layers():
            await asyncio.sleep(300)
            _pipeline_layers.pop(run_id, None)
        asyncio.create_task(_cleanup_layers())


@router.post("/run", summary="Pipeline multi-agente (background)")
async def run_pipeline(
    request: PipelineRunRequest,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
    from src.database.repositories.pipeline_repo import PipelineRunRepository

    run_id = uuid.uuid4().hex[:8]
    repo = PipelineRunRepository(session)
    run = await repo.create_run({
        "run_id": run_id, "status": "queued", "mode": "agents",
        "requested_count": request.count,
        "phrases_per_topic": request.phrases_per_topic,
        "use_comfyui": request.use_comfyui,
        "use_gemini_image": request.use_gemini_image,
        "use_phrase_context": request.use_phrase_context,
        "theme_tags": request.theme_tags or [],
    })
    await session.commit()

    background_tasks.add_task(_run_pipeline_task, run_id, request)
    return pipeline_run_to_dict(run)


@router.post("/run-sync", summary="Pipeline multi-agente (sincrono)")
async def run_pipeline_sync(
    request: PipelineRunRequest,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
    from src.database.repositories.pipeline_repo import PipelineRunRepository
    from src.database.repositories.content_repo import ContentPackageRepository

    run_id = uuid.uuid4().hex[:8]
    repo = PipelineRunRepository(session)
    await repo.create_run({
        "run_id": run_id, "status": "queued", "mode": "agents",
        "requested_count": request.count,
        "phrases_per_topic": request.phrases_per_topic,
        "use_comfyui": request.use_comfyui,
        "use_gemini_image": request.use_gemini_image,
        "use_phrase_context": request.use_phrase_context,
        "theme_tags": request.theme_tags or [],
    })
    await session.commit()

    await _run_pipeline_task(run_id, request)

    run = await repo.get_by_run_id(run_id)
    content_repo = ContentPackageRepository(session)
    packages = await content_repo.get_for_run(run.id) if run else []
    content = [content_package_summary(pkg) for pkg in packages]
    return pipeline_run_to_dict(run, content=content)


@router.get("/status/{run_id}", summary="Status do pipeline")
async def pipeline_status(run_id: str, current_user=Depends(get_current_user), session: AsyncSession = Depends(db_session)):
    from src.database.repositories.pipeline_repo import PipelineRunRepository
    from src.database.repositories.content_repo import ContentPackageRepository

    repo = PipelineRunRepository(session)
    run = await repo.get_by_run_id(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Pipeline run '{run_id}' nao encontrado")

    layers_cache = _pipeline_layers.get(run_id)

    content = []
    if run.status in ("completed", "failed"):
        content_repo = ContentPackageRepository(session)
        packages = await content_repo.get_for_run(run.id)
        content = [content_package_summary(pkg) for pkg in packages]

    return pipeline_run_to_dict(run, layers_cache=layers_cache, content=content)


@router.get("/runs", summary="Lista execucoes do pipeline")
async def list_pipeline_runs(
    status: str | None = Query(default=None),
    character_id: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
    from src.database.repositories.pipeline_repo import PipelineRunRepository

    repo = PipelineRunRepository(session)
    runs = await repo.list_runs(limit=limit, offset=offset, status=status, character_id=character_id)
    total = await repo.count_runs()
    items = [pipeline_run_list_item(run) for run in runs]
    return {"total": total, "offset": offset, "limit": limit, "runs": items}


# ============================================================
# Manual Pipeline (Phase 12 — zero Gemini Image calls)
# ============================================================

async def _run_manual_pipeline_task(run_id: str, request: ManualRunRequest):
    """Execute manual pipeline in background: compose memes with static backgrounds."""
    from src.database.session import get_session_factory
    from src.database.repositories.pipeline_repo import PipelineRunRepository
    from src.database.repositories.content_repo import ContentPackageRepository
    from src.database.models import GeneratedImage as GeneratedImageModel
    from src.image_maker import create_image
    import config as _cfg

    factory = get_session_factory()

    async with factory() as session:
        repo = PipelineRunRepository(session)
        await repo.update_run(run_id, {"status": "running", "started_at": datetime.now()})
        await session.commit()

    try:
        # Resolve character info
        char_id = None
        character_watermark = _cfg.WATERMARK_TEXT
        character_slug = request.character_slug or "mago-mestre"

        if request.character_slug:
            try:
                from src.database.repositories.character_repo import CharacterRepository
                async with factory() as session:
                    char_repo = CharacterRepository(session)
                    char = await char_repo.get_by_slug(request.character_slug)
                    if char:
                        char_id = char.id
                        character_watermark = char.watermark or char.handle or _cfg.WATERMARK_TEXT
            except Exception as e:
                logger.warning(f"Manual pipeline: failed to load character: {e}")

        # Resolve phrases
        if request.input_mode == "phrase":
            phrases = request.phrases[:request.count] if request.phrases else [""]
        else:
            # topic mode: use PhraseWorker to generate phrases from Gemini text
            try:
                from src.pipeline.workers.phrase_worker import PhraseWorker
                pw = PhraseWorker()
                generated = await asyncio.to_thread(
                    pw.generate_phrases, request.topic, count=request.count
                )
                phrases = generated if generated else [request.topic]
            except Exception as e:
                logger.warning(f"Manual pipeline: phrase generation failed: {e}, using topic as phrase")
                phrases = [request.topic] * request.count

        # Initialize Gemini Image client if enabled
        gemini_client = None
        if request.use_gemini_image:
            try:
                from src.image_gen.gemini_client import GeminiImageClient
                gemini_client = GeminiImageClient()
                if not gemini_client.is_available():
                    logger.warning("Gemini Image not available, falling back to static")
                    gemini_client = None
            except Exception as e:
                logger.warning(f"Failed to init Gemini Image: {e}")

        # Resolve background pool (used when Gemini is off or fails)
        bg_fixed = None  # User-selected specific image
        bg_pool = []     # Pool of backgrounds for random selection

        if request.background_image:
            bg_fixed = str(_cfg.BACKGROUNDS_DIR / character_slug / request.background_image)
        else:
            # Build pool of available backgrounds
            char_bg_dir = _cfg.BACKGROUNDS_DIR / character_slug
            if char_bg_dir.exists():
                for ext in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
                    bg_pool.extend(char_bg_dir.glob(ext))
            if not bg_pool and character_slug == "mago-mestre":
                legacy_dir = _cfg.BACKGROUNDS_DIR / "mago"
                if legacy_dir.exists():
                    for ext in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
                        bg_pool.extend(legacy_dir.glob(ext))
            if not bg_pool:
                all_bgs = list(_cfg.BACKGROUNDS_DIR.rglob("*.png")) + list(_cfg.BACKGROUNDS_DIR.rglob("*.jpg"))
                bg_pool = all_bgs if all_bgs else []

        # Filter by theme if possible
        if bg_pool and request.theme_key:
            theme_matched = [f for f in bg_pool if request.theme_key in f.stem]
            if theme_matched:
                bg_pool = theme_matched

        # Compose memes
        _cfg.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        results = []
        for i, phrase in enumerate(phrases):
            try:
                bg_path = None
                bg_source = "static"

                # Try Gemini generation first if enabled
                if gemini_client:
                    try:
                        gen_result = await gemini_client.agenerate_image(
                            situacao_key=request.theme_key,
                            phrase_context=phrase,
                        )
                        if gen_result:
                            bg_path = gen_result.path
                            bg_source = "gemini"
                            logger.info(f"Manual pipeline [{i}]: Gemini background generated: {bg_path}")
                    except Exception as e:
                        logger.warning(f"Manual pipeline [{i}]: Gemini failed ({e}), using static fallback")

                # Fallback to static background
                if not bg_path:
                    if bg_fixed:
                        bg_path = bg_fixed
                    elif bg_pool:
                        bg_path = str(random.choice(bg_pool))
                    else:
                        bg_path = "#1A1A3E"

                output_path = str(_cfg.OUTPUT_DIR / f"manual_{run_id}_{i}.png")
                image_path = await asyncio.to_thread(
                    create_image,
                    text=phrase,
                    background_path=bg_path,
                    output_path=output_path,
                    watermark_text="",  # watermark so no download/export
                    layout=request.layout,
                )
                results.append({
                    "phrase": phrase,
                    "image_path": image_path,
                    "background_path": bg_path,
                    "background_source": bg_source,
                })
            except Exception as e:
                logger.error(f"Manual pipeline: failed to compose image {i}: {e}")

        # L5 post-production (caption/hashtags)
        captions_and_tags = []
        if request.enable_l5 and results:
            try:
                from src.pipeline.workers.post_production_worker import PostProductionWorker
                pp = PostProductionWorker()
                for r in results:
                    try:
                        result_l5 = await asyncio.to_thread(
                            pp.generate_caption_and_hashtags, r["phrase"]
                        )
                        captions_and_tags.append(result_l5)
                    except Exception:
                        captions_and_tags.append({"caption": "", "hashtags": []})
            except ImportError:
                captions_and_tags = [{"caption": "", "hashtags": []} for _ in results]
        else:
            captions_and_tags = [{"caption": "", "hashtags": []} for _ in results]

        # Persist to DB
        async with factory() as session:
            repo = PipelineRunRepository(session)
            content_repo = ContentPackageRepository(session)

            run_obj = await repo.get_by_run_id(run_id)
            for i, r in enumerate(results):
                l5_data = captions_and_tags[i] if i < len(captions_and_tags) else {}
                pkg_data = {
                    "pipeline_run_id": run_obj.id,
                    "phrase": r["phrase"],
                    "topic": request.topic if request.input_mode == "topic" else "",
                    "source": "manual",
                    "image_path": r["image_path"],
                    "background_path": r["background_path"],
                    "background_source": "solid" if request.background_type == "solid" else "static",
                    "caption": l5_data.get("caption", ""),
                    "hashtags": l5_data.get("hashtags", []),
                    "approval_status": "pending",
                }
                if char_id:
                    pkg_data["character_id"] = char_id

                content_pkg = await content_repo.create(pkg_data)

                img_record = GeneratedImageModel(
                    character_id=char_id,
                    content_package_id=content_pkg.id,
                    filename=Path(r["image_path"]).name,
                    file_path=r["image_path"],
                    image_type="composed",
                    source="solid" if request.background_type == "solid" else "static",
                    width=1080, height=1350,
                    theme_key=request.theme_key,
                )
                session.add(img_record)

            await repo.finish_run(run_id, status="completed", results={
                "packages_produced": len(results),
                "images_generated": len(results),
                "errors": [],
            })
            await session.commit()

        logger.info(f"Manual pipeline {run_id} completed: {len(results)} packages")

    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        try:
            async with factory() as session:
                repo = PipelineRunRepository(session)
                await repo.finish_run(run_id, status="failed", results={
                    "errors": [str(e)],
                    "traceback": tb,
                })
                await session.commit()
        except Exception:
            pass
        logger.error(f"Manual pipeline {run_id} failed: {e}")


@router.post("/manual-run", summary="Manual pipeline run (optional Gemini Image)")
async def manual_run(
    request: ManualRunRequest,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
    """Run manual pipeline: compose memes with existing backgrounds or optional Gemini generation."""
    from src.database.repositories.pipeline_repo import PipelineRunRepository

    run_id = uuid.uuid4().hex[:8]

    # Resolve character_id from slug (if provided)
    character_id = None
    if request.character_slug:
        from src.database.repositories.character_repo import CharacterRepository
        char_repo = CharacterRepository(session)
        char = await char_repo.get_by_slug(request.character_slug)
        if char:
            character_id = char.id

    repo = PipelineRunRepository(session)
    run = await repo.create_run({
        "run_id": run_id,
        "status": "queued",
        "mode": "manual",
        "requested_count": request.count,
        "use_gemini_image": request.use_gemini_image,
        "theme_tags": [request.theme_key] if request.theme_key else [],
        "character_id": character_id,
    })
    await session.commit()

    background_tasks.add_task(_run_manual_pipeline_task, run_id, request)
    return pipeline_run_to_dict(run)


# ── Approve / Reject / Unreject ──────────────────────────────────────────────

@router.patch("/content/{package_id}/approve", summary="Approve content package")
async def approve_content(
    package_id: int,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
    from src.database.repositories.content_repo import ContentPackageRepository

    repo = ContentPackageRepository(session)
    pkg = await repo.get_by_id(package_id)
    if not pkg:
        raise HTTPException(404, "Package not found")
    await repo.update(package_id, {"approval_status": "approved"})
    await session.commit()
    return {"id": package_id, "approval_status": "approved"}


@router.patch("/content/{package_id}/reject", summary="Reject content package")
async def reject_content(
    package_id: int,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
    from src.database.repositories.content_repo import ContentPackageRepository

    repo = ContentPackageRepository(session)
    pkg = await repo.get_by_id(package_id)
    if not pkg:
        raise HTTPException(404, "Package not found")
    await repo.update(package_id, {"approval_status": "rejected"})
    await session.commit()
    return {"id": package_id, "approval_status": "rejected"}


@router.patch("/content/{package_id}/unreject", summary="Un-reject content package (back to pending) per D-14")
async def unreject_content(
    package_id: int,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
    from src.database.repositories.content_repo import ContentPackageRepository

    repo = ContentPackageRepository(session)
    pkg = await repo.get_by_id(package_id)
    if not pkg:
        raise HTTPException(404, "Package not found")
    await repo.update(package_id, {"approval_status": "pending"})
    await session.commit()
    return {"id": package_id, "approval_status": "pending"}


@router.patch("/content/bulk-approve", summary="Bulk approve packages per D-13")
async def bulk_approve(
    request: ApprovalRequest,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
    from src.database.repositories.content_repo import ContentPackageRepository

    repo = ContentPackageRepository(session)
    for pkg_id in request.package_ids:
        pkg = await repo.get_by_id(pkg_id)
        if not pkg:
            raise HTTPException(status_code=404, detail=f"Package {pkg_id} not found")
    count = await repo.bulk_update_approval(request.package_ids, "approved")
    await session.commit()
    return {"updated": count, "approval_status": "approved"}


@router.patch("/content/bulk-reject", summary="Bulk reject packages per D-13")
async def bulk_reject(
    request: ApprovalRequest,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
    from src.database.repositories.content_repo import ContentPackageRepository

    repo = ContentPackageRepository(session)
    for pkg_id in request.package_ids:
        pkg = await repo.get_by_id(pkg_id)
        if not pkg:
            raise HTTPException(status_code=404, detail=f"Package {pkg_id} not found")
    count = await repo.bulk_update_approval(request.package_ids, "rejected")
    await session.commit()
    return {"updated": count, "approval_status": "rejected"}


# ── Background image upload / listing ────────────────────────────────────────

@router.post("/backgrounds/upload", summary="Upload background image per D-05")
async def upload_background(
    file: UploadFile,
    character_slug: str = Query(...),
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
    # Validate file size: max 5MB
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(413, "File exceeds 5MB limit")

    # Validate file type
    ext = Path(file.filename).suffix.lower() if file.filename else ""
    if ext not in (".jpg", ".jpeg", ".png", ".webp"):
        raise HTTPException(415, "Unsupported format. Use JPG, PNG or WebP.")

    # Validate character exists (no ownership check — matches list_backgrounds behavior)
    from src.database.repositories.character_repo import CharacterRepository
    repo = CharacterRepository(session)
    char = await repo.get_by_slug(character_slug)
    if not char:
        raise HTTPException(status_code=404, detail="Character not found")

    # Save to assets/backgrounds/{character_slug}/
    from config import BACKGROUNDS_DIR
    bg_dir = BACKGROUNDS_DIR / character_slug
    bg_dir.mkdir(parents=True, exist_ok=True)
    dest = bg_dir / file.filename

    # Use asyncio.to_thread for file write (per Pitfall 5)
    await asyncio.to_thread(dest.write_bytes, content)

    # Get dimensions
    from PIL import Image as PILImage
    img = await asyncio.to_thread(PILImage.open, dest)
    w, h = img.size

    return {"filename": file.filename, "path": str(dest), "width": w, "height": h}


@router.get("/backgrounds/{character_slug}", summary="List backgrounds per D-04")
async def list_backgrounds(
    character_slug: str,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
    # Backgrounds are read-only static assets — no ownership check needed.
    # Only upload_background enforces ownership.
    from src.database.repositories.character_repo import CharacterRepository
    repo = CharacterRepository(session)
    char = await repo.get_by_slug(character_slug)
    if not char:
        raise HTTPException(status_code=404, detail="Character not found")

    files = []
    _EXTS = (".jpg", ".jpeg", ".png", ".webp")

    # Primary: character-specific directory
    bg_dir = Path("assets/backgrounds") / character_slug
    if bg_dir.exists():
        for f in sorted(bg_dir.iterdir()):
            if f.suffix.lower() in _EXTS:
                files.append({"filename": f.name, "path": str(f)})

    # Legacy fallback: assets/backgrounds/mago/ for mago-mestre
    if character_slug == "mago-mestre" and not files:
        legacy_dir = Path("assets/backgrounds") / "mago"
        if legacy_dir.exists():
            for f in sorted(legacy_dir.iterdir()):
                if f.suffix.lower() in _EXTS:
                    files.append({"filename": f.name, "path": str(f)})

    return {"backgrounds": files}


@router.get("/backgrounds/{character_slug}/image/{filename}", summary="Serve background image file")
async def serve_background_image(
    character_slug: str,
    filename: str,
):
    from fastapi.responses import FileResponse
    from config import BACKGROUNDS_DIR

    safe_name = Path(filename).name
    if safe_name != filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    # Primary: character-specific directory (absolute via config)
    path = BACKGROUNDS_DIR / character_slug / safe_name
    # Legacy fallback for mago-mestre
    if not path.exists() and character_slug == "mago-mestre":
        path = BACKGROUNDS_DIR / "mago" / safe_name

    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Background not found: {safe_name}")

    return FileResponse(str(path))


@router.delete("/backgrounds/{character_slug}/{filename}", summary="Delete background image")
async def delete_background(
    character_slug: str,
    filename: str,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
    # Validate character exists (no ownership check — matches list_backgrounds behavior)
    from src.database.repositories.character_repo import CharacterRepository
    repo = CharacterRepository(session)
    char = await repo.get_by_slug(character_slug)
    if not char:
        raise HTTPException(status_code=404, detail="Character not found")

    # Prevent path traversal
    safe_name = Path(filename).name
    if safe_name != filename or ".." in filename or "/" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    from config import BACKGROUNDS_DIR
    bg_path = BACKGROUNDS_DIR / character_slug / safe_name
    if not bg_path.exists():
        raise HTTPException(status_code=404, detail="Background not found")

    await asyncio.to_thread(bg_path.unlink)
    return {"deleted": safe_name}


# ── Themes with colors ──────────────────────────────────────────────────────

@router.get("/themes", summary="List themes with color palettes per D-02")
async def list_themes_with_colors(current_user=Depends(get_current_user)):
    import yaml

    themes_path = Path("config/themes.yaml")
    with open(themes_path, encoding="utf-8") as f:
        themes = yaml.safe_load(f)
    return {"themes": [
        {"key": t["key"], "label": t.get("label", t["key"]), "colors": t.get("colors", [])}
        for t in themes
    ]}
