import logging
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from config import (
    PIPELINE_GOOGLE_TRENDS_GEO,
    PIPELINE_REDDIT_SUBREDDITS,
    PIPELINE_RSS_FEEDS,
    PIPELINE_PHRASES_PER_TOPIC,
)
from src.pipeline.models import PipelineResult
from src.pipeline.agents.google_trends import GoogleTrendsAgent
from src.pipeline.agents.reddit_memes import RedditMemesAgent
from src.pipeline.agents.rss_feeds import RSSFeedAgent
from src.pipeline.processors.aggregator import TrendAggregator
from src.pipeline.processors.analyzer import ClaudeAnalyzer
from src.pipeline.processors.generator import ContentGenerator

logger = logging.getLogger("clip-flow.orchestrator")


class PipelineOrchestrator:
    """Coordena o pipeline completo de geração de conteúdo."""

    def __init__(self, images_per_run: int = 5, phrases_per_topic: int | None = None,
                 use_comfyui: bool | None = None):
        self.images_per_run = images_per_run
        self.phrases_per_topic = phrases_per_topic or PIPELINE_PHRASES_PER_TOPIC

        self.agents = [
            GoogleTrendsAgent(geo=PIPELINE_GOOGLE_TRENDS_GEO),
            RedditMemesAgent(subreddits=PIPELINE_REDDIT_SUBREDDITS),
            RSSFeedAgent(feeds=PIPELINE_RSS_FEEDS),
        ]

        self.aggregator = TrendAggregator(max_topics=20)
        self.analyzer = ClaudeAnalyzer()
        self.generator = ContentGenerator(use_comfyui=use_comfyui)

    def run(self) -> PipelineResult:
        """Executa o pipeline completo."""
        result = PipelineResult(
            trends_fetched=0,
            topics_analyzed=0,
            images_generated=0,
        )

        logger.info("=" * 60)
        logger.info("Pipeline iniciado")
        logger.info("=" * 60)

        # Passo 1: Buscar trends de todas as fontes
        all_trends = []
        for agent in self.agents:
            if not agent.is_available():
                logger.warning(f"Agent '{agent.name}' não disponível, pulando")
                continue
            logger.info(f"Buscando de {agent.name}...")
            try:
                trends = agent.fetch()
                all_trends.extend(trends)
            except Exception as e:
                error_msg = f"Agent '{agent.name}' falhou: {e}"
                logger.error(error_msg)
                result.errors.append(error_msg)

        result.trends_fetched = len(all_trends)
        logger.info(f"Total de trends coletados: {result.trends_fetched}")

        if not all_trends:
            logger.error("Nenhum trend coletado de nenhuma fonte. Abortando.")
            result.errors.append("Nenhum trend disponível")
            return result

        # Passo 2: Agregar e deduplicar
        logger.info("Agregando e rankeando trends...")
        ranked_trends = self.aggregator.aggregate(all_trends)
        logger.info(f"Após agregação: {len(ranked_trends)} trends únicos")

        # Passo 3: Claude analisa e seleciona melhores temas
        topics_count = min(self.images_per_run, len(ranked_trends))
        logger.info(f"Pedindo ao Claude para selecionar {topics_count} temas...")
        try:
            analyzed_topics = self.analyzer.analyze(ranked_trends, count=topics_count)
            result.topics_analyzed = len(analyzed_topics)
        except Exception as e:
            error_msg = f"Análise do Claude falhou: {e}"
            logger.error(error_msg)
            result.errors.append(error_msg)
            return result

        logger.info(f"Claude selecionou {len(analyzed_topics)} temas")
        for topic in analyzed_topics:
            logger.info(f"  - {topic.gandalf_topic} ({topic.humor_angle})")

        # Passo 4: Gerar conteúdo para cada tema
        logger.info("Gerando conteúdo...")
        for topic in analyzed_topics:
            logger.info(f"  Tema: {topic.gandalf_topic}")
            try:
                contents = self.generator.generate(topic, self.phrases_per_topic)
                result.content.extend(contents)
                result.images_generated += len(contents)
            except Exception as e:
                error_msg = f"Geração falhou para '{topic.gandalf_topic}': {e}"
                logger.error(error_msg)
                result.errors.append(error_msg)

        result.finished_at = datetime.now()
        duration = (result.finished_at - result.started_at).total_seconds()

        logger.info("=" * 60)
        logger.info(f"Pipeline completo em {duration:.1f}s")
        logger.info(f"  Trends coletados:    {result.trends_fetched}")
        logger.info(f"  Temas analisados:    {result.topics_analyzed}")
        logger.info(f"  Imagens geradas:     {result.images_generated}")
        if result.errors:
            logger.warning(f"  Erros: {len(result.errors)}")
        logger.info("=" * 60)

        return result
