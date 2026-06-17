import inspect
import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

from paths import get_app_root, get_source_root


SOURCE_ROOT = get_source_root()
PROJECT_ROOT = get_app_root()
CONFIG_DIR = PROJECT_ROOT / "config"
EXAMPLE_PATH = CONFIG_DIR / "settings.example.json"
SETTINGS_PATH = CONFIG_DIR / "settings.json"
DEFAULT_SETTINGS: Dict[str, Any] = {
    "tesseract_cmd": r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    "clock_region": {},
    "clock_setup_completed": False,
    "palia_minutes_per_real_second": 0.4,
    "stale_after_seconds": 900,
    "max_estimated_reminder_age_seconds": 300,
    "poll_interval_seconds": 1.0,
    "unreadable_reads_before_hidden": 2,
    "watch_log_enabled": True,
    "reminders_enabled": True,
    "theme": "dark",
    "start_with_windows": False,
    "auto_arm_when_palia_opens": True,
    "smart_resume_enabled": True,
    "smart_recall_enabled": True,
    "start_minimized": False,
    "minimize_to_tray": True,
    "close_to_tray": True,
    "show_tray_notifications": True,
    "debug_logging": True,
    "debug_verbose": False,
    "palia_process_names": [
        "PaliaClientSteam-Win64-Shipping.exe",
        "PaliaClient-Win64-Shipping.exe",
        "Palia.exe",
    ],
    "palia_launcher_process_names": [
        "PaliaClientSteam.exe",
    ],
    "palia_process_poll_seconds": 5,
    "pause_when_palia_closes": True,
    "reminder_cooldown_seconds": 300,
    "stale_warning_enabled": True,
    "hotpot_start_time": "6:00 PM",
    "hotpot_end_time": "3:00 AM",
    "hotpot_warning_times": [
        "5:45 PM",
        "6:00 PM",
        "12:00 AM",
        "2:50 AM",
        "3:00 AM",
    ],
    "reminder_minutes": [
        "5:45 PM",
        "6:00 PM",
        "12:00 AM",
        "2:50 AM",
        "3:00 AM",
    ],
    "hotpot_reminder_messages": {
        "5:45 PM": {
            "title": "Hotpot starts soon!",
            "message": "Head over before it begins.",
        },
        "6:00 PM": {
            "title": "Hotpot has Started!",
            "message": "Good Luck and Have Fun!",
        },
        "12:00 AM": {
            "title": "Hotpot is Still Running!",
            "message": "Keep going and good luck!",
        },
        "2:50 AM": {
            "title": "Hotpot is Ending Soon!",
            "message": "Finish up while you can!",
        },
        "3:00 AM": {
            "title": "Hotpot has Ended!",
            "message": "See you next time!",
        },
    },
    "popup_style": "custom",
    "popup_duration_seconds": 15,
    "popup_position": "left",
    "popup_asset_path": r"assets\Message Board\popup_scroll_clean.png",
    "popup_width": 640,
    "popup_height": 480,
    "popup_left_margin": 24,
    "popup_top_margin": 250,
    "notifications": {
        "enabled": True,
        "sound": False,
    },
}
LAST_SETTINGS_WARNINGS: list[str] = []
SETTINGS_LOGGER = logging.getLogger("settings")

DEFAULT_GENERIC_REMINDER_TITLE = "Hotpot\nReminder"
DEFAULT_GENERIC_REMINDER_MESSAGE = "This is your reminder that Hotpot will start in 15min!"


def _read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def _settings_caller(depth: int = 2) -> str:
    try:
        frame = inspect.stack()[depth]
        module = inspect.getmodule(frame.frame)
        module_name = module.__name__ if module and module.__name__ else "settings"
        return f"{module_name}.{frame.function}"
    except Exception:
        return "settings"


def _log_settings_write(old: Dict[str, Any], new: Dict[str, Any], source: str) -> None:
    try:
        changes = []
        keys = sorted(set(old.keys()) | set(new.keys()))
        for key in keys:
            old_value = old.get(key, "<missing>")
            new_value = new.get(key, "<missing>")
            if old_value != new_value:
                changes.append(f"{key}: {old_value!r} -> {new_value!r}")
        if not changes:
            SETTINGS_LOGGER.info("SETTINGS WRITE [%s] no changes", source)
            return
        SETTINGS_LOGGER.info("SETTINGS WRITE [%s] %s", source, " | ".join(changes))
    except Exception:
        pass


def _merge_defaults(data: Dict[str, Any], defaults: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(defaults)
    for key, value in data.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_defaults(value, merged[key])
        else:
            merged[key] = value
    return merged


def _normalize_time_label(label: Any) -> str:
    text = " ".join(str(label).strip().upper().split())
    if not text:
        return ""
    for fmt in ("%I:%M %p", "%I:%M%p", "%H:%M"):
        try:
            return datetime.strptime(text, fmt).strftime("%I:%M %p").lstrip("0")
        except ValueError:
            continue
    return ""


def _normalize_reminder_messages(
    value: Any,
    defaults: Dict[str, Dict[str, str]],
) -> Tuple[Dict[str, Dict[str, str]], List[str]]:
    warnings: List[str] = []
    normalized: Dict[str, Dict[str, str]] = {}

    if not isinstance(value, dict):
        warnings.append("hotpot_reminder_messages reset to defaults")
        return {label: dict(copy) for label, copy in defaults.items()}, warnings

    for raw_label, raw_copy in value.items():
        label = _normalize_time_label(raw_label)
        if not label:
            warnings.append(f"Skipped invalid reminder message key: {raw_label}")
            continue

        default_entry = defaults.get(
            label,
            {
                "title": DEFAULT_GENERIC_REMINDER_TITLE,
                "message": DEFAULT_GENERIC_REMINDER_MESSAGE,
            },
        )
        title = default_entry.get("title", DEFAULT_GENERIC_REMINDER_TITLE)
        message = default_entry.get("message", DEFAULT_GENERIC_REMINDER_MESSAGE)

        if isinstance(raw_copy, dict):
            raw_title = raw_copy.get("title", title)
            raw_message = raw_copy.get("message", message)
        elif isinstance(raw_copy, str):
            raw_title = title
            raw_message = raw_copy
            warnings.append(f"hotpot_reminder_messages[{label}] used string fallback")
        else:
            raw_title = title
            raw_message = message
            warnings.append(f"hotpot_reminder_messages[{label}] reset to default copy")

        normalized[label] = {
            "title": str(raw_title).strip() or title,
            "message": str(raw_message).strip() or message,
        }

    for label, copy in defaults.items():
        normalized.setdefault(label, dict(copy))

    return normalized, warnings


def ensure_settings_file() -> Path:
    if SETTINGS_PATH.exists():
        return SETTINGS_PATH
    if not EXAMPLE_PATH.exists():
        raise FileNotFoundError(f"Missing example config: {EXAMPLE_PATH}")
    data = _read_json(EXAMPLE_PATH)
    _write_json(SETTINGS_PATH, data)
    return SETTINGS_PATH


def load_settings() -> Dict[str, Any]:
    global LAST_SETTINGS_WARNINGS
    warnings: list[str] = []
    ensure_settings_file()
    data = _read_json(SETTINGS_PATH)
    merged = _merge_defaults(data, DEFAULT_SETTINGS)
    ratio = merged.get("palia_minutes_per_real_second", DEFAULT_SETTINGS["palia_minutes_per_real_second"])
    try:
        ratio_value = float(ratio)
    except (TypeError, ValueError):
        ratio_value = float(DEFAULT_SETTINGS["palia_minutes_per_real_second"])
        warnings.append("Invalid palia_minutes_per_real_second reset to 0.4")
    if ratio_value <= 0:
        ratio_value = float(DEFAULT_SETTINGS["palia_minutes_per_real_second"])
        warnings.append("Non-positive palia_minutes_per_real_second reset to 0.4")
    merged["palia_minutes_per_real_second"] = ratio_value

    max_estimated_age = merged.get("max_estimated_reminder_age_seconds", DEFAULT_SETTINGS["max_estimated_reminder_age_seconds"])
    try:
        max_estimated_age_value = int(max_estimated_age)
    except (TypeError, ValueError):
        max_estimated_age_value = int(DEFAULT_SETTINGS["max_estimated_reminder_age_seconds"])
        warnings.append("Invalid max_estimated_reminder_age_seconds reset to 300")
    if max_estimated_age_value <= 0:
        max_estimated_age_value = int(DEFAULT_SETTINGS["max_estimated_reminder_age_seconds"])
        warnings.append("Non-positive max_estimated_reminder_age_seconds reset to 300")
    merged["max_estimated_reminder_age_seconds"] = max_estimated_age_value

    if "stale_timeout_seconds" in merged and "stale_after_seconds" not in data:
        merged["stale_after_seconds"] = merged["stale_timeout_seconds"]
    if "stale_timeout_seconds" in merged:
        merged.pop("stale_timeout_seconds", None)
    hotpot = merged.get("hotpot_warning_times")
    legacy = merged.get("reminder_minutes")
    if not hotpot and legacy:
        merged["hotpot_warning_times"] = legacy
        hotpot = legacy
    if hotpot:
        merged["reminder_minutes"] = hotpot
    process_names = merged.get("palia_process_names", DEFAULT_SETTINGS["palia_process_names"])
    if isinstance(process_names, str):
        process_names = [part.strip() for part in process_names.split(",")]
    if not isinstance(process_names, list):
        process_names = list(DEFAULT_SETTINGS["palia_process_names"])
        warnings.append("palia_process_names reset to defaults")
    normalized_process_names = [str(item).strip() for item in process_names if str(item).strip()]
    merged["palia_process_names"] = normalized_process_names or list(DEFAULT_SETTINGS["palia_process_names"])
    launcher_process_names = merged.get("palia_launcher_process_names", DEFAULT_SETTINGS["palia_launcher_process_names"])
    if isinstance(launcher_process_names, str):
        launcher_process_names = [part.strip() for part in launcher_process_names.split(",")]
    if not isinstance(launcher_process_names, list):
        launcher_process_names = list(DEFAULT_SETTINGS["palia_launcher_process_names"])
        warnings.append("palia_launcher_process_names reset to defaults")
    normalized_launcher_process_names = [str(item).strip() for item in launcher_process_names if str(item).strip()]
    merged["palia_launcher_process_names"] = normalized_launcher_process_names or list(DEFAULT_SETTINGS["palia_launcher_process_names"])
    poll_seconds = merged.get("palia_process_poll_seconds", DEFAULT_SETTINGS["palia_process_poll_seconds"])
    try:
        poll_seconds_value = int(poll_seconds)
    except (TypeError, ValueError):
        poll_seconds_value = int(DEFAULT_SETTINGS["palia_process_poll_seconds"])
        warnings.append("Invalid palia_process_poll_seconds reset to 5")
    if poll_seconds_value <= 0:
        poll_seconds_value = int(DEFAULT_SETTINGS["palia_process_poll_seconds"])
        warnings.append("Non-positive palia_process_poll_seconds reset to 5")
    merged["palia_process_poll_seconds"] = poll_seconds_value
    reminder_messages = merged.get("hotpot_reminder_messages", DEFAULT_SETTINGS["hotpot_reminder_messages"])
    normalized_messages, reminder_message_warnings = _normalize_reminder_messages(
        reminder_messages,
        DEFAULT_SETTINGS["hotpot_reminder_messages"],
    )
    merged["hotpot_reminder_messages"] = normalized_messages
    warnings.extend(reminder_message_warnings)
    if merged != data:
        _log_settings_write(data, merged, "load_settings.merge")
        _write_json(SETTINGS_PATH, merged)
    LAST_SETTINGS_WARNINGS = warnings
    return merged


def save_settings(settings: Dict[str, Any]) -> None:
    old = _read_json(SETTINGS_PATH) if SETTINGS_PATH.exists() else {}
    caller = _settings_caller(2)
    _log_settings_write(old, settings, caller)
    _write_json(SETTINGS_PATH, settings)


def update_clock_region(left: int, top: int, width: int, height: int) -> Dict[str, Any]:
    settings = load_settings()
    settings["clock_region"] = {
        "left": left,
        "top": top,
        "width": width,
        "height": height,
    }
    settings["clock_setup_completed"] = True
    save_settings(settings)
    return settings
