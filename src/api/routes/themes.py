"""Rotas de temas (CRUD + AI generate/enhance)."""

import asyncio
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import db_session, get_current_user
from src.api.models import ThemeItem, GenerateThemesRequest, EnhanceRequest

logger = logging.getLogger("clip-flow.api")

router = APIRouter(prefix="/themes", tags=["Temas"])

# ── AI Prompts ──────────────────────────────────────────────────────────────

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


@router.get("", summary="Lista temas disponiveis")
async def list_themes(
    character_id: int | None = Query(default=None),
    include_builtin: bool = Query(default=True),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
    from src.database.repositories.theme_repo import ThemeRepository

    repo = ThemeRepository(session)
    if character_id is not None:
        themes = await repo.list_effective(character_id)
    else:
        themes = await repo.list_global(include_builtin=include_builtin)

    items = [
        {
            "id": t.id, "key": t.key, "label": t.label, "acao": t.acao,
            "cenario": t.cenario, "count": t.count,
            "is_builtin": t.is_builtin, "character_id": t.character_id,
        }
        for t in themes
    ]
    total = len(items)
    return {"total": total, "offset": offset, "limit": limit, "themes": items[offset:offset + limit]}


@router.get("/keys", summary="Lista todas as situacao_keys disponiveis")
def list_theme_keys(current_user=Depends(get_current_user)):
    from src.pipeline.curator import _load_all_situacao_keys
    keys = _load_all_situacao_keys()
    return {"total": len(keys), "keys": keys}


@router.post("", summary="Adiciona tema customizado")
async def add_theme(
    theme: ThemeItem,
    character_id: int | None = Query(default=None),
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
    from src.database.repositories.theme_repo import ThemeRepository

    repo = ThemeRepository(session)
    existing = await repo.get_by_key(theme.key, character_id)
    if existing:
        updated = await repo.update(existing.id, {
            "label": theme.label, "acao": theme.acao,
            "cenario": theme.cenario, "count": theme.count,
        })
        return {"updated": theme.key, "id": updated.id}

    new_theme = await repo.create({
        "key": theme.key, "label": theme.label, "acao": theme.acao,
        "cenario": theme.cenario, "count": theme.count,
        "character_id": character_id, "is_builtin": False,
    })
    return {"added": theme.key, "id": new_theme.id}


@router.delete("/{key}", summary="Remove tema")
async def delete_theme(
    key: str,
    character_id: int | None = Query(default=None),
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
    from src.database.repositories.theme_repo import ThemeRepository

    repo = ThemeRepository(session)
    deleted = await repo.delete_by_key(key, character_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Tema nao encontrado: {key}")
    return {"removed": key}


@router.post("/generate", summary="Auto-gera temas variados via IA", tags=["Temas IA"])
async def generate_themes_ai(req: GenerateThemesRequest, current_user=Depends(get_current_user), session: AsyncSession = Depends(db_session)):
    from src.image_gen.gemini_client import SITUACOES
    from src.llm_client import generate_json
    from src.database.repositories.theme_repo import ThemeRepository

    repo = ThemeRepository(session)
    existing_keys = list(SITUACOES.keys())
    db_themes = await repo.list_global()
    existing_keys += [t.key for t in db_themes]

    user_prompt = f"Generate exactly {req.count} diverse themes for the Mago Mestre character."
    if req.categories:
        user_prompt += f" Focus on these categories: {', '.join(req.categories)}."
    if req.avoid_existing and existing_keys:
        user_prompt += f" AVOID themes similar to these existing keys: {', '.join(existing_keys)}."
    user_prompt += " Return a JSON array of theme objects."

    try:
        raw = await asyncio.to_thread(generate_json, system_prompt=THEME_SYSTEM_PROMPT, user_message=user_prompt, tier="lite")
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

    saved_count = 0
    if req.save_to_db and valid_themes:
        for theme in valid_themes:
            if not await repo.exists(theme["key"], req.character_id):
                await repo.create({
                    "key": theme["key"], "label": theme["label"],
                    "acao": theme["acao"], "cenario": theme["cenario"],
                    "count": theme["count"], "character_id": req.character_id,
                    "is_builtin": False,
                })
                saved_count += 1

    return {"generated": len(valid_themes), "saved_to_db": saved_count, "themes": valid_themes}


@router.post("/enhance", summary="Input simples -> prompt forte via IA", tags=["Temas IA"])
async def enhance_theme_ai(req: EnhanceRequest, current_user=Depends(get_current_user), session: AsyncSession = Depends(db_session)):
    from src.image_gen.gemini_client import construir_prompt_completo
    from src.llm_client import generate_json

    user_prompt = f'Transform this simple concept into a detailed Mago Mestre theme: "{req.input_text}"'

    try:
        raw = await asyncio.to_thread(generate_json, system_prompt=ENHANCE_SYSTEM_PROMPT, user_message=user_prompt, tier="lite")
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

    saved = False
    if req.save_to_db:
        from src.database.repositories.theme_repo import ThemeRepository
        repo = ThemeRepository(session)
        existing = await repo.get_by_key(result["key"], req.character_id)
        if existing:
            await repo.update(existing.id, {
                "label": result["label"], "acao": result["acao"],
                "cenario": result["cenario"], "count": result["count"],
            })
            saved = True
        else:
            await repo.create({
                "key": result["key"], "label": result["label"],
                "acao": result["acao"], "cenario": result["cenario"],
                "count": result["count"], "character_id": req.character_id,
                "is_builtin": False,
            })
            saved = True

    preview = await asyncio.to_thread(
        construir_prompt_completo,
        situacao_key="custom", descricao_custom=result["acao"], cenario_custom=result["cenario"],
    )

    return {
        "original_input": req.input_text,
        "enhanced_theme": result,
        "saved_to_db": saved,
        "prompt_preview": preview[:500] + "..." if len(preview) > 500 else preview,
    }
