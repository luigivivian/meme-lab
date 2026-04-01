"""Reels script generation — Gemini multimodal with structured JSON output."""

import json
import logging
from pathlib import Path

from google.genai import types

from src.llm_client import _get_client
from src.reels_pipeline.config import (
    REELS_SCRIPT_LANGUAGE,
    REELS_SCRIPT_MODEL,
)

logger = logging.getLogger("clip-flow.reels.script_gen")

# Structured JSON schema for Gemini response_schema (per RESEARCH Pattern 2)
ROTEIRO_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "titulo": {"type": "STRING"},
        "gancho": {"type": "STRING"},
        "narracao_completa": {"type": "STRING"},
        "cenas": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "imagem_index": {"type": "INTEGER"},
                    "duracao_segundos": {"type": "NUMBER"},
                    "narracao": {"type": "STRING"},
                    "legenda_overlay": {"type": "STRING"},
                },
                "required": ["imagem_index", "duracao_segundos", "narracao", "legenda_overlay"],
            },
        },
        "cta": {"type": "STRING"},
        "hashtags": {"type": "ARRAY", "items": {"type": "STRING"}},
        "caption_instagram": {"type": "STRING"},
    },
    "required": [
        "titulo", "gancho", "narracao_completa", "cenas",
        "cta", "hashtags", "caption_instagram",
    ],
}

# Language-specific system prompt templates
_SYSTEM_PROMPTS = {
    "pt-BR": """Voce e um roteirista especialista em conteudo viral para Instagram Reels no Brasil.

Regras:
- Gancho forte nos primeiros 3 segundos para prender a atencao
- Cada cena deve ter entre 3-6 segundos de duracao
- Narracao de cada cena: maximo 15 palavras
- legenda_overlay de cada cena: descricao visual detalhada do cenario (15-30 palavras, ex: 'mago idoso meditando no topo de montanha com neblina ao amanhecer'). Sera usado como prompt para gerar a imagem da cena
- CTA final claro e direto
- NUNCA use termos de Star Wars (padawan, jedi, force). Para se dirigir ao espectador use expressoes de mago/feiticeiro: "meu jovem bruxo", "jovem feiticeiro", "meu caro aprendiz", "nobre aventureiro", "jovem mago"
- Linguagem PT-BR coloquial, tom {tom}
- Duracao total alvo: {duracao}s
- Nicho: {nicho}
- Keywords: {keywords}
- CTA padrao: {cta}

ESTRUTURA OBRIGATÓRIA DO ROTEIRO (5 fases):
1. GANCHO (0-3s): Primeira frase impactante, SEM saudação. Crie um gap de informação que obrigue o espectador a continuar.
2. CONTEXTO (3-5s): Por que o espectador deveria se importar. Use prova social ou conexão emocional.
3. CONTEÚDO (5-25s): Entregue o valor prometido no gancho. UMA mensagem central por vídeo. Ritmo acelerado, sem pausas mortas.
4. PAYOFF (penúltimos segundos): Entregue a promessa do gancho. Momento de satisfação que gera saves e shares.
5. LOOP/CTA (últimos segundos): A frase final deve fluir imperceptivelmente de volta ao gancho — o espectador não deve perceber onde o vídeo termina e recomeça.

A primeira cena SEMPRE é o gancho. A última cena SEMPRE termina com frase que conecta ao gancho para criar loop.

TÉCNICA DE LOOP VERBAL (OBRIGATÓRIO):
A última frase da narracao_completa deve terminar de forma que flua naturalmente de volta à primeira frase. Exemplo: se o gancho é "Ninguém fala sobre isso, mas..." a última frase pode ser "...e é exatamente isso que → ninguém fala sobre, mas..."

SEO DE VOZ (OBRIGATÓRIO):
Fale as palavras-chave principais do tema em voz alta na narração, especialmente nos primeiros 5 segundos. TikTok e YouTube indexam o áudio falado — keywords ditas em voz alta melhoram a descoberta orgânica.

{hook_type_instruction}{image_instruction}
Crie um roteiro que:
1. {cena_instruction}
2. Distribua a narracao entre as cenas de forma natural
3. Crie um gancho irresistivel
4. Termine com CTA forte
5. Gere hashtags relevantes e caption completo para o Instagram""",

    "en-US": """You are an expert scriptwriter for viral Instagram Reels content.

Rules:
- Strong hook in the first 3 seconds to grab attention
- Each scene should be 3-6 seconds long
- Narration per scene: max 15 words
- legenda_overlay for each scene: detailed visual description of the setting (15-30 words, e.g. 'old wizard meditating on mountaintop with fog at sunrise'). This will be used as a prompt to generate the scene image
- Clear and direct final CTA
- Casual {tom} tone
- Target duration: {duracao}s
- Niche: {nicho}
- Keywords: {keywords}
- Default CTA: {cta}

ESTRUTURA OBRIGATÓRIA DO ROTEIRO (5 fases):
1. GANCHO (0-3s): Primeira frase impactante, SEM saudação. Crie um gap de informação que obrigue o espectador a continuar.
2. CONTEXTO (3-5s): Por que o espectador deveria se importar. Use prova social ou conexão emocional.
3. CONTEÚDO (5-25s): Entregue o valor prometido no gancho. UMA mensagem central por vídeo. Ritmo acelerado, sem pausas mortas.
4. PAYOFF (penúltimos segundos): Entregue a promessa do gancho. Momento de satisfação que gera saves e shares.
5. LOOP/CTA (últimos segundos): A frase final deve fluir imperceptivelmente de volta ao gancho — o espectador não deve perceber onde o vídeo termina e recomeça.

A primeira cena SEMPRE é o gancho. A última cena SEMPRE termina com frase que conecta ao gancho para criar loop.

TÉCNICA DE LOOP VERBAL (OBRIGATÓRIO):
A última frase da narracao_completa deve terminar de forma que flua naturalmente de volta à primeira frase. Exemplo: se o gancho é "Ninguém fala sobre isso, mas..." a última frase pode ser "...e é exatamente isso que → ninguém fala sobre, mas..."

SEO DE VOZ (OBRIGATÓRIO):
Fale as palavras-chave principais do tema em voz alta na narração, especialmente nos primeiros 5 segundos. TikTok e YouTube indexam o áudio falado — keywords ditas em voz alta melhoram a descoberta orgânica.

{hook_type_instruction}{image_instruction}
Create a script that:
1. {cena_instruction}
2. Distributes narration naturally across scenes
3. Creates an irresistible hook
4. Ends with a strong CTA
5. Generates relevant hashtags and a complete Instagram caption""",

    "es-ES": """Eres un guionista experto en contenido viral para Instagram Reels.

Reglas:
- Gancho fuerte en los primeros 3 segundos para captar la atencion
- Cada escena debe durar entre 3-6 segundos
- Narracion por escena: maximo 15 palabras
- legenda_overlay de cada escena: descripcion visual detallada del escenario (15-30 palabras, ej: 'mago anciano meditando en la cima de una montana con niebla al amanecer'). Se usara como prompt para generar la imagen de la escena
- CTA final claro y directo
- Lenguaje coloquial, tono {tom}
- Duracion objetivo: {duracao}s
- Nicho: {nicho}
- Keywords: {keywords}
- CTA predeterminado: {cta}

ESTRUTURA OBRIGATÓRIA DO ROTEIRO (5 fases):
1. GANCHO (0-3s): Primeira frase impactante, SEM saudação. Crie um gap de informação que obrigue o espectador a continuar.
2. CONTEXTO (3-5s): Por que o espectador deveria se importar. Use prova social ou conexão emocional.
3. CONTEÚDO (5-25s): Entregue o valor prometido no gancho. UMA mensagem central por vídeo. Ritmo acelerado, sem pausas mortas.
4. PAYOFF (penúltimos segundos): Entregue a promessa do gancho. Momento de satisfação que gera saves e shares.
5. LOOP/CTA (últimos segundos): A frase final deve fluir imperceptivelmente de volta ao gancho — o espectador não deve perceber onde o vídeo termina e recomeça.

A primeira cena SEMPRE é o gancho. A última cena SEMPRE termina com frase que conecta ao gancho para criar loop.

TÉCNICA DE LOOP VERBAL (OBRIGATÓRIO):
A última frase da narracao_completa deve terminar de forma que flua naturalmente de volta à primeira frase. Exemplo: se o gancho é "Ninguém fala sobre isso, mas..." a última frase pode ser "...e é exatamente isso que → ninguém fala sobre, mas..."

SEO DE VOZ (OBRIGATÓRIO):
Fale as palavras-chave principais do tema em voz alta na narração, especialmente nos primeiros 5 segundos. TikTok e YouTube indexam o áudio falado — keywords ditas em voz alta melhoram a descoberta orgânica.

{hook_type_instruction}{image_instruction}
Crea un guion que:
1. {cena_instruction}
2. Distribuya la narracion entre las escenas de forma natural
3. Cree un gancho irresistible
4. Termine con un CTA fuerte
5. Genere hashtags relevantes y un caption completo para Instagram""",
}

# Fallback for unsupported languages: use English template with language instruction
_SYSTEM_PROMPT_FALLBACK = """You are an expert scriptwriter for viral Instagram Reels content.
IMPORTANT: Write ALL narration, captions, hashtags, and CTA in {language}.

Rules:
- Strong hook in the first 3 seconds to grab attention
- Each scene should be 3-6 seconds long
- Narration per scene: max 15 words
- legenda_overlay for each scene: detailed visual description of the setting (15-30 words). This will be used as a prompt to generate the scene image. Write legenda_overlay in English regardless of output language.
- Clear and direct final CTA
- Casual {tom} tone
- Target duration: {duracao}s
- Niche: {nicho}
- Keywords: {keywords}
- Default CTA: {cta}

ESTRUTURA OBRIGATÓRIA DO ROTEIRO (5 fases):
1. GANCHO (0-3s): Primeira frase impactante, SEM saudação. Crie um gap de informação que obrigue o espectador a continuar.
2. CONTEXTO (3-5s): Por que o espectador deveria se importar. Use prova social ou conexão emocional.
3. CONTEÚDO (5-25s): Entregue o valor prometido no gancho. UMA mensagem central por vídeo. Ritmo acelerado, sem pausas mortas.
4. PAYOFF (penúltimos segundos): Entregue a promessa do gancho. Momento de satisfação que gera saves e shares.
5. LOOP/CTA (últimos segundos): A frase final deve fluir imperceptivelmente de volta ao gancho — o espectador não deve perceber onde o vídeo termina e recomeça.

A primeira cena SEMPRE é o gancho. A última cena SEMPRE termina com frase que conecta ao gancho para criar loop.

TÉCNICA DE LOOP VERBAL (OBRIGATÓRIO):
A última frase da narracao_completa deve terminar de forma que flua naturalmente de volta à primeira frase. Exemplo: se o gancho é "Ninguém fala sobre isso, mas..." a última frase pode ser "...e é exatamente isso que → ninguém fala sobre, mas..."

SEO DE VOZ (OBRIGATÓRIO):
Fale as palavras-chave principais do tema em voz alta na narração, especialmente nos primeiros 5 segundos. TikTok e YouTube indexam o áudio falado — keywords ditas em voz alta melhoram a descoberta orgânica.

{hook_type_instruction}{image_instruction}
Create a script that:
1. {cena_instruction}
2. Distributes narration naturally across scenes
3. Creates an irresistible hook
4. Ends with a strong CTA
5. Generates relevant hashtags and a complete Instagram caption"""


async def generate_script(
    image_paths: list[str] | None = None,
    tema: str = "",
    config_override: dict | None = None,
    character_context: dict | None = None,
) -> dict:
    """Generate a structured roteiro (script) via Gemini.

    Supports two modes:
    - Multimodal (image_paths provided): sends images + text to Gemini
    - Text-only (image_paths=None): generates script from tema text only (v2 interactive)

    Args:
        image_paths: Optional paths to reel images. None for text-only mode.
        tema: Theme/topic for the script.
        config_override: Optional DB config values to merge with defaults.
        character_context: Optional dict with character persona (name, system_prompt, humor_style, tone).

    Returns:
        Parsed JSON dict matching RoteiroSchema structure.
    """
    cfg = config_override or {}
    tom = cfg.get("tone", "inspiracional")
    duracao = cfg.get("target_duration", 30)
    nicho = cfg.get("niche", "lifestyle")
    keywords = ", ".join(cfg.get("keywords", []))
    cta = cfg.get("cta_default", "salve esse post")
    language = cfg.get("script_language", REELS_SCRIPT_LANGUAGE)
    model = cfg.get("script_model", REELS_SCRIPT_MODEL)

    # Inject character persona into script generation
    character_section = ""
    if character_context:
        char_name = character_context.get("name", "")
        char_prompt = character_context.get("system_prompt", "")
        char_humor = character_context.get("humor_style", "")
        char_tone = character_context.get("tone", "")
        if char_prompt:
            character_section = (
                f"\n\nPERSONAGEM: {char_name}\n"
                f"Use a persona deste personagem para narrar o Reel:\n{char_prompt}\n"
                f"Estilo de humor: {char_humor}\nTom: {char_tone}\n"
                f"A narracao deve soar como se o personagem estivesse falando diretamente."
            )
            tom = char_tone or tom

    if image_paths:
        n_imagens = len(image_paths)
        if language.startswith("pt"):
            image_instruction = f"Voce recebera {n_imagens} imagens que serao usadas no Reel."
            cena_instruction = f"Use cada imagem em ordem (imagem_index 0 a {n_imagens - 1})"
        elif language.startswith("es"):
            image_instruction = f"Recibiras {n_imagens} imagenes que se usaran en el Reel."
            cena_instruction = f"Usa cada imagen en orden (imagem_index 0 a {n_imagens - 1})"
        else:
            image_instruction = f"You will receive {n_imagens} images to use in the Reel."
            cena_instruction = f"Use each image in order (imagem_index 0 to {n_imagens - 1})"
    else:
        # Dynamic: duration drives scene count (~1 cena per 4-6s of content)
        min_cenas = max(3, duracao // 6)
        max_cenas = max(5, duracao // 4)
        if language.startswith("pt"):
            image_instruction = (
                f"Cada cena gerara uma imagem. Crie entre {min_cenas} e {max_cenas} cenas "
                f"para cobrir o tema em ~{duracao}s."
            )
            cena_instruction = "Uma cena por momento-chave do roteiro (imagem_index sequencial a partir de 0)"
        elif language.startswith("es"):
            image_instruction = (
                f"Cada escena generara una imagen. Crea entre {min_cenas} y {max_cenas} escenas "
                f"para cubrir el tema en ~{duracao}s."
            )
            cena_instruction = "Una escena por momento clave del guion (imagem_index secuencial desde 0)"
        else:
            image_instruction = (
                f"Each scene will generate an image. Create between {min_cenas} and {max_cenas} scenes "
                f"to cover the topic in ~{duracao}s."
            )
            cena_instruction = "One scene per key moment in the script (imagem_index sequential from 0)"

    # Build hook_type instruction if provided in config
    hook_type = cfg.get("hook_type")
    if hook_type:
        hook_type_instruction = (
            f"TIPO DE GANCHO: {hook_type}\n"
            "- curiosidade: Abra um loop mental (ex: \"Ninguém fala sobre isso, mas...\")\n"
            "- dor: Toque na frustração (ex: \"Para de fazer [ERRO] agora!\")\n"
            "- contrario: Desafie crença popular (ex: \"Tudo que você sabia sobre [X] está errado\")\n"
            "- autoridade: Mostre resultado concreto (ex: \"Como eu fui de [X] para [Y]\")\n"
            "- resultado: Mostre o final primeiro (ex: \"[RESULTADO] — e aqui está como\")\n"
            "Use este tipo de gancho no roteiro.\n\n"
        )
    else:
        hook_type_instruction = ""

    # Select language-appropriate system prompt template
    prompt_template = _SYSTEM_PROMPTS.get(language)
    if prompt_template:
        system_prompt = prompt_template.format(
            tom=tom,
            duracao=duracao,
            nicho=nicho,
            keywords=keywords or ("nenhuma" if language.startswith("pt") else "none"),
            cta=cta,
            image_instruction=image_instruction,
            cena_instruction=cena_instruction,
            hook_type_instruction=hook_type_instruction,
        )
    else:
        system_prompt = _SYSTEM_PROMPT_FALLBACK.format(
            language=language,
            tom=tom,
            duracao=duracao,
            nicho=nicho,
            keywords=keywords or "none",
            cta=cta,
            image_instruction=image_instruction,
            cena_instruction=cena_instruction,
            hook_type_instruction=hook_type_instruction,
        )
    system_prompt += character_section

    # Build content parts
    parts = []
    if image_paths:
        for img_path in image_paths:
            img_bytes = Path(img_path).read_bytes()
            mime = "image/jpeg" if img_path.lower().endswith((".jpg", ".jpeg")) else "image/png"
            parts.append(types.Part.from_bytes(data=img_bytes, mime_type=mime))
        user_prompt = (
            f"Tema do Reel: {tema}\n"
            f"Idioma: {language}\n"
            f"Crie o roteiro completo para este Reel usando as {len(image_paths)} imagens acima."
        )
    else:
        # v2 text-only: script generates from tema text before images exist
        user_prompt = (
            f"Tema do Reel: {tema}\n"
            f"Idioma: {language}\n"
            f"Crie o roteiro completo para este Reel.\n"
            f"IMPORTANTE: Em cada cena, o campo 'legenda_overlay' deve descrever detalhadamente "
            f"o cenario visual, objetos, acoes e ambiente da cena (ex: 'mago meditando em montanha ao amanhecer', "
            f"'pessoa servindo cafe em cozinha moderna', 'close no rosto com expressao de surpresa'). "
            f"Esse campo sera usado diretamente como prompt para gerar a imagem da cena. "
            f"Quanto mais descritivo e visual, melhor a imagem gerada."
        )
    parts.append(user_prompt)

    client = _get_client()
    response = client.models.generate_content(
        model=model,
        contents=parts,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_schema=ROTEIRO_SCHEMA,
            temperature=0.9,
        ),
    )

    script = json.loads(response.text)
    logger.info(f"Script generated: titulo='{script.get('titulo')}', cenas={len(script.get('cenas', []))}")
    return script
