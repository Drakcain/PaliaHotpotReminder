from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime
from typing import Optional, Sequence, Set, Tuple

try:
    import psutil
    PSUTIL_AVAILABLE = True
    PSUTIL_IMPORT_ERROR = ""
except Exception as exc:  # pragma: no cover - optional dependency
    psutil = None
    PSUTIL_AVAILABLE = False
    PSUTIL_IMPORT_ERROR = str(exc)

from runtime_trace import run_traced_subprocess, trace_action


@dataclass(frozen=True)
class PaliaProcessScanResult:
    game_detected: bool
    launcher_detected: bool
    matched_game_process_name: str = ""
    matched_launcher_process_name: str = ""
    matched_game_pid: Optional[int] = None
    matched_launcher_pid: Optional[int] = None
    last_detection_check_time: str = ""
    detection_method: str = "psutil"
    psutil_available: bool = False
    watched_game_process_names: Tuple[str, ...] = ()
    watched_launcher_process_names: Tuple[str, ...] = ()
    nearby_palia_like_processes: Tuple[str, ...] = ()


def _normalize_process_names(process_names: Sequence[str]) -> tuple[tuple[str, ...], Set[str]]:
    normalized = tuple(str(name).strip() for name in process_names if str(name).strip())
    lowered = {name.lower() for name in normalized}
    return normalized, lowered


def scan_palia_processes(
    game_process_names: Sequence[str],
    launcher_process_names: Sequence[str] = (),
) -> PaliaProcessScanResult:
    watched_game_names, game_targets = _normalize_process_names(game_process_names)
    watched_launcher_names, launcher_targets = _normalize_process_names(launcher_process_names)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if not game_targets and not launcher_targets:
        return PaliaProcessScanResult(
            game_detected=False,
            launcher_detected=False,
            last_detection_check_time=timestamp,
            detection_method="psutil",
            psutil_available=PSUTIL_AVAILABLE,
            watched_game_process_names=watched_game_names,
            watched_launcher_process_names=watched_launcher_names,
        )
    if psutil is None:
        return PaliaProcessScanResult(
            game_detected=False,
            launcher_detected=False,
            last_detection_check_time=timestamp,
            detection_method="psutil",
            psutil_available=False,
            watched_game_process_names=watched_game_names,
            watched_launcher_process_names=watched_launcher_names,
        )

    matched_game_name = ""
    matched_launcher_name = ""
    matched_game_pid: Optional[int] = None
    matched_launcher_pid: Optional[int] = None
    nearby: list[str] = []

    try:
        for proc in psutil.process_iter(["name", "pid"]):
            try:
                name = str(proc.info.get("name") or "").strip()
            except Exception:
                continue
            if not name:
                continue
            lowered = name.lower()
            if lowered in game_targets and not matched_game_name:
                matched_game_name = name
                matched_game_pid = int(proc.info.get("pid")) if proc.info.get("pid") is not None else None
            if lowered in launcher_targets and not matched_launcher_name:
                matched_launcher_name = name
                matched_launcher_pid = int(proc.info.get("pid")) if proc.info.get("pid") is not None else None
            if any(token in lowered for token in ("palia", "singularity", "shipping")) and name not in nearby:
                nearby.append(name)
    except Exception:
        return PaliaProcessScanResult(
            game_detected=False,
            launcher_detected=False,
            last_detection_check_time=timestamp,
            detection_method="psutil",
            psutil_available=PSUTIL_AVAILABLE,
            watched_game_process_names=watched_game_names,
            watched_launcher_process_names=watched_launcher_names,
        )

    return PaliaProcessScanResult(
        game_detected=bool(matched_game_name),
        launcher_detected=bool(matched_launcher_name),
        matched_game_process_name=matched_game_name,
        matched_launcher_process_name=matched_launcher_name,
        matched_game_pid=matched_game_pid,
        matched_launcher_pid=matched_launcher_pid,
        last_detection_check_time=timestamp,
        detection_method="psutil",
        psutil_available=PSUTIL_AVAILABLE,
        watched_game_process_names=watched_game_names,
        watched_launcher_process_names=watched_launcher_names,
        nearby_palia_like_processes=tuple(nearby[:10]),
    )


def get_desktop_dir() -> Path:
    desktop = Path.home() / "Desktop"
    if desktop.exists():
        return desktop
    return Path(os.path.expandvars(r"%USERPROFILE%\Desktop"))


def get_startup_dir() -> Path:
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    return Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def get_shortcut_path(folder: Path, name: str) -> Path:
    return folder / name


def _powershell_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def run_hidden_command(args: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return run_traced_subprocess(args, purpose="hidden helper command", recurring=False, hidden=True)


def create_shortcut(
    shortcut_path: Path,
    target_path: Path,
    working_directory: Optional[Path] = None,
    icon_path: Optional[Path] = None,
    description: str = "",
) -> None:
    shortcut_path.parent.mkdir(parents=True, exist_ok=True)
    script_parts = [
        "$ws = New-Object -ComObject WScript.Shell",
        f"$s = $ws.CreateShortcut({_powershell_quote(str(shortcut_path))})",
        f"$s.TargetPath = {_powershell_quote(str(target_path))}",
        f"$s.WorkingDirectory = {_powershell_quote(str(working_directory or target_path.parent))}",
    ]
    if description:
        script_parts.append(f"$s.Description = {_powershell_quote(description)}")
    if icon_path is not None:
        script_parts.append(f"$s.IconLocation = {_powershell_quote(str(icon_path))}")
    script_parts.append("$s.Save()")
    script = "; ".join(script_parts)
    trace_action(
        "powershell",
        purpose="create shortcut",
        command=["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        recurring=False,
        hidden=True,
    )
    completed = run_hidden_command(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script])
    if completed.returncode != 0:
        raise RuntimeError((completed.stderr or completed.stdout or "Unable to create shortcut").strip())


def remove_shortcut(shortcut_path: Path) -> None:
    if shortcut_path.exists():
        shortcut_path.unlink()


def is_any_process_running(process_names: Sequence[str]) -> bool:
    return scan_palia_processes(process_names).game_detected


def set_dark_title_bar(window, enabled: bool = True) -> bool:
    if not sys.platform.startswith("win"):
        return False
    try:
        import ctypes
        from ctypes import wintypes
    except Exception:
        return False

    try:
        window.update_idletasks()
        hwnd = int(window.winfo_id())
    except Exception:
        return False

    if not hasattr(ctypes, "windll"):
        return False

    try:
        dwmapi = ctypes.windll.dwmapi
        dwm_set_window_attribute = dwmapi.DwmSetWindowAttribute
    except Exception:
        return False

    value = ctypes.c_int(1 if enabled else 0)
    attr_ids = (20, 19)

    for attr in attr_ids:
        try:
            result = dwm_set_window_attribute(
                wintypes.HWND(hwnd),
                wintypes.DWORD(attr),
                ctypes.byref(value),
                ctypes.sizeof(value),
            )
            if result == 0:
                return True
        except Exception:
            continue

    return False
