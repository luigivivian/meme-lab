import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import SYSTEM_PROMPT
from src.llm_client import generate


def generate_phrases(topic: str, count: int = 5) -> list[str]:
    """Gera frases engracadas no estilo Gandalf Sincero via Gemini API."""
    raw_text = generate(
        system_prompt=SYSTEM_PROMPT,
        user_message=f"Gere {count} frases sobre o tema: {topic}",
        max_tokens=2048,
    )

    phrases = [line.strip() for line in raw_text.strip().splitlines() if line.strip()]
    return phrases
