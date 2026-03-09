"""CaptionWorker — gera legenda Instagram com CTA via Gemini.

Cria legendas engajantes que complementam a frase do mago,
com chamada para acao (salvar, compartilhar, marcar amigos).
"""

import asyncio
import logging

from config import GEMINI_MAX_CONCURRENT, CAPTION_MAX_LENGTH
from src.pipeline.models_v2 import ContentPackage
from src.llm_client import generate

logger = logging.getLogger("clip-flow.worker.caption")

# Reutiliza semaforo global do Gemini
_gemini_semaphore = asyncio.Semaphore(GEMINI_MAX_CONCURRENT)

CAPTION_PROMPT = """Voce e o social media manager do perfil @magomestre420 no Instagram.
O perfil publica memes com frases engracadas de um mago sabio e zoeiro.

Crie uma legenda para Instagram que:
1. Complementa a frase do mago (nao repita a frase, ela ja esta na imagem)
2. Seja curta, engajante e gere interacao
3. Inclua uma CTA natural (salvar, compartilhar, marcar amigo)
4. Use no maximo 3 emojis relevantes
5. NAO use hashtags (serao adicionadas separadamente)
6. Maximo {max_length} caracteres

Tom: leve, zoeiro, relatable. Como se fosse um post de meme viral.

Exemplos de CTA bons:
- "Marca aquele amigo que e assim"
- "Salva pra mandar no grupo"
- "Se voce nao se identificou, voce esta mentindo"

Responda APENAS com a legenda, sem aspas ou formatacao extra."""


class CaptionWorker:
    """Gera legenda Instagram com CTA via Gemini API."""

    async def generate(self, package: ContentPackage) -> str:
        """Gera legenda para um ContentPackage.

        Returns:
            legenda formatada ou string vazia se falhar
        """
        async with _gemini_semaphore:
            try:
                caption = await asyncio.to_thread(self._generate_sync, package)
                logger.info(f"Legenda gerada ({len(caption)} chars)")
                return caption
            except Exception as e:
                logger.error(f"Falha na geracao de legenda: {e}")
                return ""

    def _generate_sync(self, package: ContentPackage) -> str:
        """Geracao sincrona de legenda via Gemini."""
        prompt = CAPTION_PROMPT.format(max_length=CAPTION_MAX_LENGTH)

        humor_angle = ""
        if package.work_order:
            humor_angle = f"\nAngulo de humor: {package.work_order.humor_angle}"

        text = generate(
            system_prompt=prompt,
            user_message=(
                f"Frase do mago na imagem: \"{package.phrase}\"\n"
                f"Tema: {package.topic}"
                f"{humor_angle}"
            ),
            max_tokens=512,
        )
        return text.strip()
