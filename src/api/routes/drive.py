"""Rotas do Drive Browser (lista e serve imagens geradas) + Status."""

import logging
import re
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import db_session, get_current_user, output_dir, validate_filename

logger = logging.getLogger("clip-flow.api")

router = APIRouter(tags=["Drive"])


# ── Drive helpers ────────────────────────────────────────────────────────────

# Background filenames always contain a numeric timestamp (8+ digits in sequence):
#   api_{theme}_{YYYYMMDD_HHMMSS}.png    — API single generation
#   bg_{theme}_{YYYYMMDD_HHMMSS}.png     — Gemini background
#   mago_{theme}_{YYYYMMDD_HHMMSS}.png   — Gemini via batch
#   mago_{unix_ts}_{NNN}.png             — ComfyUI generation
#   single_{theme}_{YYYYMMDD_HHMMSS}.png — single generation
#   gemini_{theme}_{YYYYMMDD_HHMMSS}.png — Gemini direct
#   lote_{N}_{theme}_{YYYYMMDD_HHMMSS}.png — batch generation
# Meme filenames are phrase slugs (from create_image): lowercase words joined by
# underscores, no numeric timestamp. Also manual_{id}_{N}.png are composed memes.
_BG_FILENAME_RE = re.compile(
    r"^(api|bg|mago|single|gemini|lote)_.+\d{8,}.*\.png$"
)


def _is_background_filename(filename: str) -> bool:
    """Check if filename matches known background naming patterns."""
    return bool(_BG_FILENAME_RE.match(filename))


def _parse_theme_from_filename(stem: str) -> str:
    parts = stem.split("_")
    if len(parts) >= 3 and parts[0] in ("api", "mago", "single", "gemini"):
        return parts[1]
    if len(parts) >= 4 and parts[0] == "lote":
        return parts[2]
    return "unknown"


def _list_drive_images(theme_filter: str | None = None, category: str | None = None) -> list[dict]:
    from config import OUTPUT_DIR, GENERATED_MEMES_DIR, BACKGROUNDS_DIR
    bg_dir = output_dir()  # backgrounds_generated/

    # Classify files in backgrounds_generated/ by filename pattern.
    # Files whose names don't match known background patterns are reclassified
    # as memes (they are composed images with text that ended up here).
    bg_files = {}
    for f in bg_dir.glob("*.png"):
        if _is_background_filename(f.name):
            bg_files[f] = "background"
        else:
            bg_files[f] = "meme"

    # Scan assets/backgrounds/{character}/ directories for pre-existing images
    if BACKGROUNDS_DIR.exists():
        for char_dir in BACKGROUNDS_DIR.iterdir():
            if not char_dir.is_dir():
                continue
            for f in char_dir.glob("*.png"):
                if f not in bg_files and _is_background_filename(f.name):
                    bg_files[f] = "background"

    # Memes (compostos com frase) — from dedicated memes/ directory
    meme_files = {}
    if GENERATED_MEMES_DIR.exists():
        meme_files = {f: "meme" for f in GENERATED_MEMES_DIR.glob("*.png")}

    all_files = {**bg_files, **meme_files}
    files = sorted(all_files.keys(), key=lambda f: f.stat().st_mtime, reverse=True)

    result = []
    for f in files:
        cat = all_files[f]
        if category and cat != category:
            continue
        theme = _parse_theme_from_filename(f.stem) if cat == "background" else "meme"
        if theme_filter and theme != theme_filter:
            continue
        stat = f.stat()
        result.append({
            "filename": f.name,
            "theme": theme,
            "size_kb": round(stat.st_size / 1024, 1),
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "category": cat,
        })
    return result


# ── Drive routes ─────────────────────────────────────────────────────────────

@router.get("/drive/images", summary="Lista todas as imagens geradas")
def list_images(
    theme: str | None = Query(default=None),
    category: str | None = Query(default=None, pattern="^(background|meme)$"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user=Depends(get_current_user),
):
    imgs = _list_drive_images(theme, category)
    return {"total": len(imgs), "offset": offset, "limit": limit, "images": imgs[offset:offset + limit]}


@router.get("/drive/images/latest", summary="N imagens mais recentes")
def latest_images(count: int = Query(default=5, ge=1, le=50), current_user=Depends(get_current_user)):
    return {"count": count, "images": _list_drive_images()[:count]}


@router.get("/drive/images/by-theme/{theme_key}", summary="Imagens por tema")
def images_by_theme(theme_key: str, current_user=Depends(get_current_user)):
    imgs = _list_drive_images(theme_key)
    return {"theme": theme_key, "total": len(imgs), "images": imgs}


@router.get("/drive/images/{filename}", summary="Serve imagem PNG")
def get_image(filename: str):
    validate_filename(filename)
    from config import OUTPUT_DIR, GENERATED_MEMES_DIR, BACKGROUNDS_DIR
    # Check output dirs first, then scan assets/backgrounds/{character}/
    for directory in [output_dir(), OUTPUT_DIR, GENERATED_MEMES_DIR]:
        path = directory / filename
        if path.exists():
            return FileResponse(
                str(path), media_type="image/png", filename=filename,
                headers={"Cache-Control": "no-cache, must-revalidate"},
            )
    # Fallback: search in character background directories
    if BACKGROUNDS_DIR.exists():
        for char_dir in BACKGROUNDS_DIR.iterdir():
            if not char_dir.is_dir():
                continue
            path = char_dir / filename
            if path.exists():
                return FileResponse(
                    str(path), media_type="image/png", filename=filename,
                    headers={"Cache-Control": "no-cache, must-revalidate"},
                )
    raise HTTPException(status_code=404, detail=f"Imagem '{filename}' nao encontrada")


@router.get("/drive/images/{filename}/download", summary="Download imagem com watermark")
def download_image(filename: str, current_user=Depends(get_current_user)):
    """Serve imagem com watermark aplicada dinamicamente para download."""
    validate_filename(filename)
    from config import OUTPUT_DIR, GENERATED_MEMES_DIR, BACKGROUNDS_DIR
    from src.image_maker import stamp_watermark
    from fastapi.responses import Response

    search_dirs = [output_dir(), OUTPUT_DIR, GENERATED_MEMES_DIR]
    # Also search character background directories
    if BACKGROUNDS_DIR.exists():
        search_dirs.extend(d for d in BACKGROUNDS_DIR.iterdir() if d.is_dir())

    for directory in search_dirs:
        path = directory / filename
        if path.exists():
            img_bytes = stamp_watermark(str(path))
            return Response(
                content=img_bytes,
                media_type="image/png",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"',
                },
            )
    raise HTTPException(status_code=404, detail=f"Imagem '{filename}' nao encontrada")


@router.get("/drive/themes", summary="Temas nas imagens geradas")
def list_image_themes(current_user=Depends(get_current_user)):
    imgs = _list_drive_images()
    themes = sorted(set(i["theme"] for i in imgs))
    counts = {t: sum(1 for i in imgs if i["theme"] == t) for t in themes}
    return {"themes": themes, "counts": counts}


@router.get("/drive/health", summary="Estado da conexao")
def drive_health():
    out = output_dir()
    from config import COMFYUI_REFERENCE_DIR, OUTPUT_DIR
    bg_count = len(list(out.glob("*.png"))) if out.exists() else 0
    out_count = len(list(OUTPUT_DIR.glob("*.png"))) if OUTPUT_DIR.exists() else 0
    return {
        "output_folder": str(out),
        "output_exists": out.exists(),
        "total_images": bg_count + out_count,
        "refs_folder": str(COMFYUI_REFERENCE_DIR),
        "refs_exists": COMFYUI_REFERENCE_DIR.exists(),
    }


# ── Status ───────────────────────────────────────────────────────────────────

@router.get("/status", summary="Estado do servico", tags=["Sistema"])
async def api_status(current_user=Depends(get_current_user), session: AsyncSession = Depends(db_session)):
    from config import BACKGROUNDS_DIR
    from src.image_gen.gemini_client import MODELOS_IMAGEM
    from src.database.repositories.pipeline_repo import PipelineRunRepository
    from src.database.repositories.job_repo import BatchJobRepository

    out = output_dir()
    imagens_geradas = list(out.glob("*.png"))
    bgs = list(BACKGROUNDS_DIR.rglob("*.png")) + list(BACKGROUNDS_DIR.rglob("*.jpg"))

    gemini_ok = False
    refs_count = 0
    try:
        from src.image_gen.gemini_client import GeminiImageClient
        c = GeminiImageClient()
        gemini_ok = c.is_available()
        refs_count = len(c._referencias)
    except Exception:
        pass

    pipeline_repo = PipelineRunRepository(session)
    job_repo = BatchJobRepository(session)
    pipeline_count = await pipeline_repo.count_runs()
    jobs_total = await job_repo.count()
    jobs_running = len(await job_repo.list_jobs(status="running"))

    return {
        "api_key_ok": gemini_ok,
        "refs_loaded": refs_count,
        "output_path": str(out),
        "total_images_generated": len(imagens_geradas),
        "total_backgrounds": len(bgs),
        "jobs_total": jobs_total,
        "jobs_running": jobs_running,
        "pipeline_runs": pipeline_count,
        "models": MODELOS_IMAGEM,
        "pipeline": "Nano Banana (geracao + refinamento iterativo)",
    }
