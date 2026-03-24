"""Rotas de pipeline multi-agente."""

import asyncio
import logging
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import db_session
from src.api.models import PipelineRunRequest
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
async def pipeline_status(run_id: str, session: AsyncSession = Depends(db_session)):
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
    session: AsyncSession = Depends(db_session),
):
    from src.database.repositories.pipeline_repo import PipelineRunRepository

    repo = PipelineRunRepository(session)
    runs = await repo.list_runs(limit=limit, offset=offset, status=status, character_id=character_id)
    total = await repo.count_runs()
    items = [pipeline_run_list_item(run) for run in runs]
    return {"total": total, "offset": offset, "limit": limit, "runs": items}
