"""Rotas de geracao de imagens (single, refine, compose).

Wired with UsageAwareKeySelector (Phase 9) for dual-key resolution.
"""

import asyncio
import random
from datetime import datetime
from pathlib import Path

import PIL.Image
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import resolver_tema, output_dir, get_current_user, db_session
from src.api.models import SingleRequest, RefineRequest, ComposeImageRequest
from src.services.key_selector import UsageAwareKeySelector
from src.database.repositories.usage_repo import UsageRepository

router = APIRouter(prefix="/generate", tags=["Geracao"])


async def _resolve_key(
    force_tier: str | None,
    current_user,
    session: AsyncSession,
):
    """Resolve API key via selector. Admin-only force_tier (D-08)."""
    import logging
    _log = logging.getLogger("clip-flow.generation")
    effective_force = force_tier if (force_tier and current_user.role == "admin") else None

    selector = UsageAwareKeySelector()
    resolution = await selector.resolve(
        user_id=current_user.id,
        session=session,
        force_tier=effective_force,
    )
    key_hint = f"...{resolution.api_key[-6:]}" if resolution.api_key else "EMPTY"
    _log.info(f"_resolve_key: tier={resolution.tier}, mode={resolution.mode}, key={key_hint}")
    return resolution


async def _increment_usage(session: AsyncSession, user_id: int, tier: str, cost_usd: float = 0.0):
    """Increment usage counter after successful generation."""
    repo = UsageRepository(session)
    await repo.increment(
        user_id=user_id,
        service="gemini_image",
        tier=tier.replace("gemini_", ""),  # "free" or "paid"
        cost_usd=cost_usd,
    )
    await session.commit()


@router.post("/single", summary="Gera uma imagem individual")
async def generate_single(
    req: SingleRequest,
    force_tier: str | None = Query(None, pattern="^(free|paid)$"),
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
    import logging
    _log = logging.getLogger("clip-flow.generation")

    from src.image_gen.gemini_client import GeminiImageClient

    _log.info(f"[single] theme={req.theme_key}, auto_refine={req.auto_refine}")

    try:
        resolution = await _resolve_key(force_tier, current_user, session)
    except Exception as e:
        _log.error(f"[single] key resolution failed: {e}")
        raise HTTPException(status_code=500, detail=f"Key resolution failed: {e}")

    _log.info(f"[single] key resolved: tier={resolution.tier}, mode={resolution.mode}")

    client = GeminiImageClient()
    if not client.is_available():
        _log.warning("[single] Gemini Image not available (no refs or API key)")
        raise HTTPException(status_code=503, detail="Gemini Image nao disponivel (sem referencias ou API key)")

    situacao_key, acao, cenario = resolver_tema(req.theme_key, req.acao_custom, req.cenario_custom)
    _log.info(f"[single] situacao={situacao_key}, acao={acao[:60]}...")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome = f"single_{req.theme_key}_{ts}"

    try:
        if req.auto_refine:
            path = await asyncio.to_thread(
                client.generate_with_refinement,
                situacao_key,
                acao,
                cenario,
                req.refinement_passes,
                "",  # instrucao_refinamento
                nome,
                resolution.api_key,
            )
            final_file = f"{nome}_final.png" if path else None
        else:
            result = await asyncio.to_thread(
                lambda: client.generate_image(
                    situacao_key=situacao_key,
                    descricao_custom=acao,
                    cenario_custom=cenario,
                    nome_arquivo=nome,
                    api_key=resolution.api_key,
                )
            )
            path = result.path if result else None
            final_file = f"{nome}.png" if path else None
    except Exception as e:
        _log.error(f"[single] generation failed: {type(e).__name__}: {e}")
        raise HTTPException(status_code=502, detail=f"Gemini generation failed: {e}")

    cost = 0.0
    if not req.auto_refine and result:
        cost = result.estimated_cost_usd

    if path:
        _log.info(f"[single] success: {path}")
        await _increment_usage(session, current_user.id, resolution.tier, cost_usd=cost)
    else:
        _log.warning(f"[single] all models failed, no image generated")

    return {
        "success": path is not None,
        "theme": req.theme_key,
        "file": final_file,
        "path": path,
        "refined": req.auto_refine,
        "refinement_passes": req.refinement_passes if req.auto_refine else 0,
        "tier": resolution.tier,
        "key_mode": resolution.mode,
        "estimated_cost_usd": cost,
    }


@router.post("/refine", summary="Refina uma imagem existente", tags=["Refinamento"])
async def refine_existing(
    req: RefineRequest,
    force_tier: str | None = Query(None, pattern="^(free|paid)$"),
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
    from src.image_gen.gemini_client import GeminiImageClient
    from src.api.deps import validate_filename

    resolution = await _resolve_key(force_tier, current_user, session)

    validate_filename(req.filename)
    out = output_dir()
    path = out / req.filename
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Imagem nao encontrada: {req.filename}")

    try:
        img_base = PIL.Image.open(path).convert("RGB")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao abrir imagem: {e}")

    client = GeminiImageClient()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = Path(req.filename).stem

    img = img_base
    resultados = []
    for i in range(req.passes):
        nome_ref = f"{stem}_ref{i + 1}_{ts}"
        ref_path = await asyncio.to_thread(
            lambda im=img, nr=nome_ref: client.refine_image(
                imagem_base=im,
                instrucao=req.instrucao,
                referencias_adicionais=req.referencias_adicionais,
                nome_arquivo=nr,
                api_key=resolution.api_key,
            )
        )
        if ref_path is not None:
            img = PIL.Image.open(ref_path).convert("RGB")
            resultados.append({"pass": i + 1, "file": f"{nome_ref}.png", "path": ref_path})
        else:
            break

    # Estimate cost for refine passes (output-only estimate since we lack ref dims)
    refine_cost = 0.0
    if resultados:
        from src.image_gen.gemini_client import estimate_generation_cost
        refine_cost = estimate_generation_cost([], 0)["estimated_cost_usd"] * len(resultados)
        await _increment_usage(session, current_user.id, resolution.tier, cost_usd=refine_cost)

    return {
        "success": len(resultados) > 0,
        "original": req.filename,
        "passes_completed": len(resultados),
        "passes_requested": req.passes,
        "results": resultados,
        "final_file": resultados[-1]["file"] if resultados else None,
        "tier": resolution.tier,
        "key_mode": resolution.mode,
        "estimated_cost_usd": refine_cost,
    }


@router.post("/compose", summary="Background + frase = imagem final")
async def compose_image(
    req: ComposeImageRequest,
    force_tier: str | None = Query(None, pattern="^(free|paid)$"),
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
    from src.image_gen.gemini_client import GeminiImageClient
    from src.image_maker import create_image
    from config import GENERATED_BACKGROUNDS_DIR, OUTPUT_DIR

    resolution = await _resolve_key(force_tier, current_user, session)

    bg_path = None
    bg_result = None
    generated_bg = False

    if req.background_filename:
        candidate = GENERATED_BACKGROUNDS_DIR / req.background_filename
        if not candidate.exists():
            candidate = OUTPUT_DIR / req.background_filename
        if candidate.exists():
            bg_path = str(candidate)
        else:
            raise HTTPException(status_code=404, detail=f"Background '{req.background_filename}' nao encontrado")
    else:
        client = GeminiImageClient()
        phrase_ctx = req.phrase if req.use_phrase_context else ""

        if client.is_available():
            if req.auto_refine:
                bg_path = await asyncio.to_thread(
                    client.generate_with_refinement,
                    req.situacao, req.descricao_custom, req.cenario_custom,
                    req.refinement_passes,
                    "",  # instrucao_refinamento
                    "",  # nome_arquivo
                    resolution.api_key,
                )
            else:
                bg_result = await asyncio.to_thread(
                    lambda: client.generate_image(
                        situacao_key=req.situacao,
                        descricao_custom=req.descricao_custom,
                        cenario_custom=req.cenario_custom,
                        phrase_context=phrase_ctx,
                        api_key=resolution.api_key,
                    )
                )
                bg_path = bg_result.path if bg_result else None
            if bg_path:
                generated_bg = True

    if bg_path is None:
        from config import BACKGROUNDS_DIR
        bgs = list(BACKGROUNDS_DIR.rglob("*.png")) + list(BACKGROUNDS_DIR.rglob("*.jpg"))
        if not bgs:
            raise HTTPException(status_code=500, detail="Nenhum background disponivel")
        bg_path = str(random.choice(bgs))

    image_path = await asyncio.to_thread(create_image, req.phrase, bg_path)

    compose_cost = 0.0
    if generated_bg and not req.auto_refine and bg_result:
        compose_cost = bg_result.estimated_cost_usd

    if generated_bg:
        await _increment_usage(session, current_user.id, resolution.tier, cost_usd=compose_cost)

    return {
        "success": True,
        "image_path": image_path,
        "phrase": req.phrase,
        "background": bg_path,
        "tier": resolution.tier,
        "key_mode": resolution.mode,
        "estimated_cost_usd": compose_cost,
    }
