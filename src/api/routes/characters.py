"""Rotas de personagens (CRUD, DNA generation, validation, refs)."""

import asyncio
import logging
import random
import re
import shutil
import threading
import time
import uuid
from datetime import datetime
from io import BytesIO
from pathlib import Path

import PIL.Image
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import db_session, get_current_user, validate_filename
from src.api.models import CharacterCreateRequest, CharacterUpdateRequest
from src.api.serializers import character_to_detail, character_to_summary

logger = logging.getLogger("clip-flow.api")

router = APIRouter(prefix="/characters", tags=["Characters"])


# ── AI Prompts ──────────────────────────────────────────────────────────────

DNA_SYSTEM_PROMPT = (
    "You are a character design expert for photorealistic AI image generation.\n\n"
    "The user gives a SHORT description of a character concept in any language.\n"
    "Your job: expand it into a DETAILED visual DNA description in English that can be used "
    "as a prompt for AI image generation (Gemini Imagen, Stable Diffusion, etc).\n\n"
    "The DNA must describe:\n"
    "- Physical appearance (age, body type, skin, hair, facial features)\n"
    "- Clothing and accessories in detail\n"
    "- Props and objects they carry\n"
    "- Overall art style (photorealistic, cinematic)\n"
    "- Distinctive visual traits that make the character unique and recognizable\n\n"
    "RULES:\n"
    "- Output ONLY the DNA text, no JSON, no markdown, no explanation\n"
    "- Write in English\n"
    "- Be specific and detailed (150-300 words)\n"
    "- Use photography/cinematography language\n"
    "- The description should work as a consistent reference across multiple images\n"
)

PROFILE_SYSTEM_PROMPT = (
    "You are an expert character designer for a Brazilian meme creation platform.\n"
    "The user gives a CHARACTER NAME and a SHORT DESCRIPTION (in any language).\n"
    "Your job: generate a COMPLETE character profile as JSON.\n\n"
    "The character will be used to create viral memes for Instagram in Brazil.\n"
    "Memes are photorealistic images with funny text overlay.\n\n"
    "RULES:\n"
    "- Output ONLY valid JSON, no markdown, no explanation\n"
    "- system_prompt: write in Portuguese BR, detailed persona instructions for an LLM\n"
    "- humor_style and tone: write in Portuguese BR\n"
    "- catchphrases: 4-6 catchphrases in Portuguese BR that the character would say\n"
    "- forbidden: topics the character should NEVER touch (always include: politica, religiao, ofensivo)\n"
    "- character_dna: DETAILED visual description in ENGLISH for AI image generation (150-300 words)\n"
    "  Include: age, body type, skin, hair, facial features, clothing, accessories, props, art style\n"
    "- negative_traits: things to AVOID in image generation, in ENGLISH\n"
    "- composition: image composition notes in ENGLISH (lighting, camera angle, mood)\n"
    "- branded_hashtags: 3-5 Instagram hashtags based on the character name\n"
    "- caption_prompt: instructions in Portuguese BR for generating Instagram captions\n"
    "- watermark: the @ handle for watermark\n"
)

PROFILE_JSON_SCHEMA = (
    '{\n'
    '  "system_prompt": "string (Portuguese BR, 100-200 words, detailed persona)",\n'
    '  "humor_style": "string (Portuguese BR, 2-4 words)",\n'
    '  "tone": "string (Portuguese BR, 3-5 comma-separated adjectives)",\n'
    '  "catchphrases": ["string", "string", "..."],\n'
    '  "max_chars": 120,\n'
    '  "forbidden": ["politica", "religiao", "ofensivo", "..."],\n'
    '  "character_dna": "string (English, 150-300 words, photorealistic visual DNA)",\n'
    '  "negative_traits": "string (English, what to avoid in image gen)",\n'
    '  "composition": "string (English, lighting/camera/mood notes)",\n'
    '  "branded_hashtags": ["#hashtag1", "#hashtag2", "..."],\n'
    '  "caption_prompt": "string (Portuguese BR, instructions for caption generation)",\n'
    '  "watermark": "@handle"\n'
    '}'
)

REFERENCE_POSES = [
    "front-facing portrait, neutral expression, looking directly at camera",
    "three-quarter view, slight smile, warm lighting",
    "full body standing, staff in hand, proud posture",
    "sitting in a wooden chair, contemplative expression, relaxed",
    "walking forward, side view, cloak flowing",
    "close-up face, warm expression, gentle smile",
    "gesturing with hands while speaking, animated expression",
    "looking up at the sky, wonder expression, mystical light",
    "leaning on staff, relaxed pose, casual demeanor",
    "holding a glowing orb carefully, focused expression",
    "back view, looking over shoulder, mysterious atmosphere",
    "dramatic pose, arm raised casting spell, magical energy",
    "peaceful pose, eyes closed, meditating, serene atmosphere",
    "laughing heartily, head tilted back, joyful moment",
    "pointing forward with knowing look, wise expression",
]

# Geracao de refs em background
_ref_generation_jobs: dict[str, dict] = {}


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _get_char_with_counts(slug: str, session: AsyncSession):
    """Retorna (char, refs_counts, themes_count) ou raise 404."""
    from src.database.repositories.character_repo import CharacterRepository
    from src.database.repositories.theme_repo import ThemeRepository

    repo = CharacterRepository(session)
    char = await repo.get_by_slug(slug)
    if not char:
        raise HTTPException(status_code=404, detail=f"Personagem nao encontrado: {slug}")

    refs_counts = await repo.count_refs_by_status(char.id)
    theme_repo = ThemeRepository(session)
    themes_count = await theme_repo.count_for_character(char.id)
    return char, refs_counts, themes_count


def _generate_image_from_prompt(prompt: str) -> PIL.Image.Image | None:
    """Gera imagem via Gemini iterando modelos (extraido de 3 locais duplicados)."""
    from src.llm_client import _get_client
    from google.genai import types as genai_types
    from src.image_gen.gemini_client import MODELOS_IMAGEM

    gen_client = _get_client()
    for modelo in MODELOS_IMAGEM:
        try:
            response = gen_client.models.generate_content(
                model=modelo,
                contents=[prompt],
                config=genai_types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"],
                    temperature=0.85,
                    image_config=genai_types.ImageConfig(aspect_ratio="4:5"),
                ),
            )
            for part in response.candidates[0].content.parts:
                if hasattr(part, "inline_data") and part.inline_data:
                    return PIL.Image.open(BytesIO(part.inline_data.data))
        except Exception as e:
            msg = str(e)
            if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                time.sleep(5)
            continue
    return None


# ── CRUD ─────────────────────────────────────────────────────────────────────

@router.get("")
async def api_list_characters(
    current_user=Depends(get_current_user),
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(db_session),
):
    from src.database.repositories.character_repo import CharacterRepository
    from src.database.repositories.theme_repo import ThemeRepository

    repo = CharacterRepository(session)
    theme_repo = ThemeRepository(session)
    characters = await repo.list_all()
    if status:
        characters = [c for c in characters if c.status == status]
    total = len(characters)
    page = characters[offset:offset + limit]
    result = []
    for char in page:
        refs_counts = await repo.count_refs_by_status(char.id)
        themes_count = await theme_repo.count_for_character(char.id)
        approved_refs = await repo.get_refs(char.id, status="approved")
        avatar = approved_refs[0].filename if approved_refs else None
        result.append(character_to_summary(char, refs_counts, themes_count, avatar))
    return {"total": total, "offset": offset, "limit": limit, "characters": result}


@router.get("/{slug}")
async def api_get_character(slug: str, current_user=Depends(get_current_user), session: AsyncSession = Depends(db_session)):
    char, refs_counts, themes_count = await _get_char_with_counts(slug, session)
    return character_to_detail(char, refs_counts, themes_count)


@router.post("", status_code=201)
async def api_create_character(req: CharacterCreateRequest, current_user=Depends(get_current_user), session: AsyncSession = Depends(db_session)):
    from src.characters import slugify, create_character_dirs
    from src.database.repositories.character_repo import CharacterRepository
    from src.database.repositories.theme_repo import ThemeRepository

    slug = slugify(req.name)
    if not slug:
        raise HTTPException(status_code=400, detail="Nome invalido")

    repo = CharacterRepository(session)
    if await repo.exists(slug):
        raise HTTPException(status_code=409, detail=f"Personagem '{slug}' ja existe")

    create_character_dirs(slug)

    style_data = req.style.model_dump() if req.style else {}
    data = {
        "slug": slug, "name": req.name,
        "handle": req.handle,
        "watermark": req.watermark or req.handle or "",
        "status": "draft",
        "system_prompt": req.persona.system_prompt,
        "humor_style": req.persona.humor_style,
        "tone": req.persona.tone,
        "catchphrases": req.persona.catchphrases,
        "rules_max_chars": req.persona.rules.get("max_chars", 120),
        "rules_forbidden": req.persona.rules.get("forbidden", []),
        "character_dna": req.visual.character_dna,
        "negative_traits": req.visual.negative_traits,
        "composition": req.visual.composition,
        "rendering": req.visual.rendering if hasattr(req.visual, 'rendering') and req.visual.rendering else {},
        "comfyui_trigger_word": req.comfyui.trigger_word,
        "comfyui_character_dna": req.comfyui.character_dna,
        "comfyui_lora_path": req.comfyui.lora_path,
        "branded_hashtags": req.branding.branded_hashtags,
        "caption_prompt": req.branding.caption_prompt,
        "style": style_data,
    }

    char = await repo.create(data)
    logger.info(f"Personagem criado: {slug} (id={char.id})")

    theme_repo = ThemeRepository(session)
    refs_counts = await repo.count_refs_by_status(char.id)
    themes_count = await theme_repo.count_for_character(char.id)
    return character_to_detail(char, refs_counts, themes_count)


@router.put("/{slug}")
async def api_update_character(slug: str, req: CharacterUpdateRequest, current_user=Depends(get_current_user), session: AsyncSession = Depends(db_session)):
    from src.database.repositories.character_repo import CharacterRepository
    from src.database.converters import api_update_to_orm_dict

    char, refs_counts, themes_count = await _get_char_with_counts(slug, session)

    if req.status is not None and req.status not in ("draft", "refining", "ready"):
        raise HTTPException(status_code=400, detail="Status invalido")

    raw_updates = req.model_dump(exclude_none=True)
    orm_updates = api_update_to_orm_dict(raw_updates)

    if orm_updates:
        repo = CharacterRepository(session)
        char = await repo.update(slug, orm_updates)
        from src.database.repositories.theme_repo import ThemeRepository
        refs_counts = await repo.count_refs_by_status(char.id)
        theme_repo = ThemeRepository(session)
        themes_count = await theme_repo.count_for_character(char.id)

    return character_to_detail(char, refs_counts, themes_count)


@router.delete("/{slug}")
async def api_delete_character(slug: str, current_user=Depends(get_current_user), session: AsyncSession = Depends(db_session)):
    from src.characters import DEFAULT_CHARACTER
    from src.database.repositories.character_repo import CharacterRepository

    if slug == DEFAULT_CHARACTER:
        raise HTTPException(status_code=400, detail="Nao e possivel deletar o personagem padrao")

    repo = CharacterRepository(session)
    deleted = await repo.soft_delete(slug)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Personagem nao encontrado: {slug}")
    return {"deleted": slug}


# ── DNA / Profile Generation ────────────────────────────────────────────────

@router.post("/generate-dna", summary="Gera DNA visual via Gemini")
async def generate_character_dna(body: dict, current_user=Depends(get_current_user)):
    from src.llm_client import generate

    description = body.get("description", "").strip()
    if not description:
        raise HTTPException(status_code=400, detail="Campo 'description' obrigatorio")

    user_prompt = (
        f"Expand this short character concept into a detailed visual DNA:\n\n"
        f'"{description}"\n\n'
        f"Write a comprehensive, specific visual description that could be used "
        f"to generate consistent photorealistic images of this character."
    )

    try:
        dna = await asyncio.to_thread(generate, system_prompt=DNA_SYSTEM_PROMPT, user_message=user_prompt, tier="lite")
        return {"dna": dna.strip()}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erro ao gerar DNA via Gemini: {e}")


@router.post("/generate-profile", summary="Gera perfil completo via Gemini")
async def generate_character_profile(body: dict, current_user=Depends(get_current_user)):
    import json
    from src.llm_client import generate_json

    name = body.get("name", "").strip()
    description = body.get("description", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Campo 'name' obrigatorio")
    if not description:
        raise HTTPException(status_code=400, detail="Campo 'description' obrigatorio")

    handle = body.get("handle", "").strip()
    user_prompt = (
        f"Generate a complete character profile for a Brazilian meme character.\n\n"
        f"Character name: {name}\nHandle: {handle or '(generate one based on the name)'}\n"
        f"Description: {description}\n\n"
        f"Return a JSON object with this exact schema:\n{PROFILE_JSON_SCHEMA}"
    )

    try:
        raw = await asyncio.to_thread(generate_json, system_prompt=PROFILE_SYSTEM_PROMPT, user_message=user_prompt, max_tokens=4096, tier="lite")
        profile = json.loads(raw)
        return {"profile": profile}
    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail="Gemini retornou JSON invalido")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erro ao gerar perfil via Gemini: {e}")


# ── Rendering Presets ────────────────────────────────────────────────────────

@router.get("/rendering-presets", summary="Listar presets de rendering", tags=["Rendering"])
async def get_rendering_presets(current_user=Depends(get_current_user)):
    from src.image_gen.gemini_client import ART_STYLE_PRESETS, LIGHTING_PRESETS, CAMERA_PRESETS
    return {
        "art_style": {k: {"label": v["label"], "prompt": v["prompt"]} for k, v in ART_STYLE_PRESETS.items()},
        "lighting": {k: {"label": v["label"], "prompt": v["prompt"]} for k, v in LIGHTING_PRESETS.items()},
        "camera": {k: {"label": v["label"], "prompt": v["prompt"]} for k, v in CAMERA_PRESETS.items()},
    }


# ── Validation & Testing ────────────────────────────────────────────────────

@router.get("/{slug}/validate", summary="Checklist de prontidao", tags=["Validation"])
async def validate_character(slug: str, current_user=Depends(get_current_user), session: AsyncSession = Depends(db_session)):
    from src.database.repositories.character_repo import CharacterRepository
    from src.database.repositories.theme_repo import ThemeRepository
    from src.database.converters import orm_to_character_config

    repo = CharacterRepository(session)
    char = await repo.get_by_slug(slug)
    if not char:
        raise HTTPException(status_code=404, detail=f"Personagem nao encontrado: {slug}")

    config = orm_to_character_config(char)
    refs_stats = config.refs_stats()
    theme_repo = ThemeRepository(session)
    effective_themes = await theme_repo.list_effective(char.id)
    effective_keys = {t.key for t in effective_themes}
    from src.image_gen.gemini_client import SITUACOES
    all_keys = effective_keys | set(SITUACOES.keys())
    themes_count = len(all_keys)

    checks = []

    # Identidade
    for item, val in [("Nome definido", char.name), ("Handle definido", char.handle), ("Watermark definido", char.watermark)]:
        checks.append({"area": "identidade", "item": item, "ok": bool(val and val.strip()), "detail": val or "vazio"})

    # Persona
    checks.append({"area": "persona", "item": "System prompt definido", "ok": bool(char.system_prompt and len(char.system_prompt.strip()) >= 50), "detail": f"{len(char.system_prompt)} chars" if char.system_prompt else "vazio"})
    checks.append({"area": "persona", "item": "Estilo de humor definido", "ok": bool(char.humor_style and char.humor_style.strip()), "detail": char.humor_style or "vazio"})
    checks.append({"area": "persona", "item": "Tom definido", "ok": bool(char.tone and char.tone.strip()), "detail": char.tone or "vazio"})
    checks.append({"area": "persona", "item": "Bordoes (min 2)", "ok": len(char.catchphrases or []) >= 2, "detail": f"{len(char.catchphrases or [])} bordoes"})
    checks.append({"area": "persona", "item": "Topicos proibidos definidos", "ok": len(char.rules_forbidden or []) >= 1, "detail": f"{len(char.rules_forbidden or [])} regras"})

    # Visual
    checks.append({"area": "visual", "item": "DNA visual definido (min 100 chars)", "ok": bool(char.character_dna and len(char.character_dna.strip()) >= 100), "detail": f"{len(char.character_dna)} chars" if char.character_dna else "vazio"})
    checks.append({"area": "visual", "item": "Negative traits definidos", "ok": bool(char.negative_traits and char.negative_traits.strip()), "detail": f"{len(char.negative_traits)} chars" if char.negative_traits else "vazio"})
    checks.append({"area": "visual", "item": "Notas de composicao", "ok": bool(char.composition and char.composition.strip()), "detail": f"{len(char.composition)} chars" if char.composition else "vazio"})

    # Refs
    checks.append({"area": "refs", "item": f"Refs aprovadas (min {char.refs_min_approved})", "ok": refs_stats["approved"] >= char.refs_min_approved, "detail": f"{refs_stats['approved']}/{char.refs_min_approved}"})
    checks.append({"area": "refs", "item": f"Refs ideal ({char.refs_ideal_approved})", "ok": refs_stats["approved"] >= char.refs_ideal_approved, "detail": f"{refs_stats['approved']}/{char.refs_ideal_approved}"})

    # Branding
    checks.append({"area": "branding", "item": "Hashtags branded (min 1)", "ok": len(char.branded_hashtags or []) >= 1, "detail": f"{len(char.branded_hashtags or [])} hashtags"})
    checks.append({"area": "branding", "item": "Caption prompt definido", "ok": bool(char.caption_prompt and len(char.caption_prompt.strip()) >= 20), "detail": f"{len(char.caption_prompt)} chars" if char.caption_prompt else "vazio"})

    # Temas
    checks.append({"area": "temas", "item": "Temas visuais configurados (min 3)", "ok": themes_count >= 3, "detail": f"{themes_count} temas"})

    # Score
    areas = {}
    for c in checks:
        area = c["area"]
        if area not in areas:
            areas[area] = {"total": 0, "ok": 0}
        areas[area]["total"] += 1
        if c["ok"]:
            areas[area]["ok"] += 1

    area_scores = {k: round(v["ok"] / v["total"] * 100) for k, v in areas.items()}
    total_ok = sum(1 for c in checks if c["ok"])
    total_checks = len(checks)
    overall_score = round(total_ok / total_checks * 100) if total_checks else 0

    is_ready = all(
        c["ok"] for c in checks
        if c["item"] not in [f"Refs ideal ({char.refs_ideal_approved})", "Temas visuais configurados (min 3)"]
    )

    return {
        "slug": slug, "status": char.status, "checks": checks,
        "area_scores": area_scores, "overall_score": overall_score,
        "total_checks": total_checks, "total_ok": total_ok,
        "is_production_ready": is_ready,
    }


@router.post("/{slug}/test-phrases", summary="Gerar frases de teste", tags=["Validation"])
async def test_character_phrases(slug: str, body: dict | None = None, current_user=Depends(get_current_user), session: AsyncSession = Depends(db_session)):
    from src.llm_client import generate
    from src.database.repositories.character_repo import CharacterRepository

    repo = CharacterRepository(session)
    char = await repo.get_by_slug(slug)
    if not char:
        raise HTTPException(status_code=404, detail=f"Personagem nao encontrado: {slug}")
    if not char.system_prompt:
        raise HTTPException(status_code=400, detail="Personagem sem system prompt definido")

    topic = (body or {}).get("topic", "segunda-feira")
    count = min((body or {}).get("count", 3), 5)

    user_msg = f"Gere {count} frases sobre o tema: {topic}"
    if char.rules_max_chars:
        user_msg += f"\nMaximo {char.rules_max_chars} caracteres por frase."

    try:
        raw = await asyncio.to_thread(generate, system_prompt=char.system_prompt, user_message=user_msg, max_tokens=2048, tier="lite")
        phrases = [line.strip() for line in raw.strip().splitlines() if line.strip()]
        validation = []
        for p in phrases:
            clean = p.lstrip("0123456789.-) ").strip('"').strip()
            if not clean:
                continue
            over = len(clean) > char.rules_max_chars if char.rules_max_chars else False
            has_forbidden = [w for w in (char.rules_forbidden or []) if w.lower() in clean.lower()]
            validation.append({
                "phrase": clean, "chars": len(clean),
                "over_limit": over, "forbidden_found": has_forbidden,
                "ok": not over and not has_forbidden,
            })

        return {
            "slug": slug, "topic": topic, "phrases": validation,
            "persona_used": {"humor_style": char.humor_style, "tone": char.tone, "max_chars": char.rules_max_chars},
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erro ao gerar frases: {e}")


@router.post("/{slug}/test-visual", summary="Gerar imagem de teste", tags=["Validation"])
async def test_character_visual(slug: str, body: dict | None = None, current_user=Depends(get_current_user), session: AsyncSession = Depends(db_session)):
    from src.database.repositories.character_repo import CharacterRepository
    from src.database.converters import orm_to_character_config

    repo = CharacterRepository(session)
    char = await repo.get_by_slug(slug)
    if not char:
        raise HTTPException(status_code=404, detail=f"Personagem nao encontrado: {slug}")
    if not char.character_dna:
        raise HTTPException(status_code=400, detail="Personagem sem DNA visual definido")

    pose = (body or {}).get("pose", "front-facing portrait, neutral expression, looking directly at camera")
    config = orm_to_character_config(char)
    output_path = config.pending_refs_dir
    output_path.mkdir(parents=True, exist_ok=True)

    from src.image_gen.gemini_client import build_character_image_prompt
    prompt = build_character_image_prompt(
        character_dna=char.character_dna,
        negative_traits=char.negative_traits or "",
        composition=char.composition or "",
        rendering=char.rendering if char.rendering else None,
        pose=pose,
    )

    try:
        imagem = await asyncio.to_thread(_generate_image_from_prompt, prompt)
        if not imagem:
            raise HTTPException(status_code=502, detail="Gemini nao retornou imagem")

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"test_{slug}_{ts}.png"
        out = output_path / filename
        await asyncio.to_thread(imagem.save, out, "PNG")

        return {
            "success": True, "filename": filename, "slug": slug,
            "pose": pose, "image_url": f"/characters/{slug}/refs/image/{filename}",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erro ao gerar imagem: {e}")


@router.post("/{slug}/test-compose", summary="Gerar meme completo de teste", tags=["Validation"])
async def test_character_compose(slug: str, body: dict | None = None, current_user=Depends(get_current_user), session: AsyncSession = Depends(db_session)):
    from src.image_gen.gemini_client import GeminiImageClient, build_character_image_prompt, SITUACOES, _selecionar_referencias, _pil_para_part
    from src.image_maker import create_image
    from src.llm_client import generate
    from src.database.repositories.character_repo import CharacterRepository
    from src.database.converters import orm_to_character_config
    from config import OUTPUT_DIR

    repo = CharacterRepository(session)
    char = await repo.get_by_slug(slug)
    if not char:
        raise HTTPException(status_code=404, detail=f"Personagem nao encontrado: {slug}")
    if not char.system_prompt:
        raise HTTPException(status_code=400, detail="Personagem sem system prompt")
    if not char.character_dna:
        raise HTTPException(status_code=400, detail="Personagem sem DNA visual")

    topic = (body or {}).get("topic", "segunda-feira")
    situacao = (body or {}).get("situacao", "sabedoria")

    # 1) Gerar frase
    try:
        user_msg = f"Gere 1 frase sobre o tema: {topic}"
        if char.rules_max_chars:
            user_msg += f"\nMaximo {char.rules_max_chars} caracteres."
        raw = await asyncio.to_thread(generate, system_prompt=char.system_prompt, user_message=user_msg, max_tokens=256, tier="lite")
        phrase = raw.strip().splitlines()[0].strip().lstrip("0123456789.-) ").strip('"').strip()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erro ao gerar frase: {e}")

    # 2) Gerar background
    config = orm_to_character_config(char)
    ref_dir = config.approved_refs_dir if config.approved_refs_dir.exists() and any(config.approved_refs_dir.iterdir()) else None

    sit = SITUACOES.get(situacao, {})
    sit_pose = sit.get("acao", "standing pose holding staff, wise expression")
    sit_cenario = sit.get("cenario", "dark moody medieval forest with golden atmospheric lighting")

    compose_prompt = build_character_image_prompt(
        character_dna=char.character_dna,
        negative_traits=char.negative_traits or "",
        composition=char.composition or "",
        rendering=char.rendering if char.rendering else None,
        pose=sit_pose, cenario=sit_cenario, phrase_context=phrase,
    )

    bg_path = None
    try:
        client = GeminiImageClient(
            reference_dir=ref_dir, output_dir=OUTPUT_DIR,
            n_referencias=min(5, len(list(config.approved_refs_dir.glob("*.png"))) if ref_dir else 0),
        )
        if ref_dir and client.is_available():
            client._load_referencias()
            refs = _selecionar_referencias(client._referencias, n=client.n_referencias)
            partes = [_pil_para_part(img) for img in refs]
            partes.append("These are reference images of the character. Replicate EXACTLY.")
            partes.append(compose_prompt)
            imagem = client._tentar_modelos(partes, client.temperatura)
            if imagem:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                bg_path = str(OUTPUT_DIR / f"compose_bg_{slug}_{ts}.png")
                Path(bg_path).parent.mkdir(parents=True, exist_ok=True)
                await asyncio.to_thread(imagem.save, bg_path, "PNG")
        if not bg_path:
            imagem = await asyncio.to_thread(_generate_image_from_prompt, compose_prompt)
            if imagem:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                bg_path = str(OUTPUT_DIR / f"compose_bg_{slug}_{ts}.png")
                Path(bg_path).parent.mkdir(parents=True, exist_ok=True)
                await asyncio.to_thread(imagem.save, bg_path, "PNG")
    except Exception as e:
        logger.warning(f"Fallback para background estatico: {e}")

    if not bg_path:
        from config import BACKGROUNDS_DIR
        bgs = list(BACKGROUNDS_DIR.rglob("*.png")) + list(BACKGROUNDS_DIR.rglob("*.jpg"))
        if bgs:
            bg_path = str(random.choice(bgs))
        else:
            raise HTTPException(status_code=500, detail="Nenhum background disponivel")

    # 3) Composicao
    try:
        image_path = await asyncio.to_thread(create_image, phrase, bg_path)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erro na composicao: {e}")

    filename = Path(image_path).name
    return {
        "success": True, "slug": slug, "phrase": phrase,
        "topic": topic, "situacao": situacao,
        "background_path": bg_path, "image_path": image_path,
        "image_url": f"/drive/images/{filename}",
    }


# ── Refs Management ──────────────────────────────────────────────────────────

def _generate_refs_worker(
    job_id: str, slug: str, character_dna: str, negative_traits: str,
    composition: str, rendering: dict | None,
    approved_refs_dir: Path, pending_refs_dir: Path, batch_size: int,
):
    """Worker que gera batch de refs via Gemini em thread separada."""
    from src.image_gen.gemini_client import GeminiImageClient, build_character_image_prompt

    job = _ref_generation_jobs[job_id]
    job["status"] = "running"
    job["total"] = batch_size

    ref_dir = approved_refs_dir if approved_refs_dir.exists() and any(approved_refs_dir.iterdir()) else None
    client = GeminiImageClient(
        reference_dir=ref_dir, output_dir=pending_refs_dir,
        n_referencias=min(5, len(list(approved_refs_dir.glob("*.png"))) if ref_dir else 0),
    )

    poses = REFERENCE_POSES[:batch_size]
    for i, pose in enumerate(poses):
        try:
            prompt = build_character_image_prompt(
                character_dna=character_dna, negative_traits=negative_traits,
                composition=composition, rendering=rendering,
                pose=pose, cenario="neutral studio background, soft lighting",
            )

            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            nome = f"ref_{slug}_{i+1:02d}_{ts}"

            if ref_dir and client._referencias:
                gen_result = client.generate_image(
                    situacao_key="custom",
                    descricao_custom=pose,
                    cenario_custom="neutral studio background, soft lighting",
                    nome_arquivo=nome,
                )
                path = gen_result.path if gen_result else None
            else:
                imagem = _generate_image_from_prompt(prompt)
                if imagem:
                    pending_refs_dir.mkdir(parents=True, exist_ok=True)
                    out_path = pending_refs_dir / f"{nome}.png"
                    imagem.save(out_path, "PNG")
                    path = str(out_path)
                else:
                    path = None

            if path:
                job["done"] += 1
                job["results"].append({"filename": Path(path).name, "pose": pose, "index": i + 1})
            else:
                job["failed"] += 1
                job["errors"].append(f"Pose {i+1}: geracao falhou")
        except Exception as e:
            job["failed"] += 1
            job["errors"].append(f"Pose {i+1}: {str(e)}")

        if i < len(poses) - 1:
            time.sleep(10)

    job["status"] = "completed"
    job["finished_at"] = datetime.now().isoformat()
    logger.info(f"Refs job {job_id}: {job['done']} OK / {job['failed']} falhas")


@router.post("/{slug}/refs/generate", summary="Gerar batch de refs via Gemini", tags=["Refs"])
async def generate_refs(slug: str, body: dict | None = None, current_user=Depends(get_current_user), session: AsyncSession = Depends(db_session)):
    from src.characters import create_character_dirs
    from src.database.repositories.character_repo import CharacterRepository
    from src.database.converters import orm_to_character_config

    repo = CharacterRepository(session)
    char = await repo.get_by_slug(slug)
    if not char:
        raise HTTPException(status_code=404, detail=f"Personagem nao encontrado: {slug}")
    if not char.character_dna:
        raise HTTPException(status_code=400, detail="Personagem sem DNA visual definido")

    config = orm_to_character_config(char)
    batch_size = min((body or {}).get("batch_size", config.refs_batch_size), 15)

    job_id = uuid.uuid4().hex[:8]
    _ref_generation_jobs[job_id] = {
        "job_id": job_id, "slug": slug, "status": "queued",
        "done": 0, "failed": 0, "total": batch_size,
        "results": [], "errors": [],
        "created_at": datetime.now().isoformat(), "finished_at": None,
    }

    if char.status == "draft":
        await repo.update(slug, {"status": "refining"})

    create_character_dirs(slug)

    threading.Thread(
        target=_generate_refs_worker,
        args=(
            job_id, slug, config.character_dna, config.negative_traits,
            config.composition, char.rendering if char.rendering else None,
            config.approved_refs_dir, config.pending_refs_dir, batch_size,
        ),
        daemon=True,
    ).start()

    return _ref_generation_jobs[job_id]


@router.get("/{slug}/refs/generate/status", summary="Status da geracao de refs", tags=["Refs"])
async def refs_generate_status(slug: str, current_user=Depends(get_current_user)):
    jobs = [j for j in _ref_generation_jobs.values() if j["slug"] == slug]
    if not jobs:
        return {"status": "none", "message": "Nenhuma geracao em andamento"}
    return max(jobs, key=lambda j: j["created_at"])


@router.get("/{slug}/refs", summary="Lista refs do personagem", tags=["Refs"])
async def list_refs(slug: str, current_user=Depends(get_current_user), session: AsyncSession = Depends(db_session)):
    from src.database.repositories.character_repo import CharacterRepository
    from src.database.converters import orm_to_character_config

    repo = CharacterRepository(session)
    char = await repo.get_by_slug(slug)
    if not char:
        raise HTTPException(status_code=404, detail=f"Personagem nao encontrado: {slug}")

    config = orm_to_character_config(char)

    def _ref_info(p: Path, status: str) -> dict:
        stat = p.stat()
        return {
            "filename": p.name, "status": status,
            "size_kb": round(stat.st_size / 1024, 1),
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        }

    refs = []
    for p in config.approved_refs():
        refs.append(_ref_info(p, "approved"))
    for p in config.pending_refs():
        refs.append(_ref_info(p, "pending"))
    for p in config.rejected_refs():
        refs.append(_ref_info(p, "rejected"))

    return {"slug": slug, "stats": config.refs_stats(), "refs": refs}


@router.get("/{slug}/refs/image/{filename}", summary="Serve imagem de ref", tags=["Refs"])
async def serve_ref_image(slug: str, filename: str, current_user=Depends(get_current_user), session: AsyncSession = Depends(db_session)):
    from src.database.repositories.character_repo import CharacterRepository
    from src.database.converters import orm_to_character_config

    validate_filename(filename)
    repo = CharacterRepository(session)
    char = await repo.get_by_slug(slug)
    if not char:
        raise HTTPException(status_code=404, detail=f"Personagem nao encontrado: {slug}")

    config = orm_to_character_config(char)
    for folder in [config.approved_refs_dir, config.pending_refs_dir, config.rejected_refs_dir]:
        path = folder / filename
        if path.exists():
            return FileResponse(str(path), media_type="image/png", filename=filename)

    raise HTTPException(status_code=404, detail=f"Ref '{filename}' nao encontrada")


def _move_ref(config, filename: str, target_dir: Path, search_dirs: list[Path]):
    """Move ref para target_dir. Retorna True se movido."""
    for folder in search_dirs:
        path = folder / filename
        if path.exists():
            target_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(path), str(target_dir / filename))
            return True
    return False


@router.post("/{slug}/refs/{filename}/approve", summary="Aprovar ref", tags=["Refs"])
async def approve_ref(slug: str, filename: str, current_user=Depends(get_current_user), session: AsyncSession = Depends(db_session)):
    from src.database.repositories.character_repo import CharacterRepository
    from src.database.converters import orm_to_character_config

    validate_filename(filename)
    repo = CharacterRepository(session)
    char = await repo.get_by_slug(slug)
    if not char:
        raise HTTPException(status_code=404, detail=f"Personagem nao encontrado: {slug}")

    config = orm_to_character_config(char)

    if (config.approved_refs_dir / filename).exists():
        return {"status": "already_approved", "filename": filename}

    moved = _move_ref(config, filename, config.approved_refs_dir, [config.pending_refs_dir, config.rejected_refs_dir])
    if not moved:
        raise HTTPException(status_code=404, detail=f"Ref '{filename}' nao encontrada")

    config_updated = orm_to_character_config(char)
    if config_updated.is_ready() and char.status != "ready":
        await repo.update(slug, {"status": "ready"})
    return {"status": "approved", "filename": filename, "refs_stats": config_updated.refs_stats()}


@router.post("/{slug}/refs/{filename}/reject", summary="Rejeitar ref", tags=["Refs"])
async def reject_ref(slug: str, filename: str, current_user=Depends(get_current_user), session: AsyncSession = Depends(db_session)):
    from src.database.repositories.character_repo import CharacterRepository
    from src.database.converters import orm_to_character_config

    validate_filename(filename)
    repo = CharacterRepository(session)
    char = await repo.get_by_slug(slug)
    if not char:
        raise HTTPException(status_code=404, detail=f"Personagem nao encontrado: {slug}")

    config = orm_to_character_config(char)

    if (config.rejected_refs_dir / filename).exists():
        return {"status": "already_rejected", "filename": filename}

    moved = _move_ref(config, filename, config.rejected_refs_dir, [config.pending_refs_dir, config.approved_refs_dir])
    if not moved:
        raise HTTPException(status_code=404, detail=f"Ref '{filename}' nao encontrada")

    config_updated = orm_to_character_config(char)
    if not config_updated.is_ready() and char.status == "ready":
        await repo.update(slug, {"status": "refining"})
    return {"status": "rejected", "filename": filename, "refs_stats": config_updated.refs_stats()}


@router.delete("/{slug}/refs/{filename}", summary="Deletar ref", tags=["Refs"])
async def delete_ref(slug: str, filename: str, current_user=Depends(get_current_user), session: AsyncSession = Depends(db_session)):
    from src.database.repositories.character_repo import CharacterRepository
    from src.database.converters import orm_to_character_config

    validate_filename(filename)
    repo = CharacterRepository(session)
    char = await repo.get_by_slug(slug)
    if not char:
        raise HTTPException(status_code=404, detail=f"Personagem nao encontrado: {slug}")

    config = orm_to_character_config(char)
    deleted = False
    for folder in [config.pending_refs_dir, config.approved_refs_dir, config.rejected_refs_dir]:
        path = folder / filename
        if path.exists():
            path.unlink()
            deleted = True
            break

    if not deleted:
        raise HTTPException(status_code=404, detail=f"Ref '{filename}' nao encontrada")

    config_updated = orm_to_character_config(char)
    if not config_updated.is_ready() and char.status == "ready":
        await repo.update(slug, {"status": "refining"})
    return {"deleted": filename, "refs_stats": config_updated.refs_stats()}


@router.post("/{slug}/refs/upload", summary="Upload manual de refs", tags=["Refs"])
async def upload_refs(slug: str, files: list[UploadFile], current_user=Depends(get_current_user), session: AsyncSession = Depends(db_session)):
    from src.database.repositories.character_repo import CharacterRepository
    from src.database.converters import orm_to_character_config

    repo = CharacterRepository(session)
    char = await repo.get_by_slug(slug)
    if not char:
        raise HTTPException(status_code=404, detail=f"Personagem nao encontrado: {slug}")

    config = orm_to_character_config(char)
    config.pending_refs_dir.mkdir(parents=True, exist_ok=True)
    uploaded = []

    for file in files:
        if not file.content_type or not file.content_type.startswith("image/"):
            continue
        safe_name = re.sub(r"[^a-zA-Z0-9_.-]", "_", file.filename or "upload.png")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest_name = f"upload_{ts}_{safe_name}"
        dest = config.pending_refs_dir / dest_name
        content = await file.read()
        dest.write_bytes(content)
        uploaded.append(dest_name)

    return {"uploaded": len(uploaded), "files": uploaded, "refs_stats": config.refs_stats()}
