"""PostProductionLayer — executa caption, hashtag e quality em paralelo.

Enriquece ContentPackages com legenda, hashtags e quality score.
Se qualquer worker falha, o pacote continua valido com defaults.
"""

import asyncio
import logging

from src.pipeline.models_v2 import ContentPackage
from src.pipeline.workers.caption_worker import CaptionWorker
from src.pipeline.workers.hashtag_worker import HashtagWorker
from src.pipeline.workers.quality_worker import QualityWorker

logger = logging.getLogger("clip-flow.post_production")


class PostProductionLayer:
    """Executa pos-producao em paralelo para cada ContentPackage."""

    def __init__(
        self,
        caption_worker: CaptionWorker | None = None,
        hashtag_worker: HashtagWorker | None = None,
        quality_worker: QualityWorker | None = None,
    ):
        self.caption_worker = caption_worker or CaptionWorker()
        self.hashtag_worker = hashtag_worker or HashtagWorker()
        self.quality_worker = quality_worker or QualityWorker()

    async def enhance(self, packages: list[ContentPackage]) -> list[ContentPackage]:
        """Enriquece todos os pacotes em paralelo."""
        if not packages:
            return []

        logger.info(f"Pos-producao iniciada: {len(packages)} pacotes")
        tasks = [self._enhance_one(pkg) for pkg in packages]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        enhanced = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Pos-producao falhou para pacote {i}: {result}")
                enhanced.append(packages[i])  # retorna pacote sem enriquecimento
            else:
                enhanced.append(result)

        logger.info(f"Pos-producao concluida: {len(enhanced)} pacotes enriquecidos")
        return enhanced

    async def _enhance_one(self, package: ContentPackage) -> ContentPackage:
        """Enriquece um unico pacote com caption, hashtags e quality em paralelo."""
        caption_task = self._safe_caption(package)
        hashtag_task = self._safe_hashtags(package)
        quality_task = self._safe_quality(package)

        caption, hashtags, quality_score = await asyncio.gather(
            caption_task, hashtag_task, quality_task
        )

        package.caption = caption
        package.hashtags = hashtags
        package.quality_score = quality_score

        return package

    async def _safe_caption(self, package: ContentPackage) -> str:
        """Caption com fallback para string vazia."""
        try:
            return await self.caption_worker.generate(package)
        except Exception as e:
            logger.error(f"Caption falhou: {e}")
            return ""

    async def _safe_hashtags(self, package: ContentPackage) -> list[str]:
        """Hashtags com fallback para lista vazia."""
        try:
            return await self.hashtag_worker.research(package)
        except Exception as e:
            logger.error(f"Hashtags falhou: {e}")
            return []

    async def _safe_quality(self, package: ContentPackage) -> float:
        """Quality com fallback para 0.0."""
        try:
            return await self.quality_worker.validate(package)
        except Exception as e:
            logger.error(f"Quality falhou: {e}")
            return 0.0
