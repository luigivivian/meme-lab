"""Inicia o servidor ComfyUI com configuracoes otimizadas para RTX 4060 Ti 8GB.

Uso:
    python scripts/start_comfyui.py
    python scripts/start_comfyui.py --normalvram   # se tiver 16GB
"""

import argparse
import subprocess
import sys
from pathlib import Path

COMFYUI_DIR = Path(__file__).parent.parent.parent / "comfyui"
COMFYUI_MAIN = COMFYUI_DIR / "main.py"


def main():
    parser = argparse.ArgumentParser(description="Inicia servidor ComfyUI")
    parser.add_argument(
        "--normalvram",
        action="store_true",
        help="Usar modo normal (16GB+ VRAM). Padrao: --lowvram para 8GB",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8188,
        help="Porta do servidor (padrao: 8188)",
    )
    args = parser.parse_args()

    if not COMFYUI_DIR.exists():
        print(f"ERRO: ComfyUI nao encontrado em {COMFYUI_DIR}")
        print("Execute primeiro: python scripts/setup_comfyui.py")
        sys.exit(1)

    if not COMFYUI_MAIN.exists():
        print(f"ERRO: main.py nao encontrado em {COMFYUI_MAIN}")
        sys.exit(1)

    cmd = [
        sys.executable,
        str(COMFYUI_MAIN),
        "--listen", "127.0.0.1",
        "--port", str(args.port),
    ]

    if not args.normalvram:
        cmd.append("--lowvram")
        print("Modo: --lowvram (otimizado para 8GB VRAM)")
    else:
        print("Modo: normalvram (16GB+ VRAM)")

    print(f"Diretorio: {COMFYUI_DIR}")
    print(f"Servidor: http://127.0.0.1:{args.port}")
    print(f"Comando: {' '.join(cmd)}")
    print("-" * 50)

    try:
        subprocess.run(cmd, cwd=str(COMFYUI_DIR))
    except KeyboardInterrupt:
        print("\nServidor ComfyUI encerrado.")


if __name__ == "__main__":
    main()
