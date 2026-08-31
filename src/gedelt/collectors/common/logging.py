
from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

from src.gedelt.collectors.common.config import PROJECT_ROOT, load_logging_config

_CONFIGURED = False


def configure_logging(path: str = "config/settings/logging.yaml") -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    cfg = load_logging_config(path)

    root_logger = logging.getLogger()
    root_logger.setLevel(cfg.level)

    formatter = logging.Formatter(fmt=cfg.format, datefmt=cfg.date_format)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    if cfg.log_to_file:
        log_dir = PROJECT_ROOT / cfg.log_dir
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_dir / cfg.log_file,
            maxBytes=cfg.max_bytes,
            backupCount=cfg.backup_count,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Third-party libraries are noisy at DEBUG/INFO; keep them at WARNING
    # unless the project itself is configured for DEBUG.
    if cfg.level != "DEBUG":
        logging.getLogger("google").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("pymongo").setLevel(logging.WARNING)

    _CONFIGURED = True
