"""Curator Agent — cerebro decisor do pipeline multi-agente.

Wrapa ClaudeAnalyzer existente e emite WorkOrders com situacao_key
mapeada via KEYWORD_MAP do prompt_builder.
"""

import asyncio
import logging
import uuid

from src.pipeline.models_v2 import (
    TrendEvent,
    WorkOrder,
    event_to_trend_item,
)
from src.pipeline.processors.analyzer import ClaudeAnalyzer
from src.image_gen.prompt_builder import KEYWORD_MAP

logger = logging.getLogger("clip-flow.curator")


class CuratorAgent:
    """Agente curador — analisa TrendEvents e emite WorkOrders."""

    def __init__(self, analyzer: ClaudeAnalyzer | None = None):
        self._analyzer = analyzer or ClaudeAnalyzer()

    async def curate(self, events: list[TrendEvent], count: int = 5) -> list[WorkOrder]:
        """Analisa TrendEvents via Claude e emite WorkOrders.

        Args:
            events: lista de TrendEvents para analisar
            count: quantidade de temas a selecionar

        Returns:
            lista de WorkOrders prontos para a camada de geracao
        """
        if not events:
            logger.warning("Curador recebeu lista vazia de eventos")
            return []

        # Converter para TrendItem para reutilizar ClaudeAnalyzer.analyze()
        trend_items = [event_to_trend_item(e) for e in events]

        logger.info(f"Curador analisando {len(trend_items)} trends, selecionando {count}...")
        analyzed = await asyncio.to_thread(
            self._analyzer.analyze, trend_items, count
        )

        # Criar mapa para encontrar TrendEvent original
        event_map = {e.title.lower().strip(): e for e in events}

        work_orders = []
        for topic in analyzed:
            # Encontrar TrendEvent original
            original_title = topic.original_trend.title.lower().strip()
            trend_event = event_map.get(original_title)
            if not trend_event:
                # Fallback: criar TrendEvent a partir do TrendItem
                from src.pipeline.models_v2 import trend_item_to_event
                trend_event = trend_item_to_event(topic.original_trend)

            # Mapear tema para situacao visual
            situacao_key = self._match_situacao(
                topic.gandalf_topic, topic.humor_angle
            )

            order = WorkOrder(
                order_id=uuid.uuid4().hex[:8],
                trend_event=trend_event,
                gandalf_topic=topic.gandalf_topic,
                humor_angle=topic.humor_angle,
                situacao_key=situacao_key,
                relevance_score=topic.relevance_score,
            )
            work_orders.append(order)
            logger.info(
                f"  WorkOrder [{order.order_id}]: "
                f"{order.gandalf_topic} -> situacao={order.situacao_key}"
            )

        logger.info(f"Curador emitiu {len(work_orders)} work orders")
        return work_orders

    def _match_situacao(self, topic: str, humor_angle: str) -> str:
        """Mapeia tema + humor_angle para uma situacao_key das SCENE_TEMPLATES.

        Reutiliza KEYWORD_MAP de prompt_builder.py.
        """
        combined = f"{topic} {humor_angle}".lower()
        for keyword, situacao_key in KEYWORD_MAP.items():
            if keyword in combined:
                return situacao_key
        return "generico"
