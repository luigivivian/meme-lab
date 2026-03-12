"""Rotas de geracao de imagens (single, refine, compose)."""

import asyncio
import random
from datetime import datetime
from pathlib import Path

import PIL.Image
from fastapi import APIRouter, HTTPException

from src.api.deps import resolver_tema, output_dir
from src.api.models import SingleRequest, RefineRequest, ComposeImageRequest

router = APIRouter(prefix="/generate", tags=["Geracao"])


@router.post("/single", summary="Gera uma imagem individual")
def generate_single(req: SingleRequest):
    from src.image_gen.gemini_client import GeminiImageClient

    client = GeminiImageClient()
    if not client.is_available():
        raise HTTPException(status_code=503, detail="Gemini Image nao disponivel")

    situacao_key, acao, cenario = resolver_tema(req.theme_key, req.acao_custom, req.cenario_custom)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome = f"single_{req.theme_key}_{ts}"

    if req.auto_refine:
        path = client.generate_with_refinement(
            situacao_key=situacao_key,
            descricao_custom=acao,
            cenario_custom=cenario,
            passes_refinamento=req.refinement_passes,
            nome_arquivo=nome,
        )
        final_file = f"{nome}_final.png" if path else None
    else:
        result = client.generate_image(
            situacao_key=situacao_key,
            descricao_custom=acao,
            cenario_custom=cenario,
            nome_arquivo=nome,
        )
        path = result.path if result else None
        final_file = f"{nome}.png" if path else None

    return {
        "success": path is not None,
        "theme": req.theme_key,
        "file": final_file,
        "path": path,
        "refined": req.auto_refine,
        "refinement_passes": req.refinement_passes if req.auto_refine else 0,
    }


@router.post("/refine", summary="Refina uma imagem existente", tags=["Refinamento"])
def refine_existing(req: RefineRequest):
    from src.image_gen.gemini_client import GeminiImageClient
    from src.api.deps import validate_filename

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
        ref_path = client.refine_image(
            imagem_base=img,
            instrucao=req.instrucao,
            referencias_adicionais=req.referencias_adicionais,
            nome_arquivo=nome_ref,
        )
        if ref_path is not None:
            img = PIL.Image.open(ref_path).convert("RGB")
            resultados.append({"pass": i + 1, "file": f"{nome_ref}.png", "path": ref_path})
        else:
            break

    return {
        "success": len(resultados) > 0,
        "original": req.filename,
        "passes_completed": len(resultados),
        "passes_requested": req.passes,
        "results": resultados,
        "final_file": resultados[-1]["file"] if resultados else None,
    }


@router.post("/compose", summary="Background + frase = imagem final")
async def compose_image(req: ComposeImageRequest):
    from src.image_gen.gemini_client import GeminiImageClient
    from src.image_maker import create_image
    from config import GENERATED_BACKGROUNDS_DIR, OUTPUT_DIR

    bg_path = None

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
                )
            else:
                bg_result = await asyncio.to_thread(
                    lambda: client.generate_image(
                        situacao_key=req.situacao,
                        descricao_custom=req.descricao_custom,
                        cenario_custom=req.cenario_custom,
                        phrase_context=phrase_ctx,
                    )
                )
                bg_path = bg_result.path if bg_result else None

    if bg_path is None:
        from config import BACKGROUNDS_DIR
        bgs = list(BACKGROUNDS_DIR.rglob("*.png")) + list(BACKGROUNDS_DIR.rglob("*.jpg"))
        if not bgs:
            raise HTTPException(status_code=500, detail="Nenhum background disponivel")
        bg_path = str(random.choice(bgs))

    image_path = await asyncio.to_thread(create_image, req.phrase, bg_path)

    return {
        "success": True,
        "image_path": image_path,
        "phrase": req.phrase,
        "background": bg_path,
    }
