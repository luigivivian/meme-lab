"""Modelos Pydantic para a API REST — espelha rotas do Colab."""

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
    save_to_yaml: bool = Field(default=True, description="Salvar no themes.yaml")


class EnhanceRequest(BaseModel):
    """Input simples -> prompt forte via IA."""
    input_text: str = Field(..., min_length=2, max_length=500, description="Descricao simples do tema")
    save_to_yaml: bool = Field(default=False, description="Salvar no themes.yaml")


# ===== Pipeline =====

class PipelineRunRequest(BaseModel):
    """Executar pipeline completo de geracao de conteudo."""
    count: int = Field(default=5, ge=1, le=20, description="Quantidade de imagens a gerar")
    phrases_per_topic: int = Field(default=1, ge=1, le=5, description="Frases por topico")
    use_comfyui: bool = Field(default=False, description="Usar ComfyUI local")
    use_gemini_image: bool | None = Field(default=None, description="Usar Gemini para backgrounds")
    use_phrase_context: bool = Field(default=False, description="Background contextualizado pela frase (mais coerente, mas mais lento)")


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
