"""Wrapper para treinamento de LoRA do Mago Mestre.

Valida ambiente, prepara dataset e lanca treinamento via kohya_ss.

Uso:
    python scripts/train_lora.py
    python scripts/train_lora.py --skip-dataset   # se dataset ja esta pronto
    python scripts/train_lora.py --epochs 100      # customizar epochs
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

CLIP_FLOW_DIR = Path(__file__).parent.parent
COMFYUI_DIR = CLIP_FLOW_DIR.parent / "comfyui"
KOHYA_DIR = CLIP_FLOW_DIR.parent / "kohya_ss"
DATASET_DIR = CLIP_FLOW_DIR / "lora_training" / "dataset" / "1_ohwx_mago"
OUTPUT_DIR = CLIP_FLOW_DIR / "lora_training" / "output"
CONFIG_PATH = CLIP_FLOW_DIR / "scripts" / "train_lora.toml"


def check_environment():
    """Verifica prerequisitos para treinamento."""
    print("Verificando ambiente...\n")

    # Python
    print(f"  Python: {sys.version}")

    # CUDA
    try:
        import torch
        if torch.cuda.is_available():
            gpu = torch.cuda.get_device_name(0)
            vram = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            print(f"  GPU: {gpu} ({vram:.1f} GB VRAM)")
        else:
            print("  ERRO: CUDA nao disponivel. Verifique PyTorch com CUDA.")
            sys.exit(1)
    except ImportError:
        print("  ERRO: PyTorch nao encontrado.")
        sys.exit(1)

    # kohya_ss
    if not KOHYA_DIR.exists():
        print(f"\n  kohya_ss nao encontrado em: {KOHYA_DIR}")
        print("  Instalando...")
        install_kohya()
    else:
        print(f"  kohya_ss: {KOHYA_DIR}")

    # Modelo Flux Dev (completo, nao GGUF)
    flux_model = CLIP_FLOW_DIR.parent / "flux1-dev.safetensors"
    if not flux_model.exists():
        print(f"\n  AVISO: Modelo Flux Dev completo nao encontrado em: {flux_model}")
        print("  O treino de LoRA requer o modelo COMPLETO (~23.8 GB), nao o GGUF.")
        print("  Baixe de: https://huggingface.co/black-forest-labs/FLUX.1-dev")
        print(f"  Salve como: {flux_model}")
        print()
        print("  Alternativa: use um caminho diferente editando scripts/train_lora.toml")
        print("    [model] pretrained_model_name_or_path = '/caminho/do/modelo'")
    else:
        size_gb = flux_model.stat().st_size / (1024**3)
        print(f"  Modelo Flux Dev: {flux_model} ({size_gb:.1f} GB)")

    print()


def install_kohya():
    """Instala kohya_ss (sd-scripts)."""
    print(f"  Clonando kohya_ss em: {KOHYA_DIR}")
    subprocess.run([
        "git", "clone", "https://github.com/kohya-ss/sd-scripts.git",
        str(KOHYA_DIR),
    ], check=True)

    print("  Instalando dependencias...")
    subprocess.run([
        sys.executable, "-m", "pip", "install", "-r",
        str(KOHYA_DIR / "requirements.txt"),
    ], cwd=str(KOHYA_DIR), check=True)

    # Instalar accelerate
    subprocess.run([
        sys.executable, "-m", "pip", "install", "accelerate",
    ], check=True)


def prepare_dataset():
    """Executa prepare_lora_dataset.py."""
    print("Preparando dataset...\n")
    script = CLIP_FLOW_DIR / "scripts" / "prepare_lora_dataset.py"
    subprocess.run([sys.executable, str(script)], check=True)
    print()


def run_training(epochs: int | None = None):
    """Lanca treinamento de LoRA via kohya_ss."""
    print("Iniciando treinamento de LoRA...\n")

    # Verificar dataset
    if not DATASET_DIR.exists() or not list(DATASET_DIR.glob("*.png")):
        print(f"  ERRO: Dataset nao encontrado em {DATASET_DIR}")
        print("  Execute: python scripts/prepare_lora_dataset.py")
        sys.exit(1)

    n_images = len(list(DATASET_DIR.glob("*.png")))
    print(f"  Dataset: {n_images} imagens")
    print(f"  Config: {CONFIG_PATH}")
    print(f"  Output: {OUTPUT_DIR}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Montar comando
    train_script = KOHYA_DIR / "flux_train_network.py"
    if not train_script.exists():
        # Fallback para versao mais antiga
        train_script = KOHYA_DIR / "train_network.py"

    # Tentar accelerate CLI (Scripts dir pode nao estar no PATH)
    accelerate_exe = Path(sys.executable).parent / "Scripts" / "accelerate.exe"
    if accelerate_exe.exists():
        cmd = [
            str(accelerate_exe), "launch",
            "--mixed_precision", "fp16",
            str(train_script),
            "--config_file", str(CONFIG_PATH),
        ]
    else:
        # Fallback: rodar direto (funciona para GPU unica)
        cmd = [
            sys.executable, str(train_script),
            "--config_file", str(CONFIG_PATH),
            "--mixed_precision", "fp16",
        ]

    if epochs:
        cmd.extend(["--max_train_epochs", str(epochs)])

    print(f"\n  Comando: {' '.join(cmd[:6])}...")
    print(f"\n  Isso vai levar ~30-60 minutos na RTX 4060 Ti.")
    print(f"  Acompanhe via TensorBoard: tensorboard --logdir lora_training/logs")
    print("-" * 50)

    try:
        subprocess.run(cmd, cwd=str(CLIP_FLOW_DIR), check=True)
    except subprocess.CalledProcessError as e:
        print(f"\n  ERRO: Treinamento falhou com codigo {e.returncode}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n  Treinamento interrompido pelo usuario.")
        sys.exit(0)

    print("\n  Treinamento concluido!")
    copy_lora_to_comfyui()


def copy_lora_to_comfyui():
    """Copia LoRA treinada para o diretorio de modelos do ComfyUI."""
    lora_files = list(OUTPUT_DIR.glob("mago_mestre_v1*.safetensors"))
    if not lora_files:
        print("  Nenhum arquivo LoRA encontrado no output.")
        return

    # Pegar o arquivo mais recente
    latest = max(lora_files, key=lambda f: f.stat().st_mtime)
    dest_dir = COMFYUI_DIR / "models" / "loras"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / "mago_mestre_v1.safetensors"

    shutil.copy2(str(latest), str(dest))
    print(f"\n  LoRA copiada para ComfyUI: {dest}")
    print(f"  Arquivo fonte: {latest}")
    print(f"\n  Pronto! Use --comfyui no pipeline para gerar backgrounds com LoRA.")


def main():
    parser = argparse.ArgumentParser(description="Treinar LoRA do Mago Mestre")
    parser.add_argument(
        "--skip-dataset",
        action="store_true",
        help="Pular preparacao do dataset (se ja preparado)",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=None,
        help="Numero de epochs (padrao: 200, definido no .toml)",
    )
    parser.add_argument(
        "--copy-only",
        action="store_true",
        help="Apenas copiar LoRA existente para ComfyUI (sem treinar)",
    )
    args = parser.parse_args()

    if args.copy_only:
        copy_lora_to_comfyui()
        return

    check_environment()

    if not args.skip_dataset:
        prepare_dataset()

    run_training(args.epochs)


if __name__ == "__main__":
    main()
