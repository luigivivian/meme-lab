"""Clip-Flow API — FastAPI espelhando rotas do Colab (mago_api_server).

Servidor unico com sub-apps:
  /              — Generator API (geracao, refinamento, batch, temas IA)
  /drive         — Drive Browser API (lista e serve imagens geradas)
  /pipeline      — Pipeline API (orquestrador multi-agente)

Rodar localmente:
    python -m src.api --port 8000

Rodar no Colab com ngrok:
    from src.api.app import start_server
    start_server(port=8000, ngrok_token="SEU_TOKEN")
"""

import asyncio
import importlib
import json
import logging
import random
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

import PIL.Image
from fastapi import FastAPI, BackgroundTasks, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from src.api.models import (
    SingleRequest,
    RefineRequest,
    BatchRequest,
    ThemeItem,
    GenerateThemesRequest,
    EnhanceRequest,
    PipelineRunRequest,
    GeneratePhrasesRequest,
    ComposeImageRequest,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("clip-flow.api")


# ===== Config YAML (themes + batch) =====

def _config_dir() -> Path:
    from config import BASE_DIR
    d = BASE_DIR / "config"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _output_dir() -> Path:
    from config import GENERATED_BACKGROUNDS_DIR
    GENERATED_BACKGROUNDS_DIR.mkdir(parents=True, exist_ok=True)
    return GENERATED_BACKGROUNDS_DIR


def load_themes_config() -> list:
    """Carrega themes.yaml."""
    try:
        import yaml
        path = _config_dir() / "themes.yaml"
        if path.exists():
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
    except ImportError:
        pass
    return []


def save_themes_config(themes: list):
    """Salva lista de temas como YAML."""
    try:
        import yaml
        (_config_dir() / "themes.yaml").write_text(
            yaml.dump(themes, allow_unicode=True, default_flow_style=False),
            encoding="utf-8",
        )
    except ImportError:
        # Fallback: JSON
        (_config_dir() / "themes.json").write_text(
            json.dumps(themes, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


# ===== Job Store =====

JOBS: dict[str, dict] = {}


def _criar_job(job_id: str) -> dict:
    JOBS[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "done": 0,
        "failed": 0,
        "total": 0,
        "results": [],
        "errors": [],
        "created_at": datetime.now().isoformat(),
        "finished_at": None,
        "auto_refine": False,
        "refinement_passes": 0,
    }
    return JOBS[job_id]


def _resolver_tema(theme_key: str, acao_custom: str = "", cenario_custom: str = "") -> tuple[str, str, str]:
    """Resolve theme_key para (situacao_key, acao, cenario)."""
    from src.image_gen.gemini_client import SITUACOES

    if acao_custom or cenario_custom:
        return ("custom", acao_custom, cenario_custom)

    if theme_key in SITUACOES:
        return (theme_key, "", "")

    # Buscar no themes.yaml
    for t in load_themes_config():
        if t.get("key") == theme_key:
            return ("custom", t.get("acao", ""), t.get("cenario", ""))

    return (theme_key, "", "")


def _resolver_tema_batch(item) -> tuple[str, str, str, int]:
    """Resolve item de batch para (situacao_key, acao, cenario, count)."""
    from src.image_gen.gemini_client import SITUACOES

    if isinstance(item, str):
        if item in SITUACOES:
            return (item, "", "", 1)
        for t in load_themes_config():
            if t.get("key") == item:
                return ("custom", t.get("acao", ""), t.get("cenario", ""), t.get("count", 1))
        return (item, "", "", 1)

    if isinstance(item, dict):
        key = item.get("key", "custom")
        acao = item.get("acao", "")
        cenario = item.get("cenario", "")
        count = item.get("count", 1)
        if acao or cenario:
            return ("custom", acao, cenario, count)
        if key in SITUACOES:
            return (key, "", "", count)
        for t in load_themes_config():
            if t.get("key") == key:
                return ("custom", t.get("acao", ""), t.get("cenario", ""), t.get("count", 1))
        return (key, "", "", count)

    return ("sabedoria", "", "", 1)


def _run_batch_job(
    job_id: str, lote: list, n_refs: int, pausa: int,
    auto_refine: bool = False, refinement_passes: int = 1,
):
    """Worker de batch — roda em thread separada."""
    from src.image_gen.gemini_client import GeminiImageClient

    job = JOBS[job_id]
    job["status"] = "running"
    job["auto_refine"] = auto_refine
    job["refinement_passes"] = refinement_passes

    total = sum(
        (item.get("count", 1) if isinstance(item, dict) else 1)
        for item in lote
    )
    job["total"] = total

    client = GeminiImageClient(n_referencias=n_refs)
    gerado = 0

    for item in lote:
        situacao_key, acao, cenario, count = _resolver_tema_batch(item)
        original_key = item if isinstance(item, str) else item.get("key", "custom")

        for i in range(count):
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            nome = f"api_{original_key}_{ts}"

            try:
                if auto_refine:
                    path = client.generate_with_refinement(
                        situacao_key=situacao_key,
                        descricao_custom=acao,
                        cenario_custom=cenario,
                        passes_refinamento=refinement_passes,
                        nome_arquivo=nome,
                    )
                    final_file = f"{nome}_final.png"
                else:
                    path = client.generate_image(
                        situacao_key=situacao_key,
                        descricao_custom=acao,
                        cenario_custom=cenario,
                        nome_arquivo=nome,
                    )
                    final_file = f"{nome}.png"

                gerado += 1

                if path:
                    job["done"] += 1
                    job["results"].append({
                        "theme": original_key,
                        "file": final_file,
                        "path": path,
                        "refined": auto_refine,
                    })
                else:
                    job["failed"] += 1
                    job["errors"].append(f"{original_key}: geracao falhou")

            except Exception as e:
                job["failed"] += 1
                job["errors"].append(f"{original_key}: {str(e)}")
                gerado += 1

            if gerado < total:
                time.sleep(pausa)

    job["status"] = "completed"
    job["finished_at"] = datetime.now().isoformat()
    logger.info(f"Job {job_id} concluido: {job['done']} OK / {job['failed']} falhas")


# ===== Pipeline runs =====

_pipeline_runs: dict[str, dict] = {}


async def _run_pipeline_task(run_id: str, request: PipelineRunRequest):
    """Executa pipeline multi-agente em background."""
    from src.pipeline.async_orchestrator import AsyncPipelineOrchestrator

    run = _pipeline_runs[run_id]
    run["status"] = "running"

    try:
        orchestrator = AsyncPipelineOrchestrator(
            images_per_run=request.count,
            phrases_per_topic=request.phrases_per_topic,
            use_comfyui=request.use_comfyui,
            use_gemini_image=request.use_gemini_image,
        )
        result = await orchestrator.run()

        run["trends_fetched"] = result.trends_fetched
        run["work_orders"] = result.work_orders_emitted
        run["images_generated"] = result.images_generated
        run["packages_produced"] = result.packages_produced
        run["errors"] = result.errors
        run["content"] = [
            {
                "phrase": pkg.phrase,
                "image_path": pkg.image_path,
                "topic": pkg.topic,
                "caption": pkg.caption,
                "hashtags": pkg.hashtags,
                "quality_score": pkg.quality_score,
            }
            for pkg in result.content
        ]

        if result.finished_at and result.started_at:
            run["duration_seconds"] = (result.finished_at - result.started_at).total_seconds()

        run["status"] = "completed"

    except Exception as e:
        run["status"] = "failed"
        run["errors"].append(str(e))
        logger.error(f"Pipeline {run_id} falhou: {e}")


# ===== AI Theme Generator prompts =====

THEME_SYSTEM_PROMPT = (
    "You are a creative director for a social media character called 'O Mago Mestre' — "
    "an ancient wise wizard (Gandalf-like, ~90 years old, silver beard, pointed grey hat, "
    "dark blue robes, wooden staff with golden glow).\n\n"
    "Your job is to create THEMES for photorealistic image generation prompts.\n\n"
    "Each theme MUST have:\n"
    "- key: snake_case identifier\n"
    "- label: emoji + Portuguese short label\n"
    "- acao: DETAILED English action/pose description\n"
    "- cenario: DETAILED English cinematic background\n"
    "- count: 1\n\n"
    "RULES:\n"
    "- acao and cenario MUST be in English\n"
    "- Use photorealistic/cinematic language\n"
    "- The wizard ALWAYS has his hat, staff, robes, and long beard\n"
    "- Be specific with lighting, atmosphere, colors\n"
    "- Output ONLY valid JSON array, no markdown fences\n"
)

ENHANCE_SYSTEM_PROMPT = (
    "You are a prompt engineer for photorealistic AI image generation of 'O Mago Mestre' — "
    "an ancient wise wizard (Gandalf-like).\n\n"
    "The user gives you a SIMPLE concept in any language. Transform it into a detailed theme:\n"
    '{"key": "snake_case", "label": "emoji + Portuguese label", '
    '"acao": "detailed English action", "cenario": "detailed English background", "count": 1}\n\n'
    "RULES:\n"
    "- acao: expression, pose, hands, props, magical effects in English\n"
    "- cenario: cinematic background with lighting in English\n"
    "- Use photography language (85mm lens, f/1.8, bokeh)\n"
    "- Output ONLY valid JSON object, no markdown\n"
)


# ===== Apps =====

app = FastAPI(
    title="Clip-Flow API — Mago Mestre",
    description=(
        "API completa para O Mago Mestre.\n\n"
        "**Generator:** Geracao, refinamento Nano Banana, batch, temas IA\n"
        "**Drive Browser:** Lista e serve imagens geradas\n"
        "**Pipeline:** Orquestrador multi-agente (trends -> frases -> imagens)"
    ),
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

drive_app = FastAPI(
    title="Mago Drive Browser API",
    description="Lista e serve imagens geradas",
    version="1.0.0",
)
drive_app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


# ============================================================
# GENERATOR ROUTES
# ============================================================


@app.post("/generate/single", summary="Gera uma imagem individual", tags=["Geracao"])
def generate_single(req: SingleRequest):
    from src.image_gen.gemini_client import GeminiImageClient

    client = GeminiImageClient()
    if not client.is_available():
        raise HTTPException(status_code=503, detail="Gemini Image nao disponivel")

    situacao_key, acao, cenario = _resolver_tema(req.theme_key, req.acao_custom, req.cenario_custom)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome = f"single_{req.theme_key}_{ts}"

    if req.auto_refine:
        path = client.generate_with_refinement(
            situacao_key=situacao_key,
            descricao_custom=acao,
            cenario_custom=cenario,
            passes_refinamento=req.refinement_passes,
            nome_arquivo=nome,
        )
        final_file = f"{nome}_final.png" if path else None
    else:
        path = client.generate_image(
            situacao_key=situacao_key,
            descricao_custom=acao,
            cenario_custom=cenario,
            nome_arquivo=nome,
        )
        final_file = f"{nome}.png" if path else None

    return {
        "success": path is not None,
        "theme": req.theme_key,
        "file": final_file,
        "path": path,
        "refined": req.auto_refine,
        "refinement_passes": req.refinement_passes if req.auto_refine else 0,
    }


@app.post("/generate/refine", summary="Refina uma imagem existente", tags=["Refinamento"])
def refine_existing(req: RefineRequest):
    from src.image_gen.gemini_client import GeminiImageClient

    if "/" in req.filename or "\\" in req.filename or ".." in req.filename:
        raise HTTPException(status_code=400, detail="Nome de arquivo invalido")

    out = _output_dir()
    path = out / req.filename
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Imagem nao encontrada: {req.filename}")

    try:
        img_base = PIL.Image.open(path).convert("RGB")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao abrir imagem: {e}")

    client = GeminiImageClient()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = Path(req.filename).stem

    img = img_base
    resultados = []
    for i in range(req.passes):
        nome_ref = f"{stem}_ref{i + 1}_{ts}"
        ref_path = client.refine_image(
            imagem_base=img,
            instrucao=req.instrucao,
            referencias_adicionais=req.referencias_adicionais,
            nome_arquivo=nome_ref,
        )
        if ref_path is not None:
            img = PIL.Image.open(ref_path).convert("RGB")
            resultados.append({
                "pass": i + 1,
                "file": f"{nome_ref}.png",
                "path": ref_path,
            })
        else:
            break

    return {
        "success": len(resultados) > 0,
        "original": req.filename,
        "passes_completed": len(resultados),
        "passes_requested": req.passes,
        "results": resultados,
        "final_file": resultados[-1]["file"] if resultados else None,
    }


@app.post("/generate/compose", summary="Background + frase = imagem final", tags=["Geracao"])
async def compose_image(req: ComposeImageRequest):
    from src.image_gen.gemini_client import GeminiImageClient
    from src.image_maker import create_image

    client = GeminiImageClient()
    bg_path = None

    if client.is_available():
        if req.auto_refine:
            bg_path = await asyncio.to_thread(
                client.generate_with_refinement,
                req.situacao, req.descricao_custom, req.cenario_custom,
                req.refinement_passes,
            )
        else:
            bg_path = await asyncio.to_thread(
                client.generate_image,
                req.situacao, None, req.descricao_custom, req.cenario_custom,
            )

    if bg_path is None:
        from config import BACKGROUNDS_DIR
        bgs = list(BACKGROUNDS_DIR.rglob("*.png")) + list(BACKGROUNDS_DIR.rglob("*.jpg"))
        if not bgs:
            raise HTTPException(status_code=500, detail="Nenhum background disponivel")
        bg_path = str(random.choice(bgs))

    image_path = await asyncio.to_thread(create_image, req.phrase, bg_path)

    return {
        "success": True,
        "image_path": image_path,
        "phrase": req.phrase,
        "background": bg_path,
    }


# ============================================================
# BATCH / JOBS ROUTES
# ============================================================


@app.post("/jobs/batch", summary="Lote com lista de temas", tags=["Batch"])
def create_batch(req: BatchRequest):
    job_id = uuid.uuid4().hex[:8]
    _criar_job(job_id)
    threading.Thread(
        target=_run_batch_job,
        args=(job_id, req.themes, req.n_refs, req.pausa),
        kwargs={"auto_refine": req.auto_refine, "refinement_passes": req.refinement_passes},
        daemon=True,
    ).start()
    return {
        "job_id": job_id,
        "status": "queued",
        "total_themes": len(req.themes),
        "auto_refine": req.auto_refine,
    }


@app.post("/jobs/batch/from-config", summary="Lote usando themes.yaml", tags=["Batch"])
def batch_from_config(auto_refine: bool = False, refinement_passes: int = 1):
    themes = load_themes_config()
    if not themes:
        raise HTTPException(status_code=404, detail="themes.yaml nao encontrado")
    job_id = uuid.uuid4().hex[:8]
    _criar_job(job_id)
    threading.Thread(
        target=_run_batch_job,
        args=(job_id, themes, 5, 15),
        kwargs={"auto_refine": auto_refine, "refinement_passes": refinement_passes},
        daemon=True,
    ).start()
    return {
        "job_id": job_id,
        "status": "queued",
        "total_themes": len(themes),
        "auto_refine": auto_refine,
    }


@app.get("/jobs/{job_id}", summary="Status de um job", tags=["Batch"])
def get_job(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job nao encontrado")
    return job


@app.get("/jobs", summary="Todos os jobs", tags=["Batch"])
def list_jobs():
    return {"total": len(JOBS), "jobs": list(JOBS.values())}


# ============================================================
# THEMES / AI THEME GENERATOR ROUTES
# ============================================================


@app.get("/themes", summary="Lista temas disponiveis", tags=["Temas"])
def list_themes():
    from src.image_gen.gemini_client import SITUACOES

    yaml_themes = load_themes_config()
    if yaml_themes:
        return {"source": "themes.yaml", "themes": yaml_themes}
    return {
        "source": "built-in",
        "themes": [
            {"key": k, "label": v["label"], "count": 1}
            for k, v in SITUACOES.items()
        ],
    }


@app.post("/themes", summary="Adiciona tema customizado", tags=["Temas"])
def add_theme(theme: ThemeItem):
    themes = load_themes_config()
    themes = [t for t in themes if t.get("key") != theme.key]
    themes.append(theme.model_dump())
    save_themes_config(themes)
    return {"added": theme.key, "total_themes": len(themes)}


@app.delete("/themes/{key}", summary="Remove tema", tags=["Temas"])
def delete_theme(key: str):
    themes = load_themes_config()
    new_themes = [t for t in themes if t.get("key") != key]
    if len(new_themes) == len(themes):
        raise HTTPException(status_code=404, detail=f"Tema nao encontrado: {key}")
    save_themes_config(new_themes)
    return {"removed": key, "total_themes": len(new_themes)}


@app.post("/themes/generate", summary="Auto-gera temas variados via IA", tags=["Temas IA"])
def generate_themes_ai(req: GenerateThemesRequest):
    from src.image_gen.gemini_client import SITUACOES
    from src.llm_client import generate_json

    existing_keys = list(SITUACOES.keys())
    yaml_themes = load_themes_config()
    if yaml_themes:
        existing_keys += [t.get("key", "") for t in yaml_themes]

    user_prompt = f"Generate exactly {req.count} diverse themes for the Mago Mestre character."
    if req.categories:
        user_prompt += f" Focus on these categories: {', '.join(req.categories)}."
    if req.avoid_existing and existing_keys:
        user_prompt += f" AVOID themes similar to these existing keys: {', '.join(existing_keys)}."
    user_prompt += " Return a JSON array of theme objects."

    try:
        raw = generate_json(system_prompt=THEME_SYSTEM_PROMPT, user_message=user_prompt)
        themes = json.loads(raw)
        if isinstance(themes, dict):
            themes = themes.get("themes", [themes])
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=502, detail=f"Gemini retornou JSON invalido: {e}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erro ao chamar Gemini: {e}")

    valid_themes = []
    for t in themes:
        if not isinstance(t, dict):
            continue
        theme = {
            "key": t.get("key", "").strip().lower().replace(" ", "_"),
            "label": t.get("label", ""),
            "acao": t.get("acao", ""),
            "cenario": t.get("cenario", ""),
            "count": int(t.get("count", 1)),
        }
        if theme["key"] and theme["acao"] and theme["cenario"]:
            valid_themes.append(theme)

    if req.save_to_yaml and valid_themes:
        current = load_themes_config()
        existing_yaml_keys = {t.get("key") for t in current}
        new_themes = [t for t in valid_themes if t["key"] not in existing_yaml_keys]
        if new_themes:
            current.extend(new_themes)
            save_themes_config(current)

    return {"generated": len(valid_themes), "saved_to_yaml": req.save_to_yaml, "themes": valid_themes}


@app.post("/themes/enhance", summary="Input simples -> prompt forte via IA", tags=["Temas IA"])
def enhance_theme_ai(req: EnhanceRequest):
    from src.image_gen.gemini_client import construir_prompt_completo
    from src.llm_client import generate_json

    user_prompt = f'Transform this simple concept into a detailed Mago Mestre theme: "{req.input_text}"'

    try:
        raw = generate_json(system_prompt=ENHANCE_SYSTEM_PROMPT, user_message=user_prompt)
        theme = json.loads(raw)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=502, detail=f"Gemini retornou JSON invalido: {e}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erro ao chamar Gemini: {e}")

    if isinstance(theme, list):
        theme = theme[0] if theme else {}

    result = {
        "key": theme.get("key", "").strip().lower().replace(" ", "_"),
        "label": theme.get("label", ""),
        "acao": theme.get("acao", ""),
        "cenario": theme.get("cenario", ""),
        "count": int(theme.get("count", 1)),
    }

    if not result["key"] or not result["acao"]:
        raise HTTPException(status_code=502, detail="Gemini nao gerou tema valido")

    if req.save_to_yaml:
        current = load_themes_config()
        current = [t for t in current if t.get("key") != result["key"]]
        current.append(result)
        save_themes_config(current)

    preview = construir_prompt_completo(
        situacao_key="custom", descricao_custom=result["acao"], cenario_custom=result["cenario"],
    )

    return {
        "original_input": req.input_text,
        "enhanced_theme": result,
        "saved_to_yaml": req.save_to_yaml,
        "prompt_preview": preview[:500] + "..." if len(preview) > 500 else preview,
    }


# ============================================================
# PIPELINE ROUTES
# ============================================================


@app.post("/pipeline/run", summary="Pipeline multi-agente (background)", tags=["Pipeline"])
async def run_pipeline(request: PipelineRunRequest, background_tasks: BackgroundTasks):
    """Executa o pipeline completo em background. Retorna run_id para consultar status."""
    run_id = uuid.uuid4().hex[:8]
    _pipeline_runs[run_id] = {
        "run_id": run_id, "status": "queued",
        "trends_fetched": 0, "work_orders": 0, "images_generated": 0,
        "packages_produced": 0, "errors": [], "content": [], "duration_seconds": 0,
    }
    background_tasks.add_task(_run_pipeline_task, run_id, request)
    return _pipeline_runs[run_id]


@app.post("/pipeline/run-sync", summary="Pipeline multi-agente (sincrono)", tags=["Pipeline"])
async def run_pipeline_sync(request: PipelineRunRequest):
    """Executa o pipeline e aguarda conclusao."""
    run_id = uuid.uuid4().hex[:8]
    _pipeline_runs[run_id] = {
        "run_id": run_id, "status": "queued",
        "trends_fetched": 0, "work_orders": 0, "images_generated": 0,
        "packages_produced": 0, "errors": [], "content": [], "duration_seconds": 0,
    }
    await _run_pipeline_task(run_id, request)
    return _pipeline_runs[run_id]


@app.get("/pipeline/status/{run_id}", summary="Status do pipeline", tags=["Pipeline"])
async def pipeline_status(run_id: str):
    if run_id not in _pipeline_runs:
        raise HTTPException(status_code=404, detail=f"Pipeline run '{run_id}' nao encontrado")
    return _pipeline_runs[run_id]


@app.get("/pipeline/runs", summary="Lista execucoes do pipeline", tags=["Pipeline"])
async def list_pipeline_runs():
    return {
        run_id: {"status": r["status"], "packages": r.get("packages_produced", 0)}
        for run_id, r in _pipeline_runs.items()
    }


# ============================================================
# PHRASES ROUTES
# ============================================================


@app.post("/phrases/generate", summary="Gera frases do Mago Mestre", tags=["Frases"])
async def generate_phrases_route(req: GeneratePhrasesRequest):
    from src.phrases import generate_phrases
    phrases = await asyncio.to_thread(generate_phrases, req.topic, req.count)
    return {"topic": req.topic, "phrases": phrases, "count": len(phrases)}


# ============================================================
# AGENTS ROUTES
# ============================================================


@app.get("/agents", summary="Lista agentes e disponibilidade", tags=["Agentes"])
async def list_agents():
    agent_classes = [
        ("google_trends", "src.pipeline.agents.google_trends", "GoogleTrendsAgent"),
        ("reddit_memes", "src.pipeline.agents.reddit_memes", "RedditMemesAgent"),
        ("rss_feeds", "src.pipeline.agents.rss_feeds", "RSSFeedAgent"),
        ("tiktok_trends", "src.pipeline.agents.tiktok_trends", "TikTokTrendsAgent"),
        ("instagram_explore", "src.pipeline.agents.instagram_explore", "InstagramExploreAgent"),
        ("twitter_x", "src.pipeline.agents.twitter_x", "TwitterXAgent"),
        ("facebook_viral", "src.pipeline.agents.facebook_viral", "FacebookViralAgent"),
        ("youtube_shorts", "src.pipeline.agents.youtube_shorts", "YouTubeShortsAgent"),
    ]

    agents = []
    for name, module_path, class_name in agent_classes:
        try:
            mod = importlib.import_module(module_path)
            cls = getattr(mod, class_name)
            available = cls().is_available()
        except Exception:
            available = False
        agents.append({"name": name, "available": available, "type": "source"})

    for w in ["phrase_worker", "image_worker", "caption_worker", "hashtag_worker", "quality_worker"]:
        agents.append({"name": w, "available": True, "type": "worker"})

    return agents


@app.post("/agents/{agent_name}/fetch", summary="Fetch de um agente especifico", tags=["Agentes"])
async def fetch_from_agent(agent_name: str, limit: int = 10):
    agent_map = {
        "google_trends": ("src.pipeline.agents.google_trends", "GoogleTrendsAgent"),
        "reddit_memes": ("src.pipeline.agents.reddit_memes", "RedditMemesAgent"),
        "rss_feeds": ("src.pipeline.agents.rss_feeds", "RSSFeedAgent"),
    }

    if agent_name not in agent_map:
        raise HTTPException(status_code=404, detail=f"Agente '{agent_name}' nao encontrado")

    module_path, class_name = agent_map[agent_name]

    try:
        mod = importlib.import_module(module_path)
        cls = getattr(mod, class_name)
        agent = cls()

        items = await asyncio.to_thread(agent.fetch)
        return {
            "agent": agent_name,
            "count": min(len(items), limit),
            "items": [
                {
                    "title": item.title,
                    "source": item.source.value,
                    "score": item.score,
                    "url": item.url,
                    "traffic": item.traffic,
                }
                for item in items[:limit]
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# STATUS / HEALTH
# ============================================================


@app.get("/status", summary="Estado do servico", tags=["Sistema"])
def api_status():
    from config import BACKGROUNDS_DIR
    from src.image_gen.gemini_client import MODELOS_IMAGEM

    out = _output_dir()
    imagens_geradas = list(out.glob("*.png"))
    bgs = list(BACKGROUNDS_DIR.rglob("*.png")) + list(BACKGROUNDS_DIR.rglob("*.jpg"))

    gemini_ok = False
    refs_count = 0
    try:
        from src.image_gen.gemini_client import GeminiImageClient
        c = GeminiImageClient()
        gemini_ok = c.is_available()
        refs_count = len(c._referencias)
    except Exception:
        pass

    return {
        "api_key_ok": gemini_ok,
        "refs_loaded": refs_count,
        "output_path": str(out),
        "total_images_generated": len(imagens_geradas),
        "total_backgrounds": len(bgs),
        "jobs_total": len(JOBS),
        "jobs_running": sum(1 for j in JOBS.values() if j["status"] == "running"),
        "pipeline_runs": len(_pipeline_runs),
        "models": MODELOS_IMAGEM,
        "pipeline": "Nano Banana (geracao + refinamento iterativo)",
    }


# ============================================================
# DRIVE BROWSER SUB-APP
# ============================================================


def _parse_theme_from_filename(stem: str) -> str:
    parts = stem.split("_")
    if len(parts) >= 3 and parts[0] in ("api", "mago", "single", "gemini"):
        return parts[1]
    if len(parts) >= 4 and parts[0] == "lote":
        return parts[2]
    return "unknown"


def _list_drive_images(theme_filter: str | None = None) -> list[dict]:
    out = _output_dir()
    files = sorted(out.glob("*.png"), key=lambda f: f.stat().st_mtime, reverse=True)
    result = []
    for f in files:
        theme = _parse_theme_from_filename(f.stem)
        if theme_filter and theme != theme_filter:
            continue
        stat = f.stat()
        result.append({
            "filename": f.name,
            "theme": theme,
            "size_kb": round(stat.st_size / 1024, 1),
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        })
    return result


@drive_app.get("/images", summary="Lista todas as imagens geradas")
def list_images(
    theme: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    imgs = _list_drive_images(theme)
    return {"total": len(imgs), "offset": offset, "limit": limit, "images": imgs[offset:offset + limit]}


@drive_app.get("/images/latest", summary="N imagens mais recentes")
def latest_images(count: int = Query(default=5, ge=1, le=50)):
    return {"count": count, "images": _list_drive_images()[:count]}


@drive_app.get("/images/by-theme/{theme_key}", summary="Imagens por tema")
def images_by_theme(theme_key: str):
    imgs = _list_drive_images(theme_key)
    return {"theme": theme_key, "total": len(imgs), "images": imgs}


@drive_app.get("/images/{filename}", summary="Serve imagem PNG")
def get_image(filename: str):
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Nome de arquivo invalido")
    path = _output_dir() / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Imagem '{filename}' nao encontrada")
    return FileResponse(str(path), media_type="image/png", filename=filename)


@drive_app.get("/themes", summary="Temas nas imagens geradas")
def list_image_themes():
    imgs = _list_drive_images()
    themes = sorted(set(i["theme"] for i in imgs))
    counts = {t: sum(1 for i in imgs if i["theme"] == t) for t in themes}
    return {"themes": themes, "counts": counts}


@drive_app.get("/health", summary="Estado da conexao")
def drive_health():
    out = _output_dir()
    from config import COMFYUI_REFERENCE_DIR
    return {
        "output_folder": str(out),
        "output_exists": out.exists(),
        "total_images": len(list(out.glob("*.png"))) if out.exists() else 0,
        "refs_folder": str(COMFYUI_REFERENCE_DIR),
        "refs_exists": COMFYUI_REFERENCE_DIR.exists(),
    }


# Montar Drive Browser como sub-app
app.mount("/drive", drive_app)


# ============================================================
# PONTO DE ENTRADA
# ============================================================


def start_server(port: int = 8000, ngrok_token: str | None = None):
    """Inicia o servidor. Usa ngrok se token fornecido (Colab).

    Exemplo:
        from src.api.app import start_server
        start_server(port=8000, ngrok_token="seu_token")
    """
    import uvicorn

    if ngrok_token:
        try:
            from pyngrok import ngrok, conf as ngrok_conf
            ngrok_conf.get_default().auth_token = ngrok_token
            for tunnel in ngrok.get_tunnels():
                ngrok.disconnect(tunnel.public_url)
            tunnel = ngrok.connect(port)
            public_url = tunnel.public_url
            print(f"\n{'=' * 55}")
            print(f"  API ONLINE")
            print(f"{'=' * 55}")
            print(f"  URL Publica   : {public_url}")
            print(f"  Generator Docs: {public_url}/docs")
            print(f"  Drive Docs    : {public_url}/drive/docs")
            print(f"{'=' * 55}\n")
        except ImportError:
            print("pyngrok nao instalado. pip install pyngrok")
        except Exception as e:
            print(f"Erro ngrok: {e}")

    uvicorn.run(app, host="0.0.0.0", port=port)
