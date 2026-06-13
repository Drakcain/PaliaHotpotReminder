from __future__ import annotations

import inspect
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Iterable, Optional, Sequence


def _caller_name(depth: int = 2) -> str:
    try:
        frame = inspect.stack()[depth]
        module = inspect.getmodule(frame.frame)
        module_name = module.__name__ if module and module.__name__ else "runtime"
        func_name = frame.function
        return f"{module_name}.{func_name}"
    except Exception:
        return "runtime"


def trace_action(
    action: str,
    *,
    purpose: str = "",
    path: str | Path | None = None,
    command: Sequence[str] | None = None,
    recurring: bool = False,
    hidden: bool = False,
    extra: str = "",
) -> None:
    logger = logging.getLogger("runtime")
    details = [f"action={action}", f"caller={_caller_name()}"]
    if purpose:
        details.append(f"purpose={purpose}")
    if path is not None:
        details.append(f"path={path}")
    if command is not None:
        details.append(f"command={list(command)}")
    details.append(f"recurring={recurring}")
    details.append(f"hidden={hidden}")
    if extra:
        details.append(extra)
    logger.info("[SUBPROCESS] %s", " ".join(details))


def run_traced_subprocess(
    args: Sequence[str],
    *,
    purpose: str,
    recurring: bool = False,
    hidden: bool = True,
    capture_output: bool = True,
    text: bool = True,
    check: bool = False,
    env: Optional[dict] = None,
    cwd: Optional[str | Path] = None,
) -> subprocess.CompletedProcess[str]:
    trace_action("subprocess.run", purpose=purpose, command=args, recurring=recurring, hidden=hidden)
    kwargs: dict = {"capture_output": capture_output, "text": text, "check": check, "env": env, "cwd": cwd}
    if sys.platform.startswith("win") and hidden:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0
        kwargs["startupinfo"] = startupinfo
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    return subprocess.run(list(args), **kwargs)


def open_traced_path(path: str | Path, *, purpose: str) -> None:
    trace_action("os.startfile", purpose=purpose, path=path, recurring=False, hidden=False)
    os.startfile(str(path))


def build_subprocess_audit() -> str:
    return "\n".join(
        [
            "- create_shortcut: powershell hidden=true recurring=false",
            "- tesseract preflight: subprocess.run hidden=true recurring=false",
            "- tesseract OCR: subprocess.run hidden=true recurring=false",
            "- process detection: psutil.process_iter recurring=true hidden=n/a",
            "- open logs folder/file: os.startfile no console",
        ]
    )
