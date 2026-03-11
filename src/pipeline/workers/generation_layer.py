"""GenerationLayer — processa WorkOrders em paralelo.

Coordena PhraseWorker e ImageWorker para gerar ContentPackages.
"""

import asyncio
import logging

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
    ):
        self.phrase_worker = phrase_worker or PhraseWorker()
        self.image_worker = image_worker or ImageWorker()
        self.phrases_per_topic = phrases_per_topic

    async def process(self, work_orders: list[WorkOrder], on_step=None) -> list[ContentPackage]:
        """Processa todos os WorkOrders em paralelo.

        Args:
            on_step: callback(step, status, detail) para progresso granular.

        Para cada WorkOrder: gera frases -> compoe imagens -> empacota.
        """
        if not work_orders:
            return []

        total = len(work_orders)
        phrases_done = 0
        images_done = 0

        if on_step:
            on_step("phrases", "running", f"0/{total}")
            on_step("images", "idle", "Aguardando frases...")

        async def process_one_tracked(wo: WorkOrder) -> list[ContentPackage]:
            nonlocal phrases_done, images_done

            count = wo.phrases_count or self.phrases_per_topic
            phrases = await self.phrase_worker.generate(wo, count)
            phrases_done += 1
            if on_step:
                s = "done" if phrases_done >= total else "running"
                on_step("phrases", s, f"{phrases_done}/{total}")

            if not phrases:
                logger.warning(f"[{wo.order_id}] Nenhuma frase gerada, pulando")
                return []

            if on_step and images_done == 0:
                on_step("images", "running", f"0/{total}")

            pkgs = []
            for phrase in phrases:
                try:
                    image_path = await self.image_worker.compose(phrase, wo)
                    pkgs.append(ContentPackage(
                        phrase=phrase,
                        image_path=image_path,
                        topic=wo.gandalf_topic,
                        source=wo.trend_event.source,
                        work_order=wo,
                    ))
                except Exception as e:
                    logger.error(f"[{wo.order_id}] Falha na composicao de '{phrase[:30]}...': {e}")

            images_done += 1
            if on_step:
                s = "done" if images_done >= total else "running"
                on_step("images", s, f"{images_done}/{total}")

            return pkgs

        logger.info(f"Geracao iniciada: {total} work orders")
        results = await asyncio.gather(
            *[process_one_tracked(wo) for wo in work_orders],
            return_exceptions=True,
        )

        packages = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"WorkOrder [{work_orders[i].order_id}] falhou: {result}")
            elif isinstance(result, list):
                packages.extend(result)

        logger.info(f"Geracao concluida: {len(packages)} pacotes produzidos")
        return packages
