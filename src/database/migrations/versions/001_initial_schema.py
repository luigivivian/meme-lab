"""Initial schema — 10 tabelas do clip-flow (MySQL + SQLite).

Revision ID: 001
Revises: None
Create Date: 2026-03-11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. characters
    op.create_table(
        "characters",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("handle", sa.String(100), server_default="", nullable=False),
        sa.Column("watermark", sa.String(200), server_default="", nullable=False),
        sa.Column("status", sa.String(20), server_default="draft", nullable=False),
        # Persona — TEXT/JSON sem server_default (MySQL nao suporta)
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("humor_style", sa.String(200), server_default="", nullable=False),
        sa.Column("tone", sa.String(200), server_default="", nullable=False),
        sa.Column("catchphrases", sa.JSON(), nullable=False),
        sa.Column("rules_max_chars", sa.Integer(), server_default="120", nullable=False),
        sa.Column("rules_forbidden", sa.JSON(), nullable=False),
        # Visual DNA (Gemini)
        sa.Column("character_dna", sa.Text(), nullable=False),
        sa.Column("negative_traits", sa.Text(), nullable=False),
        sa.Column("composition", sa.Text(), nullable=False),
        # Visual DNA (ComfyUI)
        sa.Column("comfyui_trigger_word", sa.String(100), server_default="", nullable=False),
        sa.Column("comfyui_character_dna", sa.Text(), nullable=False),
        sa.Column("comfyui_lora_path", sa.String(500), server_default="", nullable=False),
        # Branding
        sa.Column("branded_hashtags", sa.JSON(), nullable=False),
        sa.Column("caption_prompt", sa.Text(), nullable=False),
        # Style
        sa.Column("style", sa.JSON(), nullable=False),
        # Refs config
        sa.Column("refs_min_approved", sa.Integer(), server_default="5", nullable=False),
        sa.Column("refs_ideal_approved", sa.Integer(), server_default="15", nullable=False),
        sa.Column("refs_batch_size", sa.Integer(), server_default="15", nullable=False),
        sa.Column("refs_priority", sa.JSON(), nullable=False),
        # Meta
        sa.Column("is_deleted", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("idx_characters_status", "characters", ["status"])
    op.create_index("idx_characters_is_deleted", "characters", ["is_deleted"])

    # 2. character_refs
    op.create_table(
        "character_refs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("character_id", sa.Integer(), sa.ForeignKey("characters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.String(300), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("file_path", sa.String(1000), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(50), server_default="generated", nullable=False),
        sa.Column("generation_prompt", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_refs_character_id", "character_refs", ["character_id"])
    op.create_index("idx_refs_status", "character_refs", ["status"])
    op.create_index("idx_refs_character_status", "character_refs", ["character_id", "status"])

    # 3. themes
    op.create_table(
        "themes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("character_id", sa.Integer(), sa.ForeignKey("characters.id", ondelete="CASCADE"), nullable=True),
        sa.Column("key", sa.String(100), nullable=False),
        sa.Column("label", sa.String(200), server_default="", nullable=False),
        sa.Column("acao", sa.Text(), nullable=False),
        sa.Column("cenario", sa.Text(), nullable=False),
        sa.Column("count", sa.Integer(), server_default="1", nullable=False),
        sa.Column("is_builtin", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("character_id", "key", name="uq_themes_character_key"),
    )
    op.create_index("idx_themes_character_id", "themes", ["character_id"])
    op.create_index("idx_themes_key", "themes", ["key"])

    # 4. pipeline_runs
    op.create_table(
        "pipeline_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.String(32), nullable=False),
        sa.Column("character_id", sa.Integer(), sa.ForeignKey("characters.id"), nullable=True),
        sa.Column("status", sa.String(20), server_default="queued", nullable=False),
        sa.Column("mode", sa.String(20), server_default="agents", nullable=False),
        # Params
        sa.Column("requested_count", sa.Integer(), server_default="5", nullable=False),
        sa.Column("phrases_per_topic", sa.Integer(), server_default="1", nullable=False),
        sa.Column("use_comfyui", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("use_gemini_image", sa.Boolean(), nullable=True),
        sa.Column("use_phrase_context", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("theme_tags", sa.JSON(), nullable=False),
        # Results
        sa.Column("trends_fetched", sa.Integer(), server_default="0", nullable=False),
        sa.Column("trend_events_queued", sa.Integer(), server_default="0", nullable=False),
        sa.Column("work_orders_emitted", sa.Integer(), server_default="0", nullable=False),
        sa.Column("images_generated", sa.Integer(), server_default="0", nullable=False),
        sa.Column("packages_produced", sa.Integer(), server_default="0", nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        # Snapshots — JSON sem server_default
        sa.Column("layers_snapshot", sa.JSON(), nullable=False),
        sa.Column("errors", sa.JSON(), nullable=False),
        # Timestamps
        sa.Column("started_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id"),
    )
    op.create_index("idx_runs_status", "pipeline_runs", ["status"])
    op.create_index("idx_runs_character_id", "pipeline_runs", ["character_id"])
    op.create_index("idx_runs_started_at", "pipeline_runs", ["started_at"])

    # 5. trend_events
    op.create_table(
        "trend_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.String(32), nullable=False),
        sa.Column("pipeline_run_id", sa.Integer(), sa.ForeignKey("pipeline_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("source", sa.String(30), nullable=False),
        sa.Column("score", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("velocity", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("category", sa.String(50), server_default="geral", nullable=False),
        sa.Column("sentiment", sa.String(30), server_default="neutro", nullable=False),
        sa.Column("traffic", sa.String(100), nullable=True),
        sa.Column("url", sa.String(1000), nullable=True),
        sa.Column("related_keywords", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("sources_count", sa.Integer(), server_default="1", nullable=False),
        sa.Column("fetched_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_trends_pipeline_run_id", "trend_events", ["pipeline_run_id"])
    op.create_index("idx_trends_source", "trend_events", ["source"])
    op.create_index("idx_trends_category", "trend_events", ["category"])
    op.create_index("idx_trends_fetched_at", "trend_events", ["fetched_at"])

    # 6. work_orders
    op.create_table(
        "work_orders",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("order_id", sa.String(32), nullable=False),
        sa.Column("pipeline_run_id", sa.Integer(), sa.ForeignKey("pipeline_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("trend_event_id", sa.Integer(), sa.ForeignKey("trend_events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("gandalf_topic", sa.String(500), nullable=False),
        sa.Column("humor_angle", sa.Text(), nullable=False),
        sa.Column("situacao_key", sa.String(100), nullable=False),
        sa.Column("relevance_score", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("priority", sa.Integer(), server_default="0", nullable=False),
        sa.Column("phrases_count", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_wo_pipeline_run_id", "work_orders", ["pipeline_run_id"])
    op.create_index("idx_wo_trend_event_id", "work_orders", ["trend_event_id"])
    op.create_index("idx_wo_situacao_key", "work_orders", ["situacao_key"])

    # 7. content_packages
    op.create_table(
        "content_packages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("pipeline_run_id", sa.Integer(), sa.ForeignKey("pipeline_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("work_order_id", sa.Integer(), sa.ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("character_id", sa.Integer(), sa.ForeignKey("characters.id"), nullable=True),
        sa.Column("phrase", sa.Text(), nullable=False),
        sa.Column("topic", sa.String(500), server_default="", nullable=False),
        sa.Column("source", sa.String(30), nullable=False),
        sa.Column("image_path", sa.String(1000), nullable=False),
        sa.Column("background_path", sa.String(1000), nullable=True),
        sa.Column("background_source", sa.String(30), server_default="static", nullable=False),
        sa.Column("caption", sa.Text(), nullable=False),
        sa.Column("hashtags", sa.JSON(), nullable=False),
        sa.Column("best_time_to_post", sa.String(50), nullable=True),
        sa.Column("quality_score", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("is_published", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_pkg_pipeline_run_id", "content_packages", ["pipeline_run_id"])
    op.create_index("idx_pkg_character_id", "content_packages", ["character_id"])
    op.create_index("idx_pkg_quality_score", "content_packages", ["quality_score"])
    op.create_index("idx_pkg_created_at", "content_packages", ["created_at"])
    op.create_index("idx_pkg_is_published", "content_packages", ["is_published"])

    # 8. batch_jobs (antes de generated_images por FK)
    op.create_table(
        "batch_jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_id", sa.String(32), nullable=False),
        sa.Column("character_id", sa.Integer(), sa.ForeignKey("characters.id"), nullable=True),
        sa.Column("status", sa.String(20), server_default="queued", nullable=False),
        sa.Column("total", sa.Integer(), server_default="0", nullable=False),
        sa.Column("done", sa.Integer(), server_default="0", nullable=False),
        sa.Column("failed", sa.Integer(), server_default="0", nullable=False),
        sa.Column("auto_refine", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("refinement_passes", sa.Integer(), server_default="0", nullable=False),
        sa.Column("results", sa.JSON(), nullable=False),
        sa.Column("errors", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id"),
    )
    op.create_index("idx_jobs_status", "batch_jobs", ["status"])
    op.create_index("idx_jobs_created_at", "batch_jobs", ["created_at"])

    # 9. generated_images
    op.create_table(
        "generated_images",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("character_id", sa.Integer(), sa.ForeignKey("characters.id"), nullable=True),
        sa.Column("content_package_id", sa.Integer(), sa.ForeignKey("content_packages.id"), nullable=True),
        sa.Column("batch_job_id", sa.Integer(), sa.ForeignKey("batch_jobs.id"), nullable=True),
        sa.Column("filename", sa.String(300), nullable=False),
        sa.Column("file_path", sa.String(1000), nullable=False),
        sa.Column("image_type", sa.String(30), nullable=False),
        sa.Column("source", sa.String(30), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("theme_key", sa.String(100), nullable=True),
        sa.Column("prompt_used", sa.Text(), nullable=True),
        sa.Column("is_refined", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("refinement_passes", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_img_character_id", "generated_images", ["character_id"])
    op.create_index("idx_img_content_package_id", "generated_images", ["content_package_id"])
    op.create_index("idx_img_image_type", "generated_images", ["image_type"])
    op.create_index("idx_img_source", "generated_images", ["source"])
    op.create_index("idx_img_created_at", "generated_images", ["created_at"])

    # 10. agent_stats
    op.create_table(
        "agent_stats",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("pipeline_run_id", sa.Integer(), sa.ForeignKey("pipeline_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_name", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("events_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_astats_pipeline_run_id", "agent_stats", ["pipeline_run_id"])
    op.create_index("idx_astats_agent_name", "agent_stats", ["agent_name"])


def downgrade() -> None:
    op.drop_table("agent_stats")
    op.drop_table("generated_images")
    op.drop_table("batch_jobs")
    op.drop_table("content_packages")
    op.drop_table("work_orders")
    op.drop_table("trend_events")
    op.drop_table("pipeline_runs")
    op.drop_table("themes")
    op.drop_table("character_refs")
    op.drop_table("characters")
