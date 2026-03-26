"""Modelos Pydantic para a API REST — espelha rotas do Colab."""

from datetime import datetime
from pydantic import BaseModel, Field


# ===== Generator API =====

class SingleRequest(BaseModel):
    """Gera 1 imagem (com ou sem refinamento Nano Banana)."""
    theme_key: str = Field(default="sabedoria", description="Chave da situacao ou key de tema gerado por IA")
    acao_custom: str = Field(default="", description="Acao customizada (sobrescreve a do tema)")
    cenario_custom: str = Field(default="", description="Cenario customizado (sobrescreve o do tema)")
    auto_refine: bool = Field(default=False, description="Ativar refinamento Nano Banana")
    refinement_passes: int = Field(default=1, ge=1, le=3, description="Passes de refinamento")


class RefineRequest(BaseModel):
    """Refina imagem existente (N passes)."""
    filename: str = Field(..., description="Nome do arquivo PNG a refinar")
    instrucao: str = Field(default="", description="Instrucao especifica de refinamento (ingles)")
    referencias_adicionais: int = Field(default=3, ge=1, le=7)
    passes: int = Field(default=1, ge=1, le=3, description="Passes de refinamento iterativo")


class BatchRequest(BaseModel):
    """Lote com lista de temas."""
    themes: list[str | dict] = Field(..., description="Lista de temas: str (key) ou dict com key/acao/cenario/count")
    n_refs: int = Field(default=5, ge=1, le=14, description="Referencias por geracao")
    pausa: int = Field(default=15, ge=5, description="Segundos entre geracoes")
    auto_refine: bool = Field(default=False, description="Ativar refinamento Nano Banana")
    refinement_passes: int = Field(default=1, ge=1, le=3, description="Passes de refinamento")


class ThemeItem(BaseModel):
    """Tema customizado para geracao."""
    key: str
    label: str = ""
    acao: str
    cenario: str
    count: int = 1


# ===== AI Theme Generator =====

class GenerateThemesRequest(BaseModel):
    """Auto-gera temas variados via IA."""
    count: int = Field(default=5, ge=1, le=20, description="Quantos temas gerar")
    categories: list[str] = Field(default=[], description="Categorias desejadas (ex: humor, fantasia)")
    avoid_existing: bool = Field(default=True, description="Evitar temas similares aos existentes")
    save_to_db: bool = Field(default=True, description="Salvar no banco de dados")
    character_id: int | None = Field(default=None, description="Associar a personagem (None=global)")


class EnhanceRequest(BaseModel):
    """Input simples -> prompt forte via IA."""
    input_text: str = Field(..., min_length=2, max_length=500, description="Descricao simples do tema")
    save_to_db: bool = Field(default=False, description="Salvar no banco de dados")
    character_id: int | None = Field(default=None, description="Associar a personagem (None=global)")


# ===== Pipeline =====

class TopicInput(BaseModel):
    """Tema fornecido manualmente (pula L1-L2-L3)."""
    topic: str = Field(description="Tema/assunto para gerar conteudo")
    humor_angle: str = Field(default="", description="Angulo de humor (opcional)")


class PipelineRunRequest(BaseModel):
    """Executar pipeline completo de geracao de conteudo."""
    count: int = Field(default=5, ge=1, le=20, description="Quantidade de imagens a gerar")
    phrases_per_topic: int = Field(default=1, ge=1, le=5, description="Frases por topico")
    use_comfyui: bool = Field(default=False, description="Usar ComfyUI local")
    use_gemini_image: bool | None = Field(default=None, description="Usar Gemini para backgrounds")
    use_phrase_context: bool = Field(default=False, description="Background contextualizado pela frase (mais coerente, mas mais lento)")
    theme_tags: list[str] = Field(default=[], description="Lista de situacao_keys para forcar temas visuais (ex: ['cafe', 'meditando', 'confronto']). Se vazio, auto-detecta com diversidade.")
    character_slug: str | None = Field(default=None, description="Slug do personagem (None=mago-mestre padrao)")
    carousel_count: int = Field(default=1, ge=1, le=5, description="Slides por tema (1=imagem unica, 2-5=carousel Instagram)")
    cost_mode: str | None = Field(default=None, description="Modo de custo: 'normal' | 'eco' | 'ultra-eco'. Se nulo, usa config.COST_MODE")
    background_mode: str = Field(default="auto", description="Modo de background: 'auto' (prioridade config), 'comfyui' (local GPU), 'gemini' (API), 'static' (custo zero)")
    topics: list[TopicInput] = Field(default=[], description="Temas manuais — pula L1/L2/L3 e vai direto para geracao. Se vazio, usa pipeline completo com fetch de trends.")


class GeneratePhrasesRequest(BaseModel):
    """Gerar frases por tema."""
    topic: str = Field(description="Tema para gerar frases")
    count: int = Field(default=5, ge=1, le=20, description="Quantidade de frases")


class ComposeImageRequest(BaseModel):
    """Compor imagem final: frase + background."""
    phrase: str = Field(description="Texto da frase")
    background_filename: str = Field(default="", description="Usar background existente (nome do arquivo)")
    situacao: str = Field(default="sabedoria", description="Situacao para o background")
    descricao_custom: str = Field(default="", description="Acao customizada")
    cenario_custom: str = Field(default="", description="Cenario customizado")
    auto_refine: bool = Field(default=False, description="Refinar background")
    refinement_passes: int = Field(default=1, ge=1, le=3)
    use_phrase_context: bool = Field(default=False, description="Background contextualizado pela frase")


# ===== Characters =====

class CharacterPersona(BaseModel):
    system_prompt: str = Field(default="", description="Prompt de sistema completo para o LLM")
    humor_style: str = Field(default="", description="Estilo de humor (zoeiro, sarcastico, etc)")
    tone: str = Field(default="", description="Tom geral (leve, engracado, viral)")
    catchphrases: list[str] = Field(default=[], description="Frases de efeito do personagem")
    rules: dict = Field(default_factory=lambda: {"max_chars": 120, "forbidden": []})


class CharacterVisual(BaseModel):
    character_dna: str = Field(default="", description="DNA visual para Gemini Image")
    negative_traits: str = Field(default="", description="Traits negativos (o que NAO gerar)")
    composition: str = Field(default="", description="Regras de composicao da imagem")
    rendering: dict = Field(default_factory=dict, description="Config de rendering: art_style, lighting, camera, custom overrides")


class CharacterComfyUI(BaseModel):
    trigger_word: str = Field(default="", description="Trigger word da LoRA")
    character_dna: str = Field(default="", description="DNA visual para ComfyUI (ilustracao)")
    lora_path: str = Field(default="", description="Caminho da LoRA")


class CharacterBranding(BaseModel):
    branded_hashtags: list[str] = Field(default=[], description="Hashtags do personagem")
    caption_prompt: str = Field(default="", description="Prompt para gerar legendas Instagram")


class CharacterStyleConfig(BaseModel):
    overlay_color: list[int] = Field(default=[10, 10, 30, 40])
    glow_color: list[int] = Field(default=[255, 200, 80, 15])
    text_color: list[int] = Field(default=[255, 255, 255])
    text_stroke_width: int = Field(default=2)
    text_vertical_position: float = Field(default=0.80)
    font_size: int = Field(default=48)
    watermark_color: list[int] = Field(default=[200, 180, 130, 120])
    watermark_font_size: int = Field(default=22)


class CharacterCreateRequest(BaseModel):
    """Criar novo personagem."""
    name: str = Field(description="Nome do personagem (ex: 'O Dragao Zoeiro')")
    handle: str = Field(default="", description="Handle Instagram (ex: '@dragaozoeiro')")
    watermark: str = Field(default="", description="Texto do watermark (default: handle)")
    persona: CharacterPersona = Field(default_factory=CharacterPersona)
    visual: CharacterVisual = Field(default_factory=CharacterVisual)
    comfyui: CharacterComfyUI = Field(default_factory=CharacterComfyUI)
    branding: CharacterBranding = Field(default_factory=CharacterBranding)
    style: CharacterStyleConfig = Field(default_factory=CharacterStyleConfig)


class CharacterUpdateRequest(BaseModel):
    """Atualizar personagem existente (campos parciais)."""
    name: str | None = None
    handle: str | None = None
    watermark: str | None = None
    status: str | None = None
    persona: dict | None = None
    visual: dict | None = None
    comfyui: dict | None = None
    branding: dict | None = None
    style: dict | None = None
    refs_config: dict | None = None


# ===== Content Export =====

class BatchExportRequest(BaseModel):
    """Exportar multiplos content packages como ZIP."""
    package_ids: list[int] = Field(..., min_length=1, max_length=50, description="IDs dos packages a exportar (max 50)")


class CharacterRefsStats(BaseModel):
    approved: int = 0
    pending: int = 0
    rejected: int = 0
    min_required: int = 5
    ideal: int = 15
    is_ready: bool = False


class CharacterSummary(BaseModel):
    slug: str
    name: str
    handle: str
    status: str
    avatar: str | None = None
    refs: CharacterRefsStats
    themes_count: int = 0


class CharacterDetail(BaseModel):
    slug: str
    name: str
    handle: str
    watermark: str
    status: str
    persona: CharacterPersona
    visual: CharacterVisual
    comfyui: CharacterComfyUI
    branding: CharacterBranding
    style: CharacterStyleConfig
    refs: CharacterRefsStats
    themes_count: int = 0


# ===== Manual Pipeline (Phase 12) =====

class ManualRunRequest(BaseModel):
    """Manual pipeline run with optional Gemini Image generation."""
    input_mode: str = Field(description="'topic' or 'phrase'")
    topic: str = Field(default="", description="Topic for Gemini phrase generation (input_mode='topic')")
    phrases: list[str] = Field(default=[], description="Literal phrases, one per meme (input_mode='phrase')")
    count: int = Field(default=3, ge=1, le=10, description="Meme count per D-08")
    theme_key: str = Field(default="sabedoria", description="Theme key from themes.yaml")
    background_type: str = Field(default="image", description="'solid' or 'image'")
    background_color: str = Field(default="", description="Hex color e.g. '#1A1A3E' (when background_type='solid')")
    background_image: str = Field(default="", description="Filename from character backgrounds (when background_type='image')")
    layout: str = Field(default="bottom", description="Layout template: bottom, top, center, split_top")
    enable_l5: bool = Field(default=True, description="Run L5 post-production per D-09")
    use_gemini_image: bool = Field(default=False, description="Generate background via Gemini API (consumes quota)")
    character_slug: str | None = Field(default=None, description="Character slug for backgrounds and watermark")


class ApprovalRequest(BaseModel):
    """Bulk approval/rejection."""
    package_ids: list[int] = Field(description="Content package IDs to update")


# ===== Publishing / Scheduling =====

class SchedulePostRequest(BaseModel):
    """Agendar um content package para publicacao."""
    content_package_id: int = Field(description="ID do content package a publicar")
    platform: str = Field(default="instagram", description="Plataforma (instagram, tiktok)")
    scheduled_at: datetime = Field(description="Data/hora para publicar (ISO 8601)")
    character_id: int | None = Field(default=None, description="ID do personagem (herda do package se nulo)")


# ===== Video Generation (Phase 999.1) =====

class VideoGenerateRequest(BaseModel):
    """Request to generate a video from an approved content package."""
    content_package_id: int
    duration: int = 10  # 10 or 15 seconds (per D-08)
    character_ids: list[str] = []  # Kie.ai character_id_list (per D-10)
    custom_prompt: str = ""  # User animation description (enhanced by LLM before sending)


class VideoBatchRequest(BaseModel):
    """Request to generate videos for multiple content packages."""
    content_package_ids: list[int]
    duration: int = 10
    character_ids: list[str] = []


class VideoStatusResponse(BaseModel):
    """Response with video generation status."""
    content_package_id: int
    video_status: str | None  # null | generating | success | failed
    video_task_id: str | None
    video_path: str | None
    video_source: str | None
    video_metadata: dict | None


class VideoBudgetResponse(BaseModel):
    """Response with remaining daily video budget."""
    daily_budget_usd: float
    spent_today_usd: float
    remaining_usd: float
    videos_remaining_estimate: int  # at current duration
