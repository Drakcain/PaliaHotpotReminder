from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable


SOURCE_ROOT = Path(__file__).resolve().parent.parent
IS_FROZEN = bool(getattr(sys, "frozen", False))
APP_ROOT = Path(sys.executable).resolve().parent if IS_FROZEN else SOURCE_ROOT


def get_source_root() -> Path:
    return SOURCE_ROOT


def get_app_root() -> Path:
    return APP_ROOT


def is_frozen() -> bool:
    return IS_FROZEN


def resolve_path(*parts: str | Path, root: Path | None = None) -> Path:
    base = root or APP_ROOT
    return base.joinpath(*parts)


def resolve_resource_path(raw: str | Path, fallback_roots: Iterable[Path] | None = None) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path

    roots = [APP_ROOT, SOURCE_ROOT]
    if fallback_roots:
        roots.extend(Path(root) for root in fallback_roots)

    for root in roots:
        candidate = root / path
        if candidate.exists():
            return candidate

    return APP_ROOT / path

