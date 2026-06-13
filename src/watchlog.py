import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from config import PROJECT_ROOT


DEBUG_DIR = PROJECT_ROOT / "debug"
WATCH_LOG_PATH = DEBUG_DIR / "watch_state_log.txt"


def append_watch_log(
    *,
    mode: str,
    status_message: str,
    raw_ocr: str,
    normalized_ocr: str,
    parse_candidates: str,
    parse_accepted: bool,
    parse_reject_reason: str,
    parse_source: str,
    parsed_time: str,
    last_confirmed_palia_time: str,
    estimated_palia_time: str,
    seconds_since_confirmed: str,
    diagnostic: str = "",
) -> Path:
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    entry: Dict[str, Any] = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "mode": mode,
        "status_message": status_message,
        "raw_ocr": raw_ocr,
        "normalized_ocr": normalized_ocr,
        "parse_candidates": parse_candidates,
        "parse_accepted": parse_accepted,
        "parse_reject_reason": parse_reject_reason,
        "parse_source": parse_source,
        "parsed_time": parsed_time,
        "last_confirmed_palia_time": last_confirmed_palia_time,
        "estimated_palia_time": estimated_palia_time,
        "seconds_since_confirmed": seconds_since_confirmed,
        "diagnostic": diagnostic,
    }
    with WATCH_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return WATCH_LOG_PATH
