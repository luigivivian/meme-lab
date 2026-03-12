"""Rotas de content packages, generated images, e frases."""

import asyncio
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import db_session
from src.api.models import GeneratePhrasesRequest
from src.api.serializers import content_package_to_dict, generated_image_to_dict

router = APIRouter(tags=["Content"])


# ── Content Packages ─────────────────────────────────────────────────────────

@router.get("/content", summary="Lista content packages com filtros")
async def list_content_packages(
    character_id: int | None = Query(default=None),
    pipeline_run_id: int | None = Query(default=None),
    min_quality: float | None = Query(default=None, ge=0.0, le=1.0),
    is_published: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(db_session),
):
    from src.database.repositories.content_repo import ContentPackageRepository

    repo = ContentPackageRepository(session)
    packages = await repo.list_packages(
        limit=limit, offset=offset, character_id=character_id,
        pipeline_run_id=pipeline_run_id, min_quality=min_quality,
        is_published=is_published,
    )
    total = await repo.count(character_id=character_id)
    items = [content_package_to_dict(pkg) for pkg in packages]
    return {"total": total, "offset": offset, "limit": limit, "packages": items}


@router.get("/content/{package_id}", summary="Detalhes de um content package")
async def get_content_package(package_id: int, session: AsyncSession = Depends(db_session)):
    from src.database.repositories.content_repo import ContentPackageRepository

    repo = ContentPackageRepository(session)
    pkg = await repo.get_by_id(package_id)
    if not pkg:
        raise HTTPException(status_code=404, detail=f"Content package {package_id} nao encontrado")
    return content_package_to_dict(pkg)


@router.post("/content/{package_id}/publish", summary="Marcar como publicado")
async def publish_content_package(package_id: int, session: AsyncSession = Depends(db_session)):
    from src.database.repositories.content_repo import ContentPackageRepository

    repo = ContentPackageRepository(session)
    pkg = await repo.mark_published(package_id)
    if not pkg:
        raise HTTPException(status_code=404, detail=f"Content package {package_id} nao encontrado")
    return {"id": pkg.id, "is_published": True, "published_at": pkg.published_at.isoformat()}


# ── Generated Images ─────────────────────────────────────────────────────────

@router.get("/images", summary="Lista imagens geradas com filtros", tags=["Images"])
async def list_generated_images(
    character_id: int | None = Query(default=None),
    image_type: str | None = Query(default=None),
    source: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(db_session),
):
    from src.database.repositories.content_repo import GeneratedImageRepository

    repo = GeneratedImageRepository(session)
    images = await repo.list_images(
        limit=limit, offset=offset, character_id=character_id,
        image_type=image_type, source=source,
    )
    total = await repo.count(character_id=character_id)
    items = [generated_image_to_dict(img) for img in images]
    return {"total": total, "offset": offset, "limit": limit, "images": items}


@router.get("/images/{image_id}", summary="Detalhes de uma imagem gerada", tags=["Images"])
async def get_generated_image(image_id: int, session: AsyncSession = Depends(db_session)):
    from src.database.repositories.content_repo import GeneratedImageRepository

    repo = GeneratedImageRepository(session)
    img = await repo.get_by_id(image_id)
    if not img:
        raise HTTPException(status_code=404, detail=f"Imagem {image_id} nao encontrada")
    return generated_image_to_dict(img)


@router.get("/images/{image_id}/serve", summary="Serve arquivo da imagem", tags=["Images"])
async def serve_generated_image(image_id: int, session: AsyncSession = Depends(db_session)):
    from src.database.repositories.content_repo import GeneratedImageRepository

    repo = GeneratedImageRepository(session)
    img = await repo.get_by_id(image_id)
    if not img:
        raise HTTPException(status_code=404, detail=f"Imagem {image_id} nao encontrada")

    path = Path(img.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Arquivo nao encontrado: {img.file_path}")
    return FileResponse(str(path), media_type="image/png", filename=img.filename)


# ── Phrases ──────────────────────────────────────────────────────────────────

@router.post("/phrases/generate", summary="Gera frases do Mago Mestre", tags=["Frases"])
async def generate_phrases_route(req: GeneratePhrasesRequest):
    from src.phrases import generate_phrases
    phrases = await asyncio.to_thread(generate_phrases, req.topic, req.count)
    return {"topic": req.topic, "phrases": phrases, "count": len(phrases)}
