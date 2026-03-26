"""Repository para Characters e CharacterRefs — with tenant isolation."""

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database.models import Character, CharacterRef, User


def _is_admin(user: User | None) -> bool:
    """Check if user has admin role (or no user filtering requested)."""
    return user is None or getattr(user, "role", "user") == "admin"


class CharacterRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_slug(
        self, slug: str, user: User | None = None, include_deleted: bool = False
    ) -> Character | None:
        stmt = select(Character).where(Character.slug == slug)
        if not include_deleted:
            stmt = stmt.where(Character.is_deleted == False)  # noqa: E712
        result = await self.session.execute(stmt)
        character = result.scalar_one_or_none()
        if character and user is not None and not _is_admin(user):
            if character.user_id != user.id:
                raise PermissionError("forbidden")
        return character

    async def get_by_id(
        self, character_id: int, user: User | None = None
    ) -> Character | None:
        stmt = select(Character).where(
            Character.id == character_id, Character.is_deleted == False  # noqa: E712
        )
        result = await self.session.execute(stmt)
        character = result.scalar_one_or_none()
        if character and user is not None and not _is_admin(user):
            if character.user_id != user.id:
                raise PermissionError("forbidden")
        return character

    async def list_all(
        self, user: User | None = None, include_deleted: bool = False
    ) -> list[Character]:
        stmt = select(Character).order_by(Character.created_at.desc())
        if not include_deleted:
            stmt = stmt.where(Character.is_deleted == False)  # noqa: E712
        # Tenant filtering: non-admin sees only own characters
        if user is not None and not _is_admin(user):
            stmt = stmt.where(Character.user_id == user.id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, data: dict) -> Character:
        character = Character(**data)
        self.session.add(character)
        await self.session.flush()
        return character

    async def update(
        self, slug: str, data: dict, user: User | None = None
    ) -> Character | None:
        character = await self.get_by_slug(slug, user=user)
        if not character:
            return None
        for key, value in data.items():
            if hasattr(character, key):
                setattr(character, key, value)
        await self.session.flush()
        return character

    async def soft_delete(self, slug: str, user: User | None = None) -> bool:
        character = await self.get_by_slug(slug, user=user)
        if not character:
            return False
        character.is_deleted = True
        await self.session.flush()
        return True

    async def exists(self, slug: str, user: User | None = None) -> bool:
        stmt = select(func.count()).select_from(Character).where(Character.slug == slug)
        if user is not None and not _is_admin(user):
            stmt = stmt.where(Character.user_id == user.id)
        result = await self.session.execute(stmt)
        return result.scalar_one() > 0

    # ---- CharacterRef methods ----

    async def get_refs(
        self, character_id: int, status: str | None = None
    ) -> list[CharacterRef]:
        stmt = select(CharacterRef).where(CharacterRef.character_id == character_id)
        if status:
            stmt = stmt.where(CharacterRef.status == status)
        stmt = stmt.order_by(CharacterRef.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_ref_by_filename(
        self, character_id: int, filename: str
    ) -> CharacterRef | None:
        stmt = select(CharacterRef).where(
            CharacterRef.character_id == character_id,
            CharacterRef.filename == filename,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_ref(self, data: dict) -> CharacterRef:
        ref = CharacterRef(**data)
        self.session.add(ref)
        await self.session.flush()
        return ref

    async def update_ref_status(
        self, character_id: int, filename: str, new_status: str
    ) -> CharacterRef | None:
        ref = await self.get_ref_by_filename(character_id, filename)
        if not ref:
            return None
        ref.status = new_status
        await self.session.flush()
        return ref

    async def delete_ref(self, character_id: int, filename: str) -> bool:
        ref = await self.get_ref_by_filename(character_id, filename)
        if not ref:
            return False
        await self.session.delete(ref)
        await self.session.flush()
        return True

    async def count_refs_by_status(self, character_id: int) -> dict[str, int]:
        stmt = (
            select(CharacterRef.status, func.count())
            .where(CharacterRef.character_id == character_id)
            .group_by(CharacterRef.status)
        )
        result = await self.session.execute(stmt)
        counts = {row[0]: row[1] for row in result.all()}
        return {
            "approved": counts.get("approved", 0),
            "pending": counts.get("pending", 0),
            "rejected": counts.get("rejected", 0),
        }
