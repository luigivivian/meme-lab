"""Engine e session factory async — suporta MySQL (aiomysql) e SQLite (aiosqlite)."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import DATABASE_URL

_engine = None
_session_factory = None


def _is_sqlite() -> bool:
    return "sqlite" in DATABASE_URL


def get_engine():
    """Retorna engine singleton (cria na primeira chamada)."""
    global _engine
    if _engine is None:
        kwargs = {"echo": False}
        if _is_sqlite():
            kwargs["connect_args"] = {"check_same_thread": False}
        else:
            kwargs["pool_size"] = 10
            kwargs["max_overflow"] = 20
            kwargs["pool_recycle"] = 3600
        _engine = create_async_engine(DATABASE_URL, **kwargs)
    return _engine


def get_session_factory():
    """Retorna session factory singleton."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


async def get_session():
    """Async context manager para obter uma session.

    Uso como FastAPI dependency:
        async def rota(session: AsyncSession = Depends(get_session)):
            ...
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db():
    """Cria todas as tabelas no banco (para dev/testes).

    Em producao, usar Alembic migrations.
    """
    from src.database.base import Base
    import src.database.models  # noqa: F401 — registra todos os models

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
