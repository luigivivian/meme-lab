"""Repository para Themes (globais e por personagem)."""

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Theme


class ThemeRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, theme_id: int) -> Theme | None:
        stmt = select(Theme).where(Theme.id == theme_id, Theme.is_deleted == False)  # noqa: E712
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_key(
        self, key: str, character_id: int | None = None
    ) -> Theme | None:
        stmt = select(Theme).where(
            Theme.key == key,
            Theme.character_id == character_id,
            Theme.is_deleted == False,  # noqa: E712
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_global(self, include_builtin: bool = True) -> list[Theme]:
        stmt = select(Theme).where(
            Theme.character_id.is_(None),
            Theme.is_deleted == False,  # noqa: E712
        )
        if not include_builtin:
            stmt = stmt.where(Theme.is_builtin == False)  # noqa: E712
        stmt = stmt.order_by(Theme.key)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_for_character(self, character_id: int) -> list[Theme]:
        stmt = (
            select(Theme)
            .where(
                Theme.character_id == character_id,
                Theme.is_deleted == False,  # noqa: E712
            )
            .order_by(Theme.key)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_effective(self, character_id: int | None = None) -> list[Theme]:
        """Retorna themes efetivos: personagem + globais (sem duplicata de key)."""
        if character_id is None:
            return await self.list_global()

        char_themes = await self.list_for_character(character_id)
        char_keys = {t.key for t in char_themes}

        global_themes = await self.list_global()
        merged = list(char_themes)
        for gt in global_themes:
            if gt.key not in char_keys:
                merged.append(gt)
        return merged

    async def create(self, data: dict) -> Theme:
        theme = Theme(**data)
        self.session.add(theme)
        await self.session.flush()
        return theme

    async def update(self, theme_id: int, data: dict) -> Theme | None:
        theme = await self.get_by_id(theme_id)
        if not theme:
            return None
        for key, value in data.items():
            if hasattr(theme, key):
                setattr(theme, key, value)
        await self.session.flush()
        return theme

    async def delete_by_key(
        self, key: str, character_id: int | None = None
    ) -> bool:
        theme = await self.get_by_key(key, character_id)
        if not theme:
            return False
        theme.is_deleted = True
        await self.session.flush()
        return True

    async def count_for_character(self, character_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(Theme)
            .where(
                Theme.character_id == character_id,
                Theme.is_deleted == False,  # noqa: E712
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def exists(self, key: str, character_id: int | None = None) -> bool:
        stmt = (
            select(func.count())
            .select_from(Theme)
            .where(
                Theme.key == key,
                Theme.character_id == character_id,
                Theme.is_deleted == False,  # noqa: E712
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one() > 0
