"""Clip-Flow API — FastAPI modular.

Rotas organizadas em src/api/routes/:
  generation.py  — /generate/*
  jobs.py        — /jobs/*
  themes.py      — /themes/*
  pipeline.py    — /pipeline/*
  content.py     — /content, /images, /phrases
  agents.py      — /agents, /trends
  drive.py       — /drive/*, /status
  characters.py  — /characters/*
  publishing.py  — /publishing/* (fila de publicacao, agendamento, calendario)

Rodar:
    python -m src.api --port 8000
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import generation, jobs, themes, pipeline, content, agents, drive, characters, publishing, auth, video, billing, dashboard
from src.api.log_sanitizer import setup_log_sanitizer

setup_log_sanitizer()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("clip-flow.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle: inicializa banco de dados e scheduler no startup."""
    from src.database.session import init_db
    from config import DATABASE_URL
    from src.services.scheduler_worker import start_scheduler, stop_scheduler
    from src.video_gen.stale_job_scanner import start_stale_job_scanner, stop_stale_job_scanner

    await init_db()
    logger.info(f"Banco de dados inicializado: {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else DATABASE_URL}")

    # Descobrir modelos de imagem Gemini (per D-03, D-04)
    import asyncio
    from src.image_gen.gemini_client import discover_image_models, update_modelos_imagem
    discovered = await asyncio.to_thread(discover_image_models)
    update_modelos_imagem(discovered)
    app.state.gemini_image_models = discovered if discovered else []
    logger.info(f"Gemini image models: {len(app.state.gemini_image_models)} modelo(s) validado(s)")

    # Iniciar scheduler de publicacao (processa posts a cada 60s)
    start_scheduler(interval_seconds=60)
    logger.info("Scheduler de publicacao iniciado")

    # Start stale job scanner (Phase 18: detect stuck video jobs)
    start_stale_job_scanner()
    logger.info("Stale job scanner iniciado")

    yield

    # Stop stale job scanner
    stop_stale_job_scanner()
    logger.info("Stale job scanner parado")

    # Parar scheduler no shutdown
    stop_scheduler()
    logger.info("Scheduler de publicacao parado")


app = FastAPI(
    title="Clip-Flow API — Mago Mestre",
    description=(
        "API completa para O Mago Mestre.\n\n"
        "**Generator:** Geracao, refinamento Nano Banana, batch, temas IA\n"
        "**Drive Browser:** Lista e serve imagens geradas\n"
        "**Pipeline:** Orquestrador multi-agente (trends -> frases -> imagens)"
    ),
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Registrar routers ────────────────────────────────────────────────────────

app.include_router(generation.router)
app.include_router(jobs.router)
app.include_router(themes.router)
app.include_router(pipeline.router)
app.include_router(content.router)
app.include_router(agents.router)
app.include_router(drive.router)
app.include_router(characters.router)
app.include_router(publishing.router)
app.include_router(auth.router)
app.include_router(video.router)
app.include_router(billing.router)
app.include_router(dashboard.router)


@app.get("/llm/status", tags=["System"], summary="Status do backend LLM")
async def llm_status():
    """Retorna backend ativo (gemini/ollama), modelo, cost_mode e disponibilidade."""
    from config import LLM_BACKEND, COST_MODE, OLLAMA_MODEL, GEMINI_MODEL_LITE, GEMINI_MODEL_NORMAL
    from src.llm_client import _ollama_available, _should_use_ollama

    ollama_ok = _ollama_available() if _should_use_ollama() else None
    return {
        "backend": LLM_BACKEND,
        "cost_mode": COST_MODE,
        "gemini_model_lite": GEMINI_MODEL_LITE,
        "gemini_model_normal": GEMINI_MODEL_NORMAL,
        "ollama_model": OLLAMA_MODEL if LLM_BACKEND == "ollama" else None,
        "ollama_available": ollama_ok,
        "effective": "ollama" if (_should_use_ollama() and ollama_ok) else "gemini",
    }


@app.get("/health", tags=["System"], summary="Health check: DB + Gemini model validation")
async def health():
    """Health check com status do banco de dados e validacao de modelos Gemini.

    Endpoint nao autenticado (per D-10) — exempto de JWT em fases futuras.
    """
    from sqlalchemy import text

    # DB check
    db_ok = False
    db_error = None
    try:
        from src.database.session import async_session_factory
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
            db_ok = True
    except Exception as e:
        db_error = str(e)

    # Gemini models (populated at startup)
    gemini_models = getattr(app.state, "gemini_image_models", [])

    overall = "healthy" if (db_ok and len(gemini_models) > 0) else "degraded"

    return {
        "status": overall,
        "database": {
            "connected": db_ok,
            "error": db_error,
        },
        "gemini_image": {
            "models_available": len(gemini_models),
            "models": gemini_models,
            "validation": "ok" if gemini_models else "no image models found",
        },
    }


def start_server(port: int = 8000, ngrok_token: str | None = None):
    """Inicia o servidor. Usa ngrok se token fornecido (Colab)."""
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
            print(f"  Docs          : {public_url}/docs")
            print(f"{'=' * 55}\n")
        except ImportError:
            print("pyngrok nao instalado. pip install pyngrok")
        except Exception as e:
            print(f"Erro ngrok: {e}")

    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
