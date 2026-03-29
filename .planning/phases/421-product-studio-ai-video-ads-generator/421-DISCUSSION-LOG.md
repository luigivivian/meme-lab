# Phase 421: Product Studio — AI Video Ads Generator - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-29
**Phase:** 421-product-studio-ai-video-ads-generator
**Areas discussed:** Background Removal, Suno API Integration, Multi-formato Export, Wizard UX

---

## Background Removal

| Option | Description | Selected |
|--------|-------------|----------|
| rembg local | Python open-source, zero custo, qualidade boa para produtos | X |
| Gemini Image edit | Custo ~R$0.10/chamada, qualidade variavel | |
| remove.bg API | Melhor qualidade detalhes finos, $0.20/img, dependencia externa | |
| Sem remocao | Foto direto pro I2V, mais simples, menos controle | |

**User's choice:** rembg local
**Notes:** Zero custo API prioritizado

## Scene Generation

| Option | Description | Selected |
|--------|-------------|----------|
| Gemini Image inpainting | Produto recortado + prompt cenario, ~R$0.50/img | X |
| Composicao Pillow | Produto sobre cenarios pre-gerados, zero custo API | |
| Prompt direto no I2V | Modelo cria cenario + movimento ao mesmo tempo | |

**User's choice:** Gemini Image inpainting

## Music Duration

| Option | Description | Selected |
|--------|-------------|----------|
| Gerar mais longa e cortar | 30-60s Suno, FFmpeg trim + fade-out | X |
| Duracao exata | Passar target pro Suno (nem sempre preciso) | |
| Loop trilha curta | 15s loopado, pode soar repetitivo | |

**User's choice:** Gerar mais longa e cortar

## Audio Mix

| Option | Description | Selected |
|--------|-------------|----------|
| Trilha baixa automatica | TTS 100%, trilha ~20%, FFmpeg amix fixo | X |
| Ducking inteligente | Trilha abaixa com TTS, sobe nos silencios | |
| Volume configuravel | Slider balance no wizard | |

**User's choice:** Trilha baixa automatica

## Multi-formato Export

| Option | Description | Selected |
|--------|-------------|----------|
| Crop inteligente + pad blur | Central crop + background blur, 1 FFmpeg/formato | X |
| Re-render por formato | Video separado via Kie.ai por aspecto, 3x custo | |
| Pad preto simples | Letterbox/pillarbox, parece amador | |

**User's choice:** Crop inteligente + pad blur

## Master Format

| Option | Description | Selected |
|--------|-------------|----------|
| 9:16 vertical | Mobile-first, Reels/TikTok dominante | X |
| 16:9 horizontal | YouTube/ads mais versatil | |
| Depende do estilo | Cinematico 16:9, outros 9:16 | |

**User's choice:** 9:16 vertical

## Smart Defaults

| Option | Description | Selected |
|--------|-------------|----------|
| Gemini Vision analisa + sugere | Upload -> Vision identifica produto, sugere nicho/tom/cenario | X |
| Presets por categoria | Usuario escolhe categoria manual | |
| Sem defaults | Campos vazios | |

**User's choice:** Gemini Vision analisa + sugere

## Wizard UI

| Option | Description | Selected |
|--------|-------------|----------|
| Steps em pagina unica | 4 secoes colapsaveis, menos navegacao | X |
| Multi-page wizard | 1 pagina por step com Next/Back | |
| Tabs horizontais | 4 tabs, pode pular entre eles | |

**User's choice:** Steps em pagina unica

## Claude's Discretion

- Negative prompts por estilo
- Mapeamento generos musicais Suno por tom
- Layout text overlays (posicao, fonte, tamanho)

## Deferred Ideas

- Templates por nicho, A/B testing, batch gen, musica custom, humano virtual, ducking inteligente
