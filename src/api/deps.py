"""Dependencias compartilhadas da API (FastAPI Depends, helpers)."""

import logging
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("clip-flow.api")


# ── FastAPI Dependencies ─────────────────────────────────────────────────────

async def db_session():
    """FastAPI dependency para obter session do banco."""
    from src.database.session import get_session
    async for session in get_session():
        yield session


# ── Path helpers ─────────────────────────────────────────────────────────────

def config_dir() -> Path:
    from config import BASE_DIR
    d = BASE_DIR / "config"
    d.mkdir(parents=True, exist_ok=True)
    return d


def output_dir() -> Path:
    from config import GENERATED_BACKGROUNDS_DIR
    GENERATED_BACKGROUNDS_DIR.mkdir(parents=True, exist_ok=True)
    return GENERATED_BACKGROUNDS_DIR


# ── Validacao ────────────────────────────────────────────────────────────────

def validate_filename(filename: str) -> None:
    """Rejeita path traversal em nomes de arquivo."""
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Nome de arquivo invalido")


# ── Themes YAML (legacy) ────────────────────────────────────────────────────

def load_themes_config() -> list:
    """Carrega themes.yaml."""
    try:
        import yaml
        path = config_dir() / "themes.yaml"
        if path.exists():
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
    except ImportError:
        pass
    return []


def save_themes_config(themes: list):
    """Salva lista de temas como YAML."""
    import json
    try:
        import yaml
        (config_dir() / "themes.yaml").write_text(
            yaml.dump(themes, allow_unicode=True, default_flow_style=False),
            encoding="utf-8",
        )
    except ImportError:
        (config_dir() / "themes.json").write_text(
            json.dumps(themes, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


# ── Theme resolver ───────────────────────────────────────────────────────────

def resolver_tema(theme_key: str, acao_custom: str = "", cenario_custom: str = "") -> tuple[str, str, str]:
    """Resolve theme_key para (situacao_key, acao, cenario)."""
    from src.image_gen.gemini_client import SITUACOES

    if acao_custom or cenario_custom:
        return ("custom", acao_custom, cenario_custom)
    if theme_key in SITUACOES:
        return (theme_key, "", "")
    for t in load_themes_config():
        if t.get("key") == theme_key:
            return ("custom", t.get("acao", ""), t.get("cenario", ""))
    return (theme_key, "", "")


def resolver_tema_batch(item) -> tuple[str, str, str, int]:
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
