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

    async def process(self, work_orders: list[WorkOrder]) -> list[ContentPackage]:
        """Processa todos os WorkOrders em paralelo.

        Para cada WorkOrder: gera frases -> compoe imagens -> empacota.
        """
        if not work_orders:
            return []

        logger.info(f"Geracao iniciada: {len(work_orders)} work orders")
        tasks = [self._process_one(wo) for wo in work_orders]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        packages = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    f"WorkOrder [{work_orders[i].order_id}] falhou: {result}"
                )
            elif isinstance(result, list):
                packages.extend(result)

        logger.info(f"Geracao concluida: {len(packages)} pacotes produzidos")
        return packages

    async def _process_one(self, work_order: WorkOrder) -> list[ContentPackage]:
        """Processa um unico WorkOrder: frases -> imagens -> pacotes."""
        count = work_order.phrases_count or self.phrases_per_topic
        phrases = await self.phrase_worker.generate(work_order, count)

        if not phrases:
            logger.warning(
                f"[{work_order.order_id}] Nenhuma frase gerada, pulando"
            )
            return []

        packages = []
        for phrase in phrases:
            try:
                image_path = await self.image_worker.compose(phrase, work_order)
                package = ContentPackage(
                    phrase=phrase,
                    image_path=image_path,
                    topic=work_order.gandalf_topic,
                    source=work_order.trend_event.source,
                    work_order=work_order,
                )
                packages.append(package)
            except Exception as e:
                logger.error(
                    f"[{work_order.order_id}] Falha na composicao de '{phrase[:30]}...': {e}"
                )

        return packages
