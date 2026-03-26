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
from config import LAYOUT_TEMPLATES, LAYOUT_RANDOM
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
        logger.info(f"Curador inicializado: {len(self._all_keys)} situacao_keys disponiveis")

    async def curate(
        self,
        events: list[TrendEvent],
        count: int = 5,
        on_step=None,
        theme_tags: list[str] | None = None,
        exclude_topics: list[str] | None = None,
        carousel_count: int = 1,
    ) -> list[WorkOrder]:
        """Analisa TrendEvents via Claude e emite WorkOrders.

        Args:
            events: lista de TrendEvents para analisar
            count: quantidade de temas a selecionar
            on_step: callback(step, status, detail) para progresso granular.
            theme_tags: lista de situacao_keys forcadas pelo usuario.
                Se fornecida, cada work order recebe uma tag da lista (ciclica).
                Se vazia/None, auto-detecta via keyword ou sorteia do pool.
            exclude_topics: temas recentes a excluir (dedup cross-run).
            carousel_count: slides por carousel (1=imagem unica).

        Returns:
            lista de WorkOrders prontos para a camada de geracao
        """
        if not events:
            logger.warning("Curador recebeu lista vazia de eventos")
            return []

        # Dedup cross-run: remover eventos cujo titulo ja foi usado recentemente
        if exclude_topics:
            original_count = len(events)
            excluded_set = {t.lower().strip() for t in exclude_topics}
            events = [
                e for e in events
                if e.title.lower().strip() not in excluded_set
            ]
            excluded = original_count - len(events)
            if excluded > 0:
                logger.info(f"Dedup cross-run: {excluded} topics excluidos de {original_count}")

        if not events:
            logger.warning("Todos os eventos foram excluidos pelo dedup cross-run")
            return []

        # Converter para TrendItem para reutilizar ClaudeAnalyzer.analyze()
        trend_items = [event_to_trend_item(e) for e in events]

        if on_step:
            on_step("analyze", "running", f"LLM analisando {len(trend_items)} trends...")

        logger.info(f"Curador enviando {len(trend_items)} trends para analise (selecionando {count})...")
        analyzed = await asyncio.to_thread(
            self._analyzer.analyze, trend_items, count
        )
        logger.info(f"Curador recebeu {len(analyzed)} temas do analyzer")

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

        # Pool de layouts para diversidade visual
        layout_pool = list(LAYOUT_TEMPLATES.keys())
        random.shuffle(layout_pool)

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

            # Layout visual: aleatorio com diversidade ou padrao
            if LAYOUT_RANDOM:
                layout = layout_pool[i % len(layout_pool)]
            else:
                layout = "bottom"

            order = WorkOrder(
                order_id=uuid.uuid4().hex[:8],
                trend_event=trend_event,
                gandalf_topic=topic.gandalf_topic,
                humor_angle=topic.humor_angle,
                situacao_key=situacao_key,
                relevance_score=topic.relevance_score,
                layout=layout,
                carousel_count=carousel_count,
            )
            work_orders.append(order)
            logger.info(
                f"  WorkOrder [{order.order_id}]: "
                f"{order.gandalf_topic} -> situacao={order.situacao_key}, layout={layout}"
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
                logger.debug(f"  Situacao match: keyword='{keyword}' -> {situacao_key}")
                return situacao_key

        # Sortear do pool — pegar proxima nao usada
        for key in shuffled_pool:
            if key not in used_keys:
                logger.debug(f"  Situacao sorteada (sem keyword match): {key}")
                return key

        # Pool esgotado — sortear qualquer um
        key = random.choice(self._all_keys)
        logger.debug(f"  Situacao random (pool esgotado): {key}")
        return key
