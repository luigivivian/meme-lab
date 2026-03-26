"""Dependencias compartilhadas da API (FastAPI Depends, helpers)."""

import logging
from pathlib import Path

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("clip-flow.api")


# ── FastAPI Dependencies ─────────────────────────────────────────────────────

async def db_session():
    """FastAPI dependency para obter session do banco."""
    from src.database.session import get_session
    async for session in get_session():
        yield session


# ── Auth dependency ──────────────────────────────────────────────────────────

async def get_current_user(
    authorization: str = Header(..., alias="Authorization"),
    session: AsyncSession = Depends(db_session),
):
    """FastAPI dependency: extract and verify JWT from Authorization header.

    Returns User ORM object. Raises 401 if token invalid/expired/user not found.
    Used by /auth/me now, and by all protected routes in Phase 4.
    """
    from src.auth.jwt import verify_access_token
    from src.database.repositories.user_repo import UserRepository

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization[7:]  # Strip "Bearer "
    payload = verify_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = int(payload["sub"])
    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or deactivated")

    return user


# ── Tenant helpers ───────────────────────────────────────────────────

async def get_user_character(
    slug: str,
    current_user,
    session: AsyncSession,
) -> "Character":
    """Load character by slug, enforce ownership. Raises 404 or 403."""
    from src.database.repositories.character_repo import CharacterRepository

    repo = CharacterRepository(session)
    try:
        character = await repo.get_by_slug(slug, user=current_user)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Forbidden")
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    return character


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
    """Resolve theme_key para (situacao_key, acao, cenario).

    Comportamento:
    - Sem theme_key + com acao/cenario custom → tema livre ("custom")
    - Com theme_key + sem custom → usa acao/cenario padrao do tema
    - Com theme_key + com acao_custom → combina: acao do tema + variacao custom
    - Com theme_key + com cenario_custom → sobrescreve cenario, mantem acao do tema
    """
    from src.image_gen.gemini_client import SITUACOES

    # Resolver acao/cenario base do tema
    base_acao = ""
    base_cenario = ""
    found = False

    if theme_key in SITUACOES:
        base_acao = SITUACOES[theme_key]["acao"]
        base_cenario = SITUACOES[theme_key]["cenario"]
        found = True
    else:
        for t in load_themes_config():
            if t.get("key") == theme_key:
                base_acao = t.get("acao", "")
                base_cenario = t.get("cenario", "")
                found = True
                break

    # Sem tema encontrado — usar custom puro
    if not found:
        return ("custom", acao_custom, cenario_custom)

    # Tema encontrado — combinar com variacao custom
    if acao_custom:
        # Variacao: acao do tema como base + custom como direcao adicional
        acao_final = f"{base_acao}. VARIATION: {acao_custom}"
    else:
        acao_final = base_acao

    cenario_final = cenario_custom if cenario_custom else base_cenario

    return (theme_key, acao_final, cenario_final)


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
