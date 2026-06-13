from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Optional

from paths import get_app_root


LOG_DIR = get_app_root() / "logs"
LATEST_LOG = LOG_DIR / "latest.log"
PREVIOUS_LOG = LOG_DIR / "previous.log"


class _BracketFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        timestamp = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        source = record.name.split(".")[-1] if record.name else "app"
        message = record.getMessage()
        return f"[{timestamp}] [{record.levelname}] [{source}] {message}"


def initialize_logging(enabled: bool = True, verbose: bool = False) -> Optional[Path]:
    if not enabled:
        logging.getLogger().handlers.clear()
        logging.getLogger().setLevel(logging.CRITICAL)
        return None

    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        if LATEST_LOG.exists():
            try:
                if PREVIOUS_LOG.exists():
                    PREVIOUS_LOG.unlink()
            except Exception:
                pass
            try:
                shutil.copy2(LATEST_LOG, PREVIOUS_LOG)
            except Exception:
                pass
            try:
                LATEST_LOG.unlink()
            except Exception:
                pass

        root = logging.getLogger()
        root.handlers.clear()
        root.setLevel(logging.DEBUG if verbose else logging.INFO)
        handler = logging.FileHandler(LATEST_LOG, encoding="utf-8")
        handler.setLevel(logging.DEBUG if verbose else logging.INFO)
        handler.setFormatter(_BracketFormatter())
        root.addHandler(handler)
        return LATEST_LOG
    except Exception:
        logging.getLogger().handlers.clear()
        logging.getLogger().setLevel(logging.CRITICAL)
        return None


def get_log_paths() -> tuple[Path, Path]:
    return LATEST_LOG, PREVIOUS_LOG
