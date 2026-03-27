"""Testes rapidos dos agents parcialmente implementados (BlueSky, HackerNews, Lemmy).

Verifica que cada agent:
1. Instancia corretamente e herda de AsyncSourceAgent
2. Reporta is_available() como True
3. Retorna lista de TrendEvent (pode ser vazia se API estiver fora)
4. Cada evento tem campos obrigatorios preenchidos
"""

import asyncio
import pytest

from src.pipeline.agents.bluesky_trends import BlueSkyTrendsAgent
from src.pipeline.agents.hackernews import HackerNewsAgent
from src.pipeline.agents.lemmy_communities import LemmyCommunitiesAgent
from src.pipeline.agents.async_base import AsyncSourceAgent
from src.pipeline.models_v2 import TrendEvent, TrendSource


# === Testes de estrutura ===

class TestAgentStructure:
    """Verifica que os agents seguem o contrato AsyncSourceAgent."""

    def test_bluesky_herda_base(self):
        agent = BlueSkyTrendsAgent()
        assert isinstance(agent, AsyncSourceAgent)
        assert agent.name == "bluesky_trends"

    def test_hackernews_herda_base(self):
        agent = HackerNewsAgent()
        assert isinstance(agent, AsyncSourceAgent)
        assert agent.name == "hackernews"

    def test_lemmy_herda_base(self):
        agent = LemmyCommunitiesAgent()
        assert isinstance(agent, AsyncSourceAgent)
        assert agent.name == "lemmy"

    def test_trend_source_enum_tem_novos_valores(self):
        """TrendSource deve incluir BLUESKY, HACKERNEWS e LEMMY."""
        assert hasattr(TrendSource, "BLUESKY")
        assert hasattr(TrendSource, "HACKERNEWS")
        assert hasattr(TrendSource, "LEMMY")


# === Testes de disponibilidade ===

class TestAgentAvailability:
    """Verifica is_available() — todos usam API publica, devem retornar True."""

    @pytest.mark.asyncio
    async def test_bluesky_disponivel(self):
        agent = BlueSkyTrendsAgent()
        assert await agent.is_available() is True

    @pytest.mark.asyncio
    async def test_hackernews_disponivel(self):
        agent = HackerNewsAgent()
        assert await agent.is_available() is True

    @pytest.mark.asyncio
    async def test_lemmy_disponivel(self):
        agent = LemmyCommunitiesAgent()
        assert await agent.is_available() is True


# === Testes de fetch (integracao — requer internet) ===

class TestAgentFetch:
    """Testes de integracao que fazem requests reais. Marcados como slow."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_bluesky_fetch_retorna_eventos(self):
        agent = BlueSkyTrendsAgent(max_posts=5)
        events = await agent.fetch()
        # API publica pode retornar vazio se BlueSky estiver instavel
        assert isinstance(events, list)
        for ev in events:
            assert isinstance(ev, TrendEvent)
            assert ev.source == TrendSource.BLUESKY
            assert ev.title
            assert 0.0 <= ev.score <= 1.0
            assert ev.category == "humor"

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_hackernews_fetch_retorna_eventos(self):
        agent = HackerNewsAgent(max_stories=5)
        events = await agent.fetch()
        assert isinstance(events, list)
        for ev in events:
            assert isinstance(ev, TrendEvent)
            assert ev.source == TrendSource.HACKERNEWS
            assert ev.title
            assert 0.0 <= ev.score <= 1.0
            assert ev.category == "tecnologia"
            assert "hn_score" in ev.metadata

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_lemmy_fetch_retorna_eventos(self):
        agent = LemmyCommunitiesAgent(max_posts=5)
        events = await agent.fetch()
        assert isinstance(events, list)
        for ev in events:
            assert isinstance(ev, TrendEvent)
            assert ev.source == TrendSource.LEMMY
            assert ev.title
            assert 0.0 <= ev.score <= 1.0
            assert "instance" in ev.metadata

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_todos_agents_em_paralelo(self):
        """Simula o que o MonitoringLayer faz — fetch paralelo dos 3 agents."""
        agents = [
            BlueSkyTrendsAgent(max_posts=3),
            HackerNewsAgent(max_stories=3),
            LemmyCommunitiesAgent(max_posts=3),
        ]
        results = await asyncio.gather(
            *[a.fetch() for a in agents],
            return_exceptions=True,
        )
        # Nenhum deve lancar excecao (erros tratados internamente)
        for result in results:
            assert not isinstance(result, Exception), f"Agent falhou: {result}"
            assert isinstance(result, list)
