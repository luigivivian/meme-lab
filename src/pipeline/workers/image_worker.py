"""ImageWorker — gera background e compoe imagem final.

Prioridade de geracao de background:
1. Gemini API (imagens com referencias visuais)
2. ComfyUI local (Flux + LoRA)
3. Background estatico (assets/backgrounds/)

Usa Semaphore para serializar acessos a recursos limitados.
"""

import asyncio
import logging
import random

from config import COMFYUI_MAX_CONCURRENT, GEMINI_MAX_CONCURRENT, GEMINI_IMAGE_ENABLED
from src.image_maker import create_image
from src.pipeline.models_v2 import WorkOrder, event_to_trend_item
from src.pipeline.models import AnalyzedTopic
from src.pipeline.processors.generator import ContentGenerator

logger = logging.getLogger("clip-flow.worker.image")

# Semaforos para recursos limitados
_gpu_semaphore = asyncio.Semaphore(COMFYUI_MAX_CONCURRENT)
_gemini_image_semaphore = asyncio.Semaphore(GEMINI_MAX_CONCURRENT)


class ImageWorker:
    """Gera background via Gemini/ComfyUI/estatico e compoe imagem final com Pillow."""

    def __init__(
        self,
        use_comfyui: bool = False,
        use_gemini_image: bool | None = None,
        use_phrase_context: bool = False,
    ):
        self._generator = ContentGenerator(use_comfyui=use_comfyui)
        self._use_gemini_image = use_gemini_image if use_gemini_image is not None else GEMINI_IMAGE_ENABLED
        self._use_phrase_context = use_phrase_context
        self._gemini_client = None

        if self._use_gemini_image:
            self._init_gemini_image()

    def _init_gemini_image(self):
        """Inicializa GeminiImageClient se disponivel."""
        try:
            from src.image_gen.gemini_client import GeminiImageClient

            client = GeminiImageClient()
            if client.is_available():
                self._gemini_client = client
                logger.info("Gemini Image ativado — geracao via API com referencias visuais")
            else:
                logger.warning("Gemini Image nao disponivel (sem referencias ou API key)")
        except Exception as e:
            logger.warning(f"Erro ao inicializar Gemini Image: {e}")

    async def compose(self, phrase: str, work_order: WorkOrder) -> str:
        """Gera imagem composta para uma frase.

        Args:
            phrase: texto da frase para compor na imagem
            work_order: ordem de trabalho com metadados do tema

        Returns:
            caminho da imagem gerada
        """
        topic = AnalyzedTopic(
            original_trend=event_to_trend_item(work_order.trend_event),
            gandalf_topic=work_order.gandalf_topic,
            humor_angle=work_order.humor_angle,
            relevance_score=work_order.relevance_score,
        )

        bg = None

        # 1. Tentar Gemini Image API (prioridade)
        if self._gemini_client:
            try:
                phrase_ctx = phrase if self._use_phrase_context else ""
                bg = await self._gemini_client.agenerate_for_topic(
                    topic, semaphore=_gemini_image_semaphore,
                    phrase_context=phrase_ctx,
                )
                if bg:
                    ctx_label = " (com contexto da frase)" if phrase_ctx else ""
                    logger.info(f"[{work_order.order_id}] Background via Gemini{ctx_label}: {bg}")
            except Exception as e:
                logger.warning(f"[{work_order.order_id}] Gemini Image falhou: {e}")

        # 2. Fallback: ComfyUI local
        if bg is None:
            async with _gpu_semaphore:
                bg = await asyncio.to_thread(
                    self._generator._generate_background, topic
                )

        # 3. Fallback: background estatico
        if bg is None:
            bg = random.choice(self._generator.backgrounds)
            logger.debug(f"[{work_order.order_id}] Usando background estatico: {bg}")

        # Compor imagem final com Pillow
        image_path = await asyncio.to_thread(create_image, phrase, bg)
        logger.info(f"[{work_order.order_id}] Imagem gerada: {image_path}")
        return image_path
