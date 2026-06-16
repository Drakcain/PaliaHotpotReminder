import argparse
import sys
import tempfile
import tkinter as tk
from contextlib import redirect_stdout
from pathlib import Path

from config import load_settings
from debug_report import build_debug_report
from instance_guard import SingleInstanceGuard
from ocr import parse_clock_result, preflight_tesseract
from paths import get_app_root, get_source_root, resolve_resource_path
from smart_recall import RECALL_KEYS, default_recall_state, load_recall_state, save_recall_state
from smart_resume import NEEDS_SETUP, PALIA_NOT_OPEN, READY, evaluate_smart_resume, monitor_fingerprint
from ui import PaliaHotpotReminderUI


def run_self_test() -> int:
    settings = load_settings()
    checks = [
        ("app_root", str(get_app_root())),
        ("source_root", str(get_source_root())),
        ("icon", str(resolve_resource_path(r"assets\App Icon\HPR_Icon.ico"))),
        ("popup", str(resolve_resource_path(r"assets\Message Board\popup_scroll_clean.png"))),
    ]
    ok, msg, output, tessdata = preflight_tesseract(settings)
    print("SELF_TEST: app_root=", get_app_root())
    print("SELF_TEST: source_root=", get_source_root())
    for key, value in checks:
        print(f"SELF_TEST: {key}={value}")
    print(f"SELF_TEST: tesseract_ok={ok}")
    print(f"SELF_TEST: tesseract_msg={msg}")
    print(f"SELF_TEST: tessdata={tessdata}")
    print(f"SELF_TEST: eng_present={'eng' in output}")
    print(f"SELF_TEST: config_loaded={bool(settings)}")
    print(f"SELF_TEST: clock_region={settings.get('clock_region')}")
    parser_cases = [
        ("10:05 PM", "10:05 PM"),
        ("10:59 PM", "10:59 PM"),
        ("11:00 PM", "11:00 PM"),
        ("11:49 PM", "11:49 PM"),
        ("11:50 PM", "11:50 PM"),
        ("11:59 PM", "11:59 PM"),
        ("12:00 AM", "12:00 AM"),
        ("12:30 AM", "12:30 AM"),
        ("12:48 AM", "12:48 AM"),
        ("12:59 AM", "12:59 AM"),
        ("1:00 AM", "1:00 AM"),
        ("1:49 PM", "1:49 PM"),
        ("11-50 PM", "11:50 PM"),
        ("11 50 PM", "11:50 PM"),
        ("11:50PM", "11:50 PM"),
        ("12-48 AM", "12:48 AM"),
        ("12 48 AM", "12:48 AM"),
        ("12:48AM", "12:48 AM"),
    ]
    parser_ok = True
    for raw, expected in parser_cases:
        result = parse_clock_result(raw, source="self_test")
        case_ok = result.accepted and result.parsed_display_time == expected
        parser_ok = parser_ok and case_ok
        print(f"SELF_TEST: parser_case raw={raw!r} accepted={result.accepted} parsed={result.parsed_display_time!r} expected={expected!r}")
    for raw in ("11:50", "12:48"):
        result = parse_clock_result(raw, source="self_test")
        case_ok = not result.accepted
        parser_ok = parser_ok and case_ok
        print(f"SELF_TEST: parser_reject raw={raw!r} accepted={result.accepted} reject_reason={result.reject_reason!r}")
    print(f"SELF_TEST: parser_ok={parser_ok}")

    diagnostics = {
        "monitors": [
            {"index": 0, "left": -1920, "top": 0, "width": 3840, "height": 1080},
            {"index": 1, "left": 0, "top": 0, "width": 1920, "height": 1080},
        ]
    }
    fingerprint = monitor_fingerprint(diagnostics)
    recall = default_recall_state()
    recall["last_good_clock_region"] = {"left": 100, "top": 20, "width": 240, "height": 84}
    recall["last_good_monitor_fingerprint"] = fingerprint
    resume_settings = {
        "clock_setup_completed": True,
        "clock_region": dict(recall["last_good_clock_region"]),
        "auto_arm_when_palia_opens": True,
    }
    ready_result = evaluate_smart_resume(
        trigger="tray_show",
        settings=resume_settings,
        diagnostics=diagnostics,
        region_valid=True,
        region_reason="ok",
        capture_ready=True,
        capture_reason="ok",
        palia_game_detected=True,
        palia_launcher_detected=True,
        ocr_preflight_result="ok: eng",
        recall_state=recall,
        watcher_running=False,
    )
    invalid_result = evaluate_smart_resume(
        trigger="start_reminder_preflight",
        settings={**resume_settings, "clock_setup_completed": False, "clock_region": {}},
        diagnostics=diagnostics,
        region_valid=False,
        region_reason="clock_region is missing",
        capture_ready=False,
        capture_reason="clock_region is missing",
        palia_game_detected=True,
        palia_launcher_detected=True,
        ocr_preflight_result="ok: eng",
        recall_state=recall,
        watcher_running=False,
    )
    no_game_result = evaluate_smart_resume(
        trigger="startup",
        settings=resume_settings,
        diagnostics=diagnostics,
        region_valid=True,
        region_reason="ok",
        capture_ready=True,
        capture_reason="ok",
        palia_game_detected=False,
        palia_launcher_detected=False,
        ocr_preflight_result="ok: eng",
        recall_state=recall,
        watcher_running=False,
    )
    smart_resume_ok = (
        ready_result.readiness_state == READY
        and ready_result.can_start_reminder
        and ready_result.can_test_clock
        and ready_result.trigger == "tray_show"
        and ready_result.recall_state_used
        and invalid_result.readiness_state == NEEDS_SETUP
        and not invalid_result.can_start_reminder
        and no_game_result.readiness_state == PALIA_NOT_OPEN
        and not no_game_result.can_test_clock
    )
    changed_diagnostics = {
        "monitors": [{"index": 0, "left": 0, "top": 0, "width": 1920, "height": 1080}]
    }
    fingerprint_ok = fingerprint != monitor_fingerprint(changed_diagnostics)
    print(f"SELF_TEST: smart_resume_ok={smart_resume_ok}")
    print(f"SELF_TEST: monitor_fingerprint_ok={fingerprint_ok}")

    recall_ok = False
    with tempfile.TemporaryDirectory(prefix="hpr-self-test-") as temp_dir:
        recall_path = Path(temp_dir) / "recall_state.json"
        missing_state, missing_status = load_recall_state(recall_path)
        save_recall_state(recall, recall_path)
        loaded_state, loaded_status = load_recall_state(recall_path)
        recall_path.write_text("{not-json", encoding="utf-8")
        corrupt_state, corrupt_status = load_recall_state(recall_path)
        recall_ok = (
            missing_status == "missing"
            and loaded_status == "loaded"
            and loaded_state["last_good_clock_region"] == recall["last_good_clock_region"]
            and corrupt_status == "corrupt"
            and corrupt_state == missing_state
            and set(loaded_state) == RECALL_KEYS
            and "current_ocr_frame" not in loaded_state
            and "reminder_cooldown_state" not in loaded_state
        )
    print(f"SELF_TEST: recall_ok={recall_ok}")

    report = build_debug_report(
        header_lines=["self_test=true"],
        settings_lines=[],
        runtime_lines=[],
        warnings=[],
        errors=[],
        state_lines=[],
        process_audit_lines=[],
        session_lines=[],
        smart_resume_lines=["readiness_state=Ready"],
        smart_recall_lines=["recall_load_status=loaded"],
        support_summary_lines=["normal_user_next_step=Start Reminder"],
    )
    report_ok = all(
        heading in report
        for heading in ("## Smart Resume", "## Smart Recall", "## Debug / Support Summary")
    )
    print(f"SELF_TEST: debug_report_ok={report_ok}")

    all_ok = ok and parser_ok and smart_resume_ok and fingerprint_ok and recall_ok and report_ok
    return 0 if all_ok else 2


def main() -> None:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--self-test", action="store_true", help="Run a non-GUI release smoke test and exit.")
    args = parser.parse_args()

    if args.self_test:
        if getattr(sys, "frozen", False) and sys.stdout is None:
            log_path = get_app_root() / "debug" / "self_test.log"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("w", encoding="utf-8") as handle, redirect_stdout(handle):
                code = run_self_test()
            raise SystemExit(code)
        raise SystemExit(run_self_test())

    guard = SingleInstanceGuard("Local\\PaliaHotpotReminder")
    if not guard.acquire():
        raise SystemExit(0)

    root = tk.Tk()
    PaliaHotpotReminderUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
