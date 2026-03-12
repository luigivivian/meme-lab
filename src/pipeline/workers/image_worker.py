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
from dataclasses import dataclass, field

from config import COMFYUI_MAX_CONCURRENT, GEMINI_MAX_CONCURRENT, GEMINI_IMAGE_ENABLED
from src.image_maker import create_image
from src.pipeline.models_v2 import WorkOrder, event_to_trend_item
from src.pipeline.models import AnalyzedTopic
from src.pipeline.processors.generator import ContentGenerator

logger = logging.getLogger("clip-flow.worker.image")


@dataclass
class ComposeResult:
    """Resultado da composicao de imagem com metadata."""
    image_path: str
    background_path: str | None = None
    background_source: str = "static"  # gemini | comfyui | static
    image_metadata: dict = field(default_factory=dict)


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
        reference_dir: str | None = None,
        character_dna: str | None = None,
        negative_traits: str | None = None,
        composition: str | None = None,
        rendering: dict | None = None,
        refs_priority: list[str] | None = None,
        watermark_text: str | None = None,
    ):
        self._generator = ContentGenerator(use_comfyui=use_comfyui)
        self._watermark_text = watermark_text
        self._use_gemini_image = use_gemini_image if use_gemini_image is not None else GEMINI_IMAGE_ENABLED
        self._use_phrase_context = use_phrase_context
        self._gemini_client = None
        self._reference_dir = reference_dir
        self._character_dna = character_dna
        self._negative_traits = negative_traits
        self._composition = composition
        self._rendering = rendering
        self._refs_priority = refs_priority

        if self._use_gemini_image:
            self._init_gemini_image()

    def _init_gemini_image(self):
        """Inicializa GeminiImageClient se disponivel."""
        try:
            from src.image_gen.gemini_client import GeminiImageClient

            kwargs = {}
            if self._reference_dir:
                kwargs["reference_dir"] = self._reference_dir
            if self._character_dna:
                kwargs["character_dna"] = self._character_dna
            if self._negative_traits:
                kwargs["negative_traits"] = self._negative_traits
            if self._composition:
                kwargs["composition"] = self._composition
            if self._rendering:
                kwargs["rendering"] = self._rendering
            if self._refs_priority:
                kwargs["refs_priority"] = self._refs_priority

            client = GeminiImageClient(**kwargs)
            if client.is_available():
                self._gemini_client = client
                logger.info(f"Gemini Image ativado — refs dir: {client.reference_dir}, custom_dna={bool(self._character_dna)}")
            else:
                logger.warning("Gemini Image nao disponivel (sem referencias ou API key)")
        except Exception as e:
            logger.warning(f"Erro ao inicializar Gemini Image: {e}")

    async def compose(self, phrase: str, work_order: WorkOrder) -> ComposeResult:
        """Gera imagem composta para uma frase.

        Args:
            phrase: texto da frase para compor na imagem
            work_order: ordem de trabalho com metadados do tema

        Returns:
            ComposeResult com caminho da imagem e metadata
        """
        # Usar situacao_key definida pelo Curator (respeita theme_tags e diversidade)
        situacao_key = work_order.situacao_key

        topic = AnalyzedTopic(
            original_trend=event_to_trend_item(work_order.trend_event),
            gandalf_topic=work_order.gandalf_topic,
            humor_angle=work_order.humor_angle,
            relevance_score=work_order.relevance_score,
        )

        bg = None
        bg_source = "static"
        gen_metadata = {}

        # 1. Tentar Gemini Image API (prioridade) — usa situacao_key do WorkOrder diretamente
        if self._gemini_client:
            try:
                phrase_ctx = phrase if self._use_phrase_context else ""
                gen_result = await self._gemini_client.agenerate_image(
                    situacao_key=situacao_key,
                    semaphore=_gemini_image_semaphore,
                    phrase_context=phrase_ctx,
                )
                if gen_result:
                    bg = gen_result.path
                    bg_source = "gemini"
                    gen_metadata = {
                        "pose": gen_result.pose,
                        "scene": gen_result.scene,
                        "theme_key": gen_result.theme_key,
                        "prompt_used": gen_result.prompt_used,
                        "reference_images": gen_result.reference_images,
                        "rendering_config": gen_result.rendering_config,
                        "phrase_context_used": gen_result.phrase_context_used,
                        "character_dna_used": gen_result.character_dna_used,
                    }
                    ctx_label = " (com contexto da frase)" if phrase_ctx else ""
                    logger.info(f"[{work_order.order_id}] Background via Gemini [{situacao_key}]{ctx_label}: {bg}")
            except Exception as e:
                logger.warning(f"[{work_order.order_id}] Gemini Image falhou: {e}")

        # 2. Fallback: ComfyUI local
        if bg is None:
            async with _gpu_semaphore:
                bg = await asyncio.to_thread(
                    self._generator._generate_background, topic
                )
            if bg:
                bg_source = "comfyui"
                gen_metadata = {"theme_key": situacao_key}

        # 3. Fallback: background estatico
        if bg is None:
            bg = random.choice(self._generator.backgrounds)
            bg_source = "static"
            gen_metadata = {"theme_key": situacao_key}
            logger.debug(f"[{work_order.order_id}] Usando background estatico: {bg}")

        # Compor imagem final com Pillow
        image_path = await asyncio.to_thread(
            create_image, phrase, bg, None, self._watermark_text,
        )
        logger.info(f"[{work_order.order_id}] Imagem gerada: {image_path}")

        return ComposeResult(
            image_path=image_path,
            background_path=bg,
            background_source=bg_source,
            image_metadata=gen_metadata,
        )
