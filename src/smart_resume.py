from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict


READY = "Ready"
NEEDS_SETUP = "Needs Setup Clock"
PALIA_NOT_OPEN = "Palia Not Open"
WAITING_MANUAL = "Waiting for Manual Start"
CHECKING_CLOCK = "Checking Clock"
CLOCK_CHECK_FAILED = "Clock Check Failed"
RUNNING = "Running"
PAUSED = "Paused"
RECOVERING = "Recovering"
DEBUG_NEEDED = "Debug Needed"


def monitor_fingerprint(diagnostics: Dict[str, Any]) -> str:
    monitors = diagnostics.get("monitors") or []
    parts = []
    for monitor in monitors:
        parts.append(
            "{index}:{width}x{height}@{left},{top}".format(
                index=monitor.get("index", "?"),
                width=monitor.get("width", "?"),
                height=monitor.get("height", "?"),
                left=monitor.get("left", "?"),
                top=monitor.get("top", "?"),
            )
        )
    return "|".join(parts) or "unknown"


@dataclass(frozen=True)
class SmartResumeResult:
    trigger: str
    checked_at: str
    readiness_state: str
    user_message: str
    region_valid: bool
    region_reason: str
    capture_ready: bool
    capture_reason: str
    palia_game_detected: bool
    palia_launcher_detected: bool
    monitor_fingerprint: str
    screen_geometry_changed: bool
    ocr_preflight_result: str
    recall_state_used: bool
    recovery_action: str
    failure_reason: str

    @property
    def can_test_clock(self) -> bool:
        return self.readiness_state in {READY, WAITING_MANUAL, RUNNING}

    @property
    def can_start_reminder(self) -> bool:
        return self.readiness_state in {READY, WAITING_MANUAL, RUNNING}


def evaluate_smart_resume(
    *,
    trigger: str,
    settings: Dict[str, Any],
    diagnostics: Dict[str, Any],
    region_valid: bool,
    region_reason: str,
    capture_ready: bool,
    capture_reason: str,
    palia_game_detected: bool,
    palia_launcher_detected: bool,
    ocr_preflight_result: str,
    recall_state: Dict[str, Any],
    watcher_running: bool,
) -> SmartResumeResult:
    fingerprint = monitor_fingerprint(diagnostics)
    previous_fingerprint = str(recall_state.get("last_good_monitor_fingerprint") or "")
    geometry_changed = bool(previous_fingerprint and previous_fingerprint != fingerprint)
    saved_region = settings.get("clock_region") or {}
    recall_region = recall_state.get("last_good_clock_region") or {}
    recall_used = bool(
        region_valid
        and saved_region
        and saved_region == recall_region
        and previous_fingerprint == fingerprint
    )

    if not palia_game_detected:
        state = PALIA_NOT_OPEN
        message = "Palia not detected - open Palia first."
        action = "open_palia"
        failure = "palia_game_not_detected"
    elif not bool(settings.get("clock_setup_completed", False)):
        state = NEEDS_SETUP
        message = "Clock setup needed - click Setup Clock once."
        action = "setup_clock"
        failure = "clock_setup_incomplete"
    elif not region_valid:
        state = NEEDS_SETUP
        message = "Clock needs setup - click Setup Clock."
        action = "setup_clock"
        failure = region_reason or "clock_region_invalid"
    elif not capture_ready:
        state = CLOCK_CHECK_FAILED
        message = "Clock check failed - run Setup Clock."
        action = "setup_clock"
        failure = capture_reason or "clock_capture_failed"
    elif ocr_preflight_result.startswith("failed"):
        state = DEBUG_NEEDED
        message = "Clock reader needs attention - open Debug / Support."
        action = "open_debug_support"
        failure = ocr_preflight_result
    elif watcher_running:
        state = RUNNING
        message = "Running - reminders are active."
        action = "continue_running"
        failure = ""
    elif bool(settings.get("auto_arm_when_palia_opens", False)):
        state = READY
        message = "Ready - HPR will start reminders automatically."
        action = "ready_auto_arm"
        failure = ""
    else:
        state = WAITING_MANUAL
        message = "Ready - click Start Reminder."
        action = "start_reminder"
        failure = ""

    return SmartResumeResult(
        trigger=trigger,
        checked_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        readiness_state=state,
        user_message=message,
        region_valid=region_valid,
        region_reason=region_reason,
        capture_ready=capture_ready,
        capture_reason=capture_reason,
        palia_game_detected=palia_game_detected,
        palia_launcher_detected=palia_launcher_detected,
        monitor_fingerprint=fingerprint,
        screen_geometry_changed=geometry_changed,
        ocr_preflight_result=ocr_preflight_result,
        recall_state_used=recall_used,
        recovery_action=action,
        failure_reason=failure,
    )

