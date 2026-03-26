"""Camada de monitoramento — executa agentes em paralelo.

Substitui o loop sequencial do orchestrator.py por asyncio.gather().
"""

import asyncio
import logging
import time

from config import AGENT_FETCH_TIMEOUT
from src.pipeline.agents.async_base import AsyncSourceAgent
from src.pipeline.models_v2 import TrendEvent

logger = logging.getLogger("clip-flow.monitoring")


class MonitoringLayer:
    """Executa todos os agentes de monitoramento em paralelo."""

    def __init__(self, agents: list[AsyncSourceAgent]):
        self.agents = agents

    async def fetch_all(self, on_step=None) -> list[TrendEvent]:
        """Executa todos os agentes em paralelo via asyncio.gather."""
        available_agents = []
        skipped_agents = []

        for agent in self.agents:
            try:
                available = await agent.is_available()
            except Exception as e:
                available = False
                logger.debug(f"  Agent '{agent.name}' is_available() erro: {e}")

            if available:
                available_agents.append(agent)
                if on_step:
                    on_step(agent.name, "running", "Fetching...")
            else:
                skipped_agents.append(agent.name)
                if on_step:
                    on_step(agent.name, "idle", "Indisponivel")

        logger.info(f"Agents disponiveis: {len(available_agents)}/{len(self.agents)}")
        if skipped_agents:
            logger.warning(f"Agents pulados: {', '.join(skipped_agents)}")

        if not available_agents:
            logger.warning("Nenhum agent disponivel para monitoramento")
            return []

        tasks = [self._safe_fetch(agent, on_step) for agent in available_agents]
        results = await asyncio.gather(*tasks)

        # Resumo por agente
        all_events = []
        agent_summary = []
        for agent, events in zip(available_agents, results):
            all_events.extend(events)
            agent_summary.append(f"{agent.name}={len(events)}")

        logger.info(f"Monitoramento: {len(all_events)} eventos de {len(available_agents)} agents [{', '.join(agent_summary)}]")
        return all_events

    async def _safe_fetch(self, agent: AsyncSourceAgent, on_step=None) -> list[TrendEvent]:
        """Fetch com timeout e tratamento de erro — agente nunca derruba o pipeline."""
        t0 = time.perf_counter()
        try:
            events = await asyncio.wait_for(
                agent.fetch(),
                timeout=AGENT_FETCH_TIMEOUT,
            )
            elapsed = time.perf_counter() - t0
            logger.info(f"  Agent '{agent.name}': {len(events)} eventos em {elapsed:.1f}s")
            if on_step:
                on_step(agent.name, "done", f"{len(events)} eventos")
            return events
        except asyncio.TimeoutError:
            elapsed = time.perf_counter() - t0
            logger.error(f"  Agent '{agent.name}' TIMEOUT apos {elapsed:.1f}s (limit={AGENT_FETCH_TIMEOUT}s)")
            if on_step:
                on_step(agent.name, "error", f"Timeout {AGENT_FETCH_TIMEOUT}s")
            return []
        except Exception as e:
            elapsed = time.perf_counter() - t0
            logger.error(f"  Agent '{agent.name}' FALHOU em {elapsed:.1f}s: {type(e).__name__}: {e}")
            if on_step:
                on_step(agent.name, "error", str(e)[:60])
            return []
