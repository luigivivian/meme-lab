import os
import sys

from dotenv import load_dotenv
import anthropic

load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import SYSTEM_PROMPT


def generate_phrases(topic: str, count: int = 5) -> list[str]:
    """Gera frases sarcásticas no estilo Gandalf Sincero via Claude API."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key or api_key == "your-api-key-here":
        print("Erro: Configure ANTHROPIC_API_KEY no arquivo .env")
        print("Obtenha sua chave em: https://console.anthropic.com/settings/keys")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Gere {count} frases sobre o tema: {topic}",
            }
        ],
    )

    raw_text = message.content[0].text
    phrases = [line.strip() for line in raw_text.strip().splitlines() if line.strip()]
    return phrases
