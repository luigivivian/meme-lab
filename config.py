from pathlib import Path

# Diretórios
BASE_DIR = Path(__file__).parent
ASSETS_DIR = BASE_DIR / "assets"
BACKGROUNDS_DIR = ASSETS_DIR / "backgrounds"
FONTS_DIR = ASSETS_DIR / "fonts"
OUTPUT_DIR = BASE_DIR / "output"

# Banco de dados
import os
from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite+aiosqlite:///{BASE_DIR / 'data' / 'clipflow.db'}")

# Tamanho da imagem (Instagram post 4:5)
IMAGE_WIDTH = 1080
IMAGE_HEIGHT = 1350

# Estilo visual — tema mago místico medieval
TEXT_COLOR = (255, 255, 255)          # Branco puro (melhor legibilidade)
TEXT_STROKE_COLOR = (0, 0, 0)         # Contorno preto
TEXT_STROKE_WIDTH = 2                 # Contorno mais fino e limpo
SHADOW_COLOR = (0, 0, 0, 120)        # Sombra mais suave
SHADOW_OFFSET = 3                    # Offset da sombra em px
OVERLAY_COLOR = (10, 10, 30, 40)     # Overlay bem leve — mago visivel
VIGNETTE_STRENGTH = 80               # Vinheta sutil nas bordas (0-255)
GLOW_COLOR = (255, 200, 80, 15)      # Glow bem sutil
FONT_SIZE = 48                       # Fonte menor e mais legivel
WATERMARK_FONT_SIZE = 22
WATERMARK_COLOR = (200, 180, 130, 120)  # Dourado sutil semi-transparente
WATERMARK_TEXT = "@magomestre420"
TEXT_VERTICAL_POSITION = 0.80         # Texto no terco inferior (0.0=topo, 1.0=base)

# Prompt base para geracao de frases
SYSTEM_PROMPT = """Voce e o Mago Mestre — um bruxo velho e sabio que ja viu de tudo na vida e fala verdades com humor viral brasileiro.

## PERSONA
- Velho mago barbudo, tranquilo, que observa o mundo com calma e sabedoria
- Conhece da rua, ja viveu muito, da conselhos hilarios com ar de quem sabe das coisas
- Mistura sabedoria mistica com humor sobre o cotidiano — tipo um tio sabio zoeiro
- Tom: ENGRACADO, RELATABLE, VIRAL. O publico deve rir e pensar "MEU DEUS SOU EU"
- Fala como se tivesse tido uma revelacao cosmica sobre coisas banais do dia a dia

## ESTILO — O que faz uma frase VIRAL:
1. IDENTIFICACAO INSTANTANEA — a pessoa se ve na frase em 2 segundos
2. CONTRASTE COMICO — sabedoria epica sobre coisas banais do cotidiano
3. FORMATO MEME — curta, impactante, facil de ler rapido no feed
4. COMPARTILHAVEL — "preciso mandar isso no grupo"

## FORMULAS QUE FUNCIONAM:
- "[Pensamento aleatorio] mas com linguagem epica de mago"
- "Minha bola de cristal mostrou que [verdade incomoda engraçada]"
- "[Sabedoria mistica] sobre [coisa banal do dia a dia]"
- "[Situacao cotidiana] mas narrada como profecia mistica"
- "Os pergaminhos antigos revelam que [observacao hilaria]"

## TEMAS QUE BOMBAM:
- Fome de madrugada, delivery 3h da manha, miojo gourmet
- Preguica extrema, ficar deitado, "hoje nao", cancelar planos
- Segunda-feira, trabalho, home office dormindo, reuniao desnecessaria
- Comida, dieta que começa segunda, geladeira vazia
- Wifi caiu, celular sem bateria, perder o celular no sofa
- Sono, alarme, "so mais 5 minutinhos", dormir 14h
- Pensamentos aleatorios de madrugada, filosofia inutil
- Netflix, series, maratonar ate 4h da manha, esquecer o episodio
- Procrastinacao, "amanha eu faco", prazo estourando
- Relacionamentos, crush, solteiro, ex

## EXEMPLOS PERFEITOS (use como referencia de tom):
- "Minha bola de cristal mostra larica no seu futuro proximo"
- "O feitico mais poderoso que eu conheco se chama delivery de madrugada"
- "A profecia diz: quem cancela plano pra ficar em casa tera paz eterna"
- "Meu grimorio so tem receita de miojo gourmet e playlist lo-fi"
- "Os astros dizem que voce vai ignorar o alarme amanha de novo"
- "Eu no domingo a noite fingindo que segunda nao existe"
- "WiFi caiu e eu descobri que nao sei viver sem internet"
- "Cafe e o unico relacionamento estavel que eu mantenho"

## REGRAS ABSOLUTAS:
- Maximo 120 caracteres por frase
- Humor LEVE e NATURAL — sem forcar piada
- NUNCA ofensivo, grosseiro, desmotivacional ou deprimente
- NUNCA politica, religiao, temas polemicos
- NUNCA humor acido que magoa
- Cada frase deve funcionar SOZINHA (sem contexto extra)
- Responda APENAS com as frases, uma por linha, sem numeracao ou marcadores"""

# ===== Pipeline Settings =====

# Quantas imagens gerar por execução do pipeline
PIPELINE_IMAGES_PER_RUN = 5

# Intervalo entre execuções automáticas (em horas)
PIPELINE_INTERVAL_HOURS = 6

# Quantas frases gerar por tópico
PIPELINE_PHRASES_PER_TOPIC = 1

# Geo para Google Trends (BR = Brasil)
PIPELINE_GOOGLE_TRENDS_GEO = "BR"

# Subreddits para monitorar
PIPELINE_REDDIT_SUBREDDITS = [
    "brasil",
    "eu_nvr",
    "DiretoDoZapZap",
    "memes",
    "dankmemes",
    "meirl",
]

# RSS feeds de humor
PIPELINE_RSS_FEEDS = [
    "https://www.reddit.com/r/brasil/hot/.rss",
    "https://www.reddit.com/r/eu_nvr/hot/.rss",
    "https://www.reddit.com/r/memes/hot/.rss",
    "https://www.sensacionalista.com.br/feed/",
]

# ===== ComfyUI Settings =====

# Habilitar geracao local de backgrounds via ComfyUI
COMFYUI_ENABLED = True

# Endereco do servidor ComfyUI
COMFYUI_HOST = "127.0.0.1"
COMFYUI_PORT = 8188

# Timeout para geracao de imagem (segundos)
COMFYUI_TIMEOUT = 300

# Estrategia de prompt: "static" (keyword match) ou "gemini" (via Gemini API)
COMFYUI_PROMPT_STRATEGY = "gemini"

# Forca do LoRA (0.0 a 1.0)
COMFYUI_LORA_STRENGTH = 0.85

# Steps de sampling (mais steps = melhor qualidade, mais lento)
COMFYUI_SAMPLING_STEPS = 25

# Guidance scale para Flux
COMFYUI_GUIDANCE = 4.0

# Diretorio para backgrounds gerados (sem texto — prontos para reuso)
GENERATED_BACKGROUNDS_DIR = OUTPUT_DIR / "backgrounds_generated"

# Diretorio para memes finais (background + frase sobreposta pelo Pillow)
GENERATED_MEMES_DIR = OUTPUT_DIR / "memes"

# Fallback: se ComfyUI falhar, usar backgrounds estaticos
COMFYUI_FALLBACK_TO_STATIC = True

# ===== img2img Settings =====

# Denoise para img2img (0.0 = copia exata, 1.0 = ignora referencia)
# 0.55 = bom equilibrio entre fidelidade ao estilo e variacao
COMFYUI_IMG2IMG_DENOISE = 0.55

# Diretorio com imagens de referencia do Mago Mestre (geradas no Leonardo AI)
COMFYUI_REFERENCE_DIR = ASSETS_DIR / "backgrounds" / "mago"

# ===== Image Backend Priority =====

# Ordem de prioridade para geracao de backgrounds: "comfyui" | "gemini"
# "comfyui" = ComfyUI local primeiro (custo zero), Gemini como fallback
# "gemini" = Gemini Image API primeiro, ComfyUI como fallback
IMAGE_BACKEND_PRIORITY = os.getenv("IMAGE_BACKEND_PRIORITY", "comfyui")

# ===== Gemini Image Generation Settings =====

# Habilitar geracao de backgrounds via Gemini API (com referencias visuais)
GEMINI_IMAGE_ENABLED = True

# Temperatura para geracao de imagem (0.0-2.0, mais alto = mais criativo)
GEMINI_IMAGE_TEMPERATURE = 0.85

# Quantas imagens de referencia enviar por geracao (3 recomendado, max 14)
GEMINI_IMAGE_N_REFS = int(os.getenv("GEMINI_IMAGE_N_REFS", "3"))

# Limite maximo de refs permitido pela API Gemini (gemini-2.5-flash-image: up to 14)
GEMINI_IMAGE_MAX_REFS = 14

# Retry para rate limit 429
GEMINI_IMAGE_MAX_RETRIES = 2
GEMINI_IMAGE_WAIT_BASE = 60

# ===== LLM Cost Tiers =====

# Modelo "lite" para chamadas baratas (frases, captions, scoring)
# gemini-2.5-flash-lite: $0.10/$0.40 por 1M tokens (6x mais barato que flash)
GEMINI_MODEL_LITE = os.getenv("GEMINI_MODEL_LITE", "gemini-2.5-flash-lite")

# Modelo "normal" para chamadas criticas (analyzer, grounding)
GEMINI_MODEL_NORMAL = os.getenv("GEMINI_MODEL_NORMAL", "gemini-2.5-flash")

# Modo de custo: "normal" | "eco" | "ultra-eco"
COST_MODE = os.getenv("COST_MODE", "normal")

# ===== Ollama (modelos locais) =====

# Backend de texto: "gemini" | "ollama"
LLM_BACKEND = os.getenv("LLM_BACKEND", "gemini")

# Modelo Ollama (recomendado: gemma3:4b para 8GB VRAM, llama3.1:8b para 16GB)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")

# Host do servidor Ollama
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# Timeout para chamadas Ollama (segundos)
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))

# Fallback para Gemini se Ollama falhar
OLLAMA_FALLBACK_TO_GEMINI = os.getenv("OLLAMA_FALLBACK_TO_GEMINI", "true").lower() == "true"

# ===== Multi-Agent Pipeline Settings =====

# Timeout para cada agente individual (segundos)
AGENT_FETCH_TIMEOUT = 30

# Tamanho maximo da fila do TrendBroker
BROKER_MAX_QUEUE_SIZE = 100

# Semaforo para ComfyUI — evitar OOM na GPU (RTX 4060 Ti 8GB)
COMFYUI_MAX_CONCURRENT = 1

# Semaforo para chamadas simultaneas ao Gemini API
GEMINI_MAX_CONCURRENT = 5

# Post-production: legenda Instagram
CAPTION_MAX_LENGTH = 2200

# Post-production: quantidade de hashtags por post
HASHTAG_COUNT = 20

# Post-production: score minimo de qualidade para considerar valido
QUALITY_MIN_SCORE = 0.5

# ===== YouTube RSS Agent =====

# Max itens por categoria de trending (geral, comedy, entertainment)
YOUTUBE_RSS_MAX_PER_CATEGORY = 30

# ===== Gemini Web Trends Agent =====

# Modelo para busca grounded de trends (precisa suportar google_search tool)
GEMINI_TRENDS_MODEL = "gemini-2.5-flash"

# Quantos topicos virais pedir ao Gemini por fetch
GEMINI_TRENDS_MAX_TOPICS = 15

# ===== BlueSky Trends Agent =====

# Max posts virais BR coletados do BlueSky por fetch
BLUESKY_MAX_POSTS = 15
# Credenciais BlueSky (app password — criar em bsky.app/settings/app-passwords)
BLUESKY_HANDLE = os.getenv("BLUESKY_HANDLE", "")
BLUESKY_APP_PASSWORD = os.getenv("BLUESKY_APP_PASSWORD", "")

# ===== Brazil Viral RSS Agent =====

# Max itens por feed curado de memes BR
BRAZIL_VIRAL_RSS_MAX_PER_FEED = 10

# ===== Lemmy Communities Agent =====

# Max posts por comunidade Lemmy
LEMMY_MAX_POSTS = 15

# ===== HackerNews Agent =====

# Max stories para buscar do HN top stories
HACKERNEWS_MAX_STORIES = 20

# ===== Dedup Cross-Run =====

# Habilitar dedup entre runs (nao repetir temas recentes)
DEDUP_CROSS_RUN_ENABLED = True

# Quantos dias olhar para tras para encontrar temas ja usados
DEDUP_CROSS_RUN_DAYS = 7

# ===== Layout Variations =====

# Templates de posicionamento de texto na imagem
LAYOUT_TEMPLATES = {
    "bottom": {"text_vertical_position": 0.80, "text_align": "center"},
    "top": {"text_vertical_position": 0.20, "text_align": "center"},
    "center": {"text_vertical_position": 0.50, "text_align": "center"},
    "split_top": {"text_vertical_position": 0.15, "text_align": "left", "margin_left": 60},
}

# Layout padrao quando nao especificado
LAYOUT_DEFAULT = "bottom"

# Sortear layout automaticamente por imagem
LAYOUT_RANDOM = True

# ===== A/B Testing de Frases =====

# Habilitar geracao de alternativas com scoring
PHRASE_AB_ENABLED = True

# Quantas alternativas gerar por frase
PHRASE_AB_ALTERNATIVES = 3

# ===== Carousel Mode =====

# Quantidade padrao de slides por carousel (1 = imagem unica)
CAROUSEL_DEFAULT_COUNT = 1

# Maximo de slides permitido
CAROUSEL_MAX_COUNT = 5

# ===== Instagram Graph API =====

# Token de acesso (long-lived, gerado via Facebook Developer Portal)
INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")

# ID da conta Instagram Business (encontrado em Graph API Explorer)
INSTAGRAM_BUSINESS_ID = os.getenv("INSTAGRAM_BUSINESS_ID", "")

# Versao da Graph API
INSTAGRAM_API_VERSION = "v21.0"
INSTAGRAM_API_BASE = f"https://graph.facebook.com/{INSTAGRAM_API_VERSION}"

# Limites do Instagram
INSTAGRAM_MAX_HASHTAGS = 30
INSTAGRAM_MAX_CAPTION_LENGTH = 2200

# Melhores horarios para postar no Brasil (fuso BRT/Brasilia)
INSTAGRAM_BEST_TIMES_BR = {
    "monday": ["09:00", "12:00", "19:00"],
    "tuesday": ["09:00", "12:00", "19:00"],
    "wednesday": ["09:00", "12:00", "19:00", "21:00"],
    "thursday": ["09:00", "12:00", "19:00"],
    "friday": ["09:00", "12:00", "19:00", "21:00"],
    "saturday": ["10:00", "14:00", "20:00"],
    "sunday": ["10:00", "14:00", "20:00"],
}

# ===== Video Generation (Kie.ai Sora 2) — Phase 999.1 =====

# Feature flag — video generation disabled by default (per D-05: opt-in only)
VIDEO_ENABLED = os.getenv("VIDEO_ENABLED", "false").lower() == "true"

# Feature flag — Reels pipeline disabled by default (Phase 999.4)
REELS_ENABLED = os.getenv("REELS_ENABLED", "false").lower() == "true"

# Kie.ai API key (get from https://kie.ai/api-key)
KIE_API_KEY = os.getenv("KIE_API_KEY", "")

# Default video duration in seconds: 10 or 15 (per D-08)
VIDEO_DURATION = int(os.getenv("VIDEO_DURATION", "10"))

# Default model ID for video generation
VIDEO_MODEL = os.getenv("VIDEO_MODEL", "hailuo/2-3-image-to-video-standard")

# BRL per USD (updated periodically)
VIDEO_USD_TO_BRL = float(os.getenv("VIDEO_USD_TO_BRL", "5.75"))

# Available video models on Kie.ai
# prices_brl: {5s, 10s, 15s} — None means duration not supported
# input_format: how the model receives the image
VIDEO_MODELS = {
    # Kie.ai pricing: 30 credits/call = $0.15/call = R$0.86/call (any duration)
    # $5.00 per 1000 credits, 30 credits per video generation
    "hailuo/2-3-image-to-video-standard": {
        "name": "Hailuo 2.3 Standard",
        "resolution": "720p",
        "tier": "cost",
        "durations": [6, 10],
        "prices_brl": {6: 0.86, 10: 0.86},
        "credits_per_call": 30,
        "speed": 3,
        "notes": "Motion aprimorado, estilos. 30 cred/call",
        "input_format": "hailuo",
    },
    "hailuo/2-3-image-to-video-pro": {
        "name": "Hailuo 2.3 Pro",
        "resolution": "1080p",
        "tier": "cost",
        "durations": [6, 10],
        "prices_brl": {6: 0.86, 10: 0.86},
        "credits_per_call": 30,
        "speed": 3,
        "notes": "Fotorrealista, iluminacao avancada. 30 cred/call",
        "input_format": "hailuo",
    },
    "bytedance/v1-pro-fast-image-to-video": {
        "name": "Seedance Pro Fast",
        "resolution": "1080p",
        "tier": "cost",
        "durations": [5, 10],
        "prices_brl": {5: 2.09, 10: 4.18},
        "speed": 4,
        "notes": "3x mais rapido que Pro, cinema",
        "input_format": "bytedance",
    },
    "bytedance/v1-lite-image-to-video": {
        "name": "Seedance Lite",
        "resolution": "720p",
        "tier": "cost",
        "durations": [5, 10],
        "prices_brl": {5: 1.05, 10: 2.09},
        "speed": 4,
        "notes": "Custo-beneficio, rapido",
        "input_format": "bytedance",
    },
    "wan/2-6-flash-image-to-video": {
        "name": "Wan 2.6 Flash",
        "resolution": "720p",
        "tier": "cost",
        "durations": [5, 10, 15],
        "prices_brl": {5: 1.05, 10: 2.09, 15: 3.14},
        "speed": 4,
        "notes": "Rapido, bom p/ iteracao em volume",
        "input_format": "wan_flash",
    },
    "wan/2-6-image-to-video": {
        "name": "Wan 2.6",
        "resolution": "720p",
        "tier": "standard",
        "durations": [5, 10, 15],
        "prices_brl": {5: 1.83, 10: 3.66, 15: 5.49},
        "speed": 3,
        "notes": "Open-source, ate 15s, 30% OFF",
        "input_format": "wan",
    },
    "kling/v2-1-standard": {
        "name": "Kling v2.1",
        "resolution": "720p",
        "tier": "standard",
        "durations": [5, 10],
        "prices_brl": {5: 1.44, 10: 2.88},
        "speed": 3,
        "notes": "Negative prompt support, cfg_scale",
        "input_format": "kling_v2",
    },
    "bytedance/seedance-1.5-pro": {
        "name": "Seedance 1.5 Pro",
        "resolution": "1080p",
        "tier": "premium",
        "durations": [4, 8, 12],
        "prices_brl": {4: 2.62, 8: 5.23, 12: 7.85},
        "speed": 2,
        "notes": "input_urls, duration INTEGER (not string), aspect_ratio required",
        "input_format": "seedance",
    },
    "kling-3.0/video": {
        "name": "Kling 3.0",
        "resolution": "1080p",
        "tier": "premium",
        "durations": [5, 10],
        "prices_brl": {5: 3.50, 10: 7.00},
        "speed": 2,
        "notes": "Pro mode 1080p, image_urls, aspect_ratio",
        "input_format": "kling_v3",
    },
    "grok-imagine/image-to-video": {
        "name": "Grok Imagine",
        "resolution": "720p",
        "tier": "standard",
        "durations": [6, 10],
        "prices_brl": {6: 1.50, 10: 2.50},
        "speed": 3,
        "notes": "xAI Grok, modos fun/normal/spicy",
        "input_format": "grok",
    },
}

# Hard daily budget cap in USD (per D-09: $3.00 default = ~20 standard videos/day)
VIDEO_DAILY_BUDGET_USD = float(os.getenv("VIDEO_DAILY_BUDGET_USD", "3.0"))

# Cost per second (fallback — overridden per-model from VIDEO_MODELS)
VIDEO_COST_PER_SECOND = float(os.getenv("VIDEO_COST_PER_SECOND", "0.005"))


def compute_video_cost_brl(model_id: str, duration: int) -> float:
    """Look up BRL cost from VIDEO_MODELS config.

    Returns prices_brl value for exact or closest duration.
    Falls back to cost_usd * VIDEO_USD_TO_BRL if model not found.
    """
    import logging

    model_info = VIDEO_MODELS.get(model_id)
    if model_info and "prices_brl" in model_info:
        prices = model_info["prices_brl"]
        if duration in prices:
            return prices[duration]
        valid = list(prices.keys())
        if valid:
            closest = min(valid, key=lambda d: abs(d - duration))
            return prices[closest]
    logging.getLogger("clip-flow.credits").warning(
        "Model %s not in VIDEO_MODELS, using USD fallback", model_id,
    )
    return round(duration * VIDEO_COST_PER_SECOND * VIDEO_USD_TO_BRL, 2)


# Prompt style for video motion templates: "v1" (original) or "v2" (Sora 2 researched)
# Per D-05: v2 uses three-layer motion framework (OpenAI Cookbook + awesome-sora2)
VIDEO_PROMPT_STYLE = os.getenv("VIDEO_PROMPT_STYLE", "v2")

# Concurrency limiter for Kie.ai API calls
KIE_MAX_CONCURRENT = int(os.getenv("KIE_MAX_CONCURRENT", "3"))

# Polling config
KIE_POLL_INITIAL_INTERVAL = int(os.getenv("KIE_POLL_INITIAL_INTERVAL", "5"))
KIE_POLL_MAX_INTERVAL = int(os.getenv("KIE_POLL_MAX_INTERVAL", "30"))
KIE_POLL_TIMEOUT = int(os.getenv("KIE_POLL_TIMEOUT", "600"))

# Generated videos output directory
GENERATED_VIDEOS_DIR = OUTPUT_DIR / "videos"

# ===== GCS Upload (for Kie.ai public URLs) — Phase 999.1 =====

# GCS bucket name for temporary image uploads (per D-04)
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "clipflow-video-uploads")

# Signed URL expiry in seconds (1 hour — video gen takes 30-120s)
GCS_SIGNED_URL_EXPIRY = int(os.getenv("GCS_SIGNED_URL_EXPIRY", "3600"))

# ===== Stripe Billing — Phase 17 =====

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRO_PRICE_ID = os.getenv("STRIPE_PRO_PRICE_ID", "")
STRIPE_ENTERPRISE_PRICE_ID = os.getenv("STRIPE_ENTERPRISE_PRICE_ID", "")

# ===== Video Legends (FFmpeg drawtext) — Phase 999.2 =====

# Feature flag — legend rendering disabled by default (requires FFmpeg installed)
VIDEO_LEGEND_ENABLED = os.getenv("VIDEO_LEGEND_ENABLED", "false").lower() == "true"

# Default animation mode: "static" | "fade" | "typewriter" (per D-05, D-08)
VIDEO_LEGEND_MODE = os.getenv("VIDEO_LEGEND_MODE", "static")

# Font size for video text overlay (matches FONT_SIZE=48 by default)
VIDEO_LEGEND_FONT_SIZE = int(os.getenv("VIDEO_LEGEND_FONT_SIZE", "48"))
