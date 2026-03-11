"""Trend Broker — fila central de eventos com dedup e ranking.

Recebe TrendEvents dos agentes de monitoramento, aplica deduplicacao
e boost multi-fonte reutilizando TrendAggregator existente.
"""

import asyncio
import logging

from config import BROKER_MAX_QUEUE_SIZE
from src.pipeline.models_v2 import (
    TrendEvent,
    trend_item_to_event,
    event_to_trend_item,
)
from src.pipeline.processors.aggregator import TrendAggregator

logger = logging.getLogger("clip-flow.broker")


class TrendBroker:
    """Fila central de eventos de trend com dedup e boosting multi-fonte."""

    def __init__(self, max_queue_size: int = BROKER_MAX_QUEUE_SIZE):
        self.queue: asyncio.Queue[TrendEvent] = asyncio.Queue(maxsize=max_queue_size)
        self._aggregator = TrendAggregator()

    async def ingest(self, events: list[TrendEvent], on_step=None) -> int:
        """Recebe eventos, deduplica via TrendAggregator, enfileira.

        Args:
            on_step: callback(step, status, detail) para progresso granular.

        Retorna quantidade de eventos enfileirados apos dedup.
        """
        if not events:
            return 0

        if on_step:
            on_step("ingest", "running", f"{len(events)} eventos recebidos")

        # Converter para TrendItem para reutilizar logica do aggregator
        trend_items = [event_to_trend_item(e) for e in events]

        if on_step:
            on_step("dedup", "running", "Deduplicando...")
        deduplicated_items = self._aggregator.aggregate(trend_items)
        removed = len(events) - len(deduplicated_items)
        if on_step:
            on_step("dedup", "done", f"{removed} duplicados removidos")

        # Converter de volta para TrendEvent preservando dados extras
        # Criar mapa de scores atualizados pelo aggregator
        event_map = {e.title.lower().strip(): e for e in events}

        if on_step:
            on_step("queue", "running", "Enfileirando...")

        queued = 0
        for item in deduplicated_items:
            key = item.title.lower().strip()
            original_event = event_map.get(key)

            if original_event:
                # Preservar dados extras do evento original, atualizar score
                original_event.score = item.score
                event = original_event
            else:
                event = trend_item_to_event(item)

            try:
                self.queue.put_nowait(event)
                queued += 1
            except asyncio.QueueFull:
                logger.warning(f"Fila cheia ({self.queue.maxsize}), descartando evento: {event.title[:50]}")
                break

        if on_step:
            on_step("ingest", "done", f"{queued} enfileirados")
            on_step("queue", "done", f"{queued} na fila")

        logger.info(f"Broker: {len(events)} recebidos -> {queued} enfileirados (dedup: {len(events) - queued} removidos)")
        return queued

    async def drain(self, max_items: int | None = None) -> list[TrendEvent]:
        """Retira eventos da fila para processamento.

        Args:
            max_items: limite de eventos a retirar. None = todos.
        """
        events = []
        while not self.queue.empty():
            if max_items and len(events) >= max_items:
                break
            events.append(self.queue.get_nowait())
        return events

    @property
    def size(self) -> int:
        """Quantidade de eventos na fila."""
        return self.queue.qsize()
