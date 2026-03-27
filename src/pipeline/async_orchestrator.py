"""Orquestrador multi-agente event-driven.

Coordena as 5 camadas em sequencia, com execucao paralela dentro de cada camada:
L1 Monitoring -> L2 Broker -> L3 Curator -> L4 Generation -> L5 Post-Production
"""

import logging
import time
import traceback
from datetime import datetime

from config import (
    PIPELINE_GOOGLE_TRENDS_GEO,
    PIPELINE_PHRASES_PER_TOPIC,
)
from src.pipeline.agents.async_base import SyncAgentAdapter
from src.pipeline.agents.google_trends import GoogleTrendsAgent
from src.pipeline.agents.reddit_memes import RedditMemesAgent
from src.pipeline.agents.rss_feeds import RSSFeedAgent
from src.pipeline.agents.youtube_rss import YouTubeRSSAgent
from src.pipeline.agents.gemini_web_trends import GeminiWebTrendsAgent
from src.pipeline.agents.brazil_viral_rss import BrazilViralRSSAgent
from src.pipeline.agents.bluesky_trends import BlueSkyTrendsAgent
from src.pipeline.monitoring import MonitoringLayer
from src.pipeline.broker import TrendBroker
from src.pipeline.curator import CuratorAgent
from src.pipeline.workers.phrase_worker import PhraseWorker
from src.pipeline.workers.image_worker import ImageWorker
from src.pipeline.workers.generation_layer import GenerationLayer
from src.pipeline.workers.post_production import PostProductionLayer
from src.pipeline.models_v2 import AgentPipelineResult, TrendEvent, TrendSource, WorkOrder

logger = logging.getLogger("clip-flow.async_orchestrator")


class AsyncPipelineOrchestrator:
    """Orquestrador multi-agente event-driven."""

    def __init__(
        self,
        images_per_run: int = 5,
        phrases_per_topic: int | None = None,
        use_comfyui: bool | None = None,
        use_gemini_image: bool | None = None,
        use_phrase_context: bool = False,
        on_layer_update=None,
        theme_tags: list[str] | None = None,
        character_system_prompt: str | None = None,
        character_max_chars: int | None = None,
        character_reference_dir: str | None = None,
        character_dna: str | None = None,
        character_negative_traits: str | None = None,
        character_composition: str | None = None,
        character_rendering: dict | None = None,
        character_refs_priority: list[str] | None = None,
        # Branding do personagem
        character_watermark: str | None = None,
        character_name: str | None = None,
        character_handle: str | None = None,
        character_branded_hashtags: list[str] | None = None,
        character_caption_prompt: str | None = None,
        # Quick Wins
        exclude_topics: list[str] | None = None,
        carousel_count: int = 1,
        # Custo
        cost_mode: str = "normal",
        # Background mode: "auto" | "comfyui" | "gemini" | "static"
        background_mode: str = "auto",
        # Temas manuais — pula L1/L2/L3
        manual_topics: list[dict] | None = None,
        # Slug do personagem para auto-save de backgrounds gerados
        character_slug: str | None = None,
    ):
        self.images_per_run = images_per_run
        self.phrases_per_topic = phrases_per_topic or PIPELINE_PHRASES_PER_TOPIC
        self._on_layer_update = on_layer_update
        self._theme_tags = theme_tags
        self._exclude_topics = exclude_topics
        self._carousel_count = carousel_count
        self._cost_mode = cost_mode
        self._background_mode = background_mode
        self._manual_topics = manual_topics
        self._character_slug = character_slug

        # Layer 1: Monitoring — wrapa agentes sync existentes
        sync_agents = [
            GoogleTrendsAgent(geo=PIPELINE_GOOGLE_TRENDS_GEO),
            RedditMemesAgent(),
            RSSFeedAgent(),
        ]
        async_agents = [SyncAgentAdapter(a) for a in sync_agents]

        # Agents async nativos — sem API key adicional
        async_agents_list = [
            YouTubeRSSAgent(),
            BrazilViralRSSAgent(),
            BlueSkyTrendsAgent(),
        ]

        # Ultra-eco: pula GeminiWebTrends (usa Gemini API, custa dinheiro)
        if cost_mode != "ultra-eco":
            async_agents_list.append(GeminiWebTrendsAgent())
            logger.debug("GeminiWebTrendsAgent ativado")
        else:
            logger.info("Ultra-eco: GeminiWebTrendsAgent desativado para economizar")

        async_agents += async_agents_list

        # Adicionar stub agents disponiveis (requerem API keys externas)
        async_agents.extend(self._load_stub_agents())

        self.monitoring = MonitoringLayer(async_agents)

        # Layer 2: Broker
        self.broker = TrendBroker()

        # Layer 3: Curator
        self.curator = CuratorAgent()

        # Layer 4: Generation — com suporte a personagem customizado
        use_comfyui_flag = use_comfyui if use_comfyui is not None else False
        self.generation = GenerationLayer(
            phrase_worker=PhraseWorker(
                system_prompt=character_system_prompt,
                max_chars=character_max_chars,
            ),
            image_worker=ImageWorker(
                use_comfyui=use_comfyui_flag,
                use_gemini_image=use_gemini_image,
                use_phrase_context=use_phrase_context,
                reference_dir=character_reference_dir,
                character_dna=character_dna,
                negative_traits=character_negative_traits,
                composition=character_composition,
                rendering=character_rendering,
                refs_priority=character_refs_priority,
                watermark_text=character_watermark,
                background_mode=background_mode,
                character_slug=character_slug,
            ),
            phrases_per_topic=self.phrases_per_topic,
            cost_mode=cost_mode,
        )

        # Layer 5: Post-production — com branding do personagem
        from src.pipeline.workers.caption_worker import CaptionWorker
        from src.pipeline.workers.hashtag_worker import HashtagWorker
        self.post_production = PostProductionLayer(
            caption_worker=CaptionWorker(
                character_name=character_name,
                character_handle=character_handle,
                caption_prompt=character_caption_prompt,
            ),
            hashtag_worker=HashtagWorker(
                branded_hashtags=character_branded_hashtags,
            ),
        )

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

    def _notify(self, layer: str, status: str, detail: str = "", step: str = ""):
        """Notifica callback sobre progresso de camada ou sub-etapa.

        Args:
            layer: ID da camada (L1-L5).
            status: status da camada ou step.
            detail: descricao curta do progresso.
            step: se fornecido, atualiza um sub-step dentro da camada.
        """
        if self._on_layer_update:
            self._on_layer_update(layer, status, detail, step)

    def _step_cb(self, layer: str):
        """Cria callback de sub-step para uma camada especifica."""
        def cb(step: str, status: str, detail: str = ""):
            self._notify(layer, status, detail, step=step)
        return cb

    def _log_config_summary(self):
        """Loga resumo da configuracao ativa do pipeline."""
        from config import (
            LLM_BACKEND, OLLAMA_MODEL, GEMINI_MODEL_LITE, GEMINI_MODEL_NORMAL,
            IMAGE_BACKEND_PRIORITY, GEMINI_IMAGE_ENABLED, COMFYUI_ENABLED,
            PHRASE_AB_ENABLED, DEDUP_CROSS_RUN_ENABLED, DEDUP_CROSS_RUN_DAYS,
        )
        agents_names = [a.name for a in self.monitoring.agents]
        logger.info("--- Configuracao do Pipeline ---")
        logger.info(f"  LLM backend:        {LLM_BACKEND} (model: {OLLAMA_MODEL if LLM_BACKEND == 'ollama' else GEMINI_MODEL_NORMAL})")
        logger.info(f"  LLM fallback:       Gemini {GEMINI_MODEL_LITE} (lite)")
        logger.info(f"  Image priority:     {IMAGE_BACKEND_PRIORITY} (gemini_img={GEMINI_IMAGE_ENABLED}, comfyui={COMFYUI_ENABLED})")
        logger.info(f"  Cost mode:          {self._cost_mode}")
        logger.info(f"  Images/run:         {self.images_per_run}, phrases/topic: {self.phrases_per_topic}")
        logger.info(f"  A/B testing:        {PHRASE_AB_ENABLED and self._cost_mode == 'normal'}")
        logger.info(f"  Carousel:           {self._carousel_count} slide(s)")
        logger.info(f"  Dedup cross-run:    {DEDUP_CROSS_RUN_ENABLED} ({DEDUP_CROSS_RUN_DAYS}d)")
        logger.info(f"  Theme tags:         {self._theme_tags or 'auto'}")
        logger.info(f"  Exclude topics:     {len(self._exclude_topics) if self._exclude_topics else 0}")
        logger.info(f"  Agents ({len(agents_names)}):       {', '.join(agents_names)}")
        logger.info("--------------------------------")

    def _build_manual_work_orders(self) -> list[WorkOrder]:
        """Cria WorkOrders diretamente a partir de temas manuais (pula L1-L2-L3)."""
        import random
        import uuid
        from config import LAYOUT_TEMPLATES, LAYOUT_RANDOM
        from src.image_gen.prompt_builder import KEYWORD_MAP
        from src.image_gen.gemini_client import SITUACOES

        all_keys = list(SITUACOES.keys())
        layout_pool = list(LAYOUT_TEMPLATES.keys())
        random.shuffle(layout_pool)
        used_keys: set[str] = set()

        work_orders = []
        for i, t in enumerate(self._manual_topics):
            topic = t["topic"]
            humor_angle = t.get("humor_angle", "")

            # Auto-detectar situacao_key via keyword
            combined = f"{topic} {humor_angle}".lower()
            situacao_key = ""
            for kw, sk in KEYWORD_MAP.items():
                if kw in combined and sk not in used_keys:
                    situacao_key = sk
                    break
            if not situacao_key:
                for k in all_keys:
                    if k not in used_keys:
                        situacao_key = k
                        break
                if not situacao_key:
                    situacao_key = random.choice(all_keys)
            used_keys.add(situacao_key)

            # Theme tag override
            if self._theme_tags:
                situacao_key = self._theme_tags[i % len(self._theme_tags)]

            layout = layout_pool[i % len(layout_pool)] if LAYOUT_RANDOM else "bottom"

            wo = WorkOrder(
                order_id=uuid.uuid4().hex[:8],
                trend_event=TrendEvent(
                    title=topic,
                    source=TrendSource.RSS_FEED,
                ),
                gandalf_topic=topic,
                humor_angle=humor_angle,
                situacao_key=situacao_key,
                relevance_score=1.0,
                layout=layout,
                carousel_count=self._carousel_count,
            )
            work_orders.append(wo)
            logger.info(
                f"  Manual WO [{wo.order_id}]: '{topic}' "
                f"situacao={situacao_key} layout={layout}"
            )

        return work_orders

    async def run(self) -> AgentPipelineResult:
        """Executa o pipeline multi-agente completo."""
        result = AgentPipelineResult()
        layer_times: dict[str, float] = {}

        logger.info("=" * 60)
        logger.info("Pipeline multi-agente iniciado")
        self._log_config_summary()
        logger.info("=" * 60)

        # === ATALHO: temas manuais — pula L1/L2/L3, vai direto pra L4 ===
        if self._manual_topics:
            logger.info(f"[SHORTCUT] {len(self._manual_topics)} tema(s) manual(is) — pulando L1/L2/L3")
            self._notify("L1", "done", "Pulado (temas manuais)")
            self._notify("L2", "done", "Pulado (temas manuais)")
            self._notify("L3", "running", "Criando WorkOrders manuais")

            work_orders = self._build_manual_work_orders()
            result.work_orders_emitted = len(work_orders)
            self._notify("L3", "done", f"{len(work_orders)} work orders (manual)")
        else:
            # === PIPELINE COMPLETO: L1 → L2 → L3 ===

            # Layer 1: Monitoramento — busca trends em paralelo
            t0 = time.perf_counter()
            logger.info("[L1] Monitoramento — buscando trends em paralelo...")
            self._notify("L1", "running", "Buscando trends em paralelo")
            events = await self.monitoring.fetch_all(on_step=self._step_cb("L1"))
            layer_times["L1"] = time.perf_counter() - t0
            result.trends_fetched = len(events)
            logger.info(f"[L1] Concluido em {layer_times['L1']:.1f}s — {len(events)} trends coletados")
            self._notify("L1", "done", f"{len(events)} trends coletados")

            if not events:
                error = "Nenhum trend coletado de nenhuma fonte"
                logger.error(f"[L1] ERRO: {error}")
                result.errors.append(error)
                self._notify("L1", "error", error)
                result.finished_at = datetime.now()
                return result

            # Layer 2: Broker — dedup e ranking
            t0 = time.perf_counter()
            logger.info("[L2] Broker — deduplicando e rankeando...")
            self._notify("L2", "running", "Dedup + ranking")
            queued = await self.broker.ingest(events, on_step=self._step_cb("L2"))
            layer_times["L2"] = time.perf_counter() - t0
            result.trend_events_queued = queued
            logger.info(f"[L2] Concluido em {layer_times['L2']:.1f}s — {queued}/{len(events)} eventos (dedup: {len(events) - queued})")
            self._notify("L2", "done", f"{queued} eventos enfileirados")

            # Layer 3: Curador — seleciona melhores temas
            t0 = time.perf_counter()
            logger.info("[L3] Curador — selecionando temas...")
            self._notify("L3", "running", "Selecionando temas via LLM")
            # Per D-13: Drain more trends for broader curator analysis
            trend_events = await self.broker.drain(max_items=30)
            # Curator produces more WorkOrders than images_per_run for better selection
            # The relevance filter (D-14) may discard low-potential topics
            curator_count = max(self.images_per_run * 3, 15)
            topics_count = min(curator_count, len(trend_events))
            logger.info(f"[L3] Drained {len(trend_events)} eventos, requesting {topics_count} temas from curator")

            try:
                work_orders = await self.curator.curate(
                    trend_events, count=topics_count, on_step=self._step_cb("L3"),
                    theme_tags=self._theme_tags,
                    exclude_topics=self._exclude_topics,
                    carousel_count=self._carousel_count,
                )
                layer_times["L3"] = time.perf_counter() - t0
                result.work_orders_emitted = len(work_orders)
                # Log detalhado dos work orders
                for wo in work_orders:
                    logger.info(
                        f"[L3]   WO[{wo.order_id}] topic='{wo.gandalf_topic}' "
                        f"situacao={wo.situacao_key} layout={wo.layout} "
                        f"score={wo.relevance_score:.2f}"
                    )
                logger.info(f"[L3] Concluido em {layer_times['L3']:.1f}s — {len(work_orders)} work orders")
                self._notify("L3", "done", f"{len(work_orders)} work orders")
            except Exception as e:
                layer_times["L3"] = time.perf_counter() - t0
                error = f"Curador falhou: {e}"
                logger.error(f"[L3] ERRO ({layer_times['L3']:.1f}s): {error}")
                logger.debug(f"[L3] Traceback:\n{traceback.format_exc()}")
                result.errors.append(error)
                self._notify("L3", "error", error)
                result.finished_at = datetime.now()
                return result

            if not work_orders:
                error = "Curador nao emitiu nenhum work order"
                logger.error(f"[L3] ERRO: {error}")
                result.errors.append(error)
                self._notify("L3", "error", error)
                result.finished_at = datetime.now()
                return result

        # Layer 4: Geracao — frases + imagens em paralelo
        t0 = time.perf_counter()
        logger.info(f"[L4] Geracao — {len(work_orders)} work orders em paralelo...")
        self._notify("L4", "running", "Gerando frases + imagens")
        packages = await self.generation.process(
            work_orders, on_step=self._step_cb("L4")
        )
        layer_times["L4"] = time.perf_counter() - t0
        result.images_generated = len(packages)
        # Log detalhado dos pacotes
        for pkg in packages:
            logger.info(
                f"[L4]   PKG topic='{pkg.topic}' frase='{pkg.phrase[:50]}...' "
                f"bg_src={getattr(pkg, 'background_source', '?')} "
                f"layout={getattr(pkg, 'image_metadata', {}).get('layout', '?')}"
            )
        logger.info(f"[L4] Concluido em {layer_times['L4']:.1f}s — {len(packages)} imagens geradas")
        self._notify("L4", "done", f"{len(packages)} imagens geradas")

        if not packages:
            error = "Nenhum conteudo gerado"
            logger.error(f"[L4] ERRO: {error}")
            result.errors.append(error)
            self._notify("L4", "error", error)
            result.finished_at = datetime.now()
            return result

        # Layer 5: Pos-producao — caption + hashtags + quality em paralelo
        t0 = time.perf_counter()
        logger.info(f"[L5] Pos-producao — enriquecendo {len(packages)} pacotes...")
        self._notify("L5", "running", "Caption + hashtags + quality")
        packages = await self.post_production.enhance(
            packages, on_step=self._step_cb("L5")
        )
        layer_times["L5"] = time.perf_counter() - t0
        result.content = packages
        result.packages_produced = len(packages)
        logger.info(f"[L5] Concluido em {layer_times['L5']:.1f}s — {len(packages)} pacotes finalizados")
        self._notify("L5", "done", f"{len(packages)} pacotes finalizados")

        # Resumo final detalhado
        result.finished_at = datetime.now()
        total_duration = (result.finished_at - result.started_at).total_seconds()

        logger.info("=" * 60)
        logger.info("PIPELINE CONCLUIDO — RESUMO")
        logger.info(f"  Duracao total:       {total_duration:.1f}s")
        for layer, t in layer_times.items():
            pct = (t / total_duration * 100) if total_duration > 0 else 0
            logger.info(f"  {layer}:                {t:.1f}s ({pct:.0f}%)")
        logger.info(f"  ---")
        logger.info(f"  Trends coletados:    {result.trends_fetched}")
        logger.info(f"  Eventos enfileirados:{result.trend_events_queued}")
        logger.info(f"  Work orders:         {result.work_orders_emitted}")
        logger.info(f"  Imagens geradas:     {result.images_generated}")
        logger.info(f"  Pacotes produzidos:  {result.packages_produced}")
        if result.errors:
            logger.warning(f"  Erros ({len(result.errors)}):")
            for err in result.errors:
                logger.warning(f"    - {err}")
        logger.info("=" * 60)

        return result
