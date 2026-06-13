from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterable, Mapping

from app_version import APP_VERSION
from app_logging import get_log_paths
from config import PROJECT_ROOT
from runtime_trace import build_subprocess_audit


def _section(title: str, lines: Iterable[str]) -> str:
    body = "\n".join(f"- {line}" for line in lines) if lines else "- (none)"
    return f"## {title}\n{body}".strip()


def _last_lines(path: Path, limit: int = 100) -> list[str]:
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return []
    return lines[-limit:]


def build_debug_report(
    *,
    header_lines: Iterable[str],
    settings_lines: Iterable[str],
    runtime_lines: Iterable[str],
    warnings: Iterable[str],
    errors: Iterable[str],
    state_lines: Iterable[str],
    process_audit_lines: Iterable[str],
    session_lines: Iterable[str],
    smart_resume_lines: Iterable[str] = (),
    smart_recall_lines: Iterable[str] = (),
    support_summary_lines: Iterable[str] = (),
) -> str:
    latest_log, previous_log = get_log_paths()
    recent_log_lines = _last_lines(latest_log, 100)
    parts = [
        "# PaliaHotpotReminder Debug Report",
        "",
        _section("Header", header_lines),
        "",
        _section("Version", [APP_VERSION]),
        "",
        _section("Runtime Mode", runtime_lines),
        "",
        _section("Final Audit Summary", [
            "Use Palia Process Audit for live process status evidence.",
            "Use Clock OCR Parse for raw/normalized/accepted parser evidence.",
            "Use Recent Events and Last 100 Log Lines for session lifecycle evidence.",
        ]),
        "",
        _section("Paths", [f"project_root={PROJECT_ROOT}", f"latest_log={latest_log}", f"previous_log={previous_log}"]),
        "",
        _section("Settings Snapshot", settings_lines),
        "",
        _section("Tray State", [line for line in state_lines if line.startswith("tray:") or line.startswith("Tray:")]),
        "",
        _section("Watcher State", [line for line in state_lines if line.startswith("watcher:") or line.startswith("Watcher:")]),
        "",
        _section("Palia Detection", [line for line in state_lines if line.startswith("palia:") or line.startswith("Palia:")]),
        "",
        _section("Clock OCR Parse", [line for line in state_lines if line.startswith("last_") or line.startswith("estimated_time=") or line.startswith("seconds_since_confirmed=") or line.startswith("debug_log_path=")]),
        "",
        _section("Palia Process Audit", process_audit_lines),
        "",
        _section("Palia Session", session_lines),
        "",
        _section("Smart Resume", smart_resume_lines),
        "",
        _section("Smart Recall", smart_recall_lines),
        "",
        _section("Debug / Support Summary", support_summary_lines),
        "",
        _section("Subprocess Audit", build_subprocess_audit().splitlines()),
        "",
        _section("Recent Events", recent_log_lines[-25:]),
        "",
        _section("Warnings", warnings),
        "",
        _section("Errors", errors),
        "",
        _section("Last 100 Log Lines", recent_log_lines),
        "",
    ]
    return "\n".join(parts).strip() + "\n"


def export_debug_report(report_text: str, export_dir: Path | None = None) -> Path:
    export_dir = export_dir or (PROJECT_ROOT / "debug" / "reports")
    export_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    export_path = export_dir / f"debug-report-{timestamp}.md"
    export_path.write_text(report_text, encoding="utf-8")
    return export_path
