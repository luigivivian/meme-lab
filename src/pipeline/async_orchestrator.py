"""Orquestrador multi-agente event-driven.

Coordena as 5 camadas em sequencia, com execucao paralela dentro de cada camada:
L1 Monitoring -> L2 Broker -> L3 Curator -> L4 Generation -> L5 Post-Production
"""

import logging
from datetime import datetime

from config import (
    PIPELINE_GOOGLE_TRENDS_GEO,
    PIPELINE_REDDIT_SUBREDDITS,
    PIPELINE_RSS_FEEDS,
    PIPELINE_PHRASES_PER_TOPIC,
)
from src.pipeline.agents.async_base import SyncAgentAdapter
from src.pipeline.agents.google_trends import GoogleTrendsAgent
from src.pipeline.agents.reddit_memes import RedditMemesAgent
from src.pipeline.agents.rss_feeds import RSSFeedAgent
from src.pipeline.monitoring import MonitoringLayer
from src.pipeline.broker import TrendBroker
from src.pipeline.curator import CuratorAgent
from src.pipeline.workers.phrase_worker import PhraseWorker
from src.pipeline.workers.image_worker import ImageWorker
from src.pipeline.workers.generation_layer import GenerationLayer
from src.pipeline.workers.post_production import PostProductionLayer
from src.pipeline.models_v2 import AgentPipelineResult

logger = logging.getLogger("clip-flow.async_orchestrator")


class AsyncPipelineOrchestrator:
    """Orquestrador multi-agente event-driven."""

    def __init__(
        self,
        images_per_run: int = 5,
        phrases_per_topic: int | None = None,
        use_comfyui: bool | None = None,
    ):
        self.images_per_run = images_per_run
        self.phrases_per_topic = phrases_per_topic or PIPELINE_PHRASES_PER_TOPIC

        # Layer 1: Monitoring — wrapa agentes sync existentes
        sync_agents = [
            GoogleTrendsAgent(geo=PIPELINE_GOOGLE_TRENDS_GEO),
            RedditMemesAgent(subreddits=PIPELINE_REDDIT_SUBREDDITS),
            RSSFeedAgent(feeds=PIPELINE_RSS_FEEDS),
        ]
        async_agents = [SyncAgentAdapter(a) for a in sync_agents]

        # Adicionar stub agents disponiveis
        async_agents.extend(self._load_stub_agents())

        self.monitoring = MonitoringLayer(async_agents)

        # Layer 2: Broker
        self.broker = TrendBroker()

        # Layer 3: Curator
        self.curator = CuratorAgent()

        # Layer 4: Generation
        use_comfyui_flag = use_comfyui if use_comfyui is not None else False
        self.generation = GenerationLayer(
            phrase_worker=PhraseWorker(),
            image_worker=ImageWorker(use_comfyui=use_comfyui_flag),
            phrases_per_topic=self.phrases_per_topic,
        )

        # Layer 5: Post-production
        self.post_production = PostProductionLayer()

    def _load_stub_agents(self):
        """Carrega stub agents que estejam disponiveis (API key configurada)."""
        stubs = []
        try:
            from src.pipeline.agents.tiktok_trends import TikTokTrendsAgent
            stubs.append(TikTokTrendsAgent())
        except ImportError:
            pass
        try:
            from src.pipeline.agents.instagram_explore import InstagramExploreAgent
            stubs.append(InstagramExploreAgent())
        except ImportError:
            pass
        try:
            from src.pipeline.agents.twitter_x import TwitterXAgent
            stubs.append(TwitterXAgent())
        except ImportError:
            pass
        try:
            from src.pipeline.agents.facebook_viral import FacebookViralAgent
            stubs.append(FacebookViralAgent())
        except ImportError:
            pass
        try:
            from src.pipeline.agents.youtube_shorts import YouTubeShortsAgent
            stubs.append(YouTubeShortsAgent())
        except ImportError:
            pass
        return stubs

    async def run(self) -> AgentPipelineResult:
        """Executa o pipeline multi-agente completo."""
        result = AgentPipelineResult()

        logger.info("=" * 60)
        logger.info("Pipeline multi-agente iniciado")
        logger.info("=" * 60)

        # Layer 1: Monitoramento — busca trends em paralelo
        logger.info("[Layer 1] Monitoramento — buscando trends em paralelo...")
        events = await self.monitoring.fetch_all()
        result.trends_fetched = len(events)

        if not events:
            error = "Nenhum trend coletado de nenhuma fonte"
            logger.error(error)
            result.errors.append(error)
            result.finished_at = datetime.now()
            return result

        # Layer 2: Broker — dedup e ranking
        logger.info("[Layer 2] Broker — deduplicando e rankeando...")
        queued = await self.broker.ingest(events)
        result.trend_events_queued = queued

        # Layer 3: Curador — seleciona melhores temas
        logger.info("[Layer 3] Curador — selecionando temas...")
        trend_events = await self.broker.drain(max_items=20)
        topics_count = min(self.images_per_run, len(trend_events))

        try:
            work_orders = await self.curator.curate(trend_events, count=topics_count)
            result.work_orders_emitted = len(work_orders)
        except Exception as e:
            error = f"Curador falhou: {e}"
            logger.error(error)
            result.errors.append(error)
            result.finished_at = datetime.now()
            return result

        if not work_orders:
            error = "Curador nao emitiu nenhum work order"
            logger.error(error)
            result.errors.append(error)
            result.finished_at = datetime.now()
            return result

        # Layer 4: Geracao — frases + imagens em paralelo
        logger.info("[Layer 4] Geracao — frases + imagens em paralelo...")
        packages = await self.generation.process(work_orders)
        result.images_generated = len(packages)

        if not packages:
            error = "Nenhum conteudo gerado"
            logger.error(error)
            result.errors.append(error)
            result.finished_at = datetime.now()
            return result

        # Layer 5: Pos-producao — caption + hashtags + quality em paralelo
        logger.info("[Layer 5] Pos-producao — enriquecendo pacotes...")
        packages = await self.post_production.enhance(packages)
        result.content = packages
        result.packages_produced = len(packages)

        # Resumo
        result.finished_at = datetime.now()
        duration = (result.finished_at - result.started_at).total_seconds()

        logger.info("=" * 60)
        logger.info(f"Pipeline multi-agente completo em {duration:.1f}s")
        logger.info(f"  Trends coletados:    {result.trends_fetched}")
        logger.info(f"  Eventos enfileirados:{result.trend_events_queued}")
        logger.info(f"  Work orders:         {result.work_orders_emitted}")
        logger.info(f"  Imagens geradas:     {result.images_generated}")
        logger.info(f"  Pacotes produzidos:  {result.packages_produced}")
        if result.errors:
            logger.warning(f"  Erros: {len(result.errors)}")
        logger.info("=" * 60)

        return result
