"""Curator Agent — cerebro decisor do pipeline multi-agente.

Wrapa ClaudeAnalyzer existente e emite WorkOrders com situacao_key
mapeada via LLM (Gemini flash-lite) com KEYWORD_MAP como fallback.

Per D-12: LLM-based theme mapping replaces rigid keyword matching.
Per D-13: Increased throughput (default 15 WorkOrders).
Per D-14: Relevance filter via meme_potential scoring in analyzer.

Garante diversidade visual: quando LLM/keyword nao bate, sorteia do pool
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
from src.llm_client import generate

logger = logging.getLogger("clip-flow.curator")

# In-memory cache for LLM theme mappings (topic|humor_angle -> situacao_key)
_theme_cache: dict[str, str] = {}

# Theme descriptions for LLM context — maps each situacao_key to a visual scene description
_THEME_DESCRIPTIONS = {
    "sabedoria": "wise contemplation, reading ancient books, giving advice",
    "confusao": "bewildered, confused, scratching head, question marks",
    "segunda_feira": "tired monday morning, sleepy with coffee, dark circles",
    "vitoria": "triumphant celebration, staff raised high, golden particles",
    "tecnologia": "holding smartphone/device, digital runes, blue glow",
    "cafe": "holding coffee mug, content expression, golden steam",
    "comida": "cooking cauldron, floating ingredients, hungry expression",
    "trabalho": "at desk with laptop, focused/stressed, office setting",
    "relaxando": "sleeping in chair, hat over eyes, peaceful",
    "meditando": "cross-legged meditation, serene aura, ethereal glow",
    "relacionamento": "holding heart crystal, romantic mood, love sparkles",
    "confronto": "stern expression, staff with energy, dramatic wind",
    "surpresa": "wide eyes, shocked expression, hands raised, exclamation",
    "cotidiano": "relaxed casual pose, holding ale mug, warm smile",
    "descanso": "peaceful sleeping, chair, floating particles, blissful",
    "internet": "looking at crystal ball like screen, amused, blue glow",
    "generico": "standing with staff, wise serious expression, neutral",
}

_THEME_MAPPING_PROMPT = """You are a visual theme selector for a Brazilian meme generator featuring "O Mago Mestre" (a wise old wizard).
Given a trending topic and humor angle, select the single best visual theme from this list:

{theme_list}

Rules:
- Return ONLY the theme key (e.g., "cafe"), nothing else
- Match the topic's mood and context to the theme's visual scene
- "segunda_feira" = tired/monday/exhaustion vibes
- "tecnologia" = tech, apps, wifi, digital stuff
- "relacionamento" = love, crush, dating, ex
- "trabalho" = work, boss, office, employment
- "cafe" = coffee, morning energy, caffeine
- When in doubt, prefer "cotidiano" or "generico" over a bad match
"""


def _llm_map_theme(topic: str, humor_angle: str, all_keys: list[str]) -> str | None:
    """Map a topic to the best situacao_key via LLM. Returns None on failure.

    Per D-12: Uses Gemini flash-lite for cheap theme mapping (~$0.001/call).
    Results are cached in-memory per topic+humor_angle pair.
    """
    cache_key = f"{topic}|{humor_angle}".lower().strip()
    if cache_key in _theme_cache:
        logger.debug(f"  Theme cache hit: '{topic}' -> {_theme_cache[cache_key]}")
        return _theme_cache[cache_key]

    theme_list = "\n".join(
        f"- {key}: {_THEME_DESCRIPTIONS.get(key, key)}"
        for key in all_keys
    )

    try:
        result = generate(
            system_prompt=_THEME_MAPPING_PROMPT.format(theme_list=theme_list),
            user_message=f"Topic: {topic}\nHumor angle: {humor_angle}\n\nBest theme key:",
            max_tokens=20,
            tier="lite",
        ).strip().lower().replace('"', '').replace("'", "")

        # Validate result is a known key
        if result in all_keys:
            _theme_cache[cache_key] = result
            logger.debug(f"  LLM theme mapping: '{topic}' -> {result}")
            return result
        else:
            logger.warning(f"LLM returned unknown theme '{result}' for '{topic}', falling back")
            return None
    except Exception as e:
        logger.warning(f"LLM theme mapping failed for '{topic}': {e}")
        return None


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
        count: int = 15,
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

        Per D-12: LLM-based mapping first, KEYWORD_MAP as fallback, random as last resort.

        1. Tenta LLM mapping via Gemini flash-lite (cached)
        2. Fallback: KEYWORD_MAP (match semantico direto, for offline/error resilience)
        3. Last resort: sorteia do pool sem repetir
        """
        # Try LLM mapping first (per D-12)
        llm_key = _llm_map_theme(topic, humor_angle, self._all_keys)
        if llm_key and llm_key not in used_keys:
            logger.debug(f"  Situacao via LLM: '{topic}' -> {llm_key}")
            return llm_key

        # Fallback: keyword match (kept for offline/error resilience)
        combined = f"{topic} {humor_angle}".lower()
        for keyword, situacao_key in KEYWORD_MAP.items():
            if keyword in combined and situacao_key not in used_keys:
                logger.debug(f"  Situacao via keyword fallback: '{keyword}' -> {situacao_key}")
                return situacao_key

        # Last resort: random from pool
        for key in shuffled_pool:
            if key not in used_keys:
                logger.debug(f"  Situacao random (no LLM/keyword match): {key}")
                return key

        key = random.choice(self._all_keys)
        logger.debug(f"  Situacao random (pool exhausted): {key}")
        return key
