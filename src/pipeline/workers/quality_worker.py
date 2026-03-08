"""QualityWorker — valida qualidade da imagem gerada.

Verifica existencia, resolucao e dimensoes corretas.
"""

import logging
from pathlib import Path

from PIL import Image

from config import IMAGE_WIDTH, IMAGE_HEIGHT, QUALITY_MIN_SCORE
from src.pipeline.models_v2 import ContentPackage

logger = logging.getLogger("clip-flow.worker.quality")


class QualityWorker:
    """Valida qualidade das imagens geradas."""

    async def validate(self, package: ContentPackage) -> float:
        """Valida imagem e retorna quality_score (0.0 a 1.0).

        Verificacoes:
        - Arquivo existe e e legivel
        - Dimensoes corretas (1080x1350)
        - Tamanho minimo do arquivo (nao esta corrompido)
        """
        score = 0.0
        path = Path(package.image_path)

        # Verificar existencia
        if not path.exists():
            logger.error(f"Imagem nao encontrada: {path}")
            return 0.0

        score += 0.2  # arquivo existe

        # Verificar tamanho minimo (>10KB = provavelmente nao corrompido)
        file_size = path.stat().st_size
        if file_size < 10_000:
            logger.warning(f"Imagem muito pequena ({file_size} bytes): {path}")
            return score

        score += 0.2  # tamanho OK

        # Verificar dimensoes
        try:
            with Image.open(path) as img:
                width, height = img.size

                if width == IMAGE_WIDTH and height == IMAGE_HEIGHT:
                    score += 0.4  # dimensoes perfeitas
                    logger.debug(f"Dimensoes OK: {width}x{height}")
                else:
                    # Proporcional — quao perto esta do ideal
                    w_ratio = min(width, IMAGE_WIDTH) / max(width, IMAGE_WIDTH)
                    h_ratio = min(height, IMAGE_HEIGHT) / max(height, IMAGE_HEIGHT)
                    dim_score = (w_ratio + h_ratio) / 2 * 0.4
                    score += dim_score
                    logger.warning(
                        f"Dimensoes inesperadas: {width}x{height} "
                        f"(esperado {IMAGE_WIDTH}x{IMAGE_HEIGHT})"
                    )

                # Verificar se a imagem e RGB/RGBA (nao grayscale)
                if img.mode in ("RGB", "RGBA"):
                    score += 0.2
                else:
                    logger.warning(f"Modo de cor inesperado: {img.mode}")
                    score += 0.1

        except Exception as e:
            logger.error(f"Erro ao abrir imagem {path}: {e}")

        logger.info(f"Quality score: {score:.2f} para {path.name}")
        return round(score, 2)
