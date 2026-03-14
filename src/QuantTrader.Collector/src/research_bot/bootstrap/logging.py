from __future__ import annotations

import logging
import sys


def configure_logging() -> None:
    logger = logging.getLogger("research_bot")
    if logger.handlers:
        logger.setLevel(logging.INFO)
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(message)s",
            datefmt="%H:%M:%S",
        )
    )
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
