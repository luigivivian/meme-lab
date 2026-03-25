"""Repository para BatchJob — with tenant isolation."""

from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import BatchJob, Character, User


def _is_admin(user: User | None) -> bool:
    """Check if user has admin role (or no user filtering requested)."""
    return user is None or getattr(user, "role", "user") == "admin"


class BatchJobRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_job_id(
        self, job_id: str, user: User | None = None
    ) -> BatchJob | None:
        stmt = select(BatchJob).where(BatchJob.job_id == job_id)
        result = await self.session.execute(stmt)
        job = result.scalar_one_or_none()
        if job and not _is_admin(user):
            character = await self.session.get(Character, job.character_id)
            if not character or character.user_id != user.id:
                raise PermissionError("forbidden")
        return job

    async def list_jobs(
        self,
        limit: int = 50,
        offset: int = 0,
        status: str | None = None,
        user: User | None = None,
    ) -> list[BatchJob]:
        stmt = select(BatchJob).order_by(BatchJob.created_at.desc())
        if status:
            stmt = stmt.where(BatchJob.status == status)
        # Tenant filtering: join Character to filter by user_id
        if not _is_admin(user):
            stmt = stmt.join(
                Character, BatchJob.character_id == Character.id
            ).where(Character.user_id == user.id)
        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, data: dict) -> BatchJob:
        job = BatchJob(**data)
        self.session.add(job)
        await self.session.flush()
        return job

    async def update(self, job_id: str, data: dict) -> BatchJob | None:
        job = await self.get_by_job_id(job_id)
        if not job:
            return None
        for key, value in data.items():
            if hasattr(job, key):
                setattr(job, key, value)
        await self.session.flush()
        return job

    async def finish_job(
        self,
        job_id: str,
        status: str = "completed",
        results: list | None = None,
        errors: list | None = None,
    ) -> BatchJob | None:
        job = await self.get_by_job_id(job_id)
        if not job:
            return None
        job.status = status
        job.finished_at = datetime.now()
        if results is not None:
            job.results = results
        if errors is not None:
            job.errors = errors
        await self.session.flush()
        return job

    async def increment_done(self, job_id: str) -> BatchJob | None:
        job = await self.get_by_job_id(job_id)
        if not job:
            return None
        job.done += 1
        await self.session.flush()
        return job

    async def increment_failed(self, job_id: str) -> BatchJob | None:
        job = await self.get_by_job_id(job_id)
        if not job:
            return None
        job.failed += 1
        await self.session.flush()
        return job

    async def count(self, user: User | None = None) -> int:
        stmt = select(func.count()).select_from(BatchJob)
        if not _is_admin(user):
            stmt = stmt.join(
                Character, BatchJob.character_id == Character.id
            ).where(Character.user_id == user.id)
        result = await self.session.execute(stmt)
        return result.scalar_one()
