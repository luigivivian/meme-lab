"""Serializers ORM-to-dict — evita duplicacao de conversao entre rotas."""

from datetime import datetime


def content_package_to_dict(pkg) -> dict:
    """Converte ContentPackage ORM para dict de resposta."""
    return {
        "id": pkg.id,
        "phrase": pkg.phrase,
        "topic": pkg.topic,
        "source": pkg.source,
        "image_path": pkg.image_path,
        "background_path": pkg.background_path,
        "background_source": pkg.background_source,
        "caption": pkg.caption,
        "hashtags": pkg.hashtags or [],
        "quality_score": pkg.quality_score,
        "image_metadata": getattr(pkg, "image_metadata", None) or {},
        "approval_status": getattr(pkg, "approval_status", "pending"),
        "is_published": pkg.is_published,
        "published_at": pkg.published_at.isoformat() if pkg.published_at else None,
        "created_at": pkg.created_at.isoformat() if pkg.created_at else None,
        "pipeline_run_id": pkg.pipeline_run_id,
        "character_id": pkg.character_id,
        # Quick Wins: A/B testing + carousel
        "phrase_alternatives": getattr(pkg, "phrase_alternatives", None) or [],
        "carousel_slides": getattr(pkg, "carousel_slides", None) or [],
        "is_carousel": bool(getattr(pkg, "carousel_slides", None)),
    }


def content_package_summary(pkg) -> dict:
    """Versao resumida para pipeline status/sync (sem id, timestamps)."""
    return {
        "phrase": pkg.phrase,
        "image_path": pkg.image_path,
        "topic": pkg.topic,
        "caption": pkg.caption,
        "hashtags": pkg.hashtags,
        "quality_score": pkg.quality_score,
        "background_path": pkg.background_path,
        "background_source": pkg.background_source,
        "approval_status": getattr(pkg, "approval_status", "pending"),
        "image_metadata": getattr(pkg, "image_metadata", None) or {},
        "character_id": pkg.character_id,
    }


def generated_image_to_dict(img) -> dict:
    """Converte GeneratedImage ORM para dict de resposta."""
    return {
        "id": img.id,
        "filename": img.filename,
        "file_path": img.file_path,
        "image_type": img.image_type,
        "source": img.source,
        "width": img.width,
        "height": img.height,
        "file_size_bytes": img.file_size_bytes,
        "theme_key": img.theme_key,
        "prompt_used": img.prompt_used,
        "is_refined": img.is_refined,
        "refinement_passes": img.refinement_passes,
        "created_at": img.created_at.isoformat() if img.created_at else None,
        "character_id": img.character_id,
        "content_package_id": img.content_package_id,
        "batch_job_id": img.batch_job_id,
    }


def job_to_dict(job) -> dict:
    """Converte BatchJob ORM para dict de resposta."""
    return {
        "job_id": job.job_id,
        "status": job.status,
        "done": job.done,
        "failed": job.failed,
        "total": job.total,
        "results": job.results or [],
        "errors": job.errors or [],
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        "auto_refine": job.auto_refine,
        "refinement_passes": job.refinement_passes,
    }


def pipeline_run_to_dict(run, layers_cache: dict | None = None, content: list | None = None) -> dict:
    """Converte PipelineRun ORM para dict de resposta."""
    layers = layers_cache or run.layers_snapshot or {
        "L1": {"status": "idle", "detail": "", "steps": {}},
        "L2": {"status": "idle", "detail": "", "steps": {}},
        "L3": {"status": "idle", "detail": "", "steps": {}},
        "L4": {"status": "idle", "detail": "", "steps": {}},
        "L5": {"status": "idle", "detail": "", "steps": {}},
    }
    current_layer = layers.pop("current_layer", None) if isinstance(layers, dict) else None
    return {
        "run_id": run.run_id,
        "status": run.status,
        "trends_fetched": run.trends_fetched or 0,
        "work_orders": run.work_orders_emitted or 0,
        "images_generated": run.images_generated or 0,
        "packages_produced": run.packages_produced or 0,
        "errors": run.errors or [],
        "content": content or [],
        "duration_seconds": run.duration_seconds or 0,
        "layers": layers,
        "current_layer": current_layer,
    }


def pipeline_run_list_item(run) -> dict:
    """Versao resumida para listagem de pipeline runs."""
    return {
        "run_id": run.run_id,
        "status": run.status,
        "mode": run.mode,
        "requested_count": run.requested_count,
        "packages_produced": run.packages_produced or 0,
        "images_generated": run.images_generated or 0,
        "trends_fetched": run.trends_fetched or 0,
        "duration_seconds": run.duration_seconds,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "errors": run.errors or [],
    }


def character_refs_stats(char, refs_counts: dict) -> dict:
    """Monta o bloco refs de um personagem."""
    approved = refs_counts.get("approved", 0)
    return {
        "approved": approved,
        "pending": refs_counts.get("pending", 0),
        "rejected": refs_counts.get("rejected", 0),
        "min_required": char.refs_min_approved or 5,
        "ideal": char.refs_ideal_approved or 15,
        "is_ready": approved >= (char.refs_min_approved or 5),
    }


def character_to_detail(char, refs_counts: dict, themes_count: int) -> dict:
    """Converte Character ORM para dict compativel com CharacterDetail."""
    style = char.style or {}
    return {
        "slug": char.slug,
        "name": char.name,
        "handle": char.handle or "",
        "watermark": char.watermark or "",
        "status": char.status or "draft",
        "persona": {
            "system_prompt": char.system_prompt or "",
            "humor_style": char.humor_style or "",
            "tone": char.tone or "",
            "catchphrases": char.catchphrases or [],
            "rules": {
                "max_chars": char.rules_max_chars or 120,
                "forbidden": char.rules_forbidden or [],
            },
        },
        "visual": {
            "character_dna": char.character_dna or "",
            "negative_traits": char.negative_traits or "",
            "composition": char.composition or "",
            "rendering": char.rendering if char.rendering else {},
        },
        "comfyui": {
            "trigger_word": char.comfyui_trigger_word or "",
            "character_dna": char.comfyui_character_dna or "",
            "lora_path": char.comfyui_lora_path or "",
        },
        "branding": {
            "branded_hashtags": char.branded_hashtags or [],
            "caption_prompt": char.caption_prompt or "",
        },
        "style": style,
        "refs": character_refs_stats(char, refs_counts),
        "themes_count": themes_count,
    }


def scheduled_post_to_dict(post) -> dict:
    """Converte ScheduledPost ORM para dict de resposta."""
    return {
        "id": post.id,
        "content_package_id": post.content_package_id,
        "character_id": post.character_id,
        "platform": post.platform,
        "status": post.status,
        "scheduled_at": post.scheduled_at.isoformat() if post.scheduled_at else None,
        "published_at": post.published_at.isoformat() if post.published_at else None,
        "publish_result": post.publish_result,
        "retry_count": post.retry_count,
        "max_retries": post.max_retries,
        "error_message": post.error_message,
        "created_at": post.created_at.isoformat() if post.created_at else None,
        "updated_at": post.updated_at.isoformat() if post.updated_at else None,
    }


def scheduled_post_calendar_item(post) -> dict:
    """Versao resumida de ScheduledPost para a view de calendario."""
    return {
        "post_id": post.id,
        "time": post.scheduled_at.strftime("%H:%M") if post.scheduled_at else None,
        "platform": post.platform,
        "status": post.status,
        "content_package_id": post.content_package_id,
        "character_id": post.character_id,
    }


def character_to_summary(char, refs_counts: dict, themes_count: int, avatar: str | None = None) -> dict:
    """Converte Character ORM para dict compativel com CharacterSummary."""
    return {
        "slug": char.slug,
        "name": char.name,
        "handle": char.handle or "",
        "status": char.status or "draft",
        "avatar": avatar,
        "refs": character_refs_stats(char, refs_counts),
        "themes_count": themes_count,
    }
