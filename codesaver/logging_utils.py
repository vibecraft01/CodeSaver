"""Small logging setup shared by CLI execution paths."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Union

LOGGER_NAME = "codesaver"


def configure_logging(path: Optional[Union[Path, str]]) -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
    if path:
        log_path = Path(path).expanduser().resolve()
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            handler = logging.FileHandler(log_path, encoding="utf-8")
        except OSError as exc:
            raise OSError(str(exc)) from exc
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
    else:
        logger.addHandler(logging.NullHandler())
    return logger
