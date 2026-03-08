"""Script de instalacao do ComfyUI e modelos para geracao local de backgrounds.

Instala ComfyUI, custom nodes necessarios e baixa modelos Flux Dev GGUF.
Requer: git, Python 3.10+, ~8GB de espaco em disco.

Uso:
    python scripts/setup_comfyui.py
"""

import os
import subprocess
import sys
from pathlib import Path

# Diretorio do ComfyUI (irmao do clip-flow)
CLIP_FLOW_DIR = Path(__file__).parent.parent
COMFYUI_DIR = CLIP_FLOW_DIR.parent / "comfyui"

# Modelos a baixar (caminho relativo ao ComfyUI models/)
MODELS = {
    "diffusion_models/flux1-dev-Q4_K_S.gguf": {
        "url": "https://huggingface.co/city96/FLUX.1-dev-gguf/resolve/main/flux1-dev-Q4_K_S.gguf",
        "size": "~4.0 GB",
    },
    "clip/t5-v1_1-xxl-encoder-Q3_K_S.gguf": {
        "url": "https://huggingface.co/city96/t5-v1_1-xxl-encoder-gguf/resolve/main/t5-v1_1-xxl-encoder-Q3_K_S.gguf",
        "size": "~2.5 GB",
    },
    "clip/clip_l.safetensors": {
        "url": "https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/clip_l.safetensors",
        "size": "~235 MB",
    },
    "vae/ae.safetensors": {
        "url": "https://huggingface.co/black-forest-labs/FLUX.1-dev/resolve/main/ae.safetensors",
        "size": "~335 MB",
    },
}

# Custom nodes necessarios
CUSTOM_NODES = {
    "ComfyUI-GGUF": "https://github.com/city96/ComfyUI-GGUF.git",
}


def print_header(msg: str):
    print(f"\n{'=' * 60}")
    print(f"  {msg}")
    print(f"{'=' * 60}\n")


def run_cmd(cmd: list[str], cwd: str | None = None) -> bool:
    """Executa comando e retorna True se sucesso."""
    try:
        subprocess.run(cmd, cwd=cwd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ERRO: Comando falhou com codigo {e.returncode}")
        return False
    except FileNotFoundError:
        print(f"  ERRO: Comando nao encontrado: {cmd[0]}")
        return False


def check_prerequisites():
    """Verifica prerequisitos do sistema."""
    print_header("Verificando prerequisitos")

    # Git
    try:
        result = subprocess.run(["git", "--version"], capture_output=True, text=True)
        print(f"  Git: {result.stdout.strip()}")
    except FileNotFoundError:
        print("  ERRO: Git nao encontrado. Instale: https://git-scm.com/")
        sys.exit(1)

    # Python
    print(f"  Python: {sys.version}")

    # CUDA
    try:
        result = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                                capture_output=True, text=True)
        print(f"  GPU: {result.stdout.strip()}")
    except FileNotFoundError:
        print("  AVISO: nvidia-smi nao encontrado. Verifique drivers NVIDIA.")

    print()


def install_comfyui():
    """Clona e configura o ComfyUI."""
    print_header("Instalando ComfyUI")

    if COMFYUI_DIR.exists():
        print(f"  ComfyUI ja existe em: {COMFYUI_DIR}")
        print("  Pulando clone...")
    else:
        print(f"  Clonando ComfyUI em: {COMFYUI_DIR}")
        if not run_cmd(["git", "clone", "https://github.com/comfyanonymous/ComfyUI.git",
                        str(COMFYUI_DIR)]):
            print("  ERRO: Falha ao clonar ComfyUI")
            sys.exit(1)

    # Instalar dependencias do ComfyUI
    print("\n  Instalando dependencias do ComfyUI...")
    requirements = COMFYUI_DIR / "requirements.txt"
    if requirements.exists():
        run_cmd([sys.executable, "-m", "pip", "install", "-r", str(requirements)])

    # Instalar PyTorch com CUDA (se necessario)
    print("\n  Verificando PyTorch com CUDA...")
    try:
        import torch
        if torch.cuda.is_available():
            print(f"  PyTorch {torch.__version__} com CUDA OK")
        else:
            print("  AVISO: PyTorch sem suporte CUDA. Reinstale com CUDA:")
            print("    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124")
    except ImportError:
        print("  PyTorch nao encontrado. Instalando com CUDA...")
        run_cmd([sys.executable, "-m", "pip", "install", "torch", "torchvision", "torchaudio",
                 "--index-url", "https://download.pytorch.org/whl/cu124"])


def install_custom_nodes():
    """Instala custom nodes necessarios."""
    print_header("Instalando custom nodes")

    custom_nodes_dir = COMFYUI_DIR / "custom_nodes"
    custom_nodes_dir.mkdir(parents=True, exist_ok=True)

    for name, repo_url in CUSTOM_NODES.items():
        node_dir = custom_nodes_dir / name
        if node_dir.exists():
            print(f"  {name} ja instalado, atualizando...")
            run_cmd(["git", "pull"], cwd=str(node_dir))
        else:
            print(f"  Clonando {name}...")
            run_cmd(["git", "clone", repo_url, str(node_dir)])

        # Instalar dependencias do custom node
        node_requirements = node_dir / "requirements.txt"
        if node_requirements.exists():
            print(f"  Instalando dependencias de {name}...")
            run_cmd([sys.executable, "-m", "pip", "install", "-r", str(node_requirements)])


def download_models():
    """Baixa modelos necessarios para Flux Dev GGUF."""
    print_header("Baixando modelos (~7 GB total)")

    models_dir = COMFYUI_DIR / "models"

    for rel_path, info in MODELS.items():
        full_path = models_dir / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        if full_path.exists():
            size_mb = full_path.stat().st_size / (1024 * 1024)
            print(f"  {rel_path} ja existe ({size_mb:.0f} MB)")
            continue

        print(f"\n  Baixando: {rel_path} ({info['size']})")
        print(f"  URL: {info['url']}")
        print(f"  Destino: {full_path}")

        # Usar huggingface-cli se disponivel, senao curl/wget
        success = False

        # Tentar com huggingface-cli
        try:
            subprocess.run(["huggingface-cli", "--version"], capture_output=True, check=True)
            success = run_cmd([
                "huggingface-cli", "download",
                "--local-dir", str(full_path.parent),
                "--local-dir-use-symlinks", "False",
                info["url"].split("huggingface.co/")[1].split("/resolve/")[0],
                full_path.name,
            ])
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass

        # Fallback: curl
        if not success:
            print("  Usando curl para download...")
            success = run_cmd([
                "curl", "-L", "-o", str(full_path),
                "--progress-bar", info["url"],
            ])

        # Fallback: Python requests
        if not success:
            print("  Usando Python requests para download...")
            try:
                import requests
                response = requests.get(info["url"], stream=True)
                response.raise_for_status()
                total = int(response.headers.get("content-length", 0))
                downloaded = 0

                with open(full_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total:
                            pct = (downloaded / total) * 100
                            print(f"\r  {pct:.1f}% ({downloaded / 1024 / 1024:.0f} MB)", end="")
                print()
                success = True
            except Exception as e:
                print(f"  ERRO no download: {e}")

        if not success:
            print(f"\n  FALHA: Nao foi possivel baixar {rel_path}")
            print(f"  Baixe manualmente de: {info['url']}")
            print(f"  Salve em: {full_path}")


def create_lora_dir():
    """Cria diretorio para LoRA no ComfyUI."""
    lora_dir = COMFYUI_DIR / "models" / "loras"
    lora_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n  Diretorio LoRA: {lora_dir}")
    print("  Apos treinar a LoRA, copie o arquivo .safetensors para ca.")


def print_summary():
    """Exibe resumo da instalacao."""
    print_header("Instalacao completa!")

    print(f"""  ComfyUI instalado em: {COMFYUI_DIR}

  Proximo passo — iniciar o servidor:
    python scripts/start_comfyui.py

  Ou manualmente:
    cd {COMFYUI_DIR}
    python main.py --listen 127.0.0.1 --port 8188 --lowvram

  Para treinar a LoRA do Mago Mestre:
    python scripts/train_lora.py

  Para usar no pipeline:
    python -m src.pipeline_cli --mode once --count 5 --comfyui --verbose
""")


def main():
    print_header("Setup ComfyUI — Clip-Flow")
    print("  Este script instala ComfyUI + Flux Dev GGUF para geracao local.")
    print(f"  Diretorio de instalacao: {COMFYUI_DIR}")
    print(f"  Espaco necessario: ~8 GB")

    check_prerequisites()
    install_comfyui()
    install_custom_nodes()
    download_models()
    create_lora_dir()
    print_summary()


if __name__ == "__main__":
    main()
