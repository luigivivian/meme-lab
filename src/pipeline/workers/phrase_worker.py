"""PhraseWorker — gera frases via Gemini API.

Wrapper async de src.phrases.generate_phrases().
Suporta system_prompt customizado por personagem.
"""

import asyncio
import logging

from config import GEMINI_MAX_CONCURRENT, SYSTEM_PROMPT
from src.llm_client import generate
from src.pipeline.models_v2 import WorkOrder

logger = logging.getLogger("clip-flow.worker.phrase")

# Semaforo global para limitar chamadas simultaneas ao Gemini
_gemini_semaphore = asyncio.Semaphore(GEMINI_MAX_CONCURRENT)


def _generate_with_prompt(system_prompt: str, topic: str, count: int, max_chars: int | None = None) -> list[str]:
    """Gera frases usando system_prompt customizado."""
    user_msg = f"Gere {count} frases sobre o tema: {topic}"
    if max_chars:
        user_msg += f"\nMaximo {max_chars} caracteres por frase."
    raw_text = generate(
        system_prompt=system_prompt,
        user_message=user_msg,
        max_tokens=2048,
    )
    phrases = [line.strip() for line in raw_text.strip().splitlines() if line.strip()]
    return phrases


class PhraseWorker:
    """Gera frases humoristicas via Gemini API."""

    def __init__(self, system_prompt: str | None = None, max_chars: int | None = None):
        self._custom_prompt = bool(system_prompt)
        self._system_prompt = system_prompt or SYSTEM_PROMPT
        self._max_chars = max_chars
        if self._custom_prompt:
            logger.info(f"PhraseWorker usando system_prompt customizado ({len(self._system_prompt)} chars)")
        else:
            logger.info("PhraseWorker usando SYSTEM_PROMPT padrao (mago-mestre)")

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
                    _generate_with_prompt,
                    self._system_prompt,
                    work_order.gandalf_topic,
                    count,
                    self._max_chars,
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
