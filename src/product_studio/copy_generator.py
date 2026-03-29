"""LLM headline + CTA + hashtags generation for product ads.

Per D-15: LLM generates Portuguese headline, CTA, and hashtags
based on product context and advertising tone.
"""

import asyncio
import json
import logging

from src.llm_client import _get_client, _extract_text

logger = logging.getLogger("clip-flow.ads.copy_generator")

_SYSTEM_PROMPT = (
    "Voce e um copywriter especialista em anuncios de produto para redes sociais brasileiras. "
    "Gere copy publicitario em portugues brasileiro. "
    "Retorne APENAS um JSON valido com as chaves: headline, cta, hashtags. "
    "Nenhum texto fora do JSON."
)


async def generate_copy(
    product_name: str,
    product_description: str,
    niche: str,
    tone: str,
    audience: str,
    style: str,
) -> dict:
    """Generate ad copy (headline + CTA + hashtags) via Gemini.

    Returns dict with keys:
        - headline: short impactful headline in Portuguese
        - cta: action-oriented CTA in Portuguese
        - hashtags: list of 5-8 relevant hashtags
    """
    user_message = (
        f"Produto: {product_name}\n"
        f"Descricao: {product_description}\n"
        f"Nicho: {niche}\n"
        f"Tom: {tone}\n"
        f"Publico-alvo: {audience}\n"
        f"Estilo do video: {style}\n\n"
        "Gere:\n"
        "- headline: frase curta e impactante (max 8 palavras)\n"
        "- cta: chamada para acao (ex: 'Compre agora', 'Saiba mais', 'Garanta o seu')\n"
        "- hashtags: lista de 5 a 8 hashtags relevantes (com #)\n\n"
        'Formato: {"headline": "...", "cta": "...", "hashtags": ["#...", ...]}'
    )

    client = _get_client()
    from google.genai import types

    response = await asyncio.to_thread(
        client.models.generate_content,
        model="gemini-2.5-flash",
        contents=user_message,
        config=types.GenerateContentConfig(
            system_instruction=_SYSTEM_PROMPT,
            max_output_tokens=300,
            temperature=0.7,
            response_mime_type="application/json",
        ),
    )

    text = _extract_text(response).strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    result = json.loads(text)
    logger.info(
        "Copy generated: headline='%s', cta='%s', %d hashtags",
        result.get("headline", ""),
        result.get("cta", ""),
        len(result.get("hashtags", [])),
    )
    return result
