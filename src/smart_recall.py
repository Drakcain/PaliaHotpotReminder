from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Tuple

from config import PROJECT_ROOT


RECALL_PATH = PROJECT_ROOT / "config" / "recall_state.json"
RECALL_KEYS = {
    "last_good_clock_region",
    "last_good_monitor_fingerprint",
    "last_good_screen_bounds",
    "last_good_ocr_time",
    "last_good_ocr_timestamp",
    "last_good_ocr_raw",
    "last_good_ocr_normalized",
    "last_clock_validation_status",
    "last_clock_validation_reason",
    "last_resume_check_time",
    "last_resume_check_result",
    "last_palia_game_detected",
    "last_palia_launcher_detected",
    "last_session_id",
    "last_recovery_action",
    "last_failure_reason",
    "last_known_app_visibility_state",
}


def default_recall_state() -> Dict[str, Any]:
    return {
        "last_good_clock_region": {},
        "last_good_monitor_fingerprint": "",
        "last_good_screen_bounds": {},
        "last_good_ocr_time": "",
        "last_good_ocr_timestamp": "",
        "last_good_ocr_raw": "",
        "last_good_ocr_normalized": "",
        "last_clock_validation_status": "unknown",
        "last_clock_validation_reason": "",
        "last_resume_check_time": "",
        "last_resume_check_result": "",
        "last_palia_game_detected": False,
        "last_palia_launcher_detected": False,
        "last_session_id": 0,
        "last_recovery_action": "",
        "last_failure_reason": "",
        "last_known_app_visibility_state": "unknown",
    }


def _sanitize_recall_state(data: Any) -> Dict[str, Any]:
    clean = default_recall_state()
    if not isinstance(data, dict):
        return clean
    for key in RECALL_KEYS:
        if key in data:
            clean[key] = data[key]
    if not isinstance(clean["last_good_clock_region"], dict):
        clean["last_good_clock_region"] = {}
    if not isinstance(clean["last_good_screen_bounds"], dict):
        clean["last_good_screen_bounds"] = {}
    clean["last_palia_game_detected"] = bool(clean["last_palia_game_detected"])
    clean["last_palia_launcher_detected"] = bool(clean["last_palia_launcher_detected"])
    try:
        clean["last_session_id"] = max(0, int(clean["last_session_id"]))
    except (TypeError, ValueError):
        clean["last_session_id"] = 0
    return clean


def load_recall_state(path: Path = RECALL_PATH) -> Tuple[Dict[str, Any], str]:
    if not path.exists():
        return default_recall_state(), "missing"
    try:
        with path.open("r", encoding="utf-8") as handle:
            return _sanitize_recall_state(json.load(handle)), "loaded"
    except Exception:
        return default_recall_state(), "corrupt"


def save_recall_state(state: Dict[str, Any], path: Path = RECALL_PATH) -> None:
    clean = _sanitize_recall_state(state)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(clean, handle, indent=2)
        handle.write("\n")
    temporary.replace(path)

