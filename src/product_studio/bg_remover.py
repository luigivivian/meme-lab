"""Background removal from product photos via rembg. Per D-05."""

import logging
from pathlib import Path

from PIL import Image
from rembg import remove, new_session

from src.product_studio.config import ADS_REMBG_MODEL

logger = logging.getLogger("clip-flow.ads.bg_remover")


def remove_background(input_path: str, output_path: str) -> str:
    """Remove background from product photo. Returns path to RGBA PNG.

    Per D-05: rembg local, zero API cost.
    Per D-07: foto original -> rembg remove bg -> RGBA cutout.
    """
    img = Image.open(input_path)
    session = new_session(model_name=ADS_REMBG_MODEL)
    result = remove(img, session=session)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    result.save(output_path, "PNG")
    logger.info("Background removed: %s -> %s", input_path, output_path)
    return output_path
