import json
import math
from dataclasses import dataclass
from datetime import datetime, time as dt_time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from config import DEFAULT_SETTINGS, PROJECT_ROOT
from custom_popup import CustomPopupController, PopupResult

try:
    from winotify import Notification
except Exception:  # pragma: no cover - optional dependency
    Notification = None


DEBUG_DIR = PROJECT_ROOT / "debug"
REMINDER_LOG_PATH = DEBUG_DIR / "reminder_log.txt"
APP_ID = "PaliaHotpotReminder"


@dataclass
class ReminderOutcome:
    surface_status: bool = False
    status_message: str = ""
    decision: str = "skipped"
    current_mode: str = ""
    reminder_kind: str = ""
    reminder_key: str = ""
    reminder_label: str = ""
    current_palia_time: str = ""
    last_reminder_fired: str = ""
    next_reminder_target: str = ""
    reminders_enabled: bool = False
    popup_style: str = ""
    cooldown_active: bool = False
    cooldown_remaining_seconds: int = 0
    notification_sent: bool = False
    diagnostic: str = ""
    hotpot_window_active: bool = False
    hotpot_window_label: str = ""
    hotpot_window_start: str = ""
    hotpot_window_end: str = ""
    warning_time_issues: str = ""
    palia_minutes_per_real_second: float = 0.0
    source_mode: str = ""
    seconds_since_confirmed: str = ""
    estimated_palia_time: str = ""
    reminder_target_time: str = ""
    reminder_title: str = ""
    reminder_message: str = ""


def _normalize_text(value: str) -> str:
    return " ".join(str(value).strip().upper().split())


def parse_time_label(label: str) -> Optional[dt_time]:
    text = _normalize_text(label)
    if not text:
        return None

    for fmt in ("%I:%M %p", "%I:%M%p", "%H:%M"):
        try:
            return datetime.strptime(text, fmt).time()
        except ValueError:
            continue
    return None


def parse_time_to_minutes(label: str) -> Optional[int]:
    parsed = parse_time_label(label)
    if parsed is None:
        return None
    return parsed.hour * 60 + parsed.minute


def normalize_time_label(label: str) -> str:
    parsed = parse_time_label(label)
    if parsed is None:
        return ""
    return parsed.strftime("%I:%M %p").lstrip("0")


def _time_sort_key(label: str) -> Tuple[int, int]:
    parsed = parse_time_label(label)
    if parsed is None:
        return (24, 0)
    return (parsed.hour, parsed.minute)


def normalize_warning_times_with_issues(value: Any) -> Tuple[List[str], List[str]]:
    if value is None:
        return [], []
    if isinstance(value, str):
        candidates = [part.strip() for part in value.split(",")]
    elif isinstance(value, Iterable):
        candidates = [str(item).strip() for item in value]
    else:
        candidates = [str(value).strip()]

    normalized: List[str] = []
    invalid: List[str] = []
    for candidate in candidates:
        label = normalize_time_label(candidate)
        if label and label not in normalized:
            normalized.append(label)
        elif candidate:
            invalid.append(candidate)
    normalized.sort(key=_time_sort_key)
    return normalized, invalid


def normalize_warning_times(value: Any) -> List[str]:
    valid, _ = normalize_warning_times_with_issues(value)
    return valid


def get_warning_times(settings: Dict[str, Any]) -> List[str]:
    value = settings.get("hotpot_warning_times")
    if not value:
        value = settings.get("reminder_minutes")
    return normalize_warning_times(value)


def get_warning_time_issues(settings: Dict[str, Any]) -> List[str]:
    value = settings.get("hotpot_warning_times")
    if not value:
        value = settings.get("reminder_minutes")
    _, invalid = normalize_warning_times_with_issues(value)
    return invalid


def _normalize_reminder_message_map_with_issues(value: Any) -> Tuple[Dict[str, Dict[str, str]], List[str]]:
    defaults = DEFAULT_SETTINGS.get("hotpot_reminder_messages", {})
    if not isinstance(value, dict):
        return {label: dict(copy) for label, copy in defaults.items()}, ["hotpot_reminder_messages reset to defaults"]

    normalized: Dict[str, Dict[str, str]] = {}
    issues: List[str] = []
    for raw_label, raw_copy in value.items():
        label = normalize_time_label(raw_label)
        if not label:
            issues.append(f"Skipped invalid reminder message key: {raw_label}")
            continue

        default_entry = defaults.get(
            label,
            {
                "title": "Hotpot\nReminder",
                "message": "This is your reminder that Hotpot will start in 15min!",
            },
        )
        title = default_entry.get("title", "Hotpot\nReminder")
        message = default_entry.get("message", "This is your reminder that Hotpot will start in 15min!")
        if isinstance(raw_copy, dict):
            raw_title = raw_copy.get("title", title)
            raw_message = raw_copy.get("message", message)
        elif isinstance(raw_copy, str):
            raw_title = title
            raw_message = raw_copy
            issues.append(f"hotpot_reminder_messages[{label}] used string fallback")
        else:
            raw_title = title
            raw_message = message
            issues.append(f"hotpot_reminder_messages[{label}] reset to default copy")

        normalized[label] = {
            "title": str(raw_title).strip() or title,
            "message": str(raw_message).strip() or message,
        }

    for label, copy in defaults.items():
        normalized.setdefault(label, dict(copy))

    return normalized, issues


def get_reminder_messages(settings: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    messages, _ = _normalize_reminder_message_map_with_issues(settings.get("hotpot_reminder_messages"))
    return messages


def get_reminder_copy(settings: Dict[str, Any], target_time: str) -> Tuple[str, str]:
    messages = get_reminder_messages(settings)
    label = normalize_time_label(target_time)
    default_title = "Hotpot\nReminder"
    default_message = "This is your reminder that Hotpot will start in 15min!"
    entry = messages.get(label, {})
    title = str(entry.get("title", default_title)).strip() or default_title
    message = str(entry.get("message", default_message)).strip() or default_message
    return title, message


def get_hotpot_window(settings: Dict[str, Any]) -> Tuple[str, str, Optional[int], Optional[int]]:
    start_label = normalize_time_label(settings.get("hotpot_start_time", "6:00 PM")) or "6:00 PM"
    end_label = normalize_time_label(settings.get("hotpot_end_time", "3:00 AM")) or "3:00 AM"
    start_minutes = parse_time_to_minutes(start_label)
    end_minutes = parse_time_to_minutes(end_label)
    return start_label, end_label, start_minutes, end_minutes


def is_time_in_window(current_minutes: Optional[int], start_minutes: Optional[int], end_minutes: Optional[int]) -> bool:
    if current_minutes is None or start_minutes is None or end_minutes is None:
        return False
    if start_minutes == end_minutes:
        return True
    if start_minutes < end_minutes:
        return start_minutes <= current_minutes < end_minutes
    return current_minutes >= start_minutes or current_minutes < end_minutes


def next_target_time(current_minutes: Optional[int], targets: Sequence[str]) -> str:
    valid_targets = [
        (parse_time_to_minutes(label), label)
        for label in targets
        if parse_time_to_minutes(label) is not None
    ]
    if not valid_targets:
        return ""
    valid_targets.sort(key=lambda item: item[0])
    if current_minutes is None:
        return valid_targets[0][1]
    for target_minutes, label in valid_targets:
        if target_minutes > current_minutes:
            return label
    return valid_targets[0][1]


def _to_bool(settings: Dict[str, Any], key: str, default: bool) -> bool:
    value = settings.get(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _to_int(settings: Dict[str, Any], key: str, default: int) -> int:
    value = settings.get(key, default)
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _log_reminder(entry: Dict[str, Any]) -> Path:
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    with REMINDER_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return REMINDER_LOG_PATH


class ReminderManager:
    def __init__(self, popup_host=None) -> None:
        self.popup_host = popup_host
        self._custom_popup: Optional[CustomPopupController] = None
        self.last_fired_at: Dict[str, datetime] = {}
        self.last_reminder_fired: str = ""
        self.last_reminder_target: str = ""
        self.last_status_message: str = ""
        self.last_decision: str = "skipped"
        self.last_diagnostic: str = ""
        self.last_stale_warning_key: str = ""

    def reset_session_state(self) -> None:
        self.last_fired_at.clear()
        self.last_reminder_fired = ""
        self.last_reminder_target = ""
        self.last_status_message = ""
        self.last_decision = "skipped"
        self.last_diagnostic = ""
        self.last_stale_warning_key = ""

    def evaluate(self, snapshot, settings: Dict[str, Any], now: Optional[datetime] = None) -> ReminderOutcome:
        now = now or datetime.now()
        reminders_enabled = _to_bool(settings, "reminders_enabled", True)
        stale_warning_enabled = _to_bool(settings, "stale_warning_enabled", True)
        cooldown_seconds = max(0, _to_int(settings, "reminder_cooldown_seconds", 300))
        max_estimated_age_seconds = max(0, _to_int(settings, "max_estimated_reminder_age_seconds", 300))
        palia_minutes_per_real_second = self._normalized_ratio(settings)
        popup_style = self._requested_popup_style(settings)
        warning_times = get_warning_times(settings)
        warning_issues = get_warning_time_issues(settings)
        hotpot_start_label, hotpot_end_label, hotpot_start_minutes, hotpot_end_minutes = get_hotpot_window(settings)
        current_time_label = normalize_time_label(snapshot.current_palia_time)
        current_minutes = parse_time_to_minutes(current_time_label)
        next_target = next_target_time(current_minutes, warning_times)
        hotpot_active = is_time_in_window(current_minutes, hotpot_start_minutes, hotpot_end_minutes)
        seconds_since_confirmed = self._snapshot_seconds_since_confirmed(snapshot)
        seconds_since_confirmed_text = f"{seconds_since_confirmed:.1f}"
        estimated_palia_time = normalize_time_label(getattr(snapshot, "estimated_palia_time", ""))
        active_target = current_time_label if current_time_label and current_time_label in warning_times else next_target
        reminder_title, reminder_message = get_reminder_copy(settings, active_target)

        outcome = ReminderOutcome(
            current_mode=getattr(snapshot, "mode", ""),
            source_mode=getattr(snapshot, "mode", ""),
            current_palia_time=current_time_label,
            seconds_since_confirmed=seconds_since_confirmed_text,
            estimated_palia_time=estimated_palia_time,
            reminder_target_time=active_target,
            reminder_title=reminder_title,
            reminder_message=reminder_message,
            next_reminder_target=next_target,
            reminders_enabled=reminders_enabled,
            popup_style=popup_style,
            hotpot_window_active=hotpot_active,
            hotpot_window_label=f"{hotpot_start_label} - {hotpot_end_label}",
            hotpot_window_start=hotpot_start_label,
            hotpot_window_end=hotpot_end_label,
            warning_time_issues=", ".join(warning_issues),
            palia_minutes_per_real_second=palia_minutes_per_real_second,
        )

        if warning_issues:
            issue_text = ", ".join(warning_issues)
            outcome.diagnostic = f"Invalid reminder times skipped: {issue_text}"

        if not reminders_enabled:
            outcome.decision = "disabled"
            outcome.status_message = "Reminders disabled"
            outcome.diagnostic = self._merge_diagnostics(
                outcome.diagnostic,
                self._build_diagnostic(outcome, current_time_label, cooldown_state="clear"),
            )
            self._store_outcome(outcome)
            self._log_decision(snapshot, outcome, now)
            return outcome

        if snapshot.mode == "Unknown":
            outcome.decision = "skipped"
            outcome.status_message = "No valid clock yet"
            outcome.diagnostic = self._merge_diagnostics(
                outcome.diagnostic,
                self._build_diagnostic(outcome, current_time_label, cooldown_state="clear"),
            )
            self._store_outcome(outcome)
            self._log_decision(snapshot, outcome, now)
            return outcome

        if snapshot.mode == "Stale":
            if not stale_warning_enabled:
                outcome.decision = "suppressed"
                outcome.status_message = "Stale clock warning suppressed"
                outcome.diagnostic = self._merge_diagnostics(
                    outcome.diagnostic,
                    self._build_diagnostic(outcome, current_time_label, cooldown_state="clear"),
                )
                self._store_outcome(outcome)
                self._log_decision(snapshot, outcome, now)
                return outcome

            stale_key = self._stale_warning_key(snapshot)
            cooldown_active, cooldown_remaining = self._cooldown_state(stale_key, cooldown_seconds, now)
            outcome.cooldown_active = cooldown_active
            outcome.cooldown_remaining_seconds = cooldown_remaining
            if not cooldown_active:
                success, diagnostic = self._deliver_popup(
                    settings,
                    title="Palia Hotpot Reminder",
                    body=self._stale_warning_body(snapshot),
                    details=self._popup_details(snapshot, stale=True),
                    requested_style=popup_style,
                )
                self._record_fire(stale_key, now)
                outcome.surface_status = True
                outcome.decision = "fired" if success else "fallback"
                outcome.reminder_kind = "stale_warning"
                outcome.reminder_key = stale_key
                outcome.reminder_label = "Stale clock estimate"
                outcome.last_reminder_fired = "Stale clock estimate"
                outcome.status_message = "Clock estimate stale"
                outcome.notification_sent = success
                outcome.diagnostic = self._merge_diagnostics(diagnostic, outcome.diagnostic)
            else:
                outcome.decision = "suppressed"
                outcome.status_message = f"Stale warning already sent ({cooldown_remaining}s cooldown remaining)"

            outcome.diagnostic = self._merge_diagnostics(
                outcome.diagnostic,
                self._build_diagnostic(outcome, current_time_label, cooldown_state=self._describe_cooldown(outcome.cooldown_active, outcome.cooldown_remaining_seconds)),
            )
            self._store_outcome(outcome)
            self._log_decision(snapshot, outcome, now)
            return outcome

        if snapshot.mode == "Estimated" and max_estimated_age_seconds > 0 and seconds_since_confirmed > max_estimated_age_seconds:
            outcome.decision = "suppressed"
            outcome.status_message = f"Estimated mode stale ({int(seconds_since_confirmed)}s since confirmed)"
            outcome.diagnostic = self._merge_diagnostics(
                outcome.diagnostic,
                self._build_diagnostic(outcome, current_time_label, cooldown_state="clear"),
                f"estimated_age_limit={max_estimated_age_seconds}s",
                f"seconds_since_confirmed={seconds_since_confirmed_text}",
            )
            self._store_outcome(outcome)
            self._log_decision(snapshot, outcome, now)
            return outcome

        if current_time_label and current_time_label in warning_times:
            reminder_key = f"hotpot:{now.date().isoformat()}:{current_time_label}"
            cooldown_active, cooldown_remaining = self._cooldown_state(reminder_key, cooldown_seconds, now)
            outcome.cooldown_active = cooldown_active
            outcome.cooldown_remaining_seconds = cooldown_remaining
            if not cooldown_active:
                success, diagnostic = self._deliver_popup(
                    settings,
                    title=reminder_title,
                    body=reminder_message,
                    details=self._popup_details(snapshot, current_time_label=current_time_label),
                    requested_style=popup_style,
                )
                self._record_fire(reminder_key, now)
                outcome.surface_status = True
                outcome.decision = "fired" if success else "fallback"
                outcome.reminder_kind = "hotpot"
                outcome.reminder_key = reminder_key
                outcome.reminder_label = current_time_label
                outcome.reminder_target_time = current_time_label
                outcome.reminder_title = reminder_title
                outcome.reminder_message = reminder_message
                outcome.last_reminder_fired = current_time_label
                outcome.status_message = f"Reminder fired: {current_time_label}"
                outcome.notification_sent = success
                outcome.diagnostic = self._merge_diagnostics(
                    diagnostic,
                    outcome.diagnostic,
                )
            else:
                outcome.decision = "suppressed"
                outcome.status_message = f"Reminder cooldown active: {current_time_label} ({cooldown_remaining}s remaining)"
        else:
            outcome.decision = "armed"
            if warning_times:
                outcome.status_message = "Reminders armed"
            else:
                outcome.status_message = "No reminder times configured"

        outcome.diagnostic = self._merge_diagnostics(
            outcome.diagnostic,
            self._build_diagnostic(outcome, current_time_label, cooldown_state=self._describe_cooldown(outcome.cooldown_active, outcome.cooldown_remaining_seconds)),
        )
        self._store_outcome(outcome)
        self._log_decision(snapshot, outcome, now)
        return outcome

    def test_popup(self, now: Optional[datetime] = None) -> ReminderOutcome:
        return self.test_system_popup(now=now)

    def test_system_popup(self, now: Optional[datetime] = None, settings: Optional[Dict[str, Any]] = None) -> ReminderOutcome:
        now = now or datetime.now()
        key = f"test:{now.isoformat(timespec='seconds')}"
        success, diagnostic = self._deliver_popup(
            settings or {},
            title="PaliaHotpotReminder Test",
            body="This is a test popup.",
            details=["System popup test"],
            force_style="system",
        )
        self._record_fire(key, now)
        outcome = ReminderOutcome(
            surface_status=True,
            status_message="Test system popup sent" if success else "Test system popup fallback",
            decision="test" if success else "fallback",
            popup_style="system",
            reminder_kind="test",
            reminder_key=key,
            reminder_label="Test system popup",
            last_reminder_fired="Test system popup",
            notification_sent=success,
            diagnostic=diagnostic,
        )
        self._store_outcome(outcome)
        self._log_decision(None, outcome, now)
        return outcome

    def test_custom_popup(self, now: Optional[datetime] = None, settings: Optional[Dict[str, Any]] = None) -> ReminderOutcome:
        now = now or datetime.now()
        key = f"test-custom:{now.isoformat(timespec='seconds')}"
        success, diagnostic = self._deliver_popup(
            settings or {},
            title="Hotpot\nReminder",
            body="This is your reminder that Hotpot will start in 15min!",
            details=["Custom popup test"],
            force_style="custom",
        )
        self._record_fire(key, now)
        outcome = ReminderOutcome(
            surface_status=True,
            status_message="Test custom popup sent" if success else "Test custom popup fallback",
            decision="test" if success else "fallback",
            popup_style="custom",
            reminder_kind="test_custom",
            reminder_key=key,
            reminder_label="Test custom popup",
            reminder_title="Hotpot\nReminder",
            reminder_message="This is your reminder that Hotpot will start in 15min!",
            last_reminder_fired="Test custom popup",
            notification_sent=success,
            diagnostic=diagnostic,
        )
        self._store_outcome(outcome)
        self._log_decision(None, outcome, now)
        return outcome

    def _store_outcome(self, outcome: ReminderOutcome) -> None:
        self.last_reminder_fired = outcome.last_reminder_fired or self.last_reminder_fired
        self.last_reminder_target = outcome.reminder_target_time or outcome.next_reminder_target or self.last_reminder_target
        self.last_status_message = outcome.status_message or self.last_status_message
        self.last_decision = outcome.decision
        self.last_diagnostic = outcome.diagnostic
        if outcome.reminder_kind == "stale_warning":
            self.last_stale_warning_key = outcome.reminder_key or self.last_stale_warning_key

    def _can_fire(self, key: str, cooldown_seconds: int, now: datetime) -> bool:
        last_fire = self.last_fired_at.get(key)
        if last_fire is None:
            return True
        return (now - last_fire).total_seconds() >= cooldown_seconds

    def _cooldown_state(self, key: str, cooldown_seconds: int, now: datetime) -> Tuple[bool, int]:
        last_fire = self.last_fired_at.get(key)
        if last_fire is None:
            return False, 0
        elapsed = max(0.0, (now - last_fire).total_seconds())
        if elapsed >= cooldown_seconds:
            return False, 0
        remaining = int(math.ceil(cooldown_seconds - elapsed))
        return True, max(0, remaining)

    def _record_fire(self, key: str, now: datetime) -> None:
        self.last_fired_at[key] = now

    def _stale_warning_key(self, snapshot) -> str:
        anchor = snapshot.last_confirmed_real_timestamp or snapshot.last_confirmed_palia_time or "unknown"
        return f"stale:{anchor}"

    def _stale_warning_body(self, snapshot) -> str:
        last_confirmed = snapshot.last_confirmed_palia_time or "unknown"
        return f"Clock estimate is stale. Last confirmed Palia time: {last_confirmed}"

    def _next_warning_target(self, current_time_label: str, warning_times: Sequence[str]) -> str:
        current_minutes = parse_time_to_minutes(current_time_label)
        return next_target_time(current_minutes, warning_times)

    def _send_notification(self, title: str, body: str) -> Tuple[bool, str]:
        if Notification is None:
            return False, "winotify unavailable"
        try:
            toast = Notification(app_id=APP_ID, title=title, msg=body, duration="short")
            toast.show()
            return True, "notification sent"
        except Exception as exc:
            return False, f"notification failed: {exc}"

    def _deliver_popup(
        self,
        settings: Dict[str, Any],
        title: str,
        body: str,
        details: Optional[Sequence[str]] = None,
        force_style: Optional[str] = None,
        requested_style: Optional[str] = None,
    ) -> Tuple[bool, str]:
        requested = (requested_style or force_style or str(settings.get("popup_style", "custom"))).strip().lower() or "custom"
        popup_body = self._compose_popup_body(body, details)
        style_order = self._popup_style_order(requested)
        diagnostics: List[str] = []

        for style in style_order:
            if style == "custom":
                success, diagnostic = self._send_custom_popup(settings, title, body, details)
            elif style == "system":
                success, diagnostic = self._send_notification(title, popup_body)
            else:
                continue
            diagnostics.append(f"{style}: {diagnostic}")
            if success:
                return True, f"{style} popup shown: {diagnostic}" if diagnostic else f"{style} popup shown"

        return False, "; ".join(diagnostics) if diagnostics else "No popup backend available"

    def _popup_style_order(self, requested: str) -> List[str]:
        if requested == "system":
            return ["system", "custom"]
        if requested == "custom":
            return ["custom", "system"]
        return ["custom", "system"]

    def _requested_popup_style(self, settings: Dict[str, Any]) -> str:
        requested = str(settings.get("popup_style", "custom")).strip().lower()
        return requested or "custom"

    def _send_custom_popup(self, settings: Dict[str, Any], title: str, body: str, details: Optional[Sequence[str]] = None) -> Tuple[bool, str]:
        if self.popup_host is None:
            return False, "No Tk host available"
        try:
            controller = self._get_custom_popup_controller()
            if controller is None:
                return False, "Custom popup controller unavailable"
            result = controller.show(settings, title, body, details)
            return result.shown, result.diagnostic or result.backend or "custom popup shown"
        except Exception as exc:
            return False, f"custom popup failed: {exc}"

    def _get_custom_popup_controller(self) -> Optional[CustomPopupController]:
        if self._custom_popup is None:
            if self.popup_host is None:
                return None
            self._custom_popup = CustomPopupController(self.popup_host)
        return self._custom_popup

    def _compose_popup_body(self, body: str, details: Optional[Sequence[str]] = None) -> str:
        detail_text = [str(item).strip() for item in details or [] if str(item).strip()]
        if detail_text:
            return "\n".join([body.strip()] + detail_text)
        return body.strip()

    def _popup_details(
        self,
        snapshot,
        current_time_label: str = "",
        stale: bool = False,
    ) -> List[str]:
        details: List[str] = []
        if current_time_label:
            details.append(f"Palia time: {current_time_label}")
        elif getattr(snapshot, "current_palia_time", ""):
            details.append(f"Palia time: {snapshot.current_palia_time}")
        if getattr(snapshot, "mode", ""):
            details.append(f"Mode: {snapshot.mode}")
        if stale and getattr(snapshot, "last_confirmed_palia_time", ""):
            details.append(f"Last confirmed: {snapshot.last_confirmed_palia_time}")
        return details

    def _log_decision(self, snapshot, outcome: ReminderOutcome, now: datetime) -> None:
        try:
            _log_reminder(
                {
                    "timestamp": now.isoformat(timespec="seconds"),
                    "mode": getattr(snapshot, "mode", ""),
                    "current_palia_time": outcome.current_palia_time,
                    "estimated_palia_time": outcome.estimated_palia_time,
                    "seconds_since_confirmed": outcome.seconds_since_confirmed,
                    "palia_minutes_per_real_second": outcome.palia_minutes_per_real_second,
                    "source_mode": outcome.source_mode,
                    "reminder_target_time": outcome.reminder_target_time,
                    "reminder_title": outcome.reminder_title,
                    "reminder_message": outcome.reminder_message,
                    "next_reminder_target": outcome.next_reminder_target,
                    "reminders_enabled": outcome.reminders_enabled,
                    "popup_style": outcome.popup_style,
                    "cooldown_active": outcome.cooldown_active,
                    "cooldown_remaining_seconds": outcome.cooldown_remaining_seconds,
                    "hotpot_window_active": outcome.hotpot_window_active,
                    "hotpot_window_label": outcome.hotpot_window_label,
                    "reminder_key": outcome.reminder_key,
                    "decision": outcome.decision,
                    "status_message": outcome.status_message,
                    "diagnostic": outcome.diagnostic,
                }
            )
        except Exception:
            pass

    def _merge_diagnostics(self, *parts: str) -> str:
        pieces = [part.strip() for part in parts if part and str(part).strip()]
        return " | ".join(pieces)

    def _describe_cooldown(self, active: bool, remaining_seconds: int) -> str:
        if not active:
            return "clear"
        return f"active({remaining_seconds}s remaining)"

    def _build_diagnostic(self, outcome: ReminderOutcome, current_time_label: str, cooldown_state: str) -> str:
        parts = [
            f"mode={outcome.current_mode or 'Unknown'}",
            f"current={current_time_label or '-'}",
            f"target={outcome.reminder_target_time or outcome.next_reminder_target or '-'}",
            f"next={outcome.next_reminder_target or '-'}",
            f"title={outcome.reminder_title or '-'}",
            f"message={outcome.reminder_message or '-'}",
            f"reminders_enabled={outcome.reminders_enabled}",
            f"popup_style={outcome.popup_style or 'custom'}",
            f"ratio={outcome.palia_minutes_per_real_second:.3f}",
            f"source_mode={outcome.source_mode or outcome.current_mode or 'Unknown'}",
            f"seconds_since_confirmed={outcome.seconds_since_confirmed or '-'}",
            f"estimated={outcome.estimated_palia_time or '-'}",
            f"cooldown={cooldown_state}",
            f"hotpot_active={outcome.hotpot_window_active}",
            f"window={outcome.hotpot_window_label or '-'}",
            f"decision={outcome.decision}",
        ]
        return " | ".join(parts)

    def _normalized_ratio(self, settings: Dict[str, Any]) -> float:
        value = settings.get("palia_minutes_per_real_second", 0.4)
        try:
            ratio = float(value)
        except (TypeError, ValueError):
            ratio = 0.4
        if ratio <= 0:
            ratio = 0.4
        return ratio

    def _snapshot_seconds_since_confirmed(self, snapshot) -> float:
        value = getattr(snapshot, "seconds_since_confirmed", "")
        try:
            return max(0.0, float(value))
        except (TypeError, ValueError):
            return 0.0
