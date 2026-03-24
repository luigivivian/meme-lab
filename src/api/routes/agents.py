"""Rotas de agentes e trends."""

import asyncio
import json
import logging
import re
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.deps import get_current_user
from src.api.registry import (
    AGENT_REGISTRY, STUB_AGENTS, WORKER_NAMES,
    check_agent_availability, get_agent_map,
)

logger = logging.getLogger("clip-flow.api")

router = APIRouter(tags=["Agentes"])


# ── Agents ───────────────────────────────────────────────────────────────────

@router.get("/agents", summary="Lista agentes e disponibilidade")
async def list_agents(current_user=Depends(get_current_user)):
    agents = []
    for name, module_path, class_name, _ in AGENT_REGISTRY:
        available = await check_agent_availability(name, module_path, class_name)
        agents.append({"name": name, "available": available, "type": "source"})

    for name, module_path, class_name in STUB_AGENTS:
        available = await check_agent_availability(name, module_path, class_name)
        agents.append({"name": name, "available": available, "type": "source"})

    for w in WORKER_NAMES:
        agents.append({"name": w, "available": True, "type": "worker"})

    return agents


@router.post("/agents/{agent_name}/fetch", summary="Fetch de um agente especifico")
async def fetch_from_agent(agent_name: str, limit: int = 10, current_user=Depends(get_current_user)):
    if agent_name in WORKER_NAMES:
        return {"agent": agent_name, "count": 0, "items": []}

    stub_names = [name for name, _, _ in STUB_AGENTS]
    if agent_name in stub_names:
        return {"agent": agent_name, "count": 0, "items": []}

    agent_map = get_agent_map()
    if agent_name not in agent_map:
        raise HTTPException(status_code=404, detail=f"Agente '{agent_name}' nao encontrado")

    module_path, class_name, is_async = agent_map[agent_name]

    try:
        import importlib
        mod = importlib.import_module(module_path)
        cls = getattr(mod, class_name)
        agent = cls()

        result = agent.fetch()
        if asyncio.iscoroutine(result):
            items = await result
        else:
            items = result
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


# ── Trends Feed ──────────────────────────────────────────────────────────────

DEFAULT_CATEGORIES = [
    {"key": "humor", "label": "😂 Humor", "keywords": ["meme", "humor", "piada", "comedia", "zoeira", "engraçado", "funny", "zueira", "rir", "hue"]},
    {"key": "cultura_pop", "label": "🎬 Cultura Pop", "keywords": ["filme", "serie", "anime", "marvel", "netflix", "disney", "game", "jogo", "cinema", "tv", "streaming"]},
    {"key": "tecnologia", "label": "💻 Tecnologia", "keywords": ["tech", "ia", "ai", "app", "celular", "iphone", "android", "software", "programacao", "code", "robot", "chatgpt"]},
    {"key": "esportes", "label": "⚽ Esportes", "keywords": ["futebol", "gol", "selecao", "copa", "brasileirao", "flamengo", "corinthians", "palmeiras", "nba", "ufc", "f1"]},
    {"key": "musica", "label": "🎵 Música", "keywords": ["musica", "show", "funk", "sertanejo", "rap", "rock", "album", "spotify", "cantora", "cantor", "clipe"]},
    {"key": "cotidiano", "label": "☕ Cotidiano", "keywords": ["segunda", "sexta", "trabalho", "cafe", "home office", "feriado", "chuva", "calor", "transito", "pix", "salario"]},
    {"key": "politica", "label": "🏛️ Política", "keywords": ["governo", "presidente", "congresso", "senado", "ministerio", "stf", "eleicao", "politica", "lei", "imposto"]},
    {"key": "ciencia", "label": "🔬 Ciência", "keywords": ["ciencia", "nasa", "espaco", "saude", "vacina", "pesquisa", "estudo", "descoberta", "medicina", "nature"]},
    {"key": "viral", "label": "🔥 Viral", "keywords": ["viral", "trending", "bombou", "trend", "challenge", "tiktok", "reels", "hype"]},
    {"key": "geral", "label": "📰 Geral", "keywords": []},
]

_user_category_prefs: dict = {
    "favorites": ["humor", "cultura_pop", "cotidiano", "viral"],
    "hidden": [],
}


def _categorize_trend(title: str) -> str:
    title_lower = title.lower()
    best_cat = "geral"
    best_score = 0
    for cat in DEFAULT_CATEGORIES:
        if not cat["keywords"]:
            continue
        score = sum(1 for kw in cat["keywords"] if kw in title_lower)
        if score > best_score:
            best_score = score
            best_cat = cat["key"]
    return best_cat


@router.get("/trends/feed", summary="Feed completo de trends", tags=["Trends"])
async def trends_feed(limit: int = Query(default=50, ge=1, le=200), current_user=Depends(get_current_user)):
    from src.pipeline.models_v2 import TrendEvent

    # Usar apenas agents ativos do feed (sem stubs)
    feed_agents = [a for a in AGENT_REGISTRY if a[0] not in ("bluesky_trends", "hackernews", "lemmy_communities")]

    async def _fetch_one(name: str, module_path: str, class_name: str, is_async: bool):
        try:
            import importlib
            mod = importlib.import_module(module_path)
            cls = getattr(mod, class_name)
            agent = cls()
            if is_async:
                items = await agent.fetch()
            else:
                items = await asyncio.to_thread(agent.fetch)
            result = []
            for item in items:
                if isinstance(item, TrendEvent):
                    result.append({
                        "title": item.title, "source": item.source.value,
                        "score": item.score, "url": item.url or "",
                        "traffic": item.traffic,
                        "category": item.category if item.category != "geral" else _categorize_trend(item.title),
                        "velocity": item.velocity, "sentiment": item.sentiment,
                        "event_id": item.event_id,
                        "fetched_at": item.fetched_at.isoformat(),
                        "_agent": name,
                    })
                else:
                    result.append({
                        "title": item.title, "source": item.source.value,
                        "score": item.score, "url": item.url or "",
                        "traffic": item.traffic,
                        "category": _categorize_trend(item.title),
                        "velocity": 0, "sentiment": "neutro", "event_id": "",
                        "fetched_at": item.fetched_at.isoformat() if hasattr(item, "fetched_at") else datetime.now().isoformat(),
                        "_agent": name,
                    })
            return name, result
        except Exception as e:
            logger.warning(f"Trends feed: agent {name} falhou: {e}")
            return name, []

    tasks = [_fetch_one(*cfg) for cfg in feed_agents]
    results = await asyncio.gather(*tasks)

    all_items = []
    agent_counts = {}
    for agent_name, items in results:
        agent_counts[agent_name] = len(items)
        all_items.extend(items)

    all_items.sort(key=lambda x: x["score"], reverse=True)

    category_counts = {}
    for item in all_items:
        cat = item["category"]
        category_counts[cat] = category_counts.get(cat, 0) + 1

    return {
        "total": len(all_items),
        "items": all_items[:limit],
        "agent_counts": agent_counts,
        "category_counts": category_counts,
    }


@router.get("/trends/search", summary="Buscar trends via Gemini", tags=["Trends"])
async def trends_search(q: str = Query(..., min_length=2, max_length=200), current_user=Depends(get_current_user)):
    import os
    from google import genai
    from google.genai import types

    api_key = os.getenv("GOOGLE_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="GOOGLE_API_KEY nao configurada")

    system_prompt = (
        "Voce e um analista de tendencias digitais especializado em cultura brasileira.\n"
        "Sua tarefa: pesquisar o que esta sendo falado sobre o TOPICO solicitado no Brasil.\n\n"
        "Retorne informacoes REAIS e ATUAIS encontradas na busca. "
        "Inclua noticias, memes, discussoes, trends de redes sociais e qualquer conteudo relevante.\n\n"
        "NUNCA incluir: conteudo ofensivo, violento ou ilegal.\n\n"
        "Responda SOMENTE com um array JSON valido, sem markdown, sem texto extra:\n"
        '[{"titulo": "topico aqui", "categoria": "geral|humor|tecnologia|entretenimento|cotidiano|cultura_pop|esportes|musica|ciencia|viral", "score": 0.0, "resumo": "breve descricao"}]'
    )

    user_prompt = (
        f"Pesquise sobre '{q}' no Brasil. O que esta sendo falado, noticiado ou viralizando "
        f"sobre este assunto? Retorne ate 15 resultados relevantes no formato JSON especificado. "
        f"Use sua busca para encontrar informacoes ATUAIS."
    )

    try:
        client = genai.Client(api_key=api_key)
        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.5-flash",
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.4,
                max_output_tokens=2048,
            ),
        )

        raw_text = ""
        try:
            parts = response.candidates[0].content.parts
            text_parts = [p.text for p in parts if hasattr(p, "text") and p.text and not getattr(p, "thought", False)]
            raw_text = "".join(text_parts)
            if not raw_text:
                raw_text = "".join(p.text for p in parts if hasattr(p, "text") and p.text)
        except (AttributeError, IndexError):
            raw_text = getattr(response, "text", "") or ""

        if not raw_text:
            return {"total": 0, "items": [], "query": q}

        text = raw_text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```\w*\n?", "", text)
            text = re.sub(r"\n?```$", "", text)
            text = text.strip()

        items_data = []
        try:
            items_data = json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\[.*\]", text, re.DOTALL)
            if match:
                try:
                    items_data = json.loads(match.group())
                except json.JSONDecodeError:
                    logger.warning(f"Trends search '{q}': JSON parse falhou")

        if not isinstance(items_data, list):
            items_data = []

        results = []
        for item in items_data:
            titulo = str(item.get("titulo", "")).strip()
            if not titulo or len(titulo) < 3:
                continue
            try:
                score = max(0.0, min(1.0, float(item.get("score", 0.75))))
            except (ValueError, TypeError):
                score = 0.75
            results.append({
                "title": titulo, "source": "gemini_trends", "score": score,
                "url": "", "traffic": None,
                "category": str(item.get("categoria", "geral")).strip(),
                "velocity": 0, "sentiment": "neutro",
                "event_id": uuid.uuid4().hex[:8],
                "fetched_at": datetime.now().isoformat(),
                "_agent": "gemini_search",
                "_resumo": str(item.get("resumo", "")).strip(),
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return {"total": len(results), "items": results, "query": q}

    except Exception as e:
        logger.error(f"Trends search falhou: {e}")
        raise HTTPException(status_code=500, detail=f"Erro na busca: {str(e)}")


@router.get("/trends/categories", summary="Categorias disponiveis e preferencias", tags=["Trends"])
async def trends_categories(current_user=Depends(get_current_user)):
    return {"categories": DEFAULT_CATEGORIES, "preferences": _user_category_prefs}


@router.post("/trends/categories/preferences", summary="Salvar preferencias", tags=["Trends"])
async def save_category_preferences(favorites: list[str] = [], hidden: list[str] = [], current_user=Depends(get_current_user)):
    _user_category_prefs["favorites"] = favorites
    _user_category_prefs["hidden"] = hidden
    return _user_category_prefs
