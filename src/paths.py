from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable


SOURCE_ROOT = Path(__file__).resolve().parent.parent
IS_FROZEN = bool(getattr(sys, "frozen", False))
APP_ROOT = Path(sys.executable).resolve().parent if IS_FROZEN else SOURCE_ROOT
LEGACY_RESOURCE_PATHS = {
    "assets/app_icon.ico": Path("assets") / "App Icon" / "HPR_Icon.ico",
    "assets/app_icon_source.png": Path("assets") / "App Icon" / "HPR_Icon.png",
    "assets/popup_scroll.png": Path("assets") / "Message Board" / "popup_scroll.png",
    "assets/popup_scroll_clean.png": Path("assets") / "Message Board" / "popup_scroll_clean.png",
}


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

    legacy_key = path.as_posix().lower()
    legacy_path = LEGACY_RESOURCE_PATHS.get(legacy_key)
    if legacy_path is not None:
        for root in roots:
            candidate = root / legacy_path
            if candidate.exists():
                return candidate

    return APP_ROOT / path
