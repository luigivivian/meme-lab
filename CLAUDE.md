# Clip-Flow

Automacao de memes "O Mago Mestre" para Instagram (@magomestre420). Pipeline multi-agente que busca trends virais, gera frases via Gemini API, cria backgrounds com Gemini Image, e compoe imagens formatadas 1080x1350.

## Stack

- **Python 3.14** / Windows 11
- **Pillow** — composicao de imagens 1080x1350 (4:5 Instagram)
- **Google Gemini API** — geracao de frases, analise de trends, e geracao de backgrounds com referencias visuais
- **trendspyg** — Google Trends RSS (substitui pytrends, arquivado em 2025)
- **feedparser** — RSS feeds (Reddit + Sensacionalista)
- **APScheduler** — agendamento automatico do pipeline
- **FastAPI + uvicorn** — API REST para controlar o pipeline
- **pyngrok** — tunel publico para a API (opcional)

## Estrutura do Projeto

```
clip-flow/
  config.py                    # Configuracoes centralizadas (imagem, prompts, pipeline, Gemini, ComfyUI)
  config/themes.yaml           # Situacoes visuais para backgrounds (YAML)
  requirements.txt
  .env                         # GOOGLE_API_KEY (nao committar)
  assets/
    character_model.md         # DNA do personagem + prompts AI
    backgrounds/mago/          # Imagens de referencia do Mago (usadas pelo Gemini Image)
    fonts/                     # Fontes customizadas — fallback: Impact/Arial do Windows
  output/                      # Imagens geradas (gitignored)
  src/
    cli.py                     # CLI original: --topic "tema" --count N / --text "frase"
    llm_client.py              # Client unificado Gemini (google.genai)
    phrases.py                 # generate_phrases(topic, count) via Gemini API
    image_maker.py             # create_image(text, bg_path) — composicao Pillow
    pipeline_cli.py            # CLI: --mode once|schedule|agents --comfyui --phrase-context
    image_gen/
      gemini_client.py         # GeminiImageClient — geracao via Gemini com refs visuais + refinamento
      prompt_builder.py        # KEYWORD_MAP + SCENE_TEMPLATES para mapear temas a situacoes
      comfyui_client.py        # ComfyUIClient REST/WS (fallback local)
    api/
      app.py                   # FastAPI — rotas de pipeline, geracao, themes, agents
      models.py                # Pydantic request/response models
      __main__.py              # python -m src.api [--port] [--ngrok]
    pipeline/
      models.py                # Dataclasses originais: TrendItem, AnalyzedTopic
      models_v2.py             # TrendEvent, WorkOrder, ContentPackage, AgentPipelineResult
      async_orchestrator.py    # AsyncPipelineOrchestrator (L1→L2→L3→L4→L5)
      monitoring.py            # MonitoringLayer — fetch paralelo de agents
      broker.py                # TrendBroker — asyncio.Queue + dedup
      curator.py               # CuratorAgent — ClaudeAnalyzer + KEYWORD_MAP → WorkOrders
      agents/
        async_base.py          # AsyncSourceAgent ABC + SyncAgentAdapter
        google_trends.py       # GoogleTrendsAgent — trendspyg RSS (geo="BR")
        reddit_memes.py        # RedditMemesAgent — RSS via feedparser
        rss_feeds.py           # RSSFeedAgent — feedparser
        tiktok_trends.py       # Stub — requer API key
        instagram_explore.py   # Stub — requer API key
        twitter_x.py           # Stub — requer API key
      processors/
        aggregator.py          # TrendAggregator — merge, dedup, boost multi-fonte
        analyzer.py            # ClaudeAnalyzer — seleciona melhores temas (JSON)
        generator.py           # ContentGenerator — wrapper sync
      workers/
        phrase_worker.py       # PhraseWorker — async wrapper de generate_phrases()
        image_worker.py        # ImageWorker — Gemini/ComfyUI/estatico + Pillow compose
        caption_worker.py      # CaptionWorker — legenda Instagram com CTA
        hashtag_worker.py      # HashtagWorker — hashtags trending + branded
        quality_worker.py      # QualityWorker — score de qualidade
        generation_layer.py    # GenerationLayer — processa WorkOrders em paralelo
        post_production.py     # PostProductionLayer — caption + hashtags + quality
  scripts/
    setup_comfyui.py           # Instalacao ComfyUI + Flux Dev GGUF
```

## Como Executar

```bash
python -m pip install -r requirements.txt

# CLI manual
python -m src.cli --topic "segunda-feira" --count 5

# Pipeline multi-agente
python -m src.pipeline_cli --mode agents --count 5 --verbose

# Pipeline com background contextualizado pela frase
python -m src.pipeline_cli --mode agents --count 5 --phrase-context

# API REST (localhost:8000/docs para Swagger)
python -m src.api --port 8000
```

## Arquitetura Multi-Agente (5 Camadas)

```
L1 Monitoring ── fetch paralelo: GoogleTrends + RedditRSS + RSSFeeds + stubs
L2 Broker ────── dedup + ranking via TrendAggregator (asyncio.Queue)
L3 Curator ───── ClaudeAnalyzer seleciona N temas → WorkOrders com situacao_key
L4 Generation ── PhraseWorker + ImageWorker em paralelo por WorkOrder
L5 PostProd ──── CaptionWorker + HashtagWorker + QualityWorker em paralelo
                 → output/*.png + metadados
```

## Geracao de Backgrounds

Fallback: **Gemini Image API → ComfyUI local → backgrounds estaticos**

- **Gemini Image**: 5 refs do mago + prompt fotorrealista com situacao/pose/cenario
- **use_phrase_context**: injeta frase no prompt para adaptar cenario ao conteudo. Prompt proibe renderizar texto na imagem (apenas mood reference).
- **ComfyUI**: Flux Dev GGUF + LoRA. Requer GPU (--lowvram).

13 situacoes em `gemini_client.py` + extras em `config/themes.yaml`.

## API REST

`http://localhost:8000/docs` para Swagger. Principais rotas:
- `POST /pipeline/run` — pipeline completo (`use_phrase_context`, `use_gemini_image`, `count`)
- `POST /generate/compose` — background + frase = imagem final
- `POST /phrases/generate` — gerar frases por tema
- `GET /themes` / `POST /themes/generate` — gerenciar situacoes visuais
- `GET /agents` — listar agents e status

## Estilo Visual

Composicao Pillow: background → overlay (10,10,30,40) → vinheta(80) → glow(255,200,80,15) → texto branco stroke 2px → watermark @magomestre420.

Texto no terco inferior (`TEXT_VERTICAL_POSITION=0.80`), fonte 48px. Backgrounds Gemini: fotorrealista cinematico, `NEGATIVE_TRAITS` proibe texto/letras.

## Configuracoes Chave (config.py)

- `IMAGE_WIDTH=1080, IMAGE_HEIGHT=1350` — Instagram 4:5
- `FONT_SIZE=48`, `TEXT_STROKE_WIDTH=2`, `TEXT_VERTICAL_POSITION=0.80`
- `WATERMARK_TEXT="@magomestre420"`
- `GEMINI_IMAGE_ENABLED=True`, `GEMINI_MAX_CONCURRENT=5`
- `COMFYUI_MAX_CONCURRENT=1` (semaforo GPU)
- `PIPELINE_IMAGES_PER_RUN=5`, `PIPELINE_GOOGLE_TRENDS_GEO="BR"`

## Tom do Conteudo — CRITICO

**VIRAL, ENGRACADO, LEVE, RELATABLE**. Memes brasileiros estilo Twitter/TikTok. Tom de "tio sabio zoeiro".

**NUNCA**: desmotivacional, ofensivo, politica, religiao, conteudo que magoa.

## Decisoes Tecnicas

- **Gemini API** para frases + analise + imagem (substituiu Anthropic SDK)
- **Reddit JSON API bloqueada (403)** — RSS via feedparser
- **asyncio.to_thread()** para wrapping sync existente
- **Semaphore**: GPU=1, Gemini=5
- **NO TEXT em backgrounds**: Gemini proibido de renderizar texto; overlay feito pelo Pillow

## Requisitos

- `GOOGLE_API_KEY` no `.env`
- Python 3.12+
- `python -m pip install -r requirements.txt`

## Idioma

Projeto, comentarios, prompts e logs em **portugues brasileiro**.
