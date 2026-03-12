"""Rotas do Drive Browser (lista e serve imagens geradas) + Status."""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import db_session, output_dir, validate_filename

logger = logging.getLogger("clip-flow.api")

router = APIRouter(tags=["Drive"])


# ── Drive helpers ────────────────────────────────────────────────────────────

def _parse_theme_from_filename(stem: str) -> str:
    parts = stem.split("_")
    if len(parts) >= 3 and parts[0] in ("api", "mago", "single", "gemini"):
        return parts[1]
    if len(parts) >= 4 and parts[0] == "lote":
        return parts[2]
    return "unknown"


def _list_drive_images(theme_filter: str | None = None) -> list[dict]:
    from config import OUTPUT_DIR
    out = output_dir()
    bg_files = set(out.glob("*.png"))
    out_files = set(OUTPUT_DIR.glob("*.png"))
    all_files = bg_files | out_files
    files = sorted(all_files, key=lambda f: f.stat().st_mtime, reverse=True)
    result = []
    for f in files:
        theme = _parse_theme_from_filename(f.stem)
        if theme_filter and theme != theme_filter:
            continue
        stat = f.stat()
        result.append({
            "filename": f.name,
            "theme": theme,
            "size_kb": round(stat.st_size / 1024, 1),
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        })
    return result


# ── Drive routes ─────────────────────────────────────────────────────────────

@router.get("/drive/images", summary="Lista todas as imagens geradas")
def list_images(
    theme: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    imgs = _list_drive_images(theme)
    return {"total": len(imgs), "offset": offset, "limit": limit, "images": imgs[offset:offset + limit]}


@router.get("/drive/images/latest", summary="N imagens mais recentes")
def latest_images(count: int = Query(default=5, ge=1, le=50)):
    return {"count": count, "images": _list_drive_images()[:count]}


@router.get("/drive/images/by-theme/{theme_key}", summary="Imagens por tema")
def images_by_theme(theme_key: str):
    imgs = _list_drive_images(theme_key)
    return {"theme": theme_key, "total": len(imgs), "images": imgs}


@router.get("/drive/images/{filename}", summary="Serve imagem PNG")
def get_image(filename: str):
    validate_filename(filename)
    path = output_dir() / filename
    if not path.exists():
        from config import OUTPUT_DIR
        path = OUTPUT_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Imagem '{filename}' nao encontrada")
    return FileResponse(str(path), media_type="image/png", filename=filename)


@router.get("/drive/themes", summary="Temas nas imagens geradas")
def list_image_themes():
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
async def api_status(session: AsyncSession = Depends(db_session)):
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
