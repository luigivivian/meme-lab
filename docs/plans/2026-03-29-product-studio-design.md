# Product Studio — Video Ads Generator Design

**Date:** 2026-03-29
**Status:** Approved (brainstorming complete)

## Conceito

Modulo integrado ao Clip-Flow para geracao 100% IA de videos comerciais de produto. Wizard progressivo guia o usuario desde a foto do produto ate o video final multi-formato, com controle granular de estilo, audio e modelo de geracao.

## Decisoes

| Decisao | Escolha |
|---------|---------|
| Target user | Interno primeiro, depois SaaS |
| Formato saida | Multi-formato (9:16, 16:9, 1:1) |
| Input | Wizard progressivo com defaults inteligentes |
| Estilos | Cinematico + Narrado + Lifestyle |
| Modelo video | Multi-modelo configuravel (Wan 2.6 default) |
| Audio | Configuravel por estilo (trilha auto, TTS, ambiente, mudo) |
| Cenas | Configuravel (single-shot cinematico, multi-cena narrado) |
| Stepper | Mesmo pattern do reels (approve/regenerate por step) |
| Cenario | Gemini Image gen (remove bg + gera cenario) |
| Text overlay | LLM gera headline + CTA, renderiza via FFmpeg |
| Musica | Auto por tom/nicho via Suno |
| Custo | Estimativa antes de gerar, usuario confirma |
| Navegacao | Secao separada /ads no menu |

## Pipeline — 8 Steps no Stepper

1. **ANALISE** — Gemini Vision analisa produto, sugere defaults
2. **CENARIO** — Remove background + gera cenario via Gemini Image
3. **PROMPT** — LLM gera prompt cinematografico otimizado pro modelo
4. **VIDEO** — Wan 2.6 / Kling 2.5 / modelo escolhido via Kie.ai
5. **COPY** — LLM gera headline + CTA + hashtags (se text overlay)
6. **AUDIO** — Suno (trilha) + Gemini TTS (narracao se narrado)
7. **MONTAGEM** — FFmpeg overlay texto, mix audio, legendas SRT
8. **EXPORT** — Crop/pad para cada formato (9:16, 16:9, 1:1)

## Mapeamento Estilo -> Pipeline

| Config | Cinematico | Narrado | Lifestyle |
|--------|-----------|---------|-----------|
| Cenas | Single-shot | Multi-cena (3-5) | Multi-cena (3-7) |
| Camera | Orbital/dolly | Cortes rapidos | Tracking/POV |
| Audio | So trilha | TTS + trilha | Ambiente + trilha |
| Texto | Headline + CTA | Legendas + CTA | Headline sutil |
| Humano | Nao | Nao (so voz) | Sim (maos/pessoa) |
| Duracao | 8-15s | 15-30s | 15-30s |
| Modelo default | Wan 2.6 | Wan 2.6 | Kling 2.5 |

## Mapeamento Tom -> Musica (Suno)

```python
MUSIC_MAP = {
    "premium":     "cinematic ambient piano, luxury, elegant",
    "energetico":  "upbeat electronic, energetic, dynamic",
    "divertido":   "happy pop, cheerful, playful",
    "minimalista": "minimal ambient, subtle, clean",
    "profissional":"corporate, modern, confident",
    "natural":     "acoustic guitar, warm, organic",
}
```

## Custo Estimado por Estilo

| Estilo | Video | Audio | Image | Total |
|--------|-------|-------|-------|-------|
| Cinematico 15s | ~R$3-5 | ~R$1 | ~R$0.50 | ~R$5-7 |
| Narrado 30s | ~R$8-12 | ~R$1.50 | ~R$2 | ~R$12-16 |
| Lifestyle 30s | ~R$10-15 | ~R$1.50 | ~R$2.50 | ~R$14-19 |

## DB Schema

```sql
CREATE TABLE product_ad_jobs (
    id VARCHAR(36) PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id),
    product_name VARCHAR(255),
    product_images JSON,
    config JSON,
    style ENUM('cinematic','narrated','lifestyle'),
    video_model VARCHAR(100),
    audio_mode ENUM('mute','music','narrated','ambient'),
    output_formats JSON,
    prompt_generated TEXT,
    step_state JSON,
    status ENUM('draft','generating','complete','failed'),
    cost_usd DECIMAL(10,4),
    cost_brl DECIMAL(10,4),
    outputs JSON,
    created_at DATETIME,
    updated_at DATETIME
);
```

## Estrutura de Arquivos

```
src/
  product_studio/
    pipeline.py
    prompt_builder.py
    scene_composer.py
    copy_generator.py
    music_selector.py
    config.py
    models.py
  api/routes/
    ads.py

memelab/src/
  app/(app)/ads/
    page.tsx
    new/page.tsx
    [jobId]/page.tsx
  components/ads/
    wizard-step-*.tsx
    step-*.tsx
    ad-card.tsx
```

## Reutilizacao do Codigo Existente

- `KieSora2Client` — ja suporta multiplos modelos via Kie.ai
- `GCSUploader` — upload de fotos para URL publica
- `concat_clips_with_audio` — montagem final multi-cena
- `transcriber.py` — SRT gen (se narrado)
- `video_builder.py` — FFmpeg assembly
- Stepper UI — mesmo pattern de approve/regenerate do reels

## Scope v1 vs Futuro

**v1:** Wizard 4 steps, 3 estilos, multi-modelo, audio configuravel, multi-formato, stepper UI
**Futuro:** Templates por nicho, A/B testing, batch gen, musica custom, humano virtual

## Research Reference

See: .planning/research/video-ads-kie-ai-guide.md
