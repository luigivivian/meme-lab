"""ORM models — 16 tabelas do banco de dados clip-flow (MySQL + SQLite)."""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, TimestampMixin


# ============================================================
# 1. characters
# ============================================================

class Character(TimestampMixin, Base):
    __tablename__ = "characters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    handle: Mapped[str] = mapped_column(String(100), default="", server_default="")
    watermark: Mapped[str] = mapped_column(String(200), default="", server_default="")
    status: Mapped[str] = mapped_column(String(20), default="draft", server_default="draft")

    # Persona (LLM) — TEXT/JSON sem server_default (MySQL nao suporta)
    system_prompt: Mapped[str] = mapped_column(Text, default="", nullable=False)
    humor_style: Mapped[str] = mapped_column(String(200), default="", server_default="")
    tone: Mapped[str] = mapped_column(String(200), default="", server_default="")
    catchphrases: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    rules_max_chars: Mapped[int] = mapped_column(Integer, default=120, server_default="120")
    rules_forbidden: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    # Visual DNA (Gemini Image)
    character_dna: Mapped[str] = mapped_column(Text, default="", nullable=False)
    negative_traits: Mapped[str] = mapped_column(Text, default="", nullable=False)
    composition: Mapped[str] = mapped_column(Text, default="", nullable=False)

    # Visual DNA (ComfyUI)
    comfyui_trigger_word: Mapped[str] = mapped_column(String(100), default="", server_default="")
    comfyui_character_dna: Mapped[str] = mapped_column(Text, default="", nullable=False)
    comfyui_lora_path: Mapped[str] = mapped_column(String(500), default="", server_default="")

    # Branding
    branded_hashtags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    caption_prompt: Mapped[str] = mapped_column(Text, default="", nullable=False)

    # Rendering (estilo artistico, iluminacao, camera) — JSON
    rendering: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # Style (composicao Pillow) — JSON serializado
    style: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # Refs config
    refs_min_approved: Mapped[int] = mapped_column(Integer, default=5, server_default="5")
    refs_ideal_approved: Mapped[int] = mapped_column(Integer, default=15, server_default="15")
    refs_batch_size: Mapped[int] = mapped_column(Integer, default=15, server_default="15")
    refs_priority: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    # Soft delete
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")

    # Owner (multi-tenant, per D-07/D-09)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )

    # Relationships
    owner: Mapped["User"] = relationship(back_populates="characters")
    refs: Mapped[list["CharacterRef"]] = relationship(
        back_populates="character", cascade="all, delete-orphan"
    )
    themes: Mapped[list["Theme"]] = relationship(
        back_populates="character", cascade="all, delete-orphan"
    )
    pipeline_runs: Mapped[list["PipelineRun"]] = relationship(back_populates="character")
    content_packages: Mapped[list["ContentPackage"]] = relationship(back_populates="character")
    batch_jobs: Mapped[list["BatchJob"]] = relationship(back_populates="character")
    generated_images: Mapped[list["GeneratedImage"]] = relationship(back_populates="character")
    scheduled_posts: Mapped[list["ScheduledPost"]] = relationship(back_populates="character")

    __table_args__ = (
        Index("idx_characters_status", "status"),
        Index("idx_characters_is_deleted", "is_deleted"),
    )


# ============================================================
# 2. character_refs
# ============================================================

class CharacterRef(TimestampMixin, Base):
    __tablename__ = "character_refs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    character_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("characters.id", ondelete="CASCADE"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(300), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", server_default="pending")
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="generated", server_default="generated")
    generation_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationship
    character: Mapped["Character"] = relationship(back_populates="refs")

    __table_args__ = (
        Index("idx_refs_character_id", "character_id"),
        Index("idx_refs_status", "status"),
        Index("idx_refs_character_status", "character_id", "status"),
    )


# ============================================================
# 3. themes
# ============================================================

class Theme(TimestampMixin, Base):
    __tablename__ = "themes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    character_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("characters.id", ondelete="CASCADE"), nullable=True
    )
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    label: Mapped[str] = mapped_column(String(200), default="", server_default="")
    acao: Mapped[str] = mapped_column(Text, nullable=False)
    cenario: Mapped[str] = mapped_column(Text, nullable=False)
    count: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")

    # Video prompt improvement (Phase 999.1, per D-03)
    video_prompt_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Owner (multi-tenant, per D-03)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )

    # Relationships
    character: Mapped[Optional["Character"]] = relationship(back_populates="themes")
    owner: Mapped[Optional["User"]] = relationship("User")

    __table_args__ = (
        UniqueConstraint("character_id", "key", name="uq_themes_character_key"),
        Index("idx_themes_character_id", "character_id"),
        Index("idx_themes_key", "key"),
        Index("idx_themes_user_id", "user_id"),
    )


# ============================================================
# 4. pipeline_runs
# ============================================================

class PipelineRun(TimestampMixin, Base):
    __tablename__ = "pipeline_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    character_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("characters.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued", server_default="queued")
    mode: Mapped[str] = mapped_column(String(20), default="agents", server_default="agents")

    # Parametros do run
    requested_count: Mapped[int] = mapped_column(Integer, default=5, server_default="5")
    phrases_per_topic: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    use_comfyui: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    use_gemini_image: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    use_phrase_context: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    theme_tags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    # Resultados
    trends_fetched: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    trend_events_queued: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    work_orders_emitted: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    images_generated: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    packages_produced: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Snapshots — JSON sem server_default (MySQL)
    layers_snapshot: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    errors: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    character: Mapped["Character"] = relationship(back_populates="pipeline_runs")
    trend_events: Mapped[list["TrendEvent"]] = relationship(
        back_populates="pipeline_run", cascade="all, delete-orphan"
    )
    work_orders: Mapped[list["WorkOrder"]] = relationship(
        back_populates="pipeline_run", cascade="all, delete-orphan"
    )
    content_packages: Mapped[list["ContentPackage"]] = relationship(
        back_populates="pipeline_run", cascade="all, delete-orphan"
    )
    agent_stats: Mapped[list["AgentStat"]] = relationship(
        back_populates="pipeline_run", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_runs_status", "status"),
        Index("idx_runs_character_id", "character_id"),
        Index("idx_runs_started_at", "started_at"),
    )


# ============================================================
# 5. trend_events
# ============================================================

class TrendEvent(Base):
    __tablename__ = "trend_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(32), nullable=False)
    pipeline_run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("pipeline_runs.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    source: Mapped[str] = mapped_column(String(30), nullable=False)
    score: Mapped[float] = mapped_column(Float, default=0.0, server_default="0.0")
    velocity: Mapped[float] = mapped_column(Float, default=0.0, server_default="0.0")
    category: Mapped[str] = mapped_column(String(50), default="geral", server_default="geral")
    sentiment: Mapped[str] = mapped_column(String(30), default="neutro", server_default="neutro")
    traffic: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    related_keywords: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict, nullable=False)
    sources_count: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    fetched_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    # Relationship
    pipeline_run: Mapped["PipelineRun"] = relationship(back_populates="trend_events")
    work_orders: Mapped[list["WorkOrder"]] = relationship(back_populates="trend_event")

    __table_args__ = (
        Index("idx_trends_pipeline_run_id", "pipeline_run_id"),
        Index("idx_trends_source", "source"),
        Index("idx_trends_category", "category"),
        Index("idx_trends_fetched_at", "fetched_at"),
    )


# ============================================================
# 6. work_orders
# ============================================================

class WorkOrder(Base):
    __tablename__ = "work_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(String(32), nullable=False)
    pipeline_run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("pipeline_runs.id", ondelete="CASCADE"), nullable=False
    )
    trend_event_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("trend_events.id", ondelete="CASCADE"), nullable=False
    )
    gandalf_topic: Mapped[str] = mapped_column(String(500), nullable=False)
    humor_angle: Mapped[str] = mapped_column(Text, default="", nullable=False)
    situacao_key: Mapped[str] = mapped_column(String(100), nullable=False)
    relevance_score: Mapped[float] = mapped_column(Float, default=0.0, server_default="0.0")
    priority: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    phrases_count: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    pipeline_run: Mapped["PipelineRun"] = relationship(back_populates="work_orders")
    trend_event: Mapped["TrendEvent"] = relationship(back_populates="work_orders")
    content_packages: Mapped[list["ContentPackage"]] = relationship(back_populates="work_order")

    __table_args__ = (
        Index("idx_wo_pipeline_run_id", "pipeline_run_id"),
        Index("idx_wo_trend_event_id", "trend_event_id"),
        Index("idx_wo_situacao_key", "situacao_key"),
    )


# ============================================================
# 7. content_packages
# ============================================================

class ContentPackage(Base):
    __tablename__ = "content_packages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pipeline_run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("pipeline_runs.id", ondelete="CASCADE"), nullable=False
    )
    work_order_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("work_orders.id", ondelete="SET NULL"), nullable=True
    )
    character_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("characters.id"), nullable=True
    )
    phrase: Mapped[str] = mapped_column(Text, nullable=False)
    topic: Mapped[str] = mapped_column(String(500), default="", server_default="")
    source: Mapped[str] = mapped_column(String(30), nullable=False)

    # Imagem
    image_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    background_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    background_source: Mapped[str] = mapped_column(String(30), default="static", server_default="static")

    # Post-production — TEXT/JSON sem server_default
    caption: Mapped[str] = mapped_column(Text, default="", nullable=False)
    hashtags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    best_time_to_post: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    quality_score: Mapped[float] = mapped_column(Float, default=0.0, server_default="0.0")

    # Metadata de geracao
    image_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # Quick Wins: A/B testing + carousel (nullable — MySQL nao suporta default em JSON)
    phrase_alternatives: Mapped[list] = mapped_column(JSON, default=list, nullable=True)
    carousel_slides: Mapped[list] = mapped_column(JSON, default=list, nullable=True)

    # Video generation (Phase 999.1)
    video_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    video_source: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    video_prompt_used: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    video_task_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    video_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    video_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Legend overlay (Phase 999.2)
    legend_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    legend_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    # Approval workflow (Phase 12)
    approval_status: Mapped[str] = mapped_column(
        String(20), default="pending", server_default="pending", nullable=False
    )

    # Publishing
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    pipeline_run: Mapped["PipelineRun"] = relationship(back_populates="content_packages")
    work_order: Mapped["WorkOrder"] = relationship(back_populates="content_packages")
    character: Mapped[Optional["Character"]] = relationship(back_populates="content_packages")
    generated_image: Mapped[Optional["GeneratedImage"]] = relationship(back_populates="content_package")
    scheduled_posts: Mapped[list["ScheduledPost"]] = relationship(back_populates="content_package")

    __table_args__ = (
        Index("idx_pkg_pipeline_run_id", "pipeline_run_id"),
        Index("idx_pkg_character_id", "character_id"),
        Index("idx_pkg_quality_score", "quality_score"),
        Index("idx_pkg_created_at", "created_at"),
        Index("idx_pkg_is_published", "is_published"),
        Index("idx_pkg_video_status", "video_status"),
        Index("idx_pkg_legend_status", "legend_status"),
    )


# ============================================================
# 8. generated_images
# ============================================================

class GeneratedImage(Base):
    __tablename__ = "generated_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    character_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("characters.id"), nullable=True
    )
    content_package_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("content_packages.id"), nullable=True
    )
    batch_job_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("batch_jobs.id"), nullable=True
    )
    filename: Mapped[str] = mapped_column(String(300), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    image_type: Mapped[str] = mapped_column(String(30), nullable=False)  # background | composed | refined
    source: Mapped[str] = mapped_column(String(30), nullable=False)  # gemini | comfyui | static | pillow
    width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    theme_key: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    prompt_used: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_refined: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    refinement_passes: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    image_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    character: Mapped[Optional["Character"]] = relationship(back_populates="generated_images")
    content_package: Mapped[Optional["ContentPackage"]] = relationship(back_populates="generated_image")
    batch_job: Mapped[Optional["BatchJob"]] = relationship(back_populates="generated_images")

    __table_args__ = (
        Index("idx_img_character_id", "character_id"),
        Index("idx_img_content_package_id", "content_package_id"),
        Index("idx_img_image_type", "image_type"),
        Index("idx_img_source", "source"),
        Index("idx_img_created_at", "created_at"),
    )


# ============================================================
# 9. batch_jobs
# ============================================================

class BatchJob(Base):
    __tablename__ = "batch_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    character_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("characters.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued", server_default="queued")
    total: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    done: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    failed: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    auto_refine: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    refinement_passes: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    results: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    errors: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    character: Mapped[Optional["Character"]] = relationship(back_populates="batch_jobs")
    generated_images: Mapped[list["GeneratedImage"]] = relationship(back_populates="batch_job")

    __table_args__ = (
        Index("idx_jobs_status", "status"),
        Index("idx_jobs_created_at", "created_at"),
    )


# ============================================================
# 10. agent_stats
# ============================================================

class AgentStat(Base):
    __tablename__ = "agent_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pipeline_run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("pipeline_runs.id", ondelete="CASCADE"), nullable=False
    )
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # done | error | timeout | idle
    events_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    # Relationship
    pipeline_run: Mapped["PipelineRun"] = relationship(back_populates="agent_stats")

    __table_args__ = (
        Index("idx_astats_pipeline_run_id", "pipeline_run_id"),
        Index("idx_astats_agent_name", "agent_name"),
    )


# ============================================================
# 11. scheduled_posts
# ============================================================

class ScheduledPost(TimestampMixin, Base):
    __tablename__ = "scheduled_posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content_package_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("content_packages.id", ondelete="CASCADE"), nullable=False
    )
    character_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("characters.id"), nullable=True
    )
    platform: Mapped[str] = mapped_column(String(30), default="instagram", server_default="instagram")
    status: Mapped[str] = mapped_column(
        String(20), default="queued", server_default="queued"
    )  # queued | publishing | published | failed | cancelled

    scheduled_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Resultado da publicacao (URL do post, response da API, etc)
    publish_result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Retentativas
    retry_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    max_retries: Mapped[int] = mapped_column(Integer, default=3, server_default="3")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    content_package: Mapped["ContentPackage"] = relationship(back_populates="scheduled_posts")
    character: Mapped[Optional["Character"]] = relationship(back_populates="scheduled_posts")

    __table_args__ = (
        Index("idx_sched_status", "status"),
        Index("idx_sched_platform", "platform"),
        Index("idx_sched_scheduled_at", "scheduled_at"),
        Index("idx_sched_character_id", "character_id"),
        Index("idx_sched_status_scheduled", "status", "scheduled_at"),
    )


# ============================================================
# 12. users
# ============================================================

class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="user", server_default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    display_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # API keys — plaintext Text, nullable (per D-01, D-02)
    gemini_free_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    gemini_paid_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    active_key_tier: Mapped[str] = mapped_column(String(20), default="free", server_default="free")

    # Billing (Phase 17 — Stripe)
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    plan_tier: Mapped[str] = mapped_column(String(20), default="free", server_default="free")
    subscription_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    subscription_ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    characters: Mapped[list["Character"]] = relationship(back_populates="owner")
    api_usage_records: Mapped[list["ApiUsage"]] = relationship(back_populates="user")

    __table_args__ = (
        Index("idx_users_role", "role"),
        Index("idx_users_is_active", "is_active"),
        Index("idx_users_plan_tier", "plan_tier"),
        Index("idx_users_stripe_customer_id", "stripe_customer_id"),
    )


# ============================================================
# 13. refresh_tokens
# ============================================================

class RefreshToken(TimestampMixin, Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    user: Mapped["User"] = relationship("User")

    __table_args__ = (
        Index("idx_refresh_tokens_user_id", "user_id"),
        Index("idx_refresh_tokens_token_hash", "token_hash"),
    )


# ============================================================
# 14. api_usage
# ============================================================

class ApiUsage(TimestampMixin, Base):
    __tablename__ = "api_usage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    service: Mapped[str] = mapped_column(String(50), nullable=False)
    tier: Mapped[str] = mapped_column(String(100), nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    usage_count: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0, server_default="0.0")
    cost_brl: Mapped[float] = mapped_column(Float, default=0.0, server_default="0.0")
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="api_usage_records")

    __table_args__ = (
        UniqueConstraint("user_id", "service", "tier", "date", name="uq_api_usage_user_service_tier_date"),
        Index("idx_api_usage_user_id", "user_id"),
        Index("idx_api_usage_date", "date"),
        Index("idx_api_usage_service", "service"),
    )


# ============================================================
# 15. reels_config
# ============================================================

class ReelsConfig(TimestampMixin, Base):
    __tablename__ = "reels_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    character_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("characters.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, default="default", server_default="default")

    # Images
    image_count: Mapped[int] = mapped_column(Integer, default=5, server_default="5")
    image_style: Mapped[str] = mapped_column(String(50), default="photographic", server_default="photographic")

    # Script
    tone: Mapped[str] = mapped_column(String(30), default="inspiracional", server_default="inspiracional")
    target_duration: Mapped[int] = mapped_column(Integer, default=30, server_default="30")
    niche: Mapped[str] = mapped_column(String(100), default="lifestyle", server_default="lifestyle")
    cta_default: Mapped[str] = mapped_column(String(200), default="salve esse post", server_default="salve esse post")
    keywords: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    script_language: Mapped[str] = mapped_column(String(10), default="pt-BR", server_default="pt-BR")
    script_system_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # TTS
    tts_provider: Mapped[str] = mapped_column(String(20), default="gemini", server_default="gemini")
    tts_voice: Mapped[str] = mapped_column(String(50), default="Charon", server_default="Charon")
    tts_speed: Mapped[float] = mapped_column(Float, default=1.1, server_default="1.1")

    # Transcription
    transcription_provider: Mapped[str] = mapped_column(String(20), default="gemini", server_default="gemini")

    # Video assembly
    image_duration: Mapped[float] = mapped_column(Float, default=4.0, server_default="4.0")
    transition_type: Mapped[str] = mapped_column(String(20), default="fade", server_default="fade")
    transition_duration: Mapped[float] = mapped_column(Float, default=0.5, server_default="0.5")
    bg_music_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    bg_music_volume: Mapped[float] = mapped_column(Float, default=0.15, server_default="0.15")

    # Subtitles
    subtitle_position: Mapped[str] = mapped_column(String(20), default="bottom", server_default="bottom")
    subtitle_font_size: Mapped[int] = mapped_column(Integer, default=12, server_default="12")
    subtitle_color: Mapped[str] = mapped_column(String(20), default="&H00B4EBFF&", server_default="&H00B4EBFF&")
    subtitle_font: Mapped[str] = mapped_column(String(50), default="MedievalSharp", server_default="MedievalSharp")
    subtitle_outline: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    subtitle_margin_v: Mapped[int] = mapped_column(Integer, default=35, server_default="35")
    subtitle_margin_h: Mapped[int] = mapped_column(Integer, default=15, server_default="15")

    # Branding
    logo_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")

    # Preset
    preset: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "character_id", "name", name="uq_reels_config_user_char_name"),
        Index("idx_reels_config_user_id", "user_id"),
    )


# ============================================================
# 16. reels_jobs
# ============================================================

class ReelsJob(TimestampMixin, Base):
    __tablename__ = "reels_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    character_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("characters.id"), nullable=True
    )
    config_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("reels_config.id"), nullable=True
    )

    # Input
    tema: Mapped[str] = mapped_column(String(500), nullable=False)

    # Status tracking
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued", server_default="queued")
    current_step: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    progress_pct: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Interactive step state (per-step persistence for step-by-step execution)
    step_state: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Artifacts
    image_paths: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    script_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    audio_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    srt_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    video_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    video_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    # Publishing
    instagram_media_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    instagram_permalink: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    caption: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    hashtags: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # Cost tracking
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0, server_default="0.0")
    cost_brl: Mapped[float] = mapped_column(Float, default=0.0, server_default="0.0")

    # Multi-platform output (Phase E)
    platforms: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    platform_outputs: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_reels_jobs_user_id", "user_id"),
        Index("idx_reels_jobs_status", "status"),
        Index("idx_reels_jobs_job_id", "job_id"),
    )


# ============================================================
# 17. product_ad_jobs
# ============================================================

class ProductAdJob(TimestampMixin, Base):
    __tablename__ = "product_ad_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )

    # Product info
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    product_images: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Style and generation settings
    style: Mapped[str] = mapped_column(String(20), nullable=False, default="cinematic", server_default="cinematic")
    video_model: Mapped[Optional[str]] = mapped_column(String(100), default="wan2.1-i2v", server_default="wan2.1-i2v")
    audio_mode: Mapped[Optional[str]] = mapped_column(String(20), default="music", server_default="music")
    output_formats: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    target_duration: Mapped[int] = mapped_column(Integer, default=15, server_default="15")
    tone: Mapped[Optional[str]] = mapped_column(String(50), default="premium", server_default="premium")
    niche: Mapped[Optional[str]] = mapped_column(String(100), default="", server_default="")
    audience: Mapped[Optional[str]] = mapped_column(String(255), default="", server_default="")
    scene_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    prompt_generated: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Status tracking
    step_state: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft", server_default="draft")
    current_step: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    progress_pct: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Cost tracking
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0, server_default="0")
    cost_brl: Mapped[float] = mapped_column(Float, default=0.0, server_default="0")

    # Output
    outputs: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_product_ad_jobs_user_id", "user_id"),
        Index("idx_product_ad_jobs_status", "status"),
        Index("idx_product_ad_jobs_job_id", "job_id"),
    )
