"""PublishingService — agendamento e publicacao de content packages.

Gerencia a fila de publicacao: agendar, cancelar, processar posts pendentes.
Instagram publishing via Graph API with OAuth tokens from Phase 14.
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
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

        Flow:
        1. Resolve user_id from post's character or content_package chain
        2. Load active InstagramConnection for that user
        3. Decrypt OAuth token via InstagramOAuthService
        4. Upload image to GCS for public URL
        5. Build caption from content package
        6. Publish via InstagramClient (image or carousel)
        7. Return result with instagram_media_id and permalink
        """
        from sqlalchemy import select as sa_select
        from src.database.models import (
            InstagramConnection, Character, ContentPackage,
        )
        from src.services.instagram_oauth import InstagramOAuthService
        from src.services.instagram_client import (
            InstagramClient, InstagramAPIError, InstagramRateLimitError,
        )
        from src.video_gen.gcs_uploader import GCSUploader

        # 1. Resolve user_id from character
        user_id = None
        if post.character_id:
            character = await self.session.get(Character, post.character_id)
            if character:
                user_id = character.user_id

        # Fallback: content_package -> character -> user_id
        if user_id is None:
            pkg = await self.session.get(ContentPackage, post.content_package_id)
            if pkg and pkg.character_id:
                character = await self.session.get(Character, pkg.character_id)
                if character:
                    user_id = character.user_id

        if user_id is None:
            raise Exception(
                f"Nao foi possivel determinar user_id para post {post.id} "
                f"(character_id={post.character_id}, content_package_id={post.content_package_id})"
            )

        # 2. Load active InstagramConnection for this user
        result = await self.session.execute(
            sa_select(InstagramConnection).where(
                InstagramConnection.user_id == user_id,
                InstagramConnection.status == "active",
            )
        )
        connection = result.scalar_one_or_none()
        if not connection:
            raise Exception(f"No active Instagram connection for user {user_id}")

        # 3. Decrypt access token
        oauth_service = InstagramOAuthService(self.session)
        decrypted_token = oauth_service._decrypt_token(connection.access_token_encrypted)
        ig_user_id = connection.ig_user_id

        # 4. Load content package for image and caption
        package = await self.session.get(ContentPackage, post.content_package_id)
        if not package:
            raise Exception(f"Content package {post.content_package_id} nao encontrado")

        # 5. Upload image to GCS for public URL
        image_path = package.image_path
        if not image_path or not Path(image_path).exists():
            raise Exception(
                f"Imagem nao encontrada: {image_path} "
                f"(content_package_id={package.id})"
            )

        uploader = GCSUploader(bucket_name="meme-lab-bucket")
        filename = Path(image_path).name
        remote_name = f"instagram-media/{package.id}/{filename}"
        signed_url = uploader.upload_image(str(image_path), remote_name=remote_name)
        logger.info(f"Imagem enviada ao GCS: {remote_name}")

        # 6. Build caption
        caption_text = package.caption if package.caption else package.phrase
        if package.hashtags:
            hashtag_str = " ".join(
                tag if tag.startswith("#") else f"#{tag}"
                for tag in package.hashtags
            )
            caption_text = f"{caption_text}\n\n{hashtag_str}"

        # 7. Publish via InstagramClient
        client = InstagramClient(access_token=decrypted_token, business_id=ig_user_id)
        try:
            carousel_slides = getattr(package, "carousel_slides", None) or []
            if len(carousel_slides) >= 2:
                # Carousel: upload all slides to GCS
                slide_urls = []
                for i, slide in enumerate(carousel_slides):
                    slide_path = slide.get("image_path", "") if isinstance(slide, dict) else str(slide)
                    if slide_path and Path(slide_path).exists():
                        slide_name = f"instagram-media/{package.id}/slide_{i}_{Path(slide_path).name}"
                        slide_url = uploader.upload_image(str(slide_path), remote_name=slide_name)
                        slide_urls.append(slide_url)
                    else:
                        # Use main image as fallback for broken slides
                        slide_urls.append(signed_url)

                ig_result = await client.publish_carousel(
                    image_urls=slide_urls, caption=caption_text
                )
            else:
                ig_result = await client.publish_image(
                    image_url=signed_url, caption=caption_text
                )

            logger.info(
                f"Post {post.id} publicado no Instagram: "
                f"media_id={ig_result.get('id')} permalink={ig_result.get('permalink')}"
            )
            return {
                "platform": "instagram",
                "instagram_media_id": ig_result.get("id"),
                "permalink": ig_result.get("permalink"),
                "timestamp": ig_result.get("timestamp"),
                "media_type": ig_result.get("media_type", "IMAGE"),
                "post_id": post.id,
                "content_package_id": post.content_package_id,
            }

        except InstagramRateLimitError as e:
            raise Exception(
                f"Instagram rate limit atingido — aguardar antes de retry: {e}"
            ) from e
        except InstagramAPIError as e:
            raise Exception(f"Instagram API error: {e}") from e
        finally:
            await client.close()

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
        """Marca post como falho com logica de retry e exponential backoff."""
        post = await self.schedule_repo.get_by_id(post_id)
        if not post:
            return

        post.retry_count += 1
        if post.retry_count < post.max_retries:
            # Ainda tem retentativas — volta pra fila com backoff
            post.status = "queued"
            post.error_message = f"Tentativa {post.retry_count}/{post.max_retries}: {error}"
            # Exponential backoff: retry_count * 120 seconds
            backoff_seconds = post.retry_count * 120
            post.scheduled_at = datetime.utcnow() + timedelta(seconds=backoff_seconds)
            logger.info(
                f"Post {post_id} falhou, retentativa {post.retry_count}/{post.max_retries} "
                f"em {backoff_seconds}s"
            )
        else:
            # Excedeu retentativas — marca como falho definitivo
            post.status = "failed"
            post.error_message = f"Excedeu {post.max_retries} tentativas. Ultimo erro: {error}"
            logger.warning(f"Post {post_id} falhou definitivamente apos {post.max_retries} tentativas")

        await self.session.flush()
