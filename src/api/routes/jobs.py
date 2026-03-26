"""Rotas de batch jobs."""

import logging
import threading
import time
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import db_session, get_current_user, resolver_tema_batch, load_themes_config
from src.api.models import BatchRequest
from src.api.serializers import job_to_dict

logger = logging.getLogger("clip-flow.api")

router = APIRouter(prefix="/jobs", tags=["Batch"])

# Cache in-memory para progresso em tempo real
JOBS: dict[str, dict] = {}


def _criar_job(job_id: str) -> dict:
    JOBS[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "done": 0,
        "failed": 0,
        "total": 0,
        "results": [],
        "errors": [],
        "created_at": datetime.now().isoformat(),
        "finished_at": None,
        "auto_refine": False,
        "refinement_passes": 0,
    }
    return JOBS[job_id]


def _persist_job_to_db(job_id: str, job: dict):
    """Persiste job finalizado no DB (chamado de thread sync)."""
    import asyncio
    from src.database.session import get_session_factory

    async def _save():
        factory = get_session_factory()
        async with factory() as session:
            from src.database.repositories.job_repo import BatchJobRepository
            repo = BatchJobRepository(session)
            existing = await repo.get_by_job_id(job_id)
            if existing:
                await repo.finish_job(
                    job_id,
                    status=job["status"],
                    results=job.get("results", []),
                    errors=job.get("errors", []),
                )
                existing.done = job.get("done", 0)
                existing.failed = job.get("failed", 0)
                existing.total = job.get("total", 0)
                await session.flush()
            await session.commit()

    try:
        loop = asyncio.new_event_loop()
        loop.run_until_complete(_save())
        loop.close()
    except Exception as e:
        logger.warning(f"Erro ao persistir job {job_id} no DB: {e}")


def _run_batch_job(
    job_id: str, lote: list, n_refs: int, pausa: int,
    auto_refine: bool = False, refinement_passes: int = 1,
):
    """Worker de batch — roda em thread separada."""
    from src.image_gen.gemini_client import GeminiImageClient

    job = JOBS[job_id]
    job["status"] = "running"
    job["auto_refine"] = auto_refine
    job["refinement_passes"] = refinement_passes

    total = sum(
        (item.get("count", 1) if isinstance(item, dict) else 1)
        for item in lote
    )
    job["total"] = total

    client = GeminiImageClient(n_referencias=n_refs)
    gerado = 0

    for item in lote:
        situacao_key, acao, cenario, count = resolver_tema_batch(item)
        original_key = item if isinstance(item, str) else item.get("key", "custom")

        for i in range(count):
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            nome = f"api_{original_key}_{ts}"

            try:
                if auto_refine:
                    path = client.generate_with_refinement(
                        situacao_key=situacao_key,
                        descricao_custom=acao,
                        cenario_custom=cenario,
                        passes_refinamento=refinement_passes,
                        nome_arquivo=nome,
                    )
                    final_file = f"{nome}_final.png"
                else:
                    result = client.generate_image(
                        situacao_key=situacao_key,
                        descricao_custom=acao,
                        cenario_custom=cenario,
                        nome_arquivo=nome,
                    )
                    path = result.path if result else None
                    final_file = f"{nome}.png"

                gerado += 1
                if path:
                    job["done"] += 1
                    job["results"].append({
                        "theme": original_key, "file": final_file,
                        "path": path, "refined": auto_refine,
                    })
                else:
                    job["failed"] += 1
                    job["errors"].append(f"{original_key}: geracao falhou")
            except Exception as e:
                job["failed"] += 1
                job["errors"].append(f"{original_key}: {str(e)}")
                gerado += 1

            if gerado < total:
                time.sleep(pausa)

    job["status"] = "completed"
    job["finished_at"] = datetime.now().isoformat()
    logger.info(f"Job {job_id} concluido: {job['done']} OK / {job['failed']} falhas")
    _persist_job_to_db(job_id, job)


@router.post("/batch", summary="Lote com lista de temas")
async def create_batch(req: BatchRequest, current_user=Depends(get_current_user), session: AsyncSession = Depends(db_session)):
    from src.database.repositories.job_repo import BatchJobRepository

    job_id = uuid.uuid4().hex[:8]
    _criar_job(job_id)

    repo = BatchJobRepository(session)
    await repo.create({
        "job_id": job_id, "status": "queued", "total": len(req.themes),
        "auto_refine": req.auto_refine, "refinement_passes": req.refinement_passes,
    })

    threading.Thread(
        target=_run_batch_job,
        args=(job_id, req.themes, req.n_refs, req.pausa),
        kwargs={"auto_refine": req.auto_refine, "refinement_passes": req.refinement_passes},
        daemon=True,
    ).start()
    return {"job_id": job_id, "status": "queued", "total_themes": len(req.themes), "auto_refine": req.auto_refine}


@router.post("/batch/from-config", summary="Lote usando themes.yaml")
async def batch_from_config(
    auto_refine: bool = False,
    refinement_passes: int = 1,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
    from src.database.repositories.job_repo import BatchJobRepository

    themes = load_themes_config()
    if not themes:
        raise HTTPException(status_code=404, detail="themes.yaml nao encontrado")
    job_id = uuid.uuid4().hex[:8]
    _criar_job(job_id)

    repo = BatchJobRepository(session)
    await repo.create({
        "job_id": job_id, "status": "queued", "total": len(themes),
        "auto_refine": auto_refine, "refinement_passes": refinement_passes,
    })

    threading.Thread(
        target=_run_batch_job,
        args=(job_id, themes, 5, 15),
        kwargs={"auto_refine": auto_refine, "refinement_passes": refinement_passes},
        daemon=True,
    ).start()
    return {"job_id": job_id, "status": "queued", "total_themes": len(themes), "auto_refine": auto_refine}


@router.get("/{job_id}", summary="Status de um job")
async def get_job(job_id: str, current_user=Depends(get_current_user), session: AsyncSession = Depends(db_session)):
    job = JOBS.get(job_id)
    if job:
        return job

    from src.database.repositories.job_repo import BatchJobRepository
    repo = BatchJobRepository(session)
    try:
        db_job = await repo.get_by_job_id(job_id, user=current_user)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Forbidden")
    if not db_job:
        raise HTTPException(status_code=404, detail="Job nao encontrado")
    return job_to_dict(db_job)


@router.get("", summary="Todos os jobs")
async def list_jobs(
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
    from src.database.repositories.job_repo import BatchJobRepository

    repo = BatchJobRepository(session)
    db_jobs = await repo.list_jobs(limit=limit + offset, status=status, user=current_user)
    total_count = await repo.count(user=current_user)
    jobs = []
    for j in db_jobs:
        if j.job_id in JOBS:
            jobs.append(JOBS[j.job_id])
        else:
            jobs.append(job_to_dict(j))
    # Jobs in-memory nao persistidos
    for job_id, job in JOBS.items():
        if not any(j.get("job_id") == job_id for j in jobs):
            if status is None or job.get("status") == status:
                jobs.append(job)
    paged = jobs[offset:offset + limit]
    return {"total": len(jobs), "offset": offset, "limit": limit, "jobs": paged}
