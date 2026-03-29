# Phase 421: Product Studio — AI Video Ads Generator - Research

**Researched:** 2026-03-29
**Domain:** AI video ad pipeline (background removal, scene composition, video generation, music, multi-format export)
**Confidence:** HIGH

## Summary

This phase builds a wizard-driven product video ad pipeline at `/ads`, replicating the proven reels pipeline pattern (step-based execution, approve/regenerate, stepper UI) with new capabilities: background removal via rembg, scene composition via Gemini Image, multi-model video generation via existing KieSora2Client, Suno music via Kie.ai API, FFmpeg text overlay + audio mixing, and multi-format export with background blur padding.

The codebase already has all foundational patterns established in phases 999.4-999.6: step-based pipeline orchestrator (ReelsPipeline), background task execution with flag_modified step_state JSON, stepper UI components, KieSora2Client with 11 models configured including Wan 2.6 and Kling 2.6, GCSUploader for public URLs, FFmpeg concat_clips_with_audio, Gemini TTS, and Gemini image generation. The new work is (1) rembg integration for bg removal, (2) Gemini conversational inpainting for scene composition, (3) Suno music generation via Kie.ai, (4) FFmpeg drawtext overlay, (5) FFmpeg multi-format crop+blur export, (6) a new ProductAdPipeline with 8 steps, and (7) new DB model + API router + frontend wizard/stepper.

**Primary recommendation:** Follow the reels pipeline pattern exactly (same file structure, same API pattern, same stepper UI). The new modules are rembg (pip install, trivial API), Suno via Kie.ai (same auth/polling as video, different endpoint), and FFmpeg filters for drawtext + blur pad (well-documented, single subprocess call each).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- D-01: Wizard progressivo com 4 steps em pagina unica (secoes colapsaveis, nao multi-page)
- D-02: Gemini Vision analisa foto do produto e sugere defaults inteligentes (nicho, tom, cenario). ~R$0.05/analise
- D-03: Steps: Produto (foto+nome) -> Contexto (nicho, publico, tom) -> Estilo (tipo, cenario, humano, duracao) -> Audio & Formato (audio mode, formatos, modelo)
- D-04: Cada step tem defaults pre-preenchidos pelo Gemini Vision. Usuario ajusta o que quiser
- D-05: rembg (Python, local) para remocao de fundo. Zero custo API, qualidade boa para produtos
- D-06: Gemini Image inpainting para gerar cenario. Produto recortado + prompt de cenario -> imagem composta. ~R$0.50/imagem
- D-07: Fluxo: foto original -> rembg remove bg -> Gemini compoe produto no cenario descrito
- D-08: Multi-modelo configuravel: Wan 2.6 I2V (default produto), Kling 2.5 Turbo (acao), Hailuo (fallback). Via KieSora2Client existente
- D-09: Single-shot para cinematico (1 clip 8-15s). Multi-cena para narrado (3-5 clips) e lifestyle (3-7 clips)
- D-10: LLM (Gemini) gera prompt cinematografico automaticamente. Inclui shot type, camera movement, lighting, aesthetic, negative prompt
- D-11: Trilha Suno via Kie.ai. Mapeamento automatico tom->genero musical. Sem config do usuario
- D-12: Suno gera trilha mais longa (30-60s), FFmpeg trim para match duracao do video + fade-out
- D-13: Mix narrado: TTS volume 100%, trilha ~20% background. FFmpeg amix com pesos fixos
- D-14: Audio modes: mudo (cinematico opcional), so trilha (cinematico default), TTS + trilha (narrado), ambiente + trilha (lifestyle)
- D-15: LLM gera headline + CTA + hashtags baseado no produto/nicho/tom
- D-16: FFmpeg drawtext para renderizar overlay. Posicao e estilo configuravel
- D-17: Formato master: 9:16 vertical (mobile-first)
- D-18: Multi-formato: crop inteligente + pad com background blur para 16:9 e 1:1. Uma chamada FFmpeg por formato
- D-19: Estimativa de custo mostrada ao usuario antes de gerar. Confirma antes de gastar creditos
- D-20: Mesmo pattern do reels: approve/regenerate por step. Reutiliza stepper.tsx como base
- D-21: Steps: Analise -> Cenario -> Prompt -> Video -> Copy -> Audio -> Montagem -> Export
- D-22: Export e auto-complete (sem aprovacao). Demais steps pedem approve
- D-23: Secao separada no menu: /ads (Product Ads / Studio). Pipeline, galeria e jobs independentes do reels

### Claude's Discretion
- Escolha de negative prompts por estilo (cinematico vs narrado vs lifestyle)
- Mapeamento especifico de generos musicais Suno por tom
- Layout dos text overlays (posicao, fonte, tamanho) por estilo

### Deferred Ideas (OUT OF SCOPE)
- Templates salvos por nicho (moda, tech, food)
- A/B testing de variacoes automaticas
- Batch generation (mesma config, N produtos)
- Musica custom com letra sobre o produto via Suno
- Humano virtual via character consistency models
- Ducking inteligente para audio mix (sidechain compress)
</user_constraints>

## Standard Stack

### Core (already in project)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| google-genai | 1.68.0 | Gemini Vision analysis, image gen, TTS | Already integrated, same API key |
| httpx | (existing) | Kie.ai API calls (video + music) | Already used by KieSora2Client |
| Pillow | 12.1.1 | Image manipulation, RGBA handling | Already used for reels images |
| FFmpeg | 8.1 | Video assembly, text overlay, audio mix, format export | Already used for reels |
| FastAPI | (existing) | API routes for ads pipeline | Already the web framework |
| SQLAlchemy | (existing) | ORM for product_ad_jobs table | Already the DB layer |

### New Dependencies
| Library | Version | Purpose | Install |
|---------|---------|---------|---------|
| rembg | latest (2026-03-25 release) | Background removal from product photos | `pip install "rembg[cpu]"` |
| onnxruntime | (rembg dep) | ML inference for bg removal models | Auto-installed with rembg |

### No New Frontend Dependencies
The frontend uses the same stack as reels (Next.js 15, React 19, SWR, shadcn/ui, Tailwind 4). No new packages needed.

**Installation:**
```bash
pip install "rembg[cpu]"
```

Note: rembg requires Python >=3.11 (project uses 3.12.8). First run downloads the AI model (~100-300 MB) to `~/.u2net/`. The `birefnet-general` model is recommended for product photos (most accurate). Default `u2net` model is also acceptable and faster.

## Architecture Patterns

### Recommended Project Structure
```
src/
  product_studio/
    __init__.py
    pipeline.py          # ProductAdPipeline (8-step orchestrator, same pattern as ReelsPipeline)
    config.py            # ADS_* constants with env var fallback
    models.py            # Pydantic request/response models
    bg_remover.py        # rembg wrapper (remove_bg -> PIL.Image with alpha)
    scene_composer.py    # Gemini Image: product cutout + scene prompt -> composed image
    prompt_builder.py    # LLM cinematic prompt generation per style
    copy_generator.py    # LLM headline + CTA + hashtags generation
    music_client.py      # Kie.ai Suno API wrapper (create task, poll, download)
    format_exporter.py   # FFmpeg multi-format: 9:16 master -> 16:9 blur + 1:1 blur
  api/routes/
    ads.py               # APIRouter prefix="/ads" (same pattern as reels.py)
  database/
    migrations/versions/
      020_product_ad_jobs.py  # New table migration

memelab/src/
  app/(app)/ads/
    page.tsx              # Job listing (gallery)
    new/page.tsx          # Wizard page (4 collapsible sections)
    [jobId]/page.tsx      # Stepper page (8 steps, approve/regenerate)
  components/ads/
    wizard.tsx            # 4-section collapsible wizard
    wizard-step-product.tsx
    wizard-step-context.tsx
    wizard-step-style.tsx
    wizard-step-audio.tsx
    stepper.tsx           # 8-step stepper header (adapted from reels)
    step-analysis.tsx
    step-scene.tsx
    step-prompt.tsx
    step-video.tsx
    step-copy.tsx
    step-audio.tsx
    step-assembly.tsx
    step-export.tsx
    ad-card.tsx           # Job card for listing
```

### Pattern 1: Pipeline Orchestrator (same as ReelsPipeline)
**What:** Class with per-step methods, each taking explicit I/O, returning artifacts
**When to use:** All 8 pipeline steps
**Example:**
```python
# Source: src/reels_pipeline/main.py (existing pattern)
class ProductAdPipeline:
    def __init__(self, config: dict | None = None):
        self.config = config or {}

    async def run_step_analysis(self, product_image_path: str) -> dict:
        """Step 1: Gemini Vision analyzes product, returns suggested defaults."""
        ...

    async def run_step_scene(self, product_image_path: str, scene_prompt: str, job_dir: str) -> str:
        """Step 2: rembg removes bg + Gemini composes scene. Returns composed image path."""
        ...
```

### Pattern 2: Step-Based API with Background Tasks (same as reels.py)
**What:** POST endpoint triggers background task, stores result in step_state JSON
**When to use:** All step execution endpoints
**Example:**
```python
# Source: src/api/routes/reels.py (existing pattern)
STEP_ORDER = ["analysis", "scene", "prompt", "video", "copy", "audio", "assembly", "export"]

async def _execute_step_task(job_id: str, step_name: str, config: dict, session_factory):
    async with session_factory() as session:
        job = ...  # fetch job
        step_state = dict(job.step_state or {})
        step_state[step_name]["status"] = "generating"
        flag_modified(job, "step_state")
        await session.commit()
        # ... execute step, update step_state, commit
```

### Pattern 3: Kie.ai API Client (reuse + extend)
**What:** Same auth, same create_task/poll/download pattern for music
**When to use:** music_client.py for Suno integration
**Example:**
```python
# Source: Kie.ai API docs — same base URL as KieSora2Client
class KieMusicClient:
    BASE_URL = "https://api.kie.ai/api/v1"  # Same as video

    async def generate_music(self, prompt: str, style: str, instrumental: bool = True) -> str:
        payload = {
            "prompt": prompt, "customMode": True, "instrumental": instrumental,
            "model": "V4", "style": style, "title": "Product Ad BGM",
        }
        # POST /generate -> taskId -> poll /generate/record-info -> audio_url
```

### Pattern 4: Collapsible Wizard (new, D-01)
**What:** Single-page form with 4 collapsible sections, not multi-step navigation
**When to use:** The `/ads/new` page
**Implementation:** Use shadcn/ui Collapsible or Accordion component. Each section auto-opens when previous is filled.

### Anti-Patterns to Avoid
- **Duplicating KieSora2Client code for music:** Kie.ai music uses different endpoints but same auth pattern. Create a separate KieMusicClient that shares auth config, do not modify KieSora2Client.
- **Inlining FFmpeg commands as strings:** Use list-based subprocess.run (existing pattern in video_builder.py). Never shell=True.
- **Storing large binary data in step_state JSON:** Store file paths, not file contents. Same as reels pattern.
- **Blocking API routes with long-running steps:** Always use BackgroundTasks with get_session_factory(). Same as reels pattern.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Background removal | Custom segmentation model | `rembg.remove(input_image)` | One line, MIT license, offline, handles edge cases (hair, transparent objects) |
| Music generation | Custom audio synthesis | Kie.ai Suno API via KieMusicClient | Professional quality, watermark-free, ~20s generation |
| Video I2V generation | Custom video model | KieSora2Client (already built) | Multi-model support, polling, retry, cost tracking all done |
| Multi-format blur pad | Custom PIL composition | FFmpeg split+gblur+overlay filter | Hardware-accelerated, handles audio stream, one subprocess call |
| Text overlay on video | Custom frame-by-frame rendering | FFmpeg drawtext filter | Font rendering, positioning, timing all built-in |
| Audio mixing (TTS + music) | Custom PCM mixing | FFmpeg amix filter with weights | Handles different sample rates, durations, fade-out |
| SRT subtitle generation | Custom word timing | Existing transcriber.py | Already integrated with Gemini, tested |

## Common Pitfalls

### Pitfall 1: rembg Model Download on First Run
**What goes wrong:** First call to `rembg.remove()` downloads ~300MB model, causing timeout in API request
**Why it happens:** Models auto-download to `~/.u2net/` on first use
**How to avoid:** Run `rembg.remove(PIL.Image.new("RGB", (1,1)))` at startup or in a setup script to pre-download the model. Or add to Dockerfile/deploy script.
**Warning signs:** First request takes 60+ seconds then works fine after

### Pitfall 2: Gemini Image Gen for Scene Composition Prompt Quality
**What goes wrong:** Gemini generates a new scene but the product looks different or distorted
**Why it happens:** Conversational image gen may alter the product appearance
**How to avoid:** Use the existing pattern from image_gen.py: pass the cutout product image as a reference image Part, then prompt with explicit "place this exact product in [scene]. Do not modify the product. Keep the product identical to the reference." Include negative traits.
**Warning signs:** Product color/shape changes in composed scene

### Pitfall 3: Suno Music Duration Mismatch
**What goes wrong:** Suno generates 2-minute tracks, video is 15 seconds
**Why it happens:** Suno V4+ generates up to 4-8 minutes by default
**How to avoid:** Generate music, then FFmpeg trim to video duration + 1s fade-out: `ffmpeg -i music.mp3 -t {duration} -af "afade=t=out:st={duration-1}:d=1" trimmed.mp3`
**Warning signs:** Audio extends far beyond video end

### Pitfall 4: FFmpeg amix Filter Duration Behavior
**What goes wrong:** Mixed audio is shorter than expected or has silent tail
**Why it happens:** `amix` defaults to `duration=longest` which may not be what you want
**How to avoid:** Use `amix=inputs=2:duration=first:weights=1 0.2` where first input (TTS) determines duration. Music (second input) will be trimmed automatically.
**Warning signs:** Audio cuts off early or has long silence at end

### Pitfall 5: Background Blur FFmpeg Filter Complexity
**What goes wrong:** FFmpeg filter_complex string errors for blur pad export
**Why it happens:** The split+scale+gblur+overlay chain requires correct stream labels and dimensions
**How to avoid:** Use the verified filter string: `split[orig][copy];[copy]scale={target_w}:{target_h},gblur=sigma=20[bg];[bg][orig]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2`
**Warning signs:** FFmpeg exits with "Invalid filter graph" or produces black frames

### Pitfall 6: SQLAlchemy JSON Mutation Detection
**What goes wrong:** step_state changes not persisted to DB
**Why it happens:** SQLAlchemy does not detect in-place mutations on JSON columns
**How to avoid:** Always call `flag_modified(job, "step_state")` before commit. Pattern already established in reels.
**Warning signs:** Step data reverts to previous state on reload

### Pitfall 7: Migration Chain — Must Chain from Latest
**What goes wrong:** Alembic migration fails with "Can't locate revision"
**Why it happens:** Revision depends_on points to wrong parent
**How to avoid:** Latest migration is 019_reels_subtitle_config.py. New migration must chain from 019 (or the most recent at implementation time). Check `ls src/database/migrations/versions/` before writing.
**Warning signs:** `alembic upgrade head` fails

## Code Examples

### rembg Background Removal
```python
# Source: rembg PyPI docs (verified 2026-03-29)
from rembg import remove
from PIL import Image

def remove_background(input_path: str, output_path: str) -> str:
    """Remove background from product photo. Returns path to RGBA PNG."""
    img = Image.open(input_path)
    result = remove(img)  # Returns RGBA PIL.Image
    result.save(output_path, "PNG")
    return output_path
```

### Gemini Scene Composition (Conversational Inpainting)
```python
# Source: src/reels_pipeline/image_gen.py existing pattern + Gemini docs
from io import BytesIO
from google.genai import types
from src.llm_client import _get_client

async def compose_scene(product_cutout: Image.Image, scene_prompt: str) -> Image.Image:
    """Compose product cutout onto AI-generated scene via Gemini Image."""
    client = _get_client()
    buf = BytesIO()
    product_cutout.save(buf, format="PNG")

    contents = [
        types.Part.from_bytes(data=buf.getvalue(), mime_type="image/png"),
        (
            f"Place this exact product into the following scene: {scene_prompt}. "
            "Keep the product IDENTICAL - same shape, color, details. "
            "Professional product photography, commercial quality. "
            "Vertical 9:16 composition (1080x1920)."
        ),
    ]

    response = await asyncio.to_thread(
        client.models.generate_content,
        model="gemini-2.5-flash-image",
        contents=contents,
        config=types.GenerateContentConfig(response_modalities=["IMAGE", "TEXT"]),
    )

    for part in response.candidates[0].content.parts:
        if part.inline_data and part.inline_data.mime_type.startswith("image/"):
            return Image.open(BytesIO(part.inline_data.data))
    raise RuntimeError("Gemini returned no image for scene composition")
```

### Kie.ai Suno Music Generation
```python
# Source: docs.kie.ai/suno-api/generate-music (verified 2026-03-29)
import httpx

class KieMusicClient:
    BASE_URL = "https://api.kie.ai/api/v1"

    def __init__(self, api_key: str):
        self._headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    async def create_music_task(self, style: str, title: str = "Product Ad BGM") -> str:
        payload = {
            "prompt": f"Background music for a product commercial. {style}",
            "customMode": True, "instrumental": True,
            "model": "V4", "style": style, "title": title,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{self.BASE_URL}/generate", json=payload, headers=self._headers)
            data = resp.json()
            return data["data"]["taskId"]

    async def get_music_status(self, task_id: str) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self.BASE_URL}/generate/record-info",
                params={"taskId": task_id}, headers=self._headers,
            )
            return resp.json()["data"]
```

### FFmpeg Multi-Format Export with Blur Pad
```python
# Source: FFmpeg docs + verified community patterns
import subprocess

def export_blur_pad(input_path: str, output_path: str, target_w: int, target_h: int):
    """Export video with blurred background padding to target dimensions."""
    filter_complex = (
        f"[0:v]split[orig][copy];"
        f"[copy]scale={target_w}:{target_h}:force_original_aspect_ratio=increase,"
        f"crop={target_w}:{target_h},gblur=sigma=20[bg];"
        f"[orig]scale={target_w}:{target_h}:force_original_aspect_ratio=decrease[fg];"
        f"[bg][fg]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2[out]"
    )
    subprocess.run([
        "ffmpeg", "-y", "-i", input_path,
        "-filter_complex", filter_complex,
        "-map", "[out]", "-map", "0:a?",
        "-c:v", "libx264", "-crf", "18", "-preset", "fast",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart", output_path,
    ], capture_output=True, text=True, timeout=120, check=True)
```

### FFmpeg drawtext Overlay
```python
# Source: FFmpeg drawtext filter docs
def overlay_text(input_path: str, output_path: str, headline: str, cta: str):
    """Overlay headline + CTA text on video via FFmpeg drawtext."""
    # Write text to temp file to avoid shell escaping (per Phase 999.2 pattern)
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(headline)
        headline_file = f.name
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(cta)
        cta_file = f.name

    filter_str = (
        f"drawtext=textfile='{headline_file}':fontsize=48:fontcolor=white:"
        f"borderw=2:bordercolor=black:x=(w-text_w)/2:y=h*0.15,"
        f"drawtext=textfile='{cta_file}':fontsize=36:fontcolor=white:"
        f"borderw=2:bordercolor=black:x=(w-text_w)/2:y=h*0.85"
    )
    subprocess.run([
        "ffmpeg", "-y", "-i", input_path,
        "-vf", filter_str,
        "-c:a", "copy", "-c:v", "libx264", "-crf", "18",
        output_path,
    ], capture_output=True, text=True, timeout=120, check=True)
```

### FFmpeg Audio Mix (TTS + Background Music)
```python
# Source: FFmpeg amix filter docs
def mix_audio(tts_path: str, music_path: str, output_path: str, video_duration: float):
    """Mix TTS (100%) + music (20%) trimmed to video duration with fade-out."""
    subprocess.run([
        "ffmpeg", "-y",
        "-i", tts_path,
        "-i", music_path,
        "-filter_complex",
        f"[1:a]atrim=0:{video_duration},afade=t=out:st={max(0, video_duration-1)}:d=1,volume=0.2[bg];"
        f"[0:a][bg]amix=inputs=2:duration=first:weights=1 0.2[out]",
        "-map", "[out]", "-c:a", "aac", "-b:a", "192k", output_path,
    ], capture_output=True, text=True, timeout=60, check=True)
```

## Discretion Recommendations

### Negative Prompts by Style
```python
NEGATIVE_PROMPTS = {
    "cinematic": "text, watermark, logo, blurry, low quality, distorted product, human hands, person",
    "narrated": "text, watermark, logo, blurry, low quality, distorted product, nudity",
    "lifestyle": "text, watermark, logo, blurry, low quality, distorted product, nudity, gore",
}
```

### Suno Music Genre Mapping (from design doc)
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

### Text Overlay Layout by Style
```python
TEXT_LAYOUTS = {
    "cinematic": {"headline_y": 0.12, "cta_y": 0.88, "fontsize_h": 52, "fontsize_cta": 36, "fontcolor": "white"},
    "narrated":  {"headline_y": None, "cta_y": 0.90, "fontsize_h": 0, "fontsize_cta": 32, "fontcolor": "white"},  # No headline, subtitles handle text
    "lifestyle": {"headline_y": 0.08, "cta_y": 0.92, "fontsize_h": 40, "fontsize_cta": 28, "fontcolor": "white"},
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Vertex AI Imagen inpainting | Gemini conversational image editing | 2025-2026 | No mask needed, text prompt describes edit. Simpler API. |
| Suno V3.5 | Suno V4/V5 via Kie.ai | 2025-2026 | Better quality, longer tracks (up to 8 min), faster generation |
| rembg u2net default | rembg birefnet-general | 2025-2026 | Higher accuracy for complex edges, better for product photos |
| KieSora2Client single model | KieSora2Client 11 models | Phase 999.6 | Wan 2.6, Kling 2.6, Seedance, Grok all already configured |

## Open Questions

1. **Suno API Callback vs Polling**
   - What we know: Kie.ai Suno supports both callback URL and polling via record-info endpoint
   - What's unclear: Whether the polling endpoint uses the same `/jobs/recordInfo` as video or a separate `/generate/record-info`
   - Recommendation: Start with polling (same pattern as video). Use separate endpoint `/generate/record-info` per Suno docs. If it uses the video endpoint, both work since same auth.

2. **rembg Model Choice for Products**
   - What we know: `birefnet-general` is most accurate, `u2net` is default and faster
   - What's unclear: Which handles product photos with reflections/shadows better
   - Recommendation: Default to `u2net` (faster, lower memory). Allow env var override `ADS_REMBG_MODEL=birefnet-general` for quality mode. Both produce RGBA output.

3. **Gemini Scene Composition Quality**
   - What we know: Conversational image editing works well for background replacement
   - What's unclear: How well it preserves exact product appearance when compositing
   - Recommendation: Always include the product cutout as reference image Part, use explicit preservation instructions in prompt. If quality is poor, fallback to simple Pillow paste on a generated background.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | All backend | Yes | 3.12.8 | -- |
| FFmpeg | Video assembly, export | Yes | 8.1 | -- |
| Pillow | Image processing | Yes | 12.1.1 | -- |
| google-genai | Gemini Vision/Image/TTS | Yes | 1.68.0 | -- |
| rembg | Background removal | No | -- | `pip install "rembg[cpu]"` (install step) |
| onnxruntime | rembg ML inference | No | -- | Auto-installed with rembg |
| Node.js | Frontend | Yes | 24.12.0 | -- |
| npm | Frontend deps | Yes | 11.6.2 | -- |

**Missing dependencies with no fallback:**
- None (rembg is installable)

**Missing dependencies with fallback:**
- rembg: Not installed. Install via `pip install "rembg[cpu]"`. First-run model download ~300MB.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (backend) |
| Config file | None detected -- Wave 0 task |
| Quick run command | `python -m pytest tests/ -x -q` |
| Full suite command | `python -m pytest tests/ -v` |

### Phase Requirements -> Test Map

Since this phase has no formal requirement IDs in REQUIREMENTS.md (it's a backlog/new feature), validation maps to the decisions:

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| D-05 | rembg removes background from product photo | unit | `pytest tests/test_bg_remover.py -x` | Wave 0 |
| D-06 | Gemini composes product onto scene | integration | `pytest tests/test_scene_composer.py -x` | Wave 0 |
| D-08 | KieSora2Client supports Wan 2.6 / Kling models | unit | `pytest tests/test_kie_client.py -x` | Wave 0 |
| D-11 | KieMusicClient creates Suno task via Kie.ai | unit | `pytest tests/test_music_client.py -x` | Wave 0 |
| D-18 | FFmpeg export produces 3 format variants | unit | `pytest tests/test_format_exporter.py -x` | Wave 0 |
| D-20 | Pipeline step execution updates step_state | integration | `pytest tests/test_ads_pipeline.py -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/ -x -q`
- **Per wave merge:** `python -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_bg_remover.py` -- rembg integration
- [ ] `tests/test_scene_composer.py` -- Gemini scene composition (mock API)
- [ ] `tests/test_music_client.py` -- Suno music client (mock API)
- [ ] `tests/test_format_exporter.py` -- FFmpeg multi-format export
- [ ] `tests/test_ads_pipeline.py` -- Pipeline step orchestration
- [ ] pytest config: `pytest.ini` or `pyproject.toml [tool.pytest]`

## Project Constraints (from CLAUDE.md)

- Primary stack: Next.js (App Router), React, Tailwind CSS, Supabase, Python
- Read existing code before modifying it
- Don't add features beyond what was asked
- Prefer editing existing files over creating new ones
- Only comment where logic isn't self-evident
- Three similar lines > premature abstraction
- No backwards-compatibility hacks
- UI in Portuguese Brazilian (per memelab CLAUDE.md)
- All components are "use client" (SWR + interatividade)
- SWR cache keys are deterministic strings
- Tailwind 4 with @theme tokens in globals.css (no tailwind.config)
- shadcn/ui pattern: Radix UI + CVA + tailwind-merge + clsx

## Sources

### Primary (HIGH confidence)
- [rembg PyPI](https://pypi.org/project/rembg/) -- Latest version, install instructions, Python API
- [rembg GitHub](https://github.com/danielgatis/rembg) -- Models, CLI usage, 21.7K stars
- [Kie.ai Suno API docs](https://docs.kie.ai/suno-api/generate-music) -- Exact endpoint, params, models, response format
- [Kie.ai Suno API overview](https://kie.ai/suno-api) -- Pricing model, capabilities
- Existing codebase: `src/video_gen/kie_client.py`, `src/reels_pipeline/main.py`, `src/api/routes/reels.py` -- Verified patterns

### Secondary (MEDIUM confidence)
- [Gemini API Image Generation docs](https://ai.google.dev/gemini-api/docs/image-generation) -- Conversational image editing
- [FFmpeg vertical to horizontal blur](https://www.junian.net/tech/ffmpeg-vertical-video-blur/) -- Blur pad filter chain
- [FFmpeg blur background gist](https://gist.github.com/ArneAnka/a1348b13fc291f72f862d92f35380428) -- Verified filter_complex syntax
- [Vertex AI Inpaint docs](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/image/edit-insert-objects) -- Imagen inpainting reference (not primary approach)

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- All libraries verified installed or verified installable, versions confirmed
- Architecture: HIGH -- Directly replicates proven reels pipeline pattern from same codebase
- Pitfalls: HIGH -- Based on existing codebase patterns and documented gotchas from prior phases
- Suno integration: MEDIUM -- Endpoint verified via docs, but no codebase precedent for music generation

**Research date:** 2026-03-29
**Valid until:** 2026-04-28 (30 days -- stable libraries, established patterns)
