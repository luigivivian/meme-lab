"""PublishingService — agendamento e publicacao de content packages.

Gerencia a fila de publicacao: agendar, cancelar, processar posts pendentes.
Publicadores por plataforma sao placeholders para integracao futura.
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.database.repositories.schedule_repo import ScheduledPostRepository
from src.database.repositories.content_repo import ContentPackageRepository
from src.database.models import ScheduledPost

logger = logging.getLogger("clip-flow.publisher")


class PublishingService:
    """Servico de publicacao — orquestra fila e publishers por plataforma."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.schedule_repo = ScheduledPostRepository(session)
        self.content_repo = ContentPackageRepository(session)

    # ── Agendamento ─────────────────────────────────────────────────────────

    async def schedule_post(
        self,
        content_package_id: int,
        platform: str,
        scheduled_at: datetime,
        character_id: int | None = None,
    ) -> ScheduledPost:
        """Agenda um content package para publicacao."""
        # Validar que o content package existe
        pkg = await self.content_repo.get_by_id(content_package_id)
        if not pkg:
            raise ValueError(f"Content package {content_package_id} nao encontrado")

        # Herdar character_id do package se nao informado
        if character_id is None:
            character_id = pkg.character_id

        post = await self.schedule_repo.create({
            "content_package_id": content_package_id,
            "character_id": character_id,
            "platform": platform,
            "scheduled_at": scheduled_at,
            "status": "queued",
        })

        logger.info(
            f"Post agendado: id={post.id} pkg={content_package_id} "
            f"plataforma={platform} para={scheduled_at.isoformat()}"
        )
        return post

    async def cancel_scheduled(self, post_id: int) -> ScheduledPost | None:
        """Cancela um post agendado."""
        post = await self.schedule_repo.cancel(post_id)
        if post:
            logger.info(f"Post {post_id} cancelado")
        return post

    async def retry_post(self, post_id: int) -> ScheduledPost | None:
        """Recoloca um post falho na fila para retentativa."""
        post = await self.schedule_repo.get_by_id(post_id)
        if not post:
            return None
        if post.status != "failed":
            return None

        post.status = "queued"
        post.error_message = None
        await self.session.flush()
        logger.info(f"Post {post_id} recolocado na fila (retry {post.retry_count})")
        return post

    # ── Resumo da fila ──────────────────────────────────────────────────────

    async def get_queue(self) -> dict:
        """Retorna resumo da fila de publicacao."""
        return await self.schedule_repo.get_queue_summary()

    # ── Processamento ───────────────────────────────────────────────────────

    async def process_due_posts(self) -> list[dict]:
        """Processa posts com horario vencido (scheduled_at <= agora).

        Retorna lista com resultado de cada tentativa de publicacao.
        """
        due_posts = await self.schedule_repo.get_due_posts()
        if not due_posts:
            return []

        logger.info(f"Processando {len(due_posts)} posts pendentes")
        results = []

        for post in due_posts:
            try:
                # Marcar como publishing
                await self.schedule_repo.update_status(post.id, "publishing")
                await self.session.commit()

                # Despachar para publisher da plataforma
                result = await self._dispatch_publish(post)

                # Marcar como publicado
                await self._mark_published(post.id, result)
                await self.session.commit()

                results.append({
                    "post_id": post.id,
                    "status": "published",
                    "result": result,
                })
                logger.info(f"Post {post.id} publicado com sucesso na plataforma {post.platform}")

            except Exception as e:
                logger.error(f"Erro ao publicar post {post.id}: {e}")
                await self.session.rollback()
                await self._mark_failed(post.id, str(e))
                await self.session.commit()
                results.append({
                    "post_id": post.id,
                    "status": "failed",
                    "error": str(e),
                })

        return results

    async def _dispatch_publish(self, post: ScheduledPost) -> dict:
        """Despacha publicacao para o publisher da plataforma."""
        publishers = {
            "instagram": self._publish_instagram,
            "tiktok": self._publish_tiktok,
        }
        publisher = publishers.get(post.platform)
        if not publisher:
            raise ValueError(f"Plataforma nao suportada: {post.platform}")
        return await publisher(post)

    async def _publish_instagram(self, post: ScheduledPost) -> dict:
        """Publica no Instagram via Graph API.

        TODO: Integrar com Instagram Graph API.
        Por enquanto, retorna placeholder indicando que precisa de implementacao.
        """
        logger.warning(
            f"Instagram publisher ainda nao implementado — post {post.id} "
            f"marcado como publicado (placeholder)"
        )
        return {
            "platform": "instagram",
            "status": "placeholder",
            "message": "Instagram Graph API nao configurada. Post marcado como publicado para teste.",
            "post_id": post.id,
            "content_package_id": post.content_package_id,
        }

    async def _publish_tiktok(self, post: ScheduledPost) -> dict:
        """Publica no TikTok.

        TODO: Integrar com TikTok API.
        """
        raise NotImplementedError("TikTok publisher ainda nao implementado")

    async def _mark_published(self, post_id: int, result: dict) -> None:
        """Marca post como publicado com resultado."""
        post = await self.schedule_repo.update_status(
            post_id, "published", publish_result=result
        )
        if post:
            # Tambem marcar o content package como publicado
            await self.content_repo.mark_published(post.content_package_id)

    async def _mark_failed(self, post_id: int, error: str) -> None:
        """Marca post como falho com logica de retry."""
        post = await self.schedule_repo.get_by_id(post_id)
        if not post:
            return

        post.retry_count += 1
        if post.retry_count < post.max_retries:
            # Ainda tem retentativas — volta pra fila
            post.status = "queued"
            post.error_message = f"Tentativa {post.retry_count}/{post.max_retries}: {error}"
            logger.info(
                f"Post {post_id} falhou, retentativa {post.retry_count}/{post.max_retries}"
            )
        else:
            # Excedeu retentativas — marca como falho definitivo
            post.status = "failed"
            post.error_message = f"Excedeu {post.max_retries} tentativas. Ultimo erro: {error}"
            logger.warning(f"Post {post_id} falhou definitivamente apos {post.max_retries} tentativas")

        await self.session.flush()
