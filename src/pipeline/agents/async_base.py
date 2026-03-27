"""Base async para agentes de monitoramento.

AsyncSourceAgent: ABC para agentes nativamente async.
SyncAgentAdapter: wrapper que roda BaseSourceAgent em asyncio.to_thread().
"""

import asyncio
import logging
from abc import ABC, abstractmethod

from src.pipeline.agents.base import BaseSourceAgent
from src.pipeline.models_v2 import TrendEvent, trend_item_to_event


class AsyncSourceAgent(ABC):
    """Classe base abstrata para agentes de monitoramento async."""

    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"clip-flow.agent.{name}")

    @abstractmethod
    async def fetch(self) -> list[TrendEvent]:
        """Busca eventos de trend desta fonte.
        Deve tratar seus proprios erros e retornar lista vazia em caso de falha."""
        ...

    async def is_available(self) -> bool:
        """Verifica se este agente pode rodar."""
        return True


class SyncAgentAdapter(AsyncSourceAgent):
    """Adapter que wrapa um BaseSourceAgent sincrono em async.

    Usa asyncio.to_thread() para rodar fetch() sem bloquear o event loop.
    """

    def __init__(self, sync_agent: BaseSourceAgent):
        super().__init__(sync_agent.name)
        self._sync = sync_agent

    async def fetch(self) -> list[TrendEvent]:
        """Executa fetch sincrono em thread e converte resultado."""
        items = await asyncio.to_thread(self._sync.fetch)
        return [trend_item_to_event(item) for item in items]

    async def is_available(self) -> bool:
        """Verifica disponibilidade em thread."""
        return await asyncio.to_thread(self._sync.is_available)
