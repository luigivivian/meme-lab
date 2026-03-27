"""PostProductionLayer — executa caption, hashtag, quality e legend em paralelo.

Enriquece ContentPackages com legenda, hashtags, quality score e
video legend overlay (D-09 auto-trigger when VIDEO_LEGEND_ENABLED=true).
Se qualquer worker falha, o pacote continua valido com defaults.
"""

import asyncio
import logging
import time

from config import VIDEO_LEGEND_ENABLED
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
        legend_worker=None,  # Optional[LegendWorker] — lazy import to avoid circular deps
    ):
        self.caption_worker = caption_worker or CaptionWorker()
        self.hashtag_worker = hashtag_worker or HashtagWorker()
        self.quality_worker = quality_worker or QualityWorker()
        self._legend_worker = legend_worker

    async def enhance(self, packages: list[ContentPackage], on_step=None) -> list[ContentPackage]:
        """Enriquece todos os pacotes em paralelo."""
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
        if on_step and VIDEO_LEGEND_ENABLED:
            on_step("legend", "pending", f"0/{total}")

        async def enhance_one_tracked(pkg: ContentPackage) -> ContentPackage:
            nonlocal caption_done, hashtag_done, quality_done
            pkg_t0 = time.perf_counter()
            wo_id = getattr(pkg, 'work_order', None)
            wo_id = getattr(wo_id, 'order_id', '?') if wo_id else '?'

            async def tracked_caption():
                nonlocal caption_done
                t0 = time.perf_counter()
                result = await self._safe_caption(pkg)
                elapsed = time.perf_counter() - t0
                caption_done += 1
                logger.debug(f"[{wo_id}] Caption gerada em {elapsed:.1f}s ({len(result)} chars)")
                if on_step:
                    s = "done" if caption_done >= total else "running"
                    on_step("caption", s, f"{caption_done}/{total}")
                return result

            async def tracked_hashtags():
                nonlocal hashtag_done
                t0 = time.perf_counter()
                result = await self._safe_hashtags(pkg)
                elapsed = time.perf_counter() - t0
                hashtag_done += 1
                logger.debug(f"[{wo_id}] Hashtags geradas em {elapsed:.1f}s ({len(result)} tags)")
                if on_step:
                    s = "done" if hashtag_done >= total else "running"
                    on_step("hashtags", s, f"{hashtag_done}/{total}")
                return result

            async def tracked_quality():
                nonlocal quality_done
                t0 = time.perf_counter()
                result = await self._safe_quality(pkg)
                elapsed = time.perf_counter() - t0
                quality_done += 1
                logger.debug(f"[{wo_id}] Quality score em {elapsed:.1f}s: {result:.2f}")
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

            # === Legend auto-trigger (D-09) ===
            # Run AFTER caption/hashtags/quality (sequential, not in gather)
            # Only for packages with completed videos
            legend_result = None
            if VIDEO_LEGEND_ENABLED and getattr(pkg, 'video_status', None) == 'success' and getattr(pkg, 'video_path', None):
                legend_result = await self._safe_legend(pkg)
                if legend_result:
                    pkg.legend_status = "success"
                    pkg.legend_path = legend_result
                    logger.info(f"[{wo_id}] Legend auto-rendered: {legend_result}")
                else:
                    # Per D-11: graceful fallback, don't set failed — just skip
                    logger.debug(f"[{wo_id}] Legend skipped or failed (graceful fallback)")
                if on_step and VIDEO_LEGEND_ENABLED:
                    on_step("legend", "done" if legend_result else "skipped", f"{caption_done}/{total}")

            pkg_elapsed = time.perf_counter() - pkg_t0
            logger.info(
                f"[{wo_id}] PostProd completo em {pkg_elapsed:.1f}s — "
                f"caption={len(caption)}ch, hashtags={len(hashtags)}, quality={quality_score:.2f}"
            )
            return pkg

        logger.info(f"Pos-producao iniciada: {total} pacotes")
        results = await asyncio.gather(
            *[enhance_one_tracked(pkg) for pkg in packages],
            return_exceptions=True,
        )

        enhanced = []
        errors = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                errors += 1
                logger.error(f"Pos-producao falhou para pacote {i}: {type(result).__name__}: {result}")
                enhanced.append(packages[i])
            else:
                enhanced.append(result)

        logger.info(f"Pos-producao concluida: {len(enhanced)} pacotes ({errors} erros)")
        return enhanced

    async def _safe_caption(self, package: ContentPackage) -> str:
        """Caption com fallback para string vazia."""
        try:
            return await self.caption_worker.generate(package)
        except Exception as e:
            logger.error(f"Caption falhou: {type(e).__name__}: {e}")
            return ""

    async def _safe_hashtags(self, package: ContentPackage) -> list[str]:
        """Hashtags com fallback para lista vazia."""
        try:
            return await self.hashtag_worker.research(package)
        except Exception as e:
            logger.error(f"Hashtags falhou: {type(e).__name__}: {e}")
            return []

    async def _safe_quality(self, package: ContentPackage) -> float:
        """Quality com fallback para 0.0."""
        try:
            return await self.quality_worker.validate(package)
        except Exception as e:
            logger.error(f"Quality falhou: {type(e).__name__}: {e}")
            return 0.0

    async def _safe_legend(self, package) -> str | None:
        """Legend overlay com fallback para None (per D-11).

        Auto-triggers when VIDEO_LEGEND_ENABLED=true and package has
        video_status='success' (per D-09).
        """
        try:
            worker = self._legend_worker
            if worker is None:
                from src.pipeline.workers.legend_worker import LegendWorker
                worker = LegendWorker()
                self._legend_worker = worker  # Cache for reuse

            video_path = getattr(package, 'video_path', None)
            phrase = getattr(package, 'phrase', None)
            if not video_path or not phrase:
                logger.debug("Legend skipped: no video_path or phrase")
                return None

            return await worker.process(
                video_path=video_path,
                phrase=phrase,
            )
        except Exception as e:
            logger.error(f"Legend falhou: {type(e).__name__}: {e}")
            return None
