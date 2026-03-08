"""Camada de monitoramento — executa agentes em paralelo.

Substitui o loop sequencial do orchestrator.py por asyncio.gather().
"""

import asyncio
import logging

from config import AGENT_FETCH_TIMEOUT
from src.pipeline.agents.async_base import AsyncSourceAgent
from src.pipeline.models_v2 import TrendEvent

logger = logging.getLogger("clip-flow.monitoring")


class MonitoringLayer:
    """Executa todos os agentes de monitoramento em paralelo."""

    def __init__(self, agents: list[AsyncSourceAgent]):
        self.agents = agents

    async def fetch_all(self) -> list[TrendEvent]:
        """Executa todos os agentes em paralelo via asyncio.gather."""
        tasks = []
        for agent in self.agents:
            try:
                available = await agent.is_available()
            except Exception:
                available = False

            if available:
                tasks.append(self._safe_fetch(agent))
            else:
                logger.warning(f"Agent '{agent.name}' nao disponivel, pulando")

        if not tasks:
            logger.warning("Nenhum agent disponivel para monitoramento")
            return []

        results = await asyncio.gather(*tasks)
        all_events = []
        for events in results:
            all_events.extend(events)

        logger.info(f"Monitoramento coletou {len(all_events)} eventos de {len(tasks)} agentes")
        return all_events

    async def _safe_fetch(self, agent: AsyncSourceAgent) -> list[TrendEvent]:
        """Fetch com timeout e tratamento de erro — agente nunca derruba o pipeline."""
        try:
            events = await asyncio.wait_for(
                agent.fetch(),
                timeout=AGENT_FETCH_TIMEOUT,
            )
            logger.info(f"Agent '{agent.name}': {len(events)} eventos")
            return events
        except asyncio.TimeoutError:
            logger.error(f"Agent '{agent.name}' timeout ({AGENT_FETCH_TIMEOUT}s)")
            return []
        except Exception as e:
            logger.error(f"Agent '{agent.name}' falhou: {e}")
            return []
