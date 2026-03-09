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
WATERMARK_TEXT = "@omagomestre"
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
COMFYUI_ENABLED = False

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

# Semaforo para chamadas simultaneas ao Gemini API
GEMINI_MAX_CONCURRENT = 5

# Post-production: legenda Instagram
CAPTION_MAX_LENGTH = 2200

# Post-production: quantidade de hashtags por post
HASHTAG_COUNT = 20

# Post-production: score minimo de qualidade para considerar valido
QUALITY_MIN_SCORE = 0.5
