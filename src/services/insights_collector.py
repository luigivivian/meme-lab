"""Coletor de metricas de engajamento do Instagram.

Busca insights de posts recentes e armazena no banco de dados.
Projetado para rodar periodicamente via APScheduler ou manualmente.
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_session
from src.services.instagram_client import InstagramClient, InstagramAPIError

logger = logging.getLogger("clip-flow.insights")


class InsightsCollector:
    """Coleta e armazena metricas de engajamento dos posts publicados."""

    def __init__(self, instagram_client: InstagramClient | None = None):
        self.ig = instagram_client or InstagramClient()

    async def collect_recent_insights(self, hours: int = 24) -> list[dict]:
        """Busca insights de posts publicados nas ultimas N horas.

        Consulta a tabela scheduled_posts (ou generated_images) para encontrar
        posts com instagram_media_id, e coleta metricas atualizadas.

        Args:
            hours: Janela de tempo para buscar posts recentes

        Returns:
            Lista de {media_id, metrics: {impressions, reach, ...}, updated_at}
        """
        if not self.ig.is_available():
            logger.warning("Instagram API nao configurada — pulando coleta de insights")
            return []

        results = []
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

        async with get_session() as session:
            media_ids = await self._get_recent_media_ids(session, cutoff)

            if not media_ids:
                logger.info(f"Nenhum post publicado nas ultimas {hours}h para coletar insights")
                return []

            logger.info(f"Coletando insights de {len(media_ids)} posts recentes")

            for media_id in media_ids:
                try:
                    metrics = await self.ig.get_media_insights(media_id)
                    result = {
                        "media_id": media_id,
                        "metrics": metrics,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }
                    results.append(result)

                    await self._store_insights(session, media_id, metrics)

                    logger.info(
                        f"Insights coletados para {media_id}: "
                        f"reach={metrics.get('reach', 0)}, "
                        f"impressions={metrics.get('impressions', 0)}, "
                        f"likes={metrics.get('likes', 0)}, "
                        f"saves={metrics.get('saved', 0)}"
                    )

                except InstagramAPIError as e:
                    logger.warning(f"Erro ao coletar insights de {media_id}: {e}")
                    continue

            await session.commit()

        logger.info(f"Coleta finalizada: {len(results)}/{len(media_ids)} posts atualizados")
        return results

    async def collect_account_insights(self, period: str = "day") -> dict:
        """Busca metricas gerais da conta.

        Args:
            period: "day", "week", "days_28"

        Returns:
            {metric_name: {title, values}, ...}
        """
        if not self.ig.is_available():
            logger.warning("Instagram API nao configurada")
            return {}

        try:
            metrics = await self.ig.get_account_insights(period=period)
            logger.info(f"Metricas da conta coletadas (periodo={period})")
            return metrics
        except InstagramAPIError as e:
            logger.error(f"Erro ao coletar metricas da conta: {e}")
            return {}

    async def get_top_performing(self, hours: int = 168, limit: int = 5) -> list[dict]:
        """Retorna os posts com melhor performance nos ultimos N horas.

        Ordena por engagement (likes + comments + shares + saves).

        Args:
            hours: Janela de tempo (default: 168 = 7 dias)
            limit: Quantidade de posts

        Returns:
            Lista de {media_id, metrics, engagement_score}
        """
        if not self.ig.is_available():
            return []

        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

        async with get_session() as session:
            media_ids = await self._get_recent_media_ids(session, cutoff)

        posts_with_metrics = []
        for media_id in media_ids:
            try:
                metrics = await self.ig.get_media_insights(media_id)
                engagement = (
                    metrics.get("likes", 0)
                    + metrics.get("comments", 0)
                    + metrics.get("shares", 0)
                    + metrics.get("saved", 0)
                )
                posts_with_metrics.append({
                    "media_id": media_id,
                    "metrics": metrics,
                    "engagement_score": engagement,
                })
            except InstagramAPIError:
                continue

        # Ordenar por engagement e retornar top N
        posts_with_metrics.sort(key=lambda x: x["engagement_score"], reverse=True)
        return posts_with_metrics[:limit]

    # ── Helpers internos ───────────────────────────────────────────

    async def _get_recent_media_ids(
        self, session: AsyncSession, cutoff: datetime
    ) -> list[str]:
        """Busca media_ids de posts publicados apos cutoff.

        Tenta buscar da tabela generated_images com campo instagram_media_id.
        Se a tabela/campo nao existir ainda, retorna lista vazia.
        """
        try:
            from src.database.models import GeneratedImage

            stmt = select(GeneratedImage.instagram_media_id).where(
                and_(
                    GeneratedImage.instagram_media_id.isnot(None),
                    GeneratedImage.instagram_media_id != "",
                    GeneratedImage.created_at >= cutoff,
                )
            )
            result = await session.execute(stmt)
            return [row[0] for row in result.fetchall()]

        except Exception as e:
            # Tabela ou campo pode nao existir ainda
            logger.debug(f"Nao foi possivel buscar media_ids do banco: {e}")
            return []

    async def _store_insights(
        self, session: AsyncSession, media_id: str, metrics: dict
    ) -> None:
        """Atualiza metricas no registro do post no banco.

        Salva no campo publish_result (JSON) da tabela generated_images.
        """
        try:
            from src.database.models import GeneratedImage
            import json

            stmt = select(GeneratedImage).where(
                GeneratedImage.instagram_media_id == media_id
            )
            result = await session.execute(stmt)
            image = result.scalar_one_or_none()

            if image:
                # Mesclar metricas no campo publish_result
                existing = {}
                if image.publish_result:
                    existing = (
                        json.loads(image.publish_result)
                        if isinstance(image.publish_result, str)
                        else image.publish_result
                    )

                existing["insights"] = metrics
                existing["insights_updated_at"] = datetime.now(timezone.utc).isoformat()
                image.publish_result = json.dumps(existing, ensure_ascii=False)

                logger.debug(f"Insights armazenados para media_id={media_id}")

        except Exception as e:
            logger.debug(f"Nao foi possivel armazenar insights: {e}")
