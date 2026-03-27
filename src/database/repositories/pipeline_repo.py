"""Repository para PipelineRun, TrendEvent, WorkOrder e AgentStat — with tenant isolation."""

from datetime import datetime
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database.models import PipelineRun, TrendEvent, WorkOrder, AgentStat, Character, User


def _is_admin(user: User | None) -> bool:
    """Check if user has admin role (or no user filtering requested)."""
    return user is None or getattr(user, "role", "user") == "admin"


class PipelineRunRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ---- PipelineRun ----

    async def get_by_run_id(
        self, run_id: str, user: User | None = None
    ) -> PipelineRun | None:
        stmt = select(PipelineRun).where(PipelineRun.run_id == run_id)
        result = await self.session.execute(stmt)
        run = result.scalar_one_or_none()
        if run and run.character_id and not _is_admin(user):
            character = await self.session.get(Character, run.character_id)
            if not character or character.user_id != user.id:
                raise PermissionError("forbidden")
        return run

    async def get_by_run_id_with_relations(
        self, run_id: str, user: User | None = None
    ) -> PipelineRun | None:
        stmt = (
            select(PipelineRun)
            .where(PipelineRun.run_id == run_id)
            .options(
                selectinload(PipelineRun.trend_events),
                selectinload(PipelineRun.work_orders),
                selectinload(PipelineRun.content_packages),
                selectinload(PipelineRun.agent_stats),
            )
        )
        result = await self.session.execute(stmt)
        run = result.scalar_one_or_none()
        if run and run.character_id and not _is_admin(user):
            character = await self.session.get(Character, run.character_id)
            if not character or character.user_id != user.id:
                raise PermissionError("forbidden")
        return run

    async def list_runs(
        self,
        limit: int = 50,
        offset: int = 0,
        status: str | None = None,
        character_id: int | None = None,
        user: User | None = None,
    ) -> list[PipelineRun]:
        stmt = select(PipelineRun).order_by(PipelineRun.started_at.desc())
        if status:
            stmt = stmt.where(PipelineRun.status == status)
        if character_id is not None:
            stmt = stmt.where(PipelineRun.character_id == character_id)
        # Tenant filtering: join Character to filter by user_id
        if not _is_admin(user):
            stmt = stmt.join(
                Character, PipelineRun.character_id == Character.id
            ).where(Character.user_id == user.id)
        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_run(self, data: dict) -> PipelineRun:
        run = PipelineRun(**data)
        self.session.add(run)
        await self.session.flush()
        return run

    async def update_run(self, run_id: str, data: dict) -> PipelineRun | None:
        run = await self.get_by_run_id(run_id)
        if not run:
            return None
        for key, value in data.items():
            if hasattr(run, key):
                setattr(run, key, value)
        await self.session.flush()
        return run

    async def finish_run(
        self,
        run_id: str,
        status: str = "completed",
        results: dict | None = None,
    ) -> PipelineRun | None:
        run = await self.get_by_run_id(run_id)
        if not run:
            return None
        run.status = status
        run.finished_at = datetime.now()
        if run.started_at:
            run.duration_seconds = (run.finished_at - run.started_at).total_seconds()
        if results:
            for key, value in results.items():
                if hasattr(run, key):
                    setattr(run, key, value)
        await self.session.flush()
        return run

    async def count_runs(
        self,
        status: str | None = None,
        character_id: int | None = None,
        user: User | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(PipelineRun)
        if status:
            stmt = stmt.where(PipelineRun.status == status)
        if character_id is not None:
            stmt = stmt.where(PipelineRun.character_id == character_id)
        if not _is_admin(user):
            stmt = stmt.join(
                Character, PipelineRun.character_id == Character.id
            ).where(Character.user_id == user.id)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    # ---- TrendEvent ----

    async def create_trend_event(self, data: dict) -> TrendEvent:
        event = TrendEvent(**data)
        self.session.add(event)
        await self.session.flush()
        return event

    async def bulk_create_trend_events(self, events: list[dict]) -> list[TrendEvent]:
        objects = [TrendEvent(**e) for e in events]
        self.session.add_all(objects)
        await self.session.flush()
        return objects

    async def get_trend_events_for_run(self, pipeline_run_id: int) -> list[TrendEvent]:
        stmt = (
            select(TrendEvent)
            .where(TrendEvent.pipeline_run_id == pipeline_run_id)
            .order_by(TrendEvent.score.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ---- WorkOrder ----

    async def create_work_order(self, data: dict) -> WorkOrder:
        order = WorkOrder(**data)
        self.session.add(order)
        await self.session.flush()
        return order

    async def bulk_create_work_orders(self, orders: list[dict]) -> list[WorkOrder]:
        objects = [WorkOrder(**o) for o in orders]
        self.session.add_all(objects)
        await self.session.flush()
        return objects

    async def get_work_orders_for_run(self, pipeline_run_id: int) -> list[WorkOrder]:
        stmt = (
            select(WorkOrder)
            .where(WorkOrder.pipeline_run_id == pipeline_run_id)
            .order_by(WorkOrder.priority.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ---- AgentStat ----

    async def create_agent_stat(self, data: dict) -> AgentStat:
        stat = AgentStat(**data)
        self.session.add(stat)
        await self.session.flush()
        return stat

    async def bulk_create_agent_stats(self, stats: list[dict]) -> list[AgentStat]:
        objects = [AgentStat(**s) for s in stats]
        self.session.add_all(objects)
        await self.session.flush()
        return objects

    async def get_agent_stats_for_run(self, pipeline_run_id: int) -> list[AgentStat]:
        stmt = (
            select(AgentStat)
            .where(AgentStat.pipeline_run_id == pipeline_run_id)
            .order_by(AgentStat.agent_name)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
