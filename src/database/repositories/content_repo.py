"""Repository para ContentPackage e GeneratedImage."""

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database.models import ContentPackage, GeneratedImage


class ContentPackageRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, package_id: int) -> ContentPackage | None:
        stmt = select(ContentPackage).where(ContentPackage.id == package_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_packages(
        self,
        limit: int = 50,
        offset: int = 0,
        character_id: int | None = None,
        pipeline_run_id: int | None = None,
        min_quality: float | None = None,
        is_published: bool | None = None,
    ) -> list[ContentPackage]:
        stmt = select(ContentPackage).order_by(ContentPackage.created_at.desc())
        if character_id is not None:
            stmt = stmt.where(ContentPackage.character_id == character_id)
        if pipeline_run_id is not None:
            stmt = stmt.where(ContentPackage.pipeline_run_id == pipeline_run_id)
        if min_quality is not None:
            stmt = stmt.where(ContentPackage.quality_score >= min_quality)
        if is_published is not None:
            stmt = stmt.where(ContentPackage.is_published == is_published)
        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, data: dict) -> ContentPackage:
        package = ContentPackage(**data)
        self.session.add(package)
        await self.session.flush()
        return package

    async def bulk_create(self, packages: list[dict]) -> list[ContentPackage]:
        objects = [ContentPackage(**p) for p in packages]
        self.session.add_all(objects)
        await self.session.flush()
        return objects

    async def update(self, package_id: int, data: dict) -> ContentPackage | None:
        package = await self.get_by_id(package_id)
        if not package:
            return None
        for key, value in data.items():
            if hasattr(package, key):
                setattr(package, key, value)
        await self.session.flush()
        return package

    async def mark_published(self, package_id: int) -> ContentPackage | None:
        package = await self.get_by_id(package_id)
        if not package:
            return None
        package.is_published = True
        package.published_at = datetime.now()
        await self.session.flush()
        return package

    async def count(self, character_id: int | None = None) -> int:
        stmt = select(func.count()).select_from(ContentPackage)
        if character_id is not None:
            stmt = stmt.where(ContentPackage.character_id == character_id)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get_by_ids(self, package_ids: list[int], load_character: bool = False) -> list[ContentPackage]:
        """Busca multiplos packages por lista de IDs."""
        if not package_ids:
            return []
        stmt = (
            select(ContentPackage)
            .where(ContentPackage.id.in_(package_ids))
            .order_by(ContentPackage.created_at.desc())
        )
        if load_character:
            stmt = stmt.options(selectinload(ContentPackage.character))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id_with_character(self, package_id: int) -> ContentPackage | None:
        """Busca package por ID com eager load do personagem."""
        stmt = (
            select(ContentPackage)
            .where(ContentPackage.id == package_id)
            .options(selectinload(ContentPackage.character))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_for_run(self, pipeline_run_id: int) -> list[ContentPackage]:
        stmt = (
            select(ContentPackage)
            .where(ContentPackage.pipeline_run_id == pipeline_run_id)
            .order_by(ContentPackage.quality_score.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_recent_topics(self, days: int = 7, limit: int = 100) -> list[str]:
        """Retorna topics unicos dos ultimos N dias para dedup cross-run.

        Args:
            days: quantos dias olhar para tras.
            limit: maximo de topics a retornar.

        Returns:
            Lista de topics (lowercase, sem duplicatas).
        """
        cutoff = datetime.now() - timedelta(days=days)
        stmt = (
            select(ContentPackage.topic)
            .where(ContentPackage.created_at >= cutoff)
            .where(ContentPackage.topic != "")
            .where(ContentPackage.topic.is_not(None))
            .distinct()
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return [row[0].lower().strip() for row in result.all() if row[0]]


class GeneratedImageRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, image_id: int) -> GeneratedImage | None:
        stmt = select(GeneratedImage).where(GeneratedImage.id == image_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_images(
        self,
        limit: int = 50,
        offset: int = 0,
        character_id: int | None = None,
        image_type: str | None = None,
        source: str | None = None,
    ) -> list[GeneratedImage]:
        stmt = select(GeneratedImage).order_by(GeneratedImage.created_at.desc())
        if character_id is not None:
            stmt = stmt.where(GeneratedImage.character_id == character_id)
        if image_type:
            stmt = stmt.where(GeneratedImage.image_type == image_type)
        if source:
            stmt = stmt.where(GeneratedImage.source == source)
        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, data: dict) -> GeneratedImage:
        image = GeneratedImage(**data)
        self.session.add(image)
        await self.session.flush()
        return image

    async def count(self, character_id: int | None = None) -> int:
        stmt = select(func.count()).select_from(GeneratedImage)
        if character_id is not None:
            stmt = stmt.where(GeneratedImage.character_id == character_id)
        result = await self.session.execute(stmt)
        return result.scalar_one()
