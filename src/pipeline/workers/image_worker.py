"""ImageWorker — gera background e compoe imagem final.

Wrapper async de ContentGenerator (background) + create_image (composicao).
Usa Semaphore(1) para serializar acessos GPU (8GB VRAM).
"""

import asyncio
import logging
import random

from config import COMFYUI_MAX_CONCURRENT
from src.image_maker import create_image
from src.pipeline.models_v2 import WorkOrder, event_to_trend_item
from src.pipeline.models import AnalyzedTopic
from src.pipeline.processors.generator import ContentGenerator

logger = logging.getLogger("clip-flow.worker.image")

# Semaforo para GPU — RTX 4060 Ti 8GB nao suporta geracao simultanea
_gpu_semaphore = asyncio.Semaphore(COMFYUI_MAX_CONCURRENT)


class ImageWorker:
    """Gera background via ComfyUI/estatico e compoe imagem final com Pillow."""

    def __init__(self, use_comfyui: bool = False):
        self._generator = ContentGenerator(use_comfyui=use_comfyui)

    async def compose(self, phrase: str, work_order: WorkOrder) -> str:
        """Gera imagem composta para uma frase.

        Args:
            phrase: texto da frase para compor na imagem
            work_order: ordem de trabalho com metadados do tema

        Returns:
            caminho da imagem gerada
        """
        # Converter WorkOrder para AnalyzedTopic (compatibilidade com ContentGenerator)
        topic = AnalyzedTopic(
            original_trend=event_to_trend_item(work_order.trend_event),
            gandalf_topic=work_order.gandalf_topic,
            humor_angle=work_order.humor_angle,
            relevance_score=work_order.relevance_score,
        )

        # Gerar background (GPU-safe com semaforo)
        async with _gpu_semaphore:
            bg = await asyncio.to_thread(
                self._generator._generate_background, topic
            )

        # Fallback para background estatico
        if bg is None:
            bg = random.choice(self._generator.backgrounds)
            logger.debug(f"[{work_order.order_id}] Usando background estatico: {bg}")

        # Compor imagem final com Pillow
        image_path = await asyncio.to_thread(create_image, phrase, bg)
        logger.info(
            f"[{work_order.order_id}] Imagem gerada: {image_path}"
        )
        return image_path
