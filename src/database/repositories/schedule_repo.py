"""Repository para ScheduledPost — fila de publicacao — with tenant isolation."""

from datetime import datetime
from typing import Optional

from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database.models import ScheduledPost, Character, User


def _is_admin(user: User | None) -> bool:
    """Check if user has admin role (or no user filtering requested)."""
    return user is None or getattr(user, "role", "user") == "admin"


class ScheduledPostRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: dict) -> ScheduledPost:
        """Cria um novo post agendado."""
        post = ScheduledPost(**data)
        self.session.add(post)
        await self.session.flush()
        return post

    async def get_by_id(
        self, post_id: int, user: User | None = None
    ) -> ScheduledPost | None:
        """Busca post agendado por ID."""
        stmt = select(ScheduledPost).options(
            selectinload(ScheduledPost.content_package),
            selectinload(ScheduledPost.character),
        ).where(ScheduledPost.id == post_id)
        result = await self.session.execute(stmt)
        post = result.scalar_one_or_none()
        if post and not _is_admin(user):
            character = await self.session.get(Character, post.character_id)
            if not character or character.user_id != user.id:
                raise PermissionError("forbidden")
        return post

    async def list_posts(
        self,
        limit: int = 50,
        offset: int = 0,
        status: str | None = None,
        platform: str | None = None,
        character_id: int | None = None,
        user: User | None = None,
    ) -> list[ScheduledPost]:
        """Lista posts agendados com filtros opcionais."""
        stmt = select(ScheduledPost).options(
            selectinload(ScheduledPost.content_package),
            selectinload(ScheduledPost.character),
        ).order_by(ScheduledPost.scheduled_at.asc())
        if status is not None:
            stmt = stmt.where(ScheduledPost.status == status)
        if platform is not None:
            stmt = stmt.where(ScheduledPost.platform == platform)
        if character_id is not None:
            stmt = stmt.where(ScheduledPost.character_id == character_id)
        # Tenant filtering: join Character to filter by user_id
        if not _is_admin(user):
            stmt = stmt.join(
                Character, ScheduledPost.character_id == Character.id
            ).where(Character.user_id == user.id)
        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count(
        self,
        status: str | None = None,
        platform: str | None = None,
        user: User | None = None,
    ) -> int:
        """Conta posts agendados com filtros opcionais."""
        stmt = select(func.count()).select_from(ScheduledPost)
        if status is not None:
            stmt = stmt.where(ScheduledPost.status == status)
        if platform is not None:
            stmt = stmt.where(ScheduledPost.platform == platform)
        if not _is_admin(user):
            stmt = stmt.join(
                Character, ScheduledPost.character_id == Character.id
            ).where(Character.user_id == user.id)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get_due_posts(self) -> list[ScheduledPost]:
        """Retorna posts com scheduled_at <= agora e status 'queued'."""
        now = datetime.utcnow()
        stmt = (
            select(ScheduledPost)
            .options(
                selectinload(ScheduledPost.content_package),
                selectinload(ScheduledPost.character),
            )
            .where(ScheduledPost.status == "queued")
            .where(ScheduledPost.scheduled_at <= now)
            .order_by(ScheduledPost.scheduled_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_status(
        self,
        post_id: int,
        status: str,
        publish_result: dict | None = None,
        error: str | None = None,
    ) -> ScheduledPost | None:
        """Atualiza status de um post agendado."""
        post = await self.get_by_id(post_id)
        if not post:
            return None
        post.status = status
        if publish_result is not None:
            post.publish_result = publish_result
        if error is not None:
            post.error_message = error
        if status == "published":
            post.published_at = datetime.utcnow()
        await self.session.flush()
        return post

    async def cancel(self, post_id: int) -> ScheduledPost | None:
        """Cancela um post agendado (apenas se estiver queued)."""
        post = await self.get_by_id(post_id)
        if not post:
            return None
        if post.status not in ("queued", "failed"):
            return None
        post.status = "cancelled"
        await self.session.flush()
        return post

    async def increment_retry(self, post_id: int) -> ScheduledPost | None:
        """Incrementa retry_count e recoloca na fila se nao excedeu max_retries."""
        post = await self.get_by_id(post_id)
        if not post:
            return None
        post.retry_count += 1
        if post.retry_count < post.max_retries:
            post.status = "queued"
            post.error_message = None
        await self.session.flush()
        return post

    async def get_queue_summary(self, user: User | None = None) -> dict:
        """Retorna contagem por status e plataforma."""
        stmt = (
            select(
                ScheduledPost.platform,
                ScheduledPost.status,
                func.count().label("total"),
            )
        )
        # Tenant filtering: join Character to filter by user_id
        if not _is_admin(user):
            stmt = stmt.join(
                Character, ScheduledPost.character_id == Character.id
            ).where(Character.user_id == user.id)
        stmt = stmt.group_by(ScheduledPost.platform, ScheduledPost.status)
        result = await self.session.execute(stmt)
        rows = result.all()

        # Montar dict: {platform: {status: count}}
        summary: dict = {}
        for platform, status, total in rows:
            if platform not in summary:
                summary[platform] = {}
            summary[platform][status] = total

        return summary

    async def get_posts_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        user: User | None = None,
    ) -> list[ScheduledPost]:
        """Retorna posts agendados entre duas datas (para calendario)."""
        stmt = (
            select(ScheduledPost)
            .options(
                selectinload(ScheduledPost.content_package),
                selectinload(ScheduledPost.character),
            )
            .where(ScheduledPost.scheduled_at >= start_date)
            .where(ScheduledPost.scheduled_at <= end_date)
            .order_by(ScheduledPost.scheduled_at.asc())
        )
        # Tenant filtering: join Character to filter by user_id
        if not _is_admin(user):
            stmt = stmt.join(
                Character, ScheduledPost.character_id == Character.id
            ).where(Character.user_id == user.id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
