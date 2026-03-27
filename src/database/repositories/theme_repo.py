"""Repository para Themes (globais e por personagem) — with tenant isolation."""

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Theme, Character, User


def _is_admin(user: User | None) -> bool:
    """Check if user has admin role (or no user filtering requested)."""
    return user is None or getattr(user, "role", "user") == "admin"


class ThemeRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(
        self, theme_id: int, user: User | None = None
    ) -> Theme | None:
        stmt = select(Theme).where(Theme.id == theme_id, Theme.is_deleted == False)  # noqa: E712
        result = await self.session.execute(stmt)
        theme = result.scalar_one_or_none()
        if theme and not _is_admin(user):
            # Global themes (no user_id, no character_id) are accessible to all
            if theme.user_id is None and theme.character_id is None:
                return theme
            # User-owned theme: check user_id directly
            if theme.user_id is not None and theme.user_id != user.id:
                raise PermissionError("forbidden")
            # Character-owned theme: check via Character.user_id
            if theme.character_id is not None:
                character = await self.session.get(Character, theme.character_id)
                if not character or character.user_id != user.id:
                    raise PermissionError("forbidden")
        return theme

    async def get_by_key(
        self, key: str, character_id: int | None = None, user: User | None = None
    ) -> Theme | None:
        stmt = select(Theme).where(
            Theme.key == key,
            Theme.character_id == character_id,
            Theme.is_deleted == False,  # noqa: E712
        )
        result = await self.session.execute(stmt)
        theme = result.scalar_one_or_none()
        if theme and not _is_admin(user):
            # Global themes accessible to all
            if theme.user_id is None and theme.character_id is None:
                return theme
            if theme.user_id is not None and theme.user_id != user.id:
                raise PermissionError("forbidden")
            if theme.character_id is not None:
                character = await self.session.get(Character, theme.character_id)
                if not character or character.user_id != user.id:
                    raise PermissionError("forbidden")
        return theme

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

    async def list_effective(
        self, character_id: int | None = None, user: User | None = None
    ) -> list[Theme]:
        """Retorna themes efetivos: personagem + globais (sem duplicata de key).

        For non-admin users: returns global themes + user's own themes.
        For admin: returns all non-deleted themes.
        """
        if _is_admin(user):
            # Admin sees everything
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

        # Non-admin user: global + user's own themes
        if character_id is None:
            # Global themes + user's own themes (by user_id)
            stmt = (
                select(Theme)
                .where(
                    Theme.is_deleted == False,  # noqa: E712
                    or_(
                        and_(Theme.user_id.is_(None), Theme.character_id.is_(None)),
                        Theme.user_id == user.id,
                    ),
                )
                .order_by(Theme.key)
            )
            result = await self.session.execute(stmt)
            return list(result.scalars().all())

        # With character_id: character themes + global (no duplicates)
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
