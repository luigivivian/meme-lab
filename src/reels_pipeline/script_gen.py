"""Reels script generation — Gemini multimodal with structured JSON output."""

import json
import logging
from pathlib import Path

from google.genai import types

from src.llm_client import _get_client
from src.reels_pipeline.config import (
    REELS_SCRIPT_LANGUAGE,
    REELS_SCRIPT_MODEL,
)

logger = logging.getLogger("clip-flow.reels.script_gen")

# Structured JSON schema for Gemini response_schema (per RESEARCH Pattern 2)
ROTEIRO_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "titulo": {"type": "STRING"},
        "gancho": {"type": "STRING"},
        "narracao_completa": {"type": "STRING"},
        "cenas": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "imagem_index": {"type": "INTEGER"},
                    "duracao_segundos": {"type": "NUMBER"},
                    "narracao": {"type": "STRING"},
                    "legenda_overlay": {"type": "STRING"},
                },
                "required": ["imagem_index", "duracao_segundos", "narracao", "legenda_overlay"],
            },
        },
        "cta": {"type": "STRING"},
        "hashtags": {"type": "ARRAY", "items": {"type": "STRING"}},
        "caption_instagram": {"type": "STRING"},
    },
    "required": [
        "titulo", "gancho", "narracao_completa", "cenas",
        "cta", "hashtags", "caption_instagram",
    ],
}

# System prompt template for roteirista (per CONTEXT.md D-03)
_SYSTEM_PROMPT = """Voce e um roteirista especialista em conteudo viral para Instagram Reels no Brasil.

Regras:
- Gancho forte nos primeiros 3 segundos para prender a atencao
- Cada cena deve ter entre 3-6 segundos de duracao
- Narracao de cada cena: maximo 15 palavras
- legenda_overlay de cada cena: maximo 5 palavras (texto curto para overlay visual)
- CTA final claro e direto
- Linguagem PT-BR coloquial, tom {tom}
- Duracao total alvo: {duracao}s
- Nicho: {nicho}
- Keywords: {keywords}
- CTA padrao: {cta}

Voce recebera {n_imagens} imagens que serao usadas no Reel. Crie um roteiro que:
1. Use cada imagem em ordem (imagem_index 0 a {max_index})
2. Distribua a narracao entre as cenas de forma natural
3. Crie um gancho irresistivel
4. Termine com CTA forte
5. Gere hashtags relevantes e caption completo para o Instagram"""


async def generate_script(
    image_paths: list[str],
    tema: str,
    config_override: dict | None = None,
) -> dict:
    """Generate a structured roteiro (script) from images via Gemini multimodal.

    Args:
        image_paths: Paths to the generated reel images.
        tema: Theme/topic for the script.
        config_override: Optional DB config values to merge with defaults.

    Returns:
        Parsed JSON dict matching RoteiroSchema structure.
    """
    cfg = config_override or {}
    tom = cfg.get("tone", "inspiracional")
    duracao = cfg.get("target_duration", 30)
    nicho = cfg.get("niche", "lifestyle")
    keywords = ", ".join(cfg.get("keywords", []))
    cta = cfg.get("cta_default", "salve esse post")
    language = cfg.get("script_language", REELS_SCRIPT_LANGUAGE)
    model = cfg.get("script_model", REELS_SCRIPT_MODEL)

    system_prompt = _SYSTEM_PROMPT.format(
        tom=tom,
        duracao=duracao,
        nicho=nicho,
        keywords=keywords or "nenhuma",
        cta=cta,
        n_imagens=len(image_paths),
        max_index=len(image_paths) - 1,
    )

    # Build multimodal content: images + text prompt
    parts = []
    for img_path in image_paths:
        img_bytes = Path(img_path).read_bytes()
        mime = "image/jpeg" if img_path.lower().endswith((".jpg", ".jpeg")) else "image/png"
        parts.append(types.Part.from_bytes(data=img_bytes, mime_type=mime))

    user_prompt = (
        f"Tema do Reel: {tema}\n"
        f"Idioma: {language}\n"
        f"Crie o roteiro completo para este Reel usando as {len(image_paths)} imagens acima."
    )
    parts.append(user_prompt)

    client = _get_client()
    response = client.models.generate_content(
        model=model,
        contents=parts,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_schema=ROTEIRO_SCHEMA,
            temperature=0.9,
        ),
    )

    script = json.loads(response.text)
    logger.info(f"Script generated: titulo='{script.get('titulo')}', cenas={len(script.get('cenas', []))}")
    return script
