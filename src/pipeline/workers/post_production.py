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

    async def enhance(self, packages: list[ContentPackage], on_step=None) -> list[ContentPackage]:
        """Enriquece todos os pacotes em paralelo.

        Args:
            on_step: callback(step, status, detail) para progresso granular.
        """
        if not packages:
            return []

        total = len(packages)
        caption_done = 0
        hashtag_done = 0
        quality_done = 0

        if on_step:
            on_step("caption", "running", f"0/{total}")
            on_step("hashtags", "running", f"0/{total}")
            on_step("quality", "running", f"0/{total}")

        async def enhance_one_tracked(pkg: ContentPackage) -> ContentPackage:
            nonlocal caption_done, hashtag_done, quality_done

            async def tracked_caption():
                nonlocal caption_done
                result = await self._safe_caption(pkg)
                caption_done += 1
                if on_step:
                    s = "done" if caption_done >= total else "running"
                    on_step("caption", s, f"{caption_done}/{total}")
                return result

            async def tracked_hashtags():
                nonlocal hashtag_done
                result = await self._safe_hashtags(pkg)
                hashtag_done += 1
                if on_step:
                    s = "done" if hashtag_done >= total else "running"
                    on_step("hashtags", s, f"{hashtag_done}/{total}")
                return result

            async def tracked_quality():
                nonlocal quality_done
                result = await self._safe_quality(pkg)
                quality_done += 1
                if on_step:
                    s = "done" if quality_done >= total else "running"
                    on_step("quality", s, f"{quality_done}/{total}")
                return result

            caption, hashtags, quality_score = await asyncio.gather(
                tracked_caption(), tracked_hashtags(), tracked_quality()
            )
            pkg.caption = caption
            pkg.hashtags = hashtags
            pkg.quality_score = quality_score
            return pkg

        logger.info(f"Pos-producao iniciada: {total} pacotes")
        results = await asyncio.gather(
            *[enhance_one_tracked(pkg) for pkg in packages],
            return_exceptions=True,
        )

        enhanced = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Pos-producao falhou para pacote {i}: {result}")
                enhanced.append(packages[i])
            else:
                enhanced.append(result)

        logger.info(f"Pos-producao concluida: {len(enhanced)} pacotes enriquecidos")
        return enhanced

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
