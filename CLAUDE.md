# Clip-Flow

Automacao de memes "O Mago Mestre" para Instagram (@omagomestre). Pipeline que busca trends virais, gera frases engracadas via Claude API, e cria imagens formatadas com estilo mistico medieval.

## Stack

- **Python 3.14** / Windows 11
- **Pillow** — composicao de imagens 1080x1350 (4:5 Instagram)
- **Anthropic SDK** — Claude API para geracao de frases e analise de trends
- **trendspyg** — Google Trends RSS (substitui pytrends, arquivado em 2025)
- **feedparser** — RSS feeds (Reddit + Sensacionalista)
- **APScheduler** — agendamento automatico do pipeline

## Estrutura do Projeto

```
clip-flow/
  config.py                  # Configuracoes centralizadas (imagem, prompts, pipeline)
  requirements.txt
  .env                       # ANTHROPIC_API_KEY (nao committar)
  assets/
    character_model.md       # DNA do personagem + prompts AI para gerar backgrounds consistentes
    backgrounds/             # Imagens de fundo do Mago (.jpg/.png/.webp) — cartoon mistico medieval
    fonts/                   # Fontes customizadas (.ttf/.otf) — fallback: Impact/Arial do Windows
  output/                    # Imagens geradas (gitignored)
  src/
    cli.py                   # CLI original: --topic "tema" --count N / --text "frase"
    phrases.py               # generate_phrases(topic, count) via Claude API
    image_maker.py           # create_image(text, bg_path) — composicao Pillow com vinheta, glow, contorno
    pipeline_cli.py          # CLI do pipeline: --mode once|schedule --count N --interval N
    pipeline/
      models.py              # Dataclasses: TrendItem, AnalyzedTopic, GeneratedContent, PipelineResult
      orchestrator.py        # Coordena: agents -> aggregator -> analyzer -> generator
      scheduler.py           # APScheduler BlockingScheduler com IntervalTrigger
      agents/
        base.py              # BaseSourceAgent (ABC): fetch() -> list[TrendItem]
        google_trends.py     # GoogleTrendsAgent — trendspyg RSS (geo="BR")
        reddit_memes.py      # RedditMemesAgent — RSS via feedparser (6 subreddits)
        rss_feeds.py         # RSSFeedAgent — feedparser (reddit RSS + sensacionalista)
      processors/
        aggregator.py        # TrendAggregator — merge, dedup por similaridade, boost multi-fonte
        analyzer.py          # ClaudeAnalyzer — Claude seleciona melhores temas para humor
        generator.py         # ContentGenerator — wrapper de phrases.py + image_maker.py
```

## Como Executar

```bash
# CLI manual (frase avulsa ou por tema)
python -m src.cli --topic "segunda-feira" --count 5
python -m src.cli --text "Voce nao passa... da primeira fase"

# Pipeline automatizado (uma vez)
python -m src.pipeline_cli --mode once --count 5 --verbose

# Pipeline com agendamento
python -m src.pipeline_cli --mode schedule --interval 6 --count 5
```

## Fluxo do Pipeline

```
[Google Trends] + [Reddit RSS] + [RSS Feeds]
        |                |              |
        v                v              v
            [TrendAggregator]
            merge + dedup + ranking
                    |
                    v
            [ClaudeAnalyzer]
            seleciona N melhores temas
            retorna JSON com gandalf_topic + humor_angle
                    |
                    v
            [ContentGenerator]
            generate_phrases() + create_image()
                    |
                    v
              output/*.png
```

## Estilo Visual — Mago Mistico Medieval

A composicao de imagem segue camadas nesta ordem:

```
1. Background (assets/backgrounds/)  — imagem do mago cartoon mistico
2. Overlay azul noturno              — OVERLAY_COLOR (10,10,30, alpha 150)
3. Vinheta escura nas bordas         — VIGNETTE_STRENGTH=180
4. Glow dourado sutil no centro      — GLOW_COLOR (255,200,80, alpha 25)
5. Texto com contorno preto          — cor pergaminho + stroke 3px
6. Watermark dourado                 — @omagomestre canto inferior direito
```

**Paleta de cores:**
- Texto: branco pergaminho `(255, 248, 220)` com contorno preto 3px
- Overlay: azul noturno `(10, 10, 30, 150)`
- Watermark: dourado sutil `(200, 180, 130, 120)`
- Glow: dourado `(255, 200, 80, 25)`

**Posicao do texto:** terco superior (`TEXT_VERTICAL_POSITION=0.35`) — area inferior reservada para o personagem do mago no background.

**Character Model completo:** ver `assets/character_model.md` para DNA do personagem, prompts por plataforma (Midjourney/Leonardo/DALL-E/Flux), variacoes de cenario, e checklist de consistencia.

**Prompt base para gerar backgrounds (resumo):**
```
Semi-realistic cartoon elderly wizard, long white wavy beard, tall pointed
blue-grey hat, dark midnight blue robes with subtle gold trim, gnarled wooden
staff with golden glow, bright blue twinkling eyes, warm wise expression.
Dark moody fantasy atmosphere, soft golden lighting. Vertical 4:5 ratio,
character centered in lower third, upper area open for text overlay.
```

## Configuracoes Importantes (config.py)

- `IMAGE_WIDTH=1080, IMAGE_HEIGHT=1350` — formato Instagram 4:5
- `FONT_SIZE=60` — fonte principal das frases
- `TEXT_STROKE_WIDTH=3` — contorno preto para legibilidade
- `TEXT_VERTICAL_POSITION=0.35` — texto no terco superior
- `WATERMARK_TEXT="@omagomestre"` — marca d'agua
- `PIPELINE_IMAGES_PER_RUN=5` — imagens por execucao
- `PIPELINE_INTERVAL_HOURS=6` — intervalo entre execucoes
- `PIPELINE_PHRASES_PER_TOPIC=1` — frases por tema selecionado
- `PIPELINE_GOOGLE_TRENDS_GEO="BR"` — Google Trends Brasil

## Modelo Claude

Usar `claude-sonnet-4-20250514` para todas as chamadas (phrases.py e analyzer.py).

## Tom do Conteudo — CRITICO

O conteudo DEVE ser **VIRAL, ENGRACADO, LEVE e RELATABLE**. Estilo memes brasileiros do Twitter/TikTok.

**FAZER:**
- Humor sobre cotidiano (trabalho, segunda-feira, wifi, transito, comida)
- Frases que geram identificacao ("MEU DEUS SOU EU")
- Ironia leve estilo Museu de Memes / Chapolin Sincero
- Tom de "tio sabio zoeiro"

**NAO FAZER:**
- NUNCA frases desmotivacionais, negativas, pessimistas
- NUNCA humor acido, ofensivo ou grosseiro
- NUNCA politica, religiao, temas polemicos
- NUNCA conteudo que magoa ou desanima

Exemplos corretos:
- "Eu no domingo a noite fingindo que segunda nao existe"
- "WiFi caiu e eu descobri que nao sei viver sem internet"
- "Cafe e o unico relacionamento estavel que eu mantenho"

## Decisoes Tecnicas

- **Reddit JSON API bloqueada (403)** — usar RSS via feedparser em vez de JSON API
- **Acentos em filenames** — usar `unicodedata.normalize("NFKD", slug)` para remover
- **Pipeline tolerante a falhas** — se um agent falha, os outros continuam normalmente
- **JSON parsing robusto** — analyzer.py tem 3 fallbacks (direto, code block, regex)
- **Fontes** — prioriza assets/fonts/, fallback para Windows system fonts (Impact, Arial)

## Requisitos

- `ANTHROPIC_API_KEY` configurada no `.env`
- Python 3.12+ (usa `type | None` syntax)
- Dependencias: `pip install -r requirements.txt`

## Idioma

O projeto, comentarios, prompts e mensagens de log sao em **portugues brasileiro**. Manter esse padrao.
