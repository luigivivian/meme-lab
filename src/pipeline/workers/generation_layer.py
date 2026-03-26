"""GenerationLayer — processa WorkOrders em paralelo.

Coordena PhraseWorker e ImageWorker para gerar ContentPackages.
Suporta A/B testing de frases, carousel mode, e topic-image coherence check.
"""

import asyncio
import logging
import time

from config import PHRASE_AB_ENABLED
from src.pipeline.models_v2 import WorkOrder, ContentPackage
from src.pipeline.workers.phrase_worker import PhraseWorker
from src.pipeline.workers.image_worker import ImageWorker
from src.llm_client import generate as llm_generate

logger = logging.getLogger("clip-flow.generation")


# ---------------------------------------------------------------------------
# Topic-image coherence check (D-16)
# ---------------------------------------------------------------------------

# Known good topic-theme matches — skip LLM for these
_OBVIOUS_MATCHES: dict[str, list[str]] = {
    "cafe": ["cafe", "coffee", "cafeina", "cappuccino", "espresso"],
    "trabalho": ["trabalho", "emprego", "chefe", "escritorio", "home office", "reuniao"],
    "segunda_feira": ["segunda", "monday", "começo de semana", "segunda-feira"],
    "tecnologia": ["wifi", "internet", "celular", "app", "rede social", "algoritmo"],
    "comida": ["comida", "cozinha", "fome", "almoco", "jantar", "miojo", "lanche"],
    "relacionamento": ["namoro", "crush", "ex", "casal", "amor", "namorada", "namorado"],
    "relaxando": ["relaxar", "descanso", "tranquilo", "paz", "preguica", "folga"],
    "meditando": ["meditar", "zen", "calma", "equilibrio", "universo"],
    "sabedoria": ["sabedoria", "sabio", "conselho", "verdade", "filosofia"],
    "confusao": ["confusao", "caos", "bagunca", "desespero", "panico"],
    "vitoria": ["vitoria", "sucesso", "conquista", "ganhar", "campeao"],
    "surpresa": ["surpresa", "choque", "inacreditavel", "nao acredito"],
    "confronto": ["confronto", "briga", "discussao", "treta", "debate"],
}


def _check_coherence(topic: str, humor_angle: str, situacao_key: str) -> bool:
    """Check if the visual theme matches the phrase topic.

    Uses a quick LLM check: 'Does {situacao_key} theme make sense for {topic}?'
    Returns True if coherent, False if mismatch detected.
    """
    combined = f"{topic} {humor_angle}".lower()

    # Check obvious matches first (skip LLM call)
    if situacao_key in _OBVIOUS_MATCHES:
        for kw in _OBVIOUS_MATCHES[situacao_key]:
            if kw in combined:
                return True  # Obvious match, skip LLM

    # For non-obvious cases, use LLM quick check
    try:
        result = llm_generate(
            system_prompt="Answer only YES or NO.",
            user_message=(
                f"Does the visual theme '{situacao_key}' make sense for a meme about: '{topic}'?\n"
                f"Humor angle: '{humor_angle}'\n"
                f"Answer YES if the theme fits the topic, NO if there's a disconnect."
            ),
            max_tokens=5,
            tier="lite",
        ).strip().upper()
        return result.startswith("YES") or result.startswith("SIM")
    except Exception as e:
        logger.debug(f"Coherence LLM check failed: {e}, assuming coherent")
        return True  # On error, assume coherent (don't block generation)


def _remap_theme(topic: str, humor_angle: str, all_keys: list[str]) -> str | None:
    """Use LLM to find a better theme for a topic when coherence fails.

    Returns a new situacao_key or None if remap fails.
    """
    try:
        keys_str = ", ".join(all_keys)
        result = llm_generate(
            system_prompt=(
                "You are a visual theme selector for Brazilian meme images. "
                "Given a topic and available themes, pick the SINGLE best theme. "
                "Reply with ONLY the theme key, nothing else."
            ),
            user_message=(
                f"Topic: {topic}\nHumor angle: {humor_angle}\n"
                f"Available themes: {keys_str}\n"
                f"Best theme key:"
            ),
            max_tokens=20,
            tier="lite",
        ).strip().lower().replace('"', '').replace("'", '')

        # Validate the result is actually one of the available keys
        if result in all_keys:
            return result

        # Try partial match
        for key in all_keys:
            if key in result:
                return key

        return None
    except Exception as e:
        logger.debug(f"Theme remap LLM failed: {e}")
        return None


class GenerationLayer:
    """Processa WorkOrders em paralelo — frases + imagens."""

    def __init__(
        self,
        phrase_worker: PhraseWorker | None = None,
        image_worker: ImageWorker | None = None,
        phrases_per_topic: int = 1,
        cost_mode: str = "normal",
    ):
        self.phrase_worker = phrase_worker or PhraseWorker()
        self.image_worker = image_worker or ImageWorker()
        self.phrases_per_topic = phrases_per_topic
        self._cost_mode = cost_mode

    async def process(
        self, work_orders: list[WorkOrder], on_step=None,
        user_id: int | None = None, session: "AsyncSession | None" = None,
    ) -> list[ContentPackage]:
        """Processa todos os WorkOrders em paralelo."""
        if not work_orders:
            return []

        total = len(work_orders)
        phrases_done = 0
        images_done = 0

        ab_enabled = PHRASE_AB_ENABLED and self._cost_mode == "normal"
        logger.info(
            f"Geracao iniciada: {total} work orders, "
            f"A/B={'ON' if ab_enabled else 'OFF'}, "
            f"cost_mode={self._cost_mode}, "
            f"phrases/topic={self.phrases_per_topic}"
        )

        if on_step:
            on_step("phrases", "running", f"0/{total}")
            on_step("images", "idle", "Aguardando frases...")

        async def process_one_tracked(wo: WorkOrder) -> list[ContentPackage]:
            nonlocal phrases_done, images_done
            wo_t0 = time.perf_counter()

            count = wo.phrases_count or self.phrases_per_topic
            phrase_alternatives = []

            # Gerar frases
            phrase_t0 = time.perf_counter()
            if ab_enabled:
                phrases, phrase_alternatives = await self.phrase_worker.generate_with_scoring(wo, count)
            else:
                phrases = await self.phrase_worker.generate(wo, count)
            phrase_elapsed = time.perf_counter() - phrase_t0

            phrases_done += 1
            if on_step:
                s = "done" if phrases_done >= total else "running"
                on_step("phrases", s, f"{phrases_done}/{total}")

            if not phrases:
                logger.warning(f"[{wo.order_id}] Nenhuma frase gerada em {phrase_elapsed:.1f}s, pulando")
                return []

            logger.info(
                f"[{wo.order_id}] {len(phrases)} frase(s) em {phrase_elapsed:.1f}s "
                f"(A/B: {len(phrase_alternatives)} alts)"
            )

            # Per D-16: Topic-image coherence check before image generation
            if not await asyncio.to_thread(
                _check_coherence, wo.gandalf_topic, wo.humor_angle, wo.situacao_key
            ):
                logger.info(
                    f"[{wo.order_id}] Coherence mismatch: "
                    f"'{wo.gandalf_topic}' vs theme '{wo.situacao_key}', remapping..."
                )
                try:
                    from src.pipeline.curator import _load_all_situacao_keys
                    all_keys = _load_all_situacao_keys()
                    new_key = await asyncio.to_thread(
                        _remap_theme, wo.gandalf_topic, wo.humor_angle, all_keys
                    )
                    if new_key and new_key != wo.situacao_key:
                        logger.info(f"[{wo.order_id}] Remapped: {wo.situacao_key} -> {new_key}")
                        wo.situacao_key = new_key
                except Exception as e:
                    logger.warning(f"[{wo.order_id}] Remap failed: {e}, keeping original theme")

            if on_step and images_done == 0:
                on_step("images", "running", f"0/{total}")

            pkgs = []
            carousel_count = getattr(wo, "carousel_count", 1) or 1

            for phrase in phrases:
                try:
                    img_t0 = time.perf_counter()
                    if carousel_count > 1:
                        # Carousel mode
                        carousel_phrases = [phrase]
                        if PHRASE_AB_ENABLED and len(phrase_alternatives) > 1:
                            for alt in phrase_alternatives[1:carousel_count]:
                                carousel_phrases.append(alt.get("frase", phrase))
                        else:
                            extra = await self.phrase_worker.generate(wo, carousel_count - 1)
                            carousel_phrases.extend(extra)

                        slides = []
                        for si, slide_phrase in enumerate(carousel_phrases[:carousel_count]):
                            slide_result = await self.image_worker.compose(slide_phrase, wo, user_id=user_id, session=session)
                            slides.append(slide_result.image_path)

                        first_result = slides[0] if slides else ""
                        compose_result = await self.image_worker.compose(phrase, wo, user_id=user_id, session=session)
                        img_elapsed = time.perf_counter() - img_t0
                        logger.info(
                            f"[{wo.order_id}] Carousel: {len(slides)} slides em {img_elapsed:.1f}s "
                            f"bg_src={compose_result.background_source}"
                        )

                        pkgs.append(ContentPackage(
                            phrase=phrase,
                            image_path=compose_result.image_path,
                            topic=wo.gandalf_topic,
                            source=wo.trend_event.source,
                            work_order=wo,
                            background_path=compose_result.background_path,
                            background_source=compose_result.background_source,
                            image_metadata=compose_result.image_metadata,
                            phrase_alternatives=phrase_alternatives,
                            carousel_slides=slides,
                        ))
                    else:
                        # Modo imagem unica (padrao)
                        compose_result = await self.image_worker.compose(phrase, wo, user_id=user_id, session=session)
                        img_elapsed = time.perf_counter() - img_t0
                        logger.info(
                            f"[{wo.order_id}] Imagem composta em {img_elapsed:.1f}s "
                            f"bg_src={compose_result.background_source} "
                            f"layout={compose_result.image_metadata.get('layout', '?')}"
                        )
                        pkgs.append(ContentPackage(
                            phrase=phrase,
                            image_path=compose_result.image_path,
                            topic=wo.gandalf_topic,
                            source=wo.trend_event.source,
                            work_order=wo,
                            background_path=compose_result.background_path,
                            background_source=compose_result.background_source,
                            image_metadata=compose_result.image_metadata,
                            phrase_alternatives=phrase_alternatives,
                        ))
                except Exception as e:
                    logger.error(
                        f"[{wo.order_id}] Falha na composicao de '{phrase[:30]}...': "
                        f"{type(e).__name__}: {e}"
                    )

            images_done += 1
            wo_elapsed = time.perf_counter() - wo_t0
            logger.info(f"[{wo.order_id}] WorkOrder completo em {wo_elapsed:.1f}s ({len(pkgs)} pkg)")
            if on_step:
                s = "done" if images_done >= total else "running"
                on_step("images", s, f"{images_done}/{total}")

            return pkgs

        results = await asyncio.gather(
            *[process_one_tracked(wo) for wo in work_orders],
            return_exceptions=True,
        )

        packages = []
        errors = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                errors += 1
                logger.error(
                    f"WorkOrder [{work_orders[i].order_id}] excecao: "
                    f"{type(result).__name__}: {result}"
                )
            elif isinstance(result, list):
                packages.extend(result)

        logger.info(f"Geracao concluida: {len(packages)} pacotes, {errors} erros de {total} work orders")
        return packages
