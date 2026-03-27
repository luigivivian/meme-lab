"""Entrypoint: python -m src.services.scheduler_worker"""

import asyncio
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)

from src.services.scheduler_worker import _main

asyncio.run(_main())
