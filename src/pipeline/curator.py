"""Curator Agent — cerebro decisor do pipeline multi-agente.

Wrapa ClaudeAnalyzer existente e emite WorkOrders com situacao_key
mapeada via KEYWORD_MAP + pool de temas (SITUACOES + themes.yaml).

Garante diversidade visual: quando keyword nao bate, sorteia do pool
completo sem repetir situacoes dentro do mesmo run.
"""

import asyncio
import logging
import random
import uuid

from src.pipeline.models_v2 import (
    TrendEvent,
    WorkOrder,
    event_to_trend_item,
)
from src.pipeline.processors.analyzer import ClaudeAnalyzer
from src.image_gen.prompt_builder import KEYWORD_MAP
from src.image_gen.gemini_client import SITUACOES

logger = logging.getLogger("clip-flow.curator")


def _load_all_situacao_keys() -> list[str]:
    """Carrega todas as situacao_keys disponiveis (built-in + themes.yaml)."""
    keys = list(SITUACOES.keys())

    try:
        import yaml
        from pathlib import Path
        from config import BASE_DIR

        themes_path = BASE_DIR / "config" / "themes.yaml"
        if themes_path.exists():
            data = yaml.safe_load(themes_path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                for theme in data:
                    key = theme.get("key", "")
                    if key and key not in keys:
                        keys.append(key)
    except Exception as e:
        logger.debug(f"Nao carregou themes.yaml: {e}")

    return keys


class CuratorAgent:
    """Agente curador — analisa TrendEvents e emite WorkOrders."""

    def __init__(self, analyzer: ClaudeAnalyzer | None = None):
        self._analyzer = analyzer or ClaudeAnalyzer()
        self._all_keys = _load_all_situacao_keys()

    async def curate(
        self,
        events: list[TrendEvent],
        count: int = 5,
        on_step=None,
        theme_tags: list[str] | None = None,
    ) -> list[WorkOrder]:
        """Analisa TrendEvents via Claude e emite WorkOrders.

        Args:
            events: lista de TrendEvents para analisar
            count: quantidade de temas a selecionar
            on_step: callback(step, status, detail) para progresso granular.
            theme_tags: lista de situacao_keys forcadas pelo usuario.
                Se fornecida, cada work order recebe uma tag da lista (ciclica).
                Se vazia/None, auto-detecta via keyword ou sorteia do pool.

        Returns:
            lista de WorkOrders prontos para a camada de geracao
        """
        if not events:
            logger.warning("Curador recebeu lista vazia de eventos")
            return []

        # Converter para TrendItem para reutilizar ClaudeAnalyzer.analyze()
        trend_items = [event_to_trend_item(e) for e in events]

        if on_step:
            on_step("analyze", "running", f"Gemini analisando {len(trend_items)} trends...")

        logger.info(f"Curador analisando {len(trend_items)} trends, selecionando {count}...")
        analyzed = await asyncio.to_thread(
            self._analyzer.analyze, trend_items, count
        )

        if on_step:
            on_step("analyze", "done", f"{len(analyzed)} temas selecionados")

        # Criar mapa para encontrar TrendEvent original
        event_map = {e.title.lower().strip(): e for e in events}

        if on_step:
            on_step("work_orders", "running", "Criando WorkOrders...")

        # Pool de situacoes disponiveis para sorteio (sem repetir no run)
        used_keys: set[str] = set()
        shuffled_pool = list(self._all_keys)
        random.shuffle(shuffled_pool)

        work_orders = []
        for i, topic in enumerate(analyzed):
            # Encontrar TrendEvent original
            original_title = topic.original_trend.title.lower().strip()
            trend_event = event_map.get(original_title)
            if not trend_event:
                from src.pipeline.models_v2 import trend_item_to_event
                trend_event = trend_item_to_event(topic.original_trend)

            # Decidir situacao visual
            if theme_tags:
                # Usuario forneceu tags — usar ciclicamente
                situacao_key = theme_tags[i % len(theme_tags)]
            else:
                # Auto-detectar via keyword ou sortear do pool
                situacao_key = self._match_situacao_diversa(
                    topic.gandalf_topic, topic.humor_angle,
                    used_keys, shuffled_pool,
                )

            used_keys.add(situacao_key)

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

        if on_step:
            on_step("work_orders", "done", f"{len(work_orders)} orders emitidos")

        logger.info(f"Curador emitiu {len(work_orders)} work orders")
        return work_orders

    def _match_situacao_diversa(
        self,
        topic: str,
        humor_angle: str,
        used_keys: set[str],
        shuffled_pool: list[str],
    ) -> str:
        """Mapeia tema para situacao visual com diversidade garantida.

        1. Tenta KEYWORD_MAP (match semantico direto)
        2. Se ja usada ou nao encontrada, sorteia do pool sem repetir
        """
        combined = f"{topic} {humor_angle}".lower()

        # Tentar match por keyword
        for keyword, situacao_key in KEYWORD_MAP.items():
            if keyword in combined and situacao_key not in used_keys:
                return situacao_key

        # Sortear do pool — pegar proxima nao usada
        for key in shuffled_pool:
            if key not in used_keys:
                return key

        # Pool esgotado — sortear qualquer um
        return random.choice(self._all_keys)
