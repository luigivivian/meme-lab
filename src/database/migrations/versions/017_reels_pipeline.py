"""create reels_config and reels_jobs tables

Revision ID: 017
Revises: 016
Create Date: 2026-03-28

Phase 999.4: Instagram Reels Pipeline
- reels_config: per user/character configuration for reel generation
- reels_jobs: job tracking for reel pipeline executions
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = '017'
down_revision: Union[str, None] = '016'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- reels_config ---
    op.create_table(
        'reels_config',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('character_id', sa.Integer(), sa.ForeignKey('characters.id'), nullable=True),
        sa.Column('name', sa.String(100), nullable=False, server_default='default'),

        # Images
        sa.Column('image_count', sa.Integer(), server_default='5', nullable=False),
        sa.Column('image_style', sa.String(50), server_default='photographic'),

        # Script
        sa.Column('tone', sa.String(30), server_default='inspiracional'),
        sa.Column('target_duration', sa.Integer(), server_default='30'),
        sa.Column('niche', sa.String(100), server_default='lifestyle'),
        sa.Column('cta_default', sa.String(200), server_default='salve esse post'),
        sa.Column('keywords', sa.JSON(), nullable=False),
        sa.Column('script_language', sa.String(10), server_default='pt-BR'),
        sa.Column('script_system_prompt', sa.Text(), nullable=True),

        # TTS
        sa.Column('tts_provider', sa.String(20), server_default='gemini'),
        sa.Column('tts_voice', sa.String(50), server_default='Puck'),
        sa.Column('tts_speed', sa.Float(), server_default='1.1'),

        # Transcription
        sa.Column('transcription_provider', sa.String(20), server_default='gemini'),

        # Video assembly
        sa.Column('image_duration', sa.Float(), server_default='4.0'),
        sa.Column('transition_type', sa.String(20), server_default='fade'),
        sa.Column('transition_duration', sa.Float(), server_default='0.5'),
        sa.Column('bg_music_enabled', sa.Boolean(), server_default='0'),
        sa.Column('bg_music_volume', sa.Float(), server_default='0.15'),

        # Subtitles
        sa.Column('subtitle_position', sa.String(20), server_default='bottom'),
        sa.Column('subtitle_font_size', sa.Integer(), server_default='52'),
        sa.Column('subtitle_color', sa.String(10), server_default='#FFFFFF'),

        # Branding
        sa.Column('logo_enabled', sa.Boolean(), server_default='0'),

        # Preset
        sa.Column('preset', sa.String(20), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),

        sa.UniqueConstraint('user_id', 'character_id', 'name', name='uq_reels_config_user_char_name'),
    )
    op.create_index('idx_reels_config_user_id', 'reels_config', ['user_id'])

    # --- reels_jobs ---
    op.create_table(
        'reels_jobs',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('job_id', sa.String(32), unique=True, nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('character_id', sa.Integer(), sa.ForeignKey('characters.id'), nullable=True),
        sa.Column('config_id', sa.Integer(), sa.ForeignKey('reels_config.id'), nullable=True),

        # Input
        sa.Column('tema', sa.String(500), nullable=False),

        # Status tracking
        sa.Column('status', sa.String(20), nullable=False, server_default='queued'),
        sa.Column('current_step', sa.String(30), nullable=True),
        sa.Column('progress_pct', sa.Integer(), server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),

        # Artifacts
        sa.Column('image_paths', sa.JSON(), nullable=True),
        sa.Column('script_json', sa.JSON(), nullable=True),
        sa.Column('audio_path', sa.String(1000), nullable=True),
        sa.Column('srt_path', sa.String(1000), nullable=True),
        sa.Column('video_path', sa.String(1000), nullable=True),
        sa.Column('video_url', sa.String(1000), nullable=True),

        # Publishing
        sa.Column('instagram_media_id', sa.String(100), nullable=True),
        sa.Column('instagram_permalink', sa.String(500), nullable=True),
        sa.Column('caption', sa.Text(), nullable=True),
        sa.Column('hashtags', sa.JSON(), nullable=True),

        # Cost tracking
        sa.Column('cost_usd', sa.Float(), server_default='0.0'),
        sa.Column('cost_brl', sa.Float(), server_default='0.0'),

        # Timestamps
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_reels_jobs_user_id', 'reels_jobs', ['user_id'])
    op.create_index('idx_reels_jobs_status', 'reels_jobs', ['status'])
    op.create_index('idx_reels_jobs_job_id', 'reels_jobs', ['job_id'])


def downgrade() -> None:
    op.drop_table('reels_jobs')
    op.drop_table('reels_config')
