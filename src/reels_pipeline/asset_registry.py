"""Asset registry — tracks generated images/videos with semantic embeddings for reuse.

Phase G: Scene Asset Registry with Semantic Reuse
- cosine_similarity: pure Python dot product (no numpy)
- generate_embedding: Gemini text-embedding-004
- find_similar_asset: queries all assets for user+type+character, returns best match
- register_asset: saves new asset to DB
- compute_file_hash: SHA-256
- increment_usage: bumps usage_count

All DB calls use get_session_factory() internally (independent sessions).
"""

import asyncio
import hashlib
import logging
import math
from typing import Optional

from src.database.models import SceneAsset

logger = logging.getLogger("clip-flow.reels.asset_registry")


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors. Pure Python, no numpy."""
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def _get_client():
    """Lazy-init Gemini client for embedding generation."""
    import os
    from google import genai
    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY", "")
    return genai.Client(api_key=api_key)


async def generate_embedding(text: str) -> list[float]:
    """Generate 768-dim embedding via Gemini text-embedding-004."""
    def _embed():
        client = _get_client()
        response = client.models.embed_content(
            model="text-embedding-004",
            contents=text,
        )
        return response.embeddings[0].values

    values = await asyncio.to_thread(_embed)
    return list(values)


async def find_similar_asset(
    user_id: int,
    character_id: int | None,
    asset_type: str,
    description: str,
    threshold: float = 0.85,
) -> tuple[Optional[SceneAsset], list[float]]:
    """Find a similar existing asset via cosine similarity.

    Returns (best_match_or_None, computed_embedding). The embedding is always
    returned to avoid recomputing it when registering a new asset.
    """
    from sqlalchemy import select
    from src.database.session import get_session_factory

    embedding = await generate_embedding(description)

    session_factory = get_session_factory()
    async with session_factory() as session:
        query = select(SceneAsset).where(
            SceneAsset.user_id == user_id,
            SceneAsset.asset_type == asset_type,
        )
        if character_id is not None:
            query = query.where(SceneAsset.character_id == character_id)

        result = await session.execute(query)
        assets = result.scalars().all()

    if not assets:
        return None, embedding

    best_asset = None
    best_score = 0.0

    for asset in assets:
        stored_emb = asset.embedding
        if not stored_emb or not isinstance(stored_emb, list):
            continue
        score = cosine_similarity(embedding, stored_emb)
        if score > best_score:
            best_score = score
            best_asset = asset

    if best_score >= threshold and best_asset is not None:
        logger.info(
            "Asset reuse: score=%.3f asset_id=%d type=%s desc='%s'",
            best_score, best_asset.id, asset_type, description[:60],
        )
        return best_asset, embedding

    logger.debug(
        "No similar asset: best_score=%.3f threshold=%.2f type=%s",
        best_score, threshold, asset_type,
    )
    return None, embedding


async def register_asset(
    user_id: int,
    character_id: int | None,
    asset_type: str,
    description: str,
    file_path: str,
    embedding: list[float],
    model_used: str = "",
    generation_prompt: str | None = None,
    kie_task_id: str | None = None,
    metadata_json: dict | None = None,
) -> int:
    """Register a newly generated asset in the registry. Returns asset.id."""
    from src.database.session import get_session_factory

    file_hash = compute_file_hash(file_path)

    asset = SceneAsset(
        user_id=user_id,
        character_id=character_id,
        asset_type=asset_type,
        scene_description=description,
        embedding=embedding,
        file_path=file_path,
        file_hash=file_hash,
        model_used=model_used,
        generation_prompt=generation_prompt,
        kie_task_id=kie_task_id,
        metadata_json=metadata_json,
        usage_count=0,
    )

    session_factory = get_session_factory()
    async with session_factory() as session:
        session.add(asset)
        await session.commit()
        await session.refresh(asset)
        asset_id = asset.id

    logger.info(
        "Asset registered: id=%d type=%s hash=%s desc='%s'",
        asset_id, asset_type, file_hash[:12], description[:60],
    )
    return asset_id


def compute_file_hash(file_path: str) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
    except FileNotFoundError:
        return ""
    return h.hexdigest()


async def increment_usage(asset_id: int) -> None:
    """Increment usage_count for an asset."""
    from sqlalchemy import select
    from src.database.session import get_session_factory

    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(
            select(SceneAsset).where(SceneAsset.id == asset_id)
        )
        asset = result.scalar_one_or_none()
        if asset:
            asset.usage_count = (asset.usage_count or 0) + 1
            await session.commit()
