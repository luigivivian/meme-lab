# Phase 421: Product Studio — AI Video Ads Generator - Context

**Gathered:** 2026-03-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Wizard-driven module (`/ads`) for 100% AI product video generation. User uploads product photos, wizard configures style/audio/format, 8-step stepper pipeline produces multi-format commercial videos. Three styles: cinematic, narrated, lifestyle. Separate section from reels pipeline.

</domain>

<decisions>
## Implementation Decisions

### Input & Wizard
- **D-01:** Wizard progressivo com 4 steps em pagina unica (secoes colapsaveis, nao multi-page)
- **D-02:** Gemini Vision analisa foto do produto e sugere defaults inteligentes (nicho, tom, cenario). ~R$0.05/analise
- **D-03:** Steps: Produto (foto+nome) -> Contexto (nicho, publico, tom) -> Estilo (tipo, cenario, humano, duracao) -> Audio & Formato (audio mode, formatos, modelo)
- **D-04:** Cada step tem defaults pre-preenchidos pelo Gemini Vision. Usuario ajusta o que quiser

### Background Removal & Scene Generation
- **D-05:** rembg (Python, local) para remocao de fundo. Zero custo API, qualidade boa para produtos
- **D-06:** Gemini Image inpainting para gerar cenario. Produto recortado + prompt de cenario -> imagem composta. ~R$0.50/imagem
- **D-07:** Fluxo: foto original -> rembg remove bg -> Gemini compoe produto no cenario descrito

### Video Generation
- **D-08:** Multi-modelo configuravel: Wan 2.6 I2V (default produto), Kling 2.5 Turbo (acao), Hailuo (fallback). Via KieSora2Client existente
- **D-09:** Single-shot para cinematico (1 clip 8-15s). Multi-cena para narrado (3-5 clips) e lifestyle (3-7 clips)
- **D-10:** LLM (Gemini) gera prompt cinematografico automaticamente. Inclui shot type, camera movement, lighting, aesthetic, negative prompt

### Audio
- **D-11:** Trilha Suno via Kie.ai. Mapeamento automatico tom->genero musical. Sem config do usuario
- **D-12:** Suno gera trilha mais longa (30-60s), FFmpeg trim para match duracao do video + fade-out
- **D-13:** Mix narrado: TTS volume 100%, trilha ~20% background. FFmpeg amix com pesos fixos
- **D-14:** Audio modes: mudo (cinematico opcionall), so trilha (cinematico default), TTS + trilha (narrado), ambiente + trilha (lifestyle)

### Text Overlay & Copy
- **D-15:** LLM gera headline + CTA + hashtags baseado no produto/nicho/tom
- **D-16:** FFmpeg drawtext para renderizar overlay. Posicao e estilo configuravel

### Export
- **D-17:** Formato master: 9:16 vertical (mobile-first)
- **D-18:** Multi-formato: crop inteligente + pad com background blur para 16:9 e 1:1. Uma chamada FFmpeg por formato
- **D-19:** Estimativa de custo mostrada ao usuario antes de gerar. Confirma antes de gastar creditos

### Stepper Pipeline (8 steps)
- **D-20:** Mesmo pattern do reels: approve/regenerate por step. Reutiliza stepper.tsx como base
- **D-21:** Steps: Analise -> Cenario -> Prompt -> Video -> Copy -> Audio -> Montagem -> Export
- **D-22:** Export e auto-complete (sem aprovacao). Demais steps pedem approve

### Navigation
- **D-23:** Secao separada no menu: `/ads` (Product Ads / Studio). Pipeline, galeria e jobs independentes do reels

### Claude's Discretion
- Escolha de negative prompts por estilo (cinematico vs narrado vs lifestyle)
- Mapeamento especifico de generos musicais Suno por tom
- Layout dos text overlays (posicao, fonte, tamanho) por estilo

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design Document
- `docs/plans/2026-03-29-product-studio-design.md` — Full brainstorming design with pipeline, schema, file structure, cost estimates

### Research
- `.planning/research/video-ads-kie-ai-guide.md` — Kie.ai models, prompt techniques, API integration examples

### Existing Pipeline (reuse patterns)
- `src/reels_pipeline/main.py` — ReelsPipeline class with step-based execution (same pattern for ProductAdPipeline)
- `src/reels_pipeline/video_builder.py` — FFmpeg assembly, concat_clips_with_audio, subtitle overlay
- `src/reels_pipeline/config.py` — Config constants pattern to replicate
- `src/api/routes/reels.py` — REST endpoints with step execution, approve, regenerate (same pattern for ads.py)
- `memelab/src/components/reels/stepper.tsx` — Stepper UI component (base for ads stepper)
- `memelab/src/app/(app)/reels/[jobId]/page.tsx` — Job detail page with stepper (pattern for ads/[jobId])

### Video Generation
- `src/video_gen/kie_client.py` — KieSora2Client: add Wan 2.6 and Kling 2.5 model configs

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `KieSora2Client` (src/video_gen/kie_client.py): Multi-modelo via Kie.ai. Adicionar Wan 2.6 e Kling 2.5 ao VIDEO_MODELS dict
- `GCSUploader` (src/video_gen/gcs_uploader.py): Upload de fotos para URL publica (necessario para I2V)
- `concat_clips_with_audio` (video_builder.py): Montagem final com xfade + audio + SRT + trim automatico
- `transcriber.py`: Geracao de SRT a partir de audio (se narrado)
- `tts.py`: Gemini TTS para narracao
- Stepper components: stepper.tsx, step-*.tsx (6 step components existentes)
- `image_gen.py`: Gemini Image gen (reutilizar para cenario inpainting)
- `script_gen.py`: LLM prompt generation pattern (reutilizar para prompt cinematografico)

### Established Patterns
- Step-based pipeline com step_state JSON (flag_modified para SQLAlchemy)
- Background task execution via FastAPI BackgroundTasks
- SWR polling no frontend para status updates
- Approve -> execute next step flow
- Regenerate clears downstream steps

### Integration Points
- Menu lateral: adicionar item "Product Ads" apos "Reels"
- DB: nova tabela product_ad_jobs (mesmo pattern de reels_jobs)
- API: novo router ads.py registrado no app principal
- Frontend: nova rota /ads com page.tsx + new/ + [jobId]

</code_context>

<specifics>
## Specific Ideas

- Mapeamento tom->musica definido no design doc (MUSIC_MAP com 6 generos)
- Custo estimado por estilo: Cinematico ~R$5-7, Narrado ~R$12-16, Lifestyle ~R$14-19
- rembg para bg removal (pip install rembg[gpu] se GPU disponivel)
- Background blur pad para multi-formato (nao pad preto)

</specifics>

<deferred>
## Deferred Ideas

- Templates salvos por nicho (moda, tech, food) — futuro
- A/B testing de variacoes automaticas — futuro
- Batch generation (mesma config, N produtos) — futuro
- Musica custom com letra sobre o produto via Suno — futuro
- Humano virtual via character consistency models — futuro
- Ducking inteligente para audio mix (sidechaincompress) — futuro, se feedback pedir

</deferred>

---

*Phase: 421-product-studio-ai-video-ads-generator*
*Context gathered: 2026-03-29*
