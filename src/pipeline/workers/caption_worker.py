"""CaptionWorker — gera legenda Instagram com CTA via Claude.

Cria legendas engajantes que complementam a frase do mago,
com chamada para acao (salvar, compartilhar, marcar amigos).
"""

import asyncio
import logging
import os

from dotenv import load_dotenv
import anthropic

from config import CLAUDE_MAX_CONCURRENT, CAPTION_MAX_LENGTH
from src.pipeline.models_v2 import ContentPackage

load_dotenv()

logger = logging.getLogger("clip-flow.worker.caption")

# Reutiliza semaforo global do Claude
_claude_semaphore = asyncio.Semaphore(CLAUDE_MAX_CONCURRENT)

CAPTION_PROMPT = """Voce e o social media manager do perfil @omagomestre no Instagram.
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
    """Gera legenda Instagram com CTA via Claude API."""

    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key and api_key != "your-api-key-here":
            self._client = anthropic.Anthropic(api_key=api_key)
        else:
            self._client = None
            logger.warning("ANTHROPIC_API_KEY nao configurada — caption worker desabilitado")

    async def generate(self, package: ContentPackage) -> str:
        """Gera legenda para um ContentPackage.

        Returns:
            legenda formatada ou string vazia se falhar
        """
        if not self._client:
            return ""

        async with _claude_semaphore:
            try:
                caption = await asyncio.to_thread(self._generate_sync, package)
                logger.info(f"Legenda gerada ({len(caption)} chars)")
                return caption
            except Exception as e:
                logger.error(f"Falha na geracao de legenda: {e}")
                return ""

    def _generate_sync(self, package: ContentPackage) -> str:
        """Geracao sincrona de legenda via Claude."""
        prompt = CAPTION_PROMPT.format(max_length=CAPTION_MAX_LENGTH)

        humor_angle = ""
        if package.work_order:
            humor_angle = f"\nAngulo de humor: {package.work_order.humor_angle}"

        message = self._client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=512,
            system=prompt,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Frase do mago na imagem: \"{package.phrase}\"\n"
                        f"Tema: {package.topic}"
                        f"{humor_angle}"
                    ),
                }
            ],
        )
        return message.content[0].text.strip()
