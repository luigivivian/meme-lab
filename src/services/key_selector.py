"""Dual-key selector stub (Phase 9 — QUOT-04, QUOT-05).

RED phase: minimal stub so imports work. Tests must FAIL.
"""

from dataclasses import dataclass

from src.database.repositories.usage_repo import UsageRepository  # noqa: F401


@dataclass(frozen=True)
class KeyResolution:
    api_key: str = ""
    tier: str = ""
    mode: str = ""


class UsageAwareKeySelector:
    def __init__(self):
        pass

    async def resolve(self, user_id, session, force_tier=None):
        raise NotImplementedError
