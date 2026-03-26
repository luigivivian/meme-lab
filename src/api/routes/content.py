"""Rotas de content packages, generated images, frases e export ZIP."""

import asyncio
import io
import json
import re
import zipfile
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import db_session, get_current_user
from src.api.models import BatchExportRequest, GeneratePhrasesRequest
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
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
    from src.database.repositories.content_repo import ContentPackageRepository

    repo = ContentPackageRepository(session)
    packages = await repo.list_packages(
        limit=limit, offset=offset, character_id=character_id,
        pipeline_run_id=pipeline_run_id, min_quality=min_quality,
        is_published=is_published, user=current_user,
    )
    total = await repo.count(character_id=character_id, user=current_user)
    items = [content_package_to_dict(pkg) for pkg in packages]
    return {"total": total, "offset": offset, "limit": limit, "packages": items}


@router.get("/content/{package_id}", summary="Detalhes de um content package")
async def get_content_package(package_id: int, current_user=Depends(get_current_user), session: AsyncSession = Depends(db_session)):
    from src.database.repositories.content_repo import ContentPackageRepository

    repo = ContentPackageRepository(session)
    try:
        pkg = await repo.get_by_id(package_id, user=current_user)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Forbidden")
    if not pkg:
        raise HTTPException(status_code=404, detail=f"Content package {package_id} nao encontrado")
    return content_package_to_dict(pkg)


@router.post("/content/{package_id}/publish", summary="Marcar como publicado")
async def publish_content_package(package_id: int, current_user=Depends(get_current_user), session: AsyncSession = Depends(db_session)):
    from src.database.repositories.content_repo import ContentPackageRepository

    repo = ContentPackageRepository(session)
    try:
        pkg = await repo.get_by_id(package_id, user=current_user)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Forbidden")
    if not pkg:
        raise HTTPException(status_code=404, detail=f"Content package {package_id} nao encontrado")
    pkg = await repo.mark_published(package_id)
    return {"id": pkg.id, "is_published": True, "published_at": pkg.published_at.isoformat()}


# ── Export ZIP ────────────────────────────────────────────────────────────────


def _slugify(text: str) -> str:
    """Converte texto para slug seguro para nome de pasta/arquivo."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return text[:60] or "sem-topico"


def _build_metadata(pkg, image_found: bool) -> dict:
    """Monta dict de metadados para export de um package."""
    char_name = None
    if pkg.character:
        char_name = pkg.character.name

    meta = {
        "id": pkg.id,
        "phrase": pkg.phrase,
        "topic": pkg.topic,
        "source": pkg.source,
        "quality_score": pkg.quality_score,
        "background_source": pkg.background_source,
        "is_published": pkg.is_published,
        "created_at": pkg.created_at.isoformat() if pkg.created_at else None,
        "character": char_name,
        "image_found": image_found,
    }
    if not image_found:
        meta["image_note"] = "Arquivo de imagem nao encontrado no disco"
    return meta


def _resolve_watermark(pkg) -> str:
    """Resolve watermark text from character or global config."""
    if pkg.character and getattr(pkg.character, "watermark", None):
        return pkg.character.watermark
    from config import WATERMARK_TEXT
    return WATERMARK_TEXT


def _add_package_to_zip(zf: zipfile.ZipFile, pkg, prefix: str = "") -> dict:
    """Adiciona arquivos de um package ao ZIP. Retorna metadados.

    Watermark e aplicada dinamicamente no export — imagens originais ficam sem watermark.
    Suporta carousel: se pkg.carousel_slides tiver multiplos paths,
    exporta como slide_01.png, slide_02.png, etc.
    """
    from src.image_maker import stamp_watermark

    carousel_slides = getattr(pkg, "carousel_slides", None) or []
    is_carousel = bool(carousel_slides) and len(carousel_slides) > 1
    image_found = False
    wm_text = _resolve_watermark(pkg)

    if is_carousel:
        # Carousel: slides numerados com watermark
        for i, slide_path in enumerate(carousel_slides, 1):
            sp = Path(slide_path)
            if sp.exists():
                image_found = True
                zf.writestr(f"{prefix}slide_{i:02d}.png", stamp_watermark(str(sp), wm_text))
    else:
        # Imagem unica com watermark
        if pkg.image_path:
            img_path = Path(pkg.image_path)
            if img_path.exists():
                image_found = True
                zf.writestr(f"{prefix}image.png", stamp_watermark(str(img_path), wm_text))

    # Caption
    caption_text = pkg.caption or ""
    zf.writestr(f"{prefix}caption.txt", caption_text)

    # Hashtags (uma por linha)
    hashtags = pkg.hashtags or []
    hashtags_text = "\n".join(hashtags) if hashtags else ""
    zf.writestr(f"{prefix}hashtags.txt", hashtags_text)

    # Metadata
    meta = _build_metadata(pkg, image_found)
    meta["is_carousel"] = is_carousel
    meta["slide_count"] = len(carousel_slides) if is_carousel else 1
    zf.writestr(
        f"{prefix}metadata.json",
        json.dumps(meta, ensure_ascii=False, indent=2),
    )
    return meta


@router.get("/content/{package_id}/export", summary="Exporta content package como ZIP")
async def export_content_package(package_id: int, current_user=Depends(get_current_user), session: AsyncSession = Depends(db_session)):
    """Exporta um content package como arquivo .zip com imagem, caption, hashtags e metadados."""
    from src.database.repositories.content_repo import ContentPackageRepository

    repo = ContentPackageRepository(session)
    try:
        await repo.get_by_id(package_id, user=current_user)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Forbidden")
    pkg = await repo.get_by_id_with_character(package_id)
    if not pkg:
        raise HTTPException(status_code=404, detail=f"Content package {package_id} nao encontrado")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        _add_package_to_zip(zf, pkg)

    buf.seek(0)
    filename = f"memelab_pack_{package_id}.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/content/export", summary="Exporta batch de content packages como ZIP")
async def export_content_batch(req: BatchExportRequest, current_user=Depends(get_current_user), session: AsyncSession = Depends(db_session)):
    """Exporta multiplos content packages como arquivo .zip com pasta por package e summary."""
    from src.database.repositories.content_repo import ContentPackageRepository

    if len(req.package_ids) > 50:
        raise HTTPException(status_code=400, detail="Maximo de 50 packages por export")

    repo = ContentPackageRepository(session)
    packages = await repo.get_by_ids(req.package_ids, load_character=True, user=current_user)

    if not packages:
        raise HTTPException(status_code=404, detail="Nenhum content package encontrado para os IDs informados")

    # Montar ZIP com pasta por package
    buf = io.BytesIO()
    summary_items = []

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for pkg in packages:

            topic_slug = _slugify(pkg.topic) if pkg.topic else "sem-topico"
            folder = f"{pkg.id}_{topic_slug}/"

            meta = _add_package_to_zip(zf, pkg, prefix=folder)
            summary_items.append({
                "id": pkg.id,
                "topic": pkg.topic,
                "phrase": pkg.phrase,
                "quality_score": pkg.quality_score,
                "image_found": meta["image_found"],
                "character": meta.get("character"),
            })

        # Summary na raiz do ZIP
        summary = {
            "exported_at": datetime.now().isoformat(),
            "total_packages": len(packages),
            "requested_ids": req.package_ids,
            "found_ids": [pkg.id for pkg in packages],
            "missing_ids": [pid for pid in req.package_ids if pid not in {pkg.id for pkg in packages}],
            "packages": summary_items,
        }
        zf.writestr("summary.json", json.dumps(summary, ensure_ascii=False, indent=2))

    buf.seek(0)
    date_str = datetime.now().strftime("%Y%m%d")
    filename = f"memelab_batch_{date_str}.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Swap Phrase (A/B Testing) ─────────────────────────────────────────────────

@router.post("/content/{package_id}/swap-phrase", summary="Troca a frase ativa por uma alternativa e recompoe imagem")
async def swap_phrase(
    package_id: int,
    phrase_index: int = Query(description="Indice da alternativa (0-based) no array phrase_alternatives"),
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
    """Troca a frase principal por uma das alternativas A/B e recompoe a imagem."""
    from src.database.repositories.content_repo import ContentPackageRepository
    from src.image_maker import create_image

    repo = ContentPackageRepository(session)
    try:
        pkg = await repo.get_by_id(package_id, user=current_user)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Forbidden")
    if not pkg:
        raise HTTPException(status_code=404, detail=f"Content package {package_id} nao encontrado")

    alternatives = pkg.phrase_alternatives or []
    if not alternatives:
        raise HTTPException(status_code=400, detail="Package nao tem alternativas de frase (A/B testing desabilitado)")

    if phrase_index < 0 or phrase_index >= len(alternatives):
        raise HTTPException(status_code=400, detail=f"Indice invalido. Disponiveis: 0-{len(alternatives)-1}")

    new_phrase = alternatives[phrase_index].get("frase", "")
    if not new_phrase:
        raise HTTPException(status_code=400, detail="Alternativa sem texto de frase")

    old_phrase = pkg.phrase

    # Recompor imagem com nova frase
    bg_path = pkg.background_path or pkg.image_path
    layout = (pkg.image_metadata or {}).get("layout", "bottom")

    new_image_path = await asyncio.to_thread(
        create_image, new_phrase, bg_path, None, None, layout,
    )

    # Atualizar package no DB
    await repo.update(package_id, {
        "phrase": new_phrase,
        "image_path": new_image_path,
    })

    return {
        "id": package_id,
        "old_phrase": old_phrase,
        "new_phrase": new_phrase,
        "new_image_path": new_image_path,
        "alternative_index": phrase_index,
    }


# ── Generated Images ─────────────────────────────────────────────────────────

@router.get("/images", summary="Lista imagens geradas com filtros", tags=["Images"])
async def list_generated_images(
    character_id: int | None = Query(default=None),
    image_type: str | None = Query(default=None),
    source: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
    from src.database.repositories.content_repo import GeneratedImageRepository

    repo = GeneratedImageRepository(session)
    images = await repo.list_images(
        limit=limit, offset=offset, character_id=character_id,
        image_type=image_type, source=source, user=current_user,
    )
    total = await repo.count(character_id=character_id, user=current_user)
    items = [generated_image_to_dict(img) for img in images]
    return {"total": total, "offset": offset, "limit": limit, "images": items}


@router.get("/images/{image_id}", summary="Detalhes de uma imagem gerada", tags=["Images"])
async def get_generated_image(image_id: int, current_user=Depends(get_current_user), session: AsyncSession = Depends(db_session)):
    from src.database.repositories.content_repo import GeneratedImageRepository

    repo = GeneratedImageRepository(session)
    try:
        img = await repo.get_by_id(image_id, user=current_user)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Forbidden")
    if not img:
        raise HTTPException(status_code=404, detail=f"Imagem {image_id} nao encontrada")
    return generated_image_to_dict(img)


@router.get("/images/{image_id}/serve", summary="Serve arquivo da imagem", tags=["Images"])
async def serve_generated_image(image_id: int, current_user=Depends(get_current_user), session: AsyncSession = Depends(db_session)):
    from src.database.repositories.content_repo import GeneratedImageRepository

    repo = GeneratedImageRepository(session)
    try:
        img = await repo.get_by_id(image_id, user=current_user)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Forbidden")
    if not img:
        raise HTTPException(status_code=404, detail=f"Imagem {image_id} nao encontrada")

    path = Path(img.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Arquivo nao encontrado: {img.file_path}")
    return FileResponse(str(path), media_type="image/png", filename=img.filename)


# ── Phrases ──────────────────────────────────────────────────────────────────

@router.post("/phrases/generate", summary="Gera frases do Mago Mestre", tags=["Frases"])
async def generate_phrases_route(req: GeneratePhrasesRequest, current_user=Depends(get_current_user)):
    from src.phrases import generate_phrases
    phrases = await asyncio.to_thread(generate_phrases, req.topic, req.count)
    return {"topic": req.topic, "phrases": phrases, "count": len(phrases)}
