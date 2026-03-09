"""PhraseWorker — gera frases via Gemini API.

Wrapper async de src.phrases.generate_phrases().
"""

import asyncio
import logging

from config import GEMINI_MAX_CONCURRENT
from src.phrases import generate_phrases
from src.pipeline.models_v2 import WorkOrder

logger = logging.getLogger("clip-flow.worker.phrase")

# Semaforo global para limitar chamadas simultaneas ao Gemini
_gemini_semaphore = asyncio.Semaphore(GEMINI_MAX_CONCURRENT)


class PhraseWorker:
    """Gera frases humoristicas via Gemini API."""

    async def generate(self, work_order: WorkOrder, count: int = 1) -> list[str]:
        """Gera frases para um WorkOrder.

        Args:
            work_order: ordem de trabalho com gandalf_topic
            count: quantidade de frases a gerar

        Returns:
            lista de frases geradas
        """
        async with _gemini_semaphore:
            logger.info(
                f"[{work_order.order_id}] Gerando {count} frase(s) "
                f"para '{work_order.gandalf_topic}'"
            )
            try:
                phrases = await asyncio.to_thread(
                    generate_phrases, work_order.gandalf_topic, count
                )
                logger.info(
                    f"[{work_order.order_id}] {len(phrases)} frase(s) gerada(s)"
                )
                return phrases
            except Exception as e:
                logger.error(
                    f"[{work_order.order_id}] Falha na geracao de frases: {e}"
                )
                return []
