"""Pydantic models for the Reels pipeline: roteiro schema, API request/response."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ===== Roteiro (Script) Schema =====

class CenaSchema(BaseModel):
    """Single scene in the roteiro."""
    imagem_index: int = Field(..., description="Index of the image for this scene (0-based)")
    duracao_segundos: float = Field(..., description="Duration in seconds for this scene")
    narracao: str = Field(..., description="Narration text for this scene")
    legenda_overlay: str = Field(..., description="Short overlay text for subtitle display")


class RoteiroSchema(BaseModel):
    """Full roteiro (script) for a Reel — matches D-03 JSON structure."""
    titulo: str = Field(..., description="Reel title")
    gancho: str = Field(..., description="Opening hook to grab attention")
    narracao_completa: str = Field(..., description="Full narration text for TTS")
    cenas: list[CenaSchema] = Field(..., description="List of scenes with per-image narration")
    cta: str = Field(default="salve esse post", description="Call to action")
    hashtags: list[str] = Field(default_factory=list, description="Hashtags for the reel")
    caption_instagram: str = Field(default="", description="Instagram caption text")


# ===== API Request/Response Models =====

class ReelGenerateRequest(BaseModel):
    """Request to generate a new Reel."""
    tema: str = Field(..., description="Theme/topic for the reel")
    character_id: Optional[int] = Field(default=None, description="Character ID to use (None = auto-detect first)")
    character_slug: Optional[str] = Field(default=None, description="Character slug to use (alternative to character_id)")
    no_character: bool = Field(default=False, description="If true, generate without character (generic)")
    config_id: Optional[int] = Field(default=None, description="Reels config preset to use")
    tone: str = Field(default="inspiracional", description="Tone: inspiracional/humor/educativo")
    target_duration: int = Field(default=30, description="Target duration in seconds: 15/30/60")
    niche: str = Field(default="lifestyle", description="Content niche")
    keywords: list[str] = Field(default_factory=list, description="Additional keywords")
    language: str = Field(default="pt-BR", description="Language for script/TTS/subtitles: pt-BR, en-US, es-ES")


class ReelStatusResponse(BaseModel):
    """Polling response for reel generation status."""
    job_id: str
    status: str
    current_step: Optional[str] = None
    progress_pct: int = 0
    video_url: Optional[str] = None
    error_message: Optional[str] = None


class ReelJobResponse(BaseModel):
    """Full job response with results."""
    job_id: str
    status: str
    tema: str
    video_url: Optional[str] = None
    caption: Optional[str] = None
    hashtags: Optional[list[str]] = None
    cost_brl: float = 0.0
    created_at: datetime


class StepStateResponse(BaseModel):
    """Full step_state for an interactive reel job."""
    job_id: str
    current_step: int
    prompt: Optional[dict] = None
    images: Optional[dict] = None
    script: Optional[dict] = None
    tts: Optional[dict] = None
    srt: Optional[dict] = None
    video: Optional[dict] = None


class StepApproveResponse(BaseModel):
    """Response after approving a step."""
    step: str
    approved: bool
    current_step: int


class StepEditRequest(BaseModel):
    """Request to edit an editable step's artifacts inline."""
    text: Optional[str] = None
    script_json: Optional[dict] = None
    srt_entries: Optional[list[dict]] = None


class ReelCreateInteractiveRequest(BaseModel):
    """Request to create an interactive (step-by-step) reel job."""
    tema: str
    character_id: Optional[int] = None
    character_slug: Optional[str] = None
    no_character: bool = False
    config_id: Optional[int] = None
    target_duration: int = 30
    language: str = "pt-BR"


class ReelsConfigRequest(BaseModel):
    """Request to create/update a reels config."""
    name: Optional[str] = "default"
    character_id: Optional[int] = None
    image_count: Optional[int] = 5
    image_style: Optional[str] = "photographic"
    tone: Optional[str] = "inspiracional"
    target_duration: Optional[int] = 30
    niche: Optional[str] = "lifestyle"
    cta_default: Optional[str] = "salve esse post"
    keywords: Optional[list[str]] = None
    script_language: Optional[str] = "pt-BR"
    script_system_prompt: Optional[str] = None
    tts_provider: Optional[str] = "gemini"
    tts_voice: Optional[str] = "Puck"
    tts_speed: Optional[float] = 1.1
    transcription_provider: Optional[str] = "gemini"
    image_duration: Optional[float] = 4.0
    transition_type: Optional[str] = "fade"
    transition_duration: Optional[float] = 0.5
    bg_music_enabled: Optional[bool] = False
    bg_music_volume: Optional[float] = 0.15
    subtitle_position: Optional[str] = "bottom"
    subtitle_font_size: Optional[int] = 52
    subtitle_color: Optional[str] = "#FFFFFF"
    logo_enabled: Optional[bool] = False
    preset: Optional[str] = None


class ReelsConfigResponse(BaseModel):
    """Response with full config details."""
    id: int
    name: str
    character_id: Optional[int] = None
    image_count: int = 5
    image_style: str = "photographic"
    tone: str = "inspiracional"
    target_duration: int = 30
    niche: str = "lifestyle"
    cta_default: str = "salve esse post"
    keywords: list[str] = []
    script_language: str = "pt-BR"
    script_system_prompt: Optional[str] = None
    tts_provider: str = "gemini"
    tts_voice: str = "Puck"
    tts_speed: float = 1.1
    transcription_provider: str = "gemini"
    image_duration: float = 4.0
    transition_type: str = "fade"
    transition_duration: float = 0.5
    bg_music_enabled: bool = False
    bg_music_volume: float = 0.15
    subtitle_position: str = "bottom"
    subtitle_font_size: int = 52
    subtitle_color: str = "#FFFFFF"
    logo_enabled: bool = False
    preset: Optional[str] = None
