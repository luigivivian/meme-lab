from pathlib import Path

# Diretórios
BASE_DIR = Path(__file__).parent
ASSETS_DIR = BASE_DIR / "assets"
BACKGROUNDS_DIR = ASSETS_DIR / "backgrounds"
FONTS_DIR = ASSETS_DIR / "fonts"
OUTPUT_DIR = BASE_DIR / "output"

# Tamanho da imagem (Instagram post 4:5)
IMAGE_WIDTH = 1080
IMAGE_HEIGHT = 1350

# Estilo visual — tema mago místico medieval
TEXT_COLOR = (255, 248, 220)          # Branco pergaminho (cornsilk)
TEXT_STROKE_COLOR = (0, 0, 0)         # Contorno preto forte
TEXT_STROKE_WIDTH = 3                 # Espessura do contorno
SHADOW_COLOR = (0, 0, 0, 200)        # Sombra preta forte
SHADOW_OFFSET = 4                    # Offset da sombra em px
OVERLAY_COLOR = (10, 10, 30, 150)    # Azul noturno semi-transparente
VIGNETTE_STRENGTH = 180              # Intensidade da vinheta escura nas bordas (0-255)
GLOW_COLOR = (255, 200, 80, 25)      # Dourado sutil para brilho mistico
FONT_SIZE = 60                       # Fonte maior para impacto
WATERMARK_FONT_SIZE = 22
WATERMARK_COLOR = (200, 180, 130, 120)  # Dourado sutil semi-transparente
WATERMARK_TEXT = "@omagomestre"
TEXT_VERTICAL_POSITION = 0.35         # Texto no terco superior (0.0=topo, 1.0=base)

# Prompt base para geração de frases
SYSTEM_PROMPT = """Você é o Gandalf Sincero — um Gandalf com humor leve, inteligente e viral no estilo memes brasileiros.

Tom: ENGRAÇADO, RELATABLE, LEVE. O público deve rir e se identificar, não se sentir mal.
Pense em memes virais do Twitter/TikTok brasileiro — aquele humor que todo mundo compartilha.

O que FAZER:
- Humor sobre situações do cotidiano (trabalho, segunda-feira, wifi, trânsito, comida)
- Frases que as pessoas pensam "MEU DEUS SOU EU" e compartilham
- Referências de cultura pop, séries, internet brasileira
- Ironia leve e inteligente (estilo Museu de Memes, Chapolin Sincero)
- Tom de "tio sábio zoeiro" que dá conselhos engraçados

O que NÃO FAZER:
- NUNCA ser ofensivo, grosseiro, desmotivacional ou deprimente
- NUNCA frases negativas, pessimistas ou que atacam alguém
- NUNCA humor ácido que magoa ou desanima
- Nada de política, religião ou temas polêmicos

Exemplos de tom certo:
- "Eu no domingo à noite fingindo que segunda não existe"
- "WiFi caiu e eu descobri que não sei viver sem internet"
- "Café é o único relacionamento estável que eu mantenho"

Cada frase deve ter no máximo 120 caracteres.
Responda APENAS com as frases, uma por linha, sem numeração ou marcadores."""

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
COMFYUI_ENABLED = False

# Endereco do servidor ComfyUI
COMFYUI_HOST = "127.0.0.1"
COMFYUI_PORT = 8188

# Timeout para geracao de imagem (segundos)
COMFYUI_TIMEOUT = 300

# Estrategia de prompt: "static" (keyword match) ou "claude" (via Claude API)
COMFYUI_PROMPT_STRATEGY = "claude"

# Forca do LoRA (0.0 a 1.0)
COMFYUI_LORA_STRENGTH = 0.85

# Steps de sampling (mais steps = melhor qualidade, mais lento)
COMFYUI_SAMPLING_STEPS = 25

# Guidance scale para Flux
COMFYUI_GUIDANCE = 4.0

# Diretorio para backgrounds gerados
GENERATED_BACKGROUNDS_DIR = OUTPUT_DIR / "backgrounds_generated"

# Fallback: se ComfyUI falhar, usar backgrounds estaticos
COMFYUI_FALLBACK_TO_STATIC = True

# ===== img2img Settings =====

# Denoise para img2img (0.0 = copia exata, 1.0 = ignora referencia)
# 0.55 = bom equilibrio entre fidelidade ao estilo e variacao
COMFYUI_IMG2IMG_DENOISE = 0.55

# Diretorio com imagens de referencia do Mago Mestre (geradas no Leonardo AI)
COMFYUI_REFERENCE_DIR = ASSETS_DIR / "backgrounds" / "mago"

# ===== Multi-Agent Pipeline Settings =====

# Timeout para cada agente individual (segundos)
AGENT_FETCH_TIMEOUT = 30

# Tamanho maximo da fila do TrendBroker
BROKER_MAX_QUEUE_SIZE = 100

# Semaforo para ComfyUI — evitar OOM na GPU (RTX 4060 Ti 8GB)
COMFYUI_MAX_CONCURRENT = 1

# Semaforo para chamadas simultaneas ao Claude API
CLAUDE_MAX_CONCURRENT = 3

# Post-production: legenda Instagram
CAPTION_MAX_LENGTH = 2200

# Post-production: quantidade de hashtags por post
HASHTAG_COUNT = 20

# Post-production: score minimo de qualidade para considerar valido
QUALITY_MIN_SCORE = 0.5
