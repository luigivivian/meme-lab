"""ImageWorker — gera background e compoe imagem final.

Prioridade de geracao de background (config.IMAGE_BACKEND_PRIORITY):
- "comfyui": ComfyUI local (custo zero) → Gemini API → estatico
- "gemini":  Gemini API → ComfyUI local → estatico

Usa Semaphore para serializar acessos a recursos limitados.
"""

import asyncio
import logging
import random
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from config import COMFYUI_MAX_CONCURRENT, GEMINI_MAX_CONCURRENT, GEMINI_IMAGE_ENABLED, IMAGE_BACKEND_PRIORITY
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
        background_mode: str = "auto",
    ):
        self._generator = ContentGenerator(use_comfyui=use_comfyui)
        self._watermark_text = watermark_text
        self._use_gemini_image = use_gemini_image if use_gemini_image is not None else GEMINI_IMAGE_ENABLED
        self._use_phrase_context = use_phrase_context
        self._background_mode = background_mode
        self._gemini_client = None
        self._reference_dir = reference_dir
        self._character_dna = character_dna
        self._negative_traits = negative_traits
        self._composition = composition
        self._rendering = rendering
        self._refs_priority = refs_priority

        # Inicializar Gemini Image apenas quando necessario
        if background_mode == "static":
            logger.info("Background mode: static — usando apenas backgrounds estaticos")
        elif background_mode == "comfyui":
            logger.info("Background mode: comfyui — apenas GPU local")
        elif self._use_gemini_image:
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

    async def _try_gemini(self, work_order: WorkOrder, phrase: str, situacao_key: str) -> tuple:
        """Tenta gerar background via Gemini Image API."""
        if not self._gemini_client:
            return None, "static", {}
        try:
            phrase_ctx = phrase if self._use_phrase_context else ""
            gen_result = await self._gemini_client.agenerate_image(
                situacao_key=situacao_key,
                semaphore=_gemini_image_semaphore,
                phrase_context=phrase_ctx,
            )
            if gen_result:
                metadata = {
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
                logger.info(f"[{work_order.order_id}] Background via Gemini [{situacao_key}]{ctx_label}: {gen_result.path}")
                return gen_result.path, "gemini", metadata
        except Exception as e:
            logger.warning(f"[{work_order.order_id}] Gemini Image falhou: {e}")
        return None, "static", {}

    async def _try_comfyui(self, work_order: WorkOrder, topic: AnalyzedTopic, situacao_key: str) -> tuple:
        """Tenta gerar background via ComfyUI local."""
        try:
            async with _gpu_semaphore:
                bg = await asyncio.to_thread(
                    self._generator._generate_background, topic, situacao_key
                )
            if bg:
                logger.info(f"[{work_order.order_id}] Background via ComfyUI [{situacao_key}]: {bg}")
                return bg, "comfyui", {"theme_key": situacao_key}
        except Exception as e:
            logger.warning(f"[{work_order.order_id}] ComfyUI falhou: {e}")
        return None, "static", {}

    async def compose(
        self, phrase: str, work_order: WorkOrder,
        user_id: int | None = None, session: AsyncSession | None = None,
    ) -> ComposeResult:
        """Gera imagem composta para uma frase.

        Args:
            phrase: texto da frase para compor na imagem
            work_order: ordem de trabalho com metadados do tema
            user_id: optional user ID for quota pre-check
            session: optional DB session for quota pre-check

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
        fallback_reason = None
        resolved_tier = None  # Track tier for metadata

        # Pre-check: quota exhaustion (D-04, D-05)
        if user_id is not None and session is not None and self._background_mode not in ("static", "comfyui"):
            try:
                from src.services.key_selector import UsageAwareKeySelector
                selector = UsageAwareKeySelector()
                resolution = await selector.resolve(user_id=user_id, session=session)
                resolved_tier = resolution.tier
                if resolution.tier == "exhausted":
                    logger.warning("Both tiers exhausted, using static fallback")
                    fallback_reason = "quota_exhausted"
                    bg = random.choice(self._generator.backgrounds)
                    bg_source = "static"
                    gen_metadata = {"theme_key": situacao_key, "fallback_reason": fallback_reason}
            except Exception as e:
                logger.warning(f"Quota pre-check failed ({e}), continuing with normal flow")

        # Determinar backend baseado no background_mode (skip if pre-check already resolved)
        if bg is None:
            mode = self._background_mode
            if mode == "static":
                # Pula todos os backends — vai direto pro fallback estatico
                fallback_reason = "mode_static"
            elif mode == "comfyui":
                bg, bg_source, gen_metadata = await self._try_comfyui(work_order, topic, situacao_key)
            elif mode == "gemini":
                bg, bg_source, gen_metadata = await self._try_gemini(work_order, phrase, situacao_key)
            else:
                # auto: usa prioridade configurada com fallback
                if IMAGE_BACKEND_PRIORITY == "comfyui":
                    bg, bg_source, gen_metadata = await self._try_comfyui(work_order, topic, situacao_key)
                    if bg is None:
                        bg, bg_source, gen_metadata = await self._try_gemini(work_order, phrase, situacao_key)
                else:
                    bg, bg_source, gen_metadata = await self._try_gemini(work_order, phrase, situacao_key)
                    if bg is None:
                        bg, bg_source, gen_metadata = await self._try_comfyui(work_order, topic, situacao_key)

        # Fallback final: background estatico
        if bg is None:
            bg = random.choice(self._generator.backgrounds)
            bg_source = "static"
            fallback_reason = fallback_reason or "generation_failed"
            gen_metadata = {"theme_key": situacao_key, "fallback_reason": fallback_reason}
            logger.debug(f"[{work_order.order_id}] Usando background estatico: {bg}")

        # Track usage for successful Gemini generations
        if bg_source == "gemini" and user_id is not None and session is not None:
            try:
                from src.database.repositories.usage_repo import UsageRepository
                tier_label = resolved_tier.replace("gemini_", "") if resolved_tier else "free"
                if tier_label not in ("free", "paid"):
                    tier_label = "free"
                repo = UsageRepository(session)
                await repo.increment(
                    user_id=user_id,
                    service="gemini_image",
                    tier=tier_label,
                )
                await session.commit()
                logger.debug(f"[{work_order.order_id}] Usage incremented: gemini_image/{tier_label}")
            except Exception as e:
                logger.warning(f"[{work_order.order_id}] Failed to increment usage: {e}")

        # Compor imagem final com Pillow (layout do WorkOrder)
        layout = getattr(work_order, "layout", "bottom")
        image_path = await asyncio.to_thread(
            create_image, phrase, bg, None, self._watermark_text, layout,
        )
        gen_metadata["layout"] = layout
        if resolved_tier and resolved_tier != "exhausted":
            gen_metadata["tier"] = resolved_tier
        # Ensure fallback_reason in metadata for all static backgrounds
        if bg_source == "static" and "fallback_reason" not in gen_metadata:
            gen_metadata["fallback_reason"] = fallback_reason or "generation_failed"
        logger.info(f"[{work_order.order_id}] Imagem gerada (layout={layout}): {image_path}")

        return ComposeResult(
            image_path=image_path,
            background_path=bg,
            background_source=bg_source,
            image_metadata=gen_metadata,
        )
