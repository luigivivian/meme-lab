import argparse
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import BACKGROUNDS_DIR, OUTPUT_DIR
from src.image_maker import create_image, create_placeholder_background
from src.phrases import generate_phrases


def _get_backgrounds() -> list[str]:
    """Retorna lista de imagens de fundo disponíveis."""
    extensions = ("*.jpg", "*.jpeg", "*.png", "*.webp")
    backgrounds = []
    for ext in extensions:
        backgrounds.extend(BACKGROUNDS_DIR.glob(ext))
    return [str(p) for p in backgrounds]


def _ensure_background() -> list[str]:
    """Garante que há pelo menos um background disponível."""
    backgrounds = _get_backgrounds()
    if not backgrounds:
        print("Nenhum background encontrado. Criando placeholder para teste...")
        BACKGROUNDS_DIR.mkdir(parents=True, exist_ok=True)
        placeholder = str(BACKGROUNDS_DIR / "placeholder.png")
        create_placeholder_background(placeholder)
        backgrounds = [placeholder]
    return backgrounds


def main():
    parser = argparse.ArgumentParser(
        description="Clip-Flow: Gerador de memes Gandalf Sincero"
    )
    parser.add_argument(
        "--topic",
        type=str,
        help="Tema para gerar frases automaticamente via IA",
    )
    parser.add_argument(
        "--text",
        type=str,
        help="Texto específico para criar uma imagem",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=3,
        help="Quantidade de frases/imagens a gerar (padrão: 3)",
    )
    parser.add_argument(
        "--bg",
        type=str,
        help="Caminho de um background específico",
    )

    args = parser.parse_args()

    if not args.topic and not args.text:
        parser.print_help()
        print("\nExemplos:")
        print('  python -m src.cli --topic "segunda-feira" --count 5')
        print('  python -m src.cli --text "Você não passa... da primeira fase"')
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Obter backgrounds
    if args.bg:
        if not os.path.exists(args.bg):
            print(f"Erro: Background não encontrado: {args.bg}")
            sys.exit(1)
        backgrounds = [args.bg]
    else:
        backgrounds = _ensure_background()

    # Modo com texto manual
    if args.text:
        bg = random.choice(backgrounds)
        output = create_image(args.text, bg)
        print(f"Imagem gerada: {output}")
        return

    # Modo com geração via IA
    print(f"Gerando {args.count} frases sobre '{args.topic}'...")
    phrases = generate_phrases(args.topic, args.count)

    print(f"\nFrases geradas:")
    for i, phrase in enumerate(phrases, 1):
        print(f"  {i}. {phrase}")

    print(f"\nCriando {len(phrases)} imagens...")
    for phrase in phrases:
        bg = random.choice(backgrounds)
        output = create_image(phrase, bg)
        print(f"  -> {output}")

    print(f"\nPronto! {len(phrases)} imagens salvas em {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
