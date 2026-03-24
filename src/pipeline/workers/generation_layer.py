"""GenerationLayer — processa WorkOrders em paralelo.

Coordena PhraseWorker e ImageWorker para gerar ContentPackages.
Suporta A/B testing de frases e carousel mode.
"""

import asyncio
import logging
import time

from config import PHRASE_AB_ENABLED
from src.pipeline.models_v2 import WorkOrder, ContentPackage
from src.pipeline.workers.phrase_worker import PhraseWorker
from src.pipeline.workers.image_worker import ImageWorker

logger = logging.getLogger("clip-flow.generation")


class GenerationLayer:
    """Processa WorkOrders em paralelo — frases + imagens."""

    def __init__(
        self,
        phrase_worker: PhraseWorker | None = None,
        image_worker: ImageWorker | None = None,
        phrases_per_topic: int = 1,
        cost_mode: str = "normal",
    ):
        self.phrase_worker = phrase_worker or PhraseWorker()
        self.image_worker = image_worker or ImageWorker()
        self.phrases_per_topic = phrases_per_topic
        self._cost_mode = cost_mode

    async def process(self, work_orders: list[WorkOrder], on_step=None) -> list[ContentPackage]:
        """Processa todos os WorkOrders em paralelo."""
        if not work_orders:
            return []

        total = len(work_orders)
        phrases_done = 0
        images_done = 0

        ab_enabled = PHRASE_AB_ENABLED and self._cost_mode == "normal"
        logger.info(
            f"Geracao iniciada: {total} work orders, "
            f"A/B={'ON' if ab_enabled else 'OFF'}, "
            f"cost_mode={self._cost_mode}, "
            f"phrases/topic={self.phrases_per_topic}"
        )

        if on_step:
            on_step("phrases", "running", f"0/{total}")
            on_step("images", "idle", "Aguardando frases...")

        async def process_one_tracked(wo: WorkOrder) -> list[ContentPackage]:
            nonlocal phrases_done, images_done
            wo_t0 = time.perf_counter()

            count = wo.phrases_count or self.phrases_per_topic
            phrase_alternatives = []

            # Gerar frases
            phrase_t0 = time.perf_counter()
            if ab_enabled:
                phrases, phrase_alternatives = await self.phrase_worker.generate_with_scoring(wo, count)
            else:
                phrases = await self.phrase_worker.generate(wo, count)
            phrase_elapsed = time.perf_counter() - phrase_t0

            phrases_done += 1
            if on_step:
                s = "done" if phrases_done >= total else "running"
                on_step("phrases", s, f"{phrases_done}/{total}")

            if not phrases:
                logger.warning(f"[{wo.order_id}] Nenhuma frase gerada em {phrase_elapsed:.1f}s, pulando")
                return []

            logger.info(
                f"[{wo.order_id}] {len(phrases)} frase(s) em {phrase_elapsed:.1f}s "
                f"(A/B: {len(phrase_alternatives)} alts)"
            )

            if on_step and images_done == 0:
                on_step("images", "running", f"0/{total}")

            pkgs = []
            carousel_count = getattr(wo, "carousel_count", 1) or 1

            for phrase in phrases:
                try:
                    img_t0 = time.perf_counter()
                    if carousel_count > 1:
                        # Carousel mode
                        carousel_phrases = [phrase]
                        if PHRASE_AB_ENABLED and len(phrase_alternatives) > 1:
                            for alt in phrase_alternatives[1:carousel_count]:
                                carousel_phrases.append(alt.get("frase", phrase))
                        else:
                            extra = await self.phrase_worker.generate(wo, carousel_count - 1)
                            carousel_phrases.extend(extra)

                        slides = []
                        for si, slide_phrase in enumerate(carousel_phrases[:carousel_count]):
                            slide_result = await self.image_worker.compose(slide_phrase, wo)
                            slides.append(slide_result.image_path)

                        first_result = slides[0] if slides else ""
                        compose_result = await self.image_worker.compose(phrase, wo)
                        img_elapsed = time.perf_counter() - img_t0
                        logger.info(
                            f"[{wo.order_id}] Carousel: {len(slides)} slides em {img_elapsed:.1f}s "
                            f"bg_src={compose_result.background_source}"
                        )

                        pkgs.append(ContentPackage(
                            phrase=phrase,
                            image_path=compose_result.image_path,
                            topic=wo.gandalf_topic,
                            source=wo.trend_event.source,
                            work_order=wo,
                            background_path=compose_result.background_path,
                            background_source=compose_result.background_source,
                            image_metadata=compose_result.image_metadata,
                            phrase_alternatives=phrase_alternatives,
                            carousel_slides=slides,
                        ))
                    else:
                        # Modo imagem unica (padrao)
                        compose_result = await self.image_worker.compose(phrase, wo)
                        img_elapsed = time.perf_counter() - img_t0
                        logger.info(
                            f"[{wo.order_id}] Imagem composta em {img_elapsed:.1f}s "
                            f"bg_src={compose_result.background_source} "
                            f"layout={compose_result.image_metadata.get('layout', '?')}"
                        )
                        pkgs.append(ContentPackage(
                            phrase=phrase,
                            image_path=compose_result.image_path,
                            topic=wo.gandalf_topic,
                            source=wo.trend_event.source,
                            work_order=wo,
                            background_path=compose_result.background_path,
                            background_source=compose_result.background_source,
                            image_metadata=compose_result.image_metadata,
                            phrase_alternatives=phrase_alternatives,
                        ))
                except Exception as e:
                    logger.error(
                        f"[{wo.order_id}] Falha na composicao de '{phrase[:30]}...': "
                        f"{type(e).__name__}: {e}"
                    )

            images_done += 1
            wo_elapsed = time.perf_counter() - wo_t0
            logger.info(f"[{wo.order_id}] WorkOrder completo em {wo_elapsed:.1f}s ({len(pkgs)} pkg)")
            if on_step:
                s = "done" if images_done >= total else "running"
                on_step("images", s, f"{images_done}/{total}")

            return pkgs

        results = await asyncio.gather(
            *[process_one_tracked(wo) for wo in work_orders],
            return_exceptions=True,
        )

        packages = []
        errors = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                errors += 1
                logger.error(
                    f"WorkOrder [{work_orders[i].order_id}] excecao: "
                    f"{type(result).__name__}: {result}"
                )
            elif isinstance(result, list):
                packages.extend(result)

        logger.info(f"Geracao concluida: {len(packages)} pacotes, {errors} erros de {total} work orders")
        return packages
