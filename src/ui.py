import os
import sys
import threading
import tkinter as tk
from tkinter import messagebox
import logging
from datetime import datetime
from pathlib import Path
from time import monotonic
from typing import Callable, Dict, Optional

import mss

import config as config_module
from app_version import APP_VERSION
from app_logging import get_log_paths, initialize_logging
from config import load_settings, save_settings
from ocr import ClockParseResult, normalize_clock_text, ocr_and_parse, parse_clock_result, preflight_tesseract, resolve_tesseract_cmd, resolve_tessdata_dir
from reminders import (
    ReminderManager,
    ReminderOutcome,
    get_reminder_copy,
    get_warning_times,
    normalize_time_label,
    normalize_warning_times,
)
from screencap import (
    DEBUG_IMAGE_PATH,
    SCREEN_DIAGNOSTIC_PATH,
    capture_clock_region,
    capture_screen_diagnostic,
    get_screen_diagnostics,
    probe_clock_region,
    setup_clock_candidate_scan,
    validate_clock_region,
)
from smart_recall import RECALL_PATH, load_recall_state, save_recall_state
from smart_resume import SmartResumeResult, evaluate_smart_resume
from state import PaliaTimeTracker, TrackerSnapshot
from paths import resolve_resource_path
from theme import THEMES
from watchlog import append_watch_log
from tray_manager import TrayManager, tray_available
from debug_report import build_debug_report, export_debug_report
from runtime_trace import open_traced_path
from windows_helpers import (
    PaliaProcessScanResult,
    create_shortcut,
    get_desktop_dir,
    get_shortcut_path,
    get_startup_dir,
    PSUTIL_AVAILABLE,
    PSUTIL_IMPORT_ERROR,
    remove_shortcut,
    scan_palia_processes,
    set_dark_title_bar,
)

def _format_region(settings: Dict) -> str:
    region = settings.get("clock_region", {})
    left = region.get("left", "?")
    top = region.get("top", "?")
    width = region.get("width", "?")
    height = region.get("height", "?")
    return f"X={left}, Y={top}, W={width}, H={height}"


def _default_region() -> Dict[str, int]:
    return {"left": 0, "top": 0, "width": 220, "height": 70}


def _current_virtual_bounds() -> Dict[str, int]:
    with mss.mss() as sct:
        virtual = sct.monitors[0]
        return {
            "left": int(virtual["left"]),
            "top": int(virtual["top"]),
            "width": int(virtual["width"]),
            "height": int(virtual["height"]),
        }


def _is_region_valid_for_bounds(region: Dict, bounds: Dict[str, int]) -> bool:
    try:
        left = int(region.get("left", -1))
        top = int(region.get("top", -1))
        width = int(region.get("width", 0))
        height = int(region.get("height", 0))
    except Exception:
        return False
    if width <= 0 or height <= 0:
        return False
    if left < bounds["left"] or top < bounds["top"]:
        return False
    if left + width > bounds["left"] + bounds["width"]:
        return False
    if top + height > bounds["top"] + bounds["height"]:
        return False
    return True


def _screen_signature() -> str:
    try:
        with mss.mss() as sct:
            monitors = sct.monitors
            primary = monitors[1] if len(monitors) > 1 else monitors[0]
            virtual = monitors[0]
            return f"virtual={virtual['width']}x{virtual['height']}@{virtual['left']},{virtual['top']}|monitors={max(0, len(monitors) - 1)}|primary={primary['width']}x{primary['height']}@{primary['left']},{primary['top']}"
    except Exception:
        return "unknown"


def _is_region_valid_for_screen(region: Dict, bounds: Dict[str, int]) -> bool:
    try:
        left = int(region.get("left", -1))
        top = int(region.get("top", -1))
        width = int(region.get("width", 0))
        height = int(region.get("height", 0))
    except Exception:
        return False
    if width <= 0 or height <= 0:
        return False
    if left < bounds["left"] or top < bounds["top"]:
        return False
    if left + width > bounds["left"] + bounds["width"]:
        return False
    if top + height > bounds["top"] + bounds["height"]:
        return False
    return True


def _format_value(value: str) -> str:
    return value if value else "-"


class PaliaHotpotReminderUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(f"Palia Hotpot Reminder {APP_VERSION}")
        self.root.geometry("820x920")
        self._set_window_icon()
        self.settings = load_settings()
        self.log_path = initialize_logging(bool(self.settings.get("debug_logging", True)), bool(self.settings.get("debug_verbose", False)))
        self.logger = logging.getLogger(__name__)
        self.tracker = PaliaTimeTracker()
        self.watching = False
        self.watch_job: Optional[str] = None
        self.detection_job: Optional[str] = None
        self.last_reminder_snapshot: Optional[TrackerSnapshot] = None
        self.palia_detected = False
        self.palia_process_result = PaliaProcessScanResult(
            game_detected=False,
            launcher_detected=False,
            detection_method="psutil",
            psutil_available=PSUTIL_AVAILABLE,
        )
        self.session_watch_active = False
        self.current_session_id = 0
        self.last_palia_transition = "Not detected"
        self.last_session_reset_reason = ""
        self.reminder_session_reset_at = ""
        self.awaiting_manual_start = False
        self.tray_enabled = False
        self._closing = False
        self._tray_manager: Optional[TrayManager] = None
        self._tray_notice_sent = False
        self._clock_setup_backup: Optional[Dict] = None
        self._clock_setup_session_active = False
        self._clock_setup_cancel_event: Optional[threading.Event] = None
        self.setup_clock_button: Optional[tk.Button] = None
        self._theme_widgets: list[tk.Widget] = []
        self.advanced_visible = False
        self.advanced_frame: Optional[tk.Frame] = None
        self.recall_state, self.recall_load_status = load_recall_state()
        self.current_session_id = int(self.recall_state.get("last_session_id", 0))
        self.last_resume_result: Optional[SmartResumeResult] = None
        self._resume_job: Optional[str] = None
        self._pending_resume_trigger = ""
        self._focus_lost_at: Optional[float] = None
        self._last_resume_monotonic = 0.0
        self._window_was_hidden = False
        self._ocr_engine_ready: Optional[bool] = None
        self._ocr_preflight_result = "not_checked"
        self._tesseract_description = ""

        self.status_var = tk.StringVar(value="Ready")
        self.readiness_var = tk.StringVar(value="Recovering")
        self.diagnostic_var = tk.StringVar(value="")
        self.region_var = tk.StringVar()
        self.resolution_var = tk.StringVar()
        self.screen_diag_var = tk.StringVar()
        self.tesseract_var = tk.StringVar()
        self.time_ratio_var = tk.StringVar(value="-")
        self.setup_state_var = tk.StringVar(value="This PC needs clock setup.")

        self.mode_var = tk.StringVar(value="Unknown")
        self.raw_ocr_var = tk.StringVar(value="-")
        self.normalized_ocr_var = tk.StringVar(value="-")
        self.parsed_time_var = tk.StringVar(value="-")
        self.current_palia_time_var = tk.StringVar(value="-")
        self.last_confirmed_var = tk.StringVar(value="-")
        self.estimated_var = tk.StringVar(value="-")
        self.seconds_since_confirmed_var = tk.StringVar(value="-")

        self.reminders_enabled_var = tk.BooleanVar(value=True)
        self.dark_mode_var = tk.BooleanVar(value=True)
        self.start_with_windows_var = tk.BooleanVar(value=False)
        self.auto_arm_var = tk.BooleanVar(value=False)
        self.start_minimized_var = tk.BooleanVar(value=False)
        self.minimize_to_tray_var = tk.BooleanVar(value=False)
        self.close_to_tray_var = tk.BooleanVar(value=False)
        self.stale_warning_enabled_var = tk.BooleanVar(value=True)
        self.debug_logging_var = tk.BooleanVar(value=True)
        self.debug_verbose_var = tk.BooleanVar(value=False)
        self.reminder_cooldown_var = tk.StringVar(value="300")
        self.hotpot_window_var = tk.StringVar(value="6:00 PM - 3:00 AM")
        self.hotpot_warning_times_var = tk.StringVar(value="5:45 PM, 6:00 PM, 12:00 AM, 2:50 AM")
        self.popup_style_var = tk.StringVar(value="custom")
        self.popup_duration_var = tk.StringVar(value="15")
        self.popup_position_var = tk.StringVar(value="left")
        self.popup_asset_path_var = tk.StringVar(value=r"assets\Message Board\popup_scroll_clean.png")
        self.popup_width_var = tk.StringVar(value="560")
        self.popup_height_var = tk.StringVar(value="420")
        self.popup_left_margin_var = tk.StringVar(value="24")
        self.popup_top_margin_var = tk.StringVar(value="250")
        self.palia_detected_var = tk.StringVar(value="Not detected")
        self.auto_arm_state_var = tk.StringVar(value="Off")
        self.clock_setup_state_var = tk.StringVar(value="Needed")
        self.startup_shortcut_state_var = tk.StringVar(value="Not set")
        self.tray_state_var = tk.StringVar(value="Unavailable")
        self.reminders_enabled_state_var = tk.StringVar(value="On")
        self.debug_log_state_var = tk.StringVar(value="Ready" if self.log_path else "Unavailable")
        self.reminder_status_var = tk.StringVar(value="Ready")
        self.reminder_text_var = tk.StringVar(value="-")
        self.reminder_diagnostic_var = tk.StringVar(value="-")
        self.last_reminder_fired_var = tk.StringVar(value="-")
        self.next_reminder_target_var = tk.StringVar(value="-")
        self.last_parse_candidates_var = tk.StringVar(value="-")
        self.last_parse_accepted_var = tk.StringVar(value="-")
        self.last_parse_reject_reason_var = tk.StringVar(value="-")
        self.last_parse_source_var = tk.StringVar(value="-")

        self.left_var = tk.StringVar()
        self.top_var = tk.StringVar()
        self.width_var = tk.StringVar()
        self.height_var = tk.StringVar()

        self.reminder_manager = ReminderManager(self.root)
        self._build()
        self._refresh_from_settings()
        self._refresh_palia_detection(force_log=False)
        self._sync_snapshot(TrackerSnapshot())
        self._run_smart_resume("startup", refresh_detection=False)
        self._maybe_autostart()
        self._apply_theme()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.bind("<Unmap>", self._on_unmap)
        self.root.bind("<Map>", self._on_map)
        self.root.bind("<FocusOut>", self._on_focus_out)
        self.root.bind("<FocusIn>", self._on_focus_in)
        self._log_startup_state()

    def _set_window_icon(self) -> None:
        icon_path = resolve_resource_path(r"assets\App Icon\HPR_Icon.ico")
        if not icon_path.exists():
            return
        try:
            self.root.iconbitmap(default=str(icon_path))
        except Exception:
            try:
                icon_png = resolve_resource_path(r"assets\App Icon\HPR_Icon.png")
                if icon_png.exists():
                    icon_image = tk.PhotoImage(file=str(icon_png))
                    self.root.iconphoto(True, icon_image)
                    self.root._icon_image = icon_image  # type: ignore[attr-defined]
            except Exception:
                pass

    def _current_theme_name(self) -> str:
        return "dark" if bool(self.dark_mode_var.get()) else "light"

    def _theme(self) -> Dict[str, str]:
        raw = THEMES.get(self._current_theme_name(), THEMES["dark"])
        return {
            "root_bg": raw["window_bg"],
            "section_bg": raw["panel_bg"],
            "raised_bg": raw["panel_raised"],
            "text_fg": raw["text"],
            "muted_fg": raw["text_secondary"],
            "dim_fg": raw["text_muted"],
            "button_bg": raw["button_bg"],
            "button_fg": raw["button_text"],
            "button_active_bg": raw["button_hover"],
            "field_bg": raw["field_bg"],
            "field_fg": raw["text"],
            "field_border": raw["border"],
            "warning_fg": raw["warning"],
            "good_fg": raw["good"],
            "error_fg": raw["error"],
            "accent_fg": raw["accent"],
            "scroll_bg": raw["panel_raised"],
            "scroll_trough": raw["window_bg"],
            "menu_bg": raw["panel_raised"],
            "menu_fg": raw["text"],
            "menu_active_bg": raw["button_hover"],
        }

    def _apply_theme(self) -> None:
        colors = self._theme()
        self.root.configure(bg=colors["root_bg"])
        self._apply_theme_widget(self.root, colors)
        if self._current_theme_name() == "dark":
            set_dark_title_bar(self.root, True)
        else:
            set_dark_title_bar(self.root, False)

    def _apply_theme_widget(self, widget: tk.Widget, colors: Dict[str, str]) -> None:
        try:
            klass = widget.winfo_class()
        except Exception:
            klass = ""

        try:
            if isinstance(widget, tk.Tk) or isinstance(widget, tk.Toplevel):
                widget.configure(bg=colors["root_bg"])
            elif klass == "Frame":
                widget.configure(bg=colors["section_bg"])
            elif klass == "Labelframe":
                widget.configure(
                    bg=colors["section_bg"],
                    fg=colors["text_fg"],
                    highlightbackground=colors["field_border"],
                    highlightcolor=colors["field_border"],
                    bd=1,
                    relief="solid",
                )
            elif klass == "Canvas":
                widget.configure(bg=colors["root_bg"], highlightthickness=0)
            elif klass == "Scrollbar":
                widget.configure(bg=colors["scroll_bg"], troughcolor=colors["scroll_trough"], activebackground=colors["button_active_bg"])
            elif klass == "Label":
                text = str(widget.cget("text")).strip() if "text" in widget.keys() else ""
                fg = colors["text_fg"]
                if text in {"Running in tray", "Ready"}:
                    fg = colors["good_fg"]
                elif text in {"Waiting for Palia...", "Palia detected. Click Setup Clock first."}:
                    fg = colors["warning_fg"]
                elif text in {"Diagnostics", "Reminder details"}:
                    fg = colors["muted_fg"]
                elif text in {"Status", "Setup", "Mode", "Hotpot Window"}:
                    fg = colors["accent_fg"]
                widget.configure(bg=colors["section_bg"], fg=fg)
            elif klass == "Button":
                widget.configure(
                    bg=colors["button_bg"],
                    fg=colors["button_fg"],
                    activebackground=colors["button_active_bg"],
                    activeforeground=colors["button_fg"],
                    highlightbackground=colors["field_border"],
                    highlightcolor=colors["field_border"],
                    bd=1,
                    relief="raised",
                )
            elif klass == "Checkbutton":
                widget.configure(
                    bg=colors["section_bg"],
                    fg=colors["text_fg"],
                    activebackground=colors["section_bg"],
                    activeforeground=colors["text_fg"],
                    selectcolor=colors["field_bg"],
                    highlightbackground=colors["field_border"],
                    highlightcolor=colors["field_border"],
                )
            elif klass == "Entry":
                widget.configure(
                    bg=colors["field_bg"],
                    fg=colors["field_fg"],
                    insertbackground=colors["field_fg"],
                    highlightbackground=colors["field_border"],
                    highlightcolor=colors["accent_fg"],
                    insertborderwidth=0,
                    relief="solid",
                    bd=1,
                )
            elif klass == "OptionMenu":
                widget.configure(
                    bg=colors["button_bg"],
                    fg=colors["button_fg"],
                    activebackground=colors["button_active_bg"],
                    highlightbackground=colors["field_border"],
                    relief="raised",
                    bd=1,
                )
                menu = widget["menu"]
                menu.configure(
                    bg=colors["menu_bg"],
                    fg=colors["menu_fg"],
                    activebackground=colors["menu_active_bg"],
                    activeforeground=colors["menu_fg"],
                    bd=1,
                )
        except Exception:
            pass

        for child in widget.winfo_children():
            self._apply_theme_widget(child, colors)

    def _build(self) -> None:
        self.root.minsize(760, 620)
        self.root.resizable(True, True)

        outer = tk.Frame(self.root)
        outer.pack(fill="both", expand=True)

        canvas = tk.Canvas(outer, highlightthickness=0)
        scrollbar = tk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        frame = tk.Frame(canvas, padx=12, pady=12)
        frame_id = canvas.create_window((0, 0), window=frame, anchor="nw")

        def _sync_scrollregion(_event=None) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _sync_width(event) -> None:
            canvas.itemconfigure(frame_id, width=event.width)

        frame.bind("<Configure>", _sync_scrollregion)
        canvas.bind("<Configure>", _sync_width)
        canvas.bind_all("<MouseWheel>", lambda event: canvas.yview_scroll(int(-1 * (event.delta / 120)), "units"))

        row = tk.Frame(frame)
        row.pack(fill="x", pady=(0, 8))
        tk.Button(row, text="Test Clock", command=self._test_ocr).pack(side="left", padx=(0, 6))
        self.setup_clock_button = tk.Button(row, text="Setup Clock", command=self._setup_clock)
        self.setup_clock_button.pack(side="left", padx=(0, 6))
        tk.Button(row, text="Start Reminder", command=self._start_watching).pack(side="left", padx=(0, 6))
        tk.Button(row, text="Stop Reminder", command=self._stop_watching).pack(side="left", padx=(0, 6))
        tk.Button(row, text="Test Popup", command=self._test_custom_popup).pack(side="left", padx=(0, 6))
        tk.Button(row, text="Debug / Support", command=self._toggle_advanced_settings).pack(side="left")

        summary = tk.LabelFrame(frame, text="HPR Status", padx=10, pady=10)
        summary.pack(fill="x", pady=6)
        self._add_display_row(summary, "Readiness", self.readiness_var, 0)
        self._add_display_row(summary, "Palia", self.palia_detected_var, 1)
        self._add_display_row(summary, "Clock setup", self.clock_setup_state_var, 2)
        self._add_display_row(summary, "Reminder", self.reminder_status_var, 3)
        self._add_display_row(summary, "Next reminder", self.next_reminder_target_var, 4)

        convenience = tk.LabelFrame(frame, text="Convenience", padx=10, pady=10)
        convenience.pack(fill="x", pady=6)
        tk.Button(convenience, text="Create Desktop Shortcut", command=self._create_desktop_shortcut).grid(row=0, column=0, sticky="we", padx=(0, 8), pady=2)
        tk.Checkbutton(convenience, text="Start with Windows", variable=self.start_with_windows_var, command=self._save_convenience_settings).grid(row=0, column=1, sticky="w", pady=2)
        tk.Checkbutton(convenience, text="Dark Mode", variable=self.dark_mode_var, command=self._save_convenience_settings).grid(row=0, column=2, sticky="w", pady=2, padx=(16, 0))
        tk.Checkbutton(convenience, text="Auto-arm when Palia opens", variable=self.auto_arm_var, command=self._save_convenience_settings).grid(row=1, column=0, sticky="w", pady=2)
        tk.Checkbutton(convenience, text="Start hidden in tray", variable=self.start_minimized_var, command=self._save_convenience_settings).grid(row=1, column=1, sticky="w", pady=2)
        tk.Checkbutton(convenience, text="Minimize to tray", variable=self.minimize_to_tray_var, command=self._save_convenience_settings).grid(row=1, column=2, sticky="w", pady=2, padx=(16, 0))
        tk.Checkbutton(convenience, text="Close to tray", variable=self.close_to_tray_var, command=self._save_convenience_settings).grid(row=2, column=0, sticky="w", pady=2)
        tk.Button(convenience, text="Reload Settings", command=self._reload_convenience_settings).grid(row=2, column=1, sticky="we", pady=2)
        tk.Button(convenience, text="Show Window", command=self._show_from_tray).grid(row=2, column=2, sticky="we", pady=2, padx=(16, 0))

        self.advanced_frame = tk.Frame(frame)
        self.advanced_frame.pack(fill="x", pady=6)

        form = tk.LabelFrame(self.advanced_frame, text="Clock Region", padx=10, pady=10)
        form.pack(fill="x", pady=6)

        self._add_field(form, "Left", self.left_var, 0)
        self._add_field(form, "Top", self.top_var, 1)
        self._add_field(form, "Width", self.width_var, 2)
        self._add_field(form, "Height", self.height_var, 3)

        nudge = tk.LabelFrame(self.advanced_frame, text="Nudge Controls", padx=10, pady=10)
        nudge.pack(fill="x", pady=6)

        self._add_nudge_row(
            nudge,
            "Move",
            [
                ("Left -5", lambda: self._nudge("left", -5)),
                ("Left +5", lambda: self._nudge("left", 5)),
                ("Up -5", lambda: self._nudge("top", -5)),
                ("Down +5", lambda: self._nudge("top", 5)),
            ],
        )
        self._add_nudge_row(
            nudge,
            "Big Move",
            [
                ("Left -25", lambda: self._nudge("left", -25)),
                ("Left +25", lambda: self._nudge("left", 25)),
                ("Up -25", lambda: self._nudge("top", -25)),
                ("Down +25", lambda: self._nudge("top", 25)),
            ],
        )
        self._add_nudge_row(
            nudge,
            "Size",
            [
                ("Wider +10", lambda: self._nudge("width", 10)),
                ("Narrower -10", lambda: self._nudge("width", -10)),
                ("Taller +10", lambda: self._nudge("height", 10)),
                ("Shorter -10", lambda: self._nudge("height", -10)),
            ],
        )

        actions = tk.LabelFrame(self.advanced_frame, text="Validation", padx=10, pady=10)
        actions.pack(fill="x", pady=6)
        tk.Button(actions, text="Open Preview Image", command=self._open_preview_image).pack(fill="x", pady=2)
        tk.Button(actions, text="Open Screen Diagnostic", command=self._open_screen_diagnostic).pack(fill="x", pady=2)
        tk.Button(actions, text="Test System Popup", command=self._test_system_popup).pack(fill="x", pady=2)
        tk.Button(actions, text="Test Custom Popup", command=self._test_custom_popup).pack(fill="x", pady=2)
        tk.Button(actions, text="Reset to Default Region", command=self._reset_default_region).pack(fill="x", pady=2)

        reminders = tk.LabelFrame(self.advanced_frame, text="Reminder Rules", padx=10, pady=10)
        reminders.pack(fill="x", pady=6)
        tk.Checkbutton(reminders, text="Reminders Enabled", variable=self.reminders_enabled_var).grid(row=0, column=0, sticky="w", pady=2)
        tk.Checkbutton(reminders, text="Stale Warning Enabled", variable=self.stale_warning_enabled_var).grid(row=0, column=1, sticky="w", pady=2, padx=(16, 0))
        self._add_field(reminders, "Reminder Cooldown (sec)", self.reminder_cooldown_var, 1)
        self._add_display_row(reminders, "Hotpot Window", self.hotpot_window_var, 2)
        tk.Label(reminders, text="Hotpot Warning Times").grid(row=3, column=0, sticky="w", pady=2)
        tk.Entry(reminders, textvariable=self.hotpot_warning_times_var, width=40).grid(row=3, column=1, sticky="w", padx=(8, 20), pady=2)
        tk.Button(reminders, text="Save Reminder Settings", command=self._save_reminder_settings_from_fields).grid(row=4, column=0, sticky="we", pady=(6, 2))
        tk.Button(reminders, text="Reload Reminder Settings", command=self._reload_reminder_settings).grid(row=4, column=1, sticky="we", pady=(6, 2))

        popup = tk.LabelFrame(self.advanced_frame, text="Popup Settings", padx=10, pady=10)
        popup.pack(fill="x", pady=6)
        self._add_option(popup, "Popup Style", self.popup_style_var, 0, ["custom", "system", "auto"])
        self._add_field(popup, "Popup Duration (sec)", self.popup_duration_var, 1)
        self._add_field(popup, "Popup Position", self.popup_position_var, 2)
        self._add_field(popup, "Popup Asset Path", self.popup_asset_path_var, 3, width=30)
        self._add_field(popup, "Popup Width", self.popup_width_var, 4)
        self._add_field(popup, "Popup Height", self.popup_height_var, 5)
        self._add_field(popup, "Popup Left Margin", self.popup_left_margin_var, 6)
        self._add_field(popup, "Popup Top Margin", self.popup_top_margin_var, 7)
        tk.Button(popup, text="Save Popup Settings", command=self._save_popup_settings_from_fields).grid(row=8, column=0, sticky="we", pady=(6, 2))
        tk.Button(popup, text="Reload Popup Settings", command=self._reload_popup_settings).grid(row=8, column=1, sticky="we", pady=(6, 2))

        debug = tk.LabelFrame(self.advanced_frame, text="Debug / Support", padx=10, pady=10)
        debug.pack(fill="x", pady=6)
        tk.Button(debug, text="Debug Report", command=self._show_debug_report).grid(row=0, column=0, sticky="we", pady=2)
        tk.Button(debug, text="Export Debug Report", command=self._export_debug_report).grid(row=0, column=1, sticky="we", pady=2, padx=(16, 0))
        tk.Button(debug, text="Copy Debug Report", command=self._copy_debug_report).grid(row=1, column=0, sticky="we", pady=2)
        tk.Button(debug, text="Open Logs Folder", command=self._open_logs_folder).grid(row=1, column=1, sticky="we", pady=2, padx=(16, 0))
        tk.Button(debug, text="Copy Palia Process Audit", command=self._copy_palia_process_audit).grid(row=2, column=0, sticky="we", pady=2)
        tk.Button(debug, text="View Debug Log", command=self._view_latest_log).grid(row=2, column=1, sticky="we", pady=2, padx=(16, 0))
        tk.Button(debug, text="Copy Clock OCR Debug", command=self._copy_clock_ocr_debug).grid(row=3, column=0, sticky="we", pady=2)
        tk.Button(debug, text="Open latest.log", command=self._open_latest_log).grid(row=3, column=1, sticky="we", pady=2, padx=(16, 0))
        tk.Button(debug, text="Copy Smart Resume Debug", command=self._copy_smart_resume_debug).grid(row=4, column=0, sticky="we", pady=2)
        tk.Button(debug, text="Open Startup Folder", command=self._open_startup_folder).grid(row=4, column=1, sticky="we", pady=2, padx=(16, 0))
        tk.Button(debug, text="Remove Startup Shortcut", command=self._remove_startup_shortcut).grid(row=5, column=0, sticky="we", pady=2)
        tk.Button(debug, text="Recreate Startup Shortcut", command=self._recreate_startup_shortcut).grid(row=5, column=1, sticky="we", pady=2, padx=(16, 0))
        tk.Checkbutton(debug, text="Debug logging", variable=self.debug_logging_var, command=self._save_convenience_settings).grid(row=6, column=0, sticky="w", pady=2)
        tk.Checkbutton(debug, text="Debug verbose", variable=self.debug_verbose_var, command=self._save_convenience_settings).grid(row=6, column=1, sticky="w", pady=2, padx=(16, 0))

        display = tk.LabelFrame(self.advanced_frame, text="Clock State", padx=10, pady=10)
        display.pack(fill="x", pady=6)
        self._add_display_row(display, "Mode", self.mode_var, 0)
        self._add_display_row(display, "Raw OCR", self.raw_ocr_var, 1)
        self._add_display_row(display, "Normalized OCR", self.normalized_ocr_var, 2)
        self._add_display_row(display, "Parsed time", self.parsed_time_var, 3)
        self._add_display_row(display, "Current Palia time", self.current_palia_time_var, 4)
        self._add_display_row(display, "Last confirmed Palia time", self.last_confirmed_var, 5)
        self._add_display_row(display, "Estimated Palia time", self.estimated_var, 6)
        self._add_display_row(display, "Seconds since confirmed", self.seconds_since_confirmed_var, 7)

        reminder_state = tk.LabelFrame(self.advanced_frame, text="Reminder Diagnostics", padx=10, pady=10)
        reminder_state.pack(fill="x", pady=6)
        self._add_display_row(reminder_state, "Palia status", self.palia_detected_var, 0)
        self._add_display_row(reminder_state, "Auto-arm", self.auto_arm_state_var, 1)
        self._add_display_row(reminder_state, "Clock setup", self.clock_setup_state_var, 2)
        self._add_display_row(reminder_state, "Startup shortcut", self.startup_shortcut_state_var, 3)
        self._add_display_row(reminder_state, "Reminders enabled", self.reminders_enabled_state_var, 4)
        self._add_display_row(reminder_state, "Last reminder fired", self.last_reminder_fired_var, 5)
        self._add_display_row(reminder_state, "Next reminder target", self.next_reminder_target_var, 6)
        self._add_display_row(reminder_state, "Reminder text", self.reminder_text_var, 7)
        self._add_display_row(reminder_state, "Reminder status", self.reminder_status_var, 8)
        self._add_display_row(reminder_state, "Reminder details", self.reminder_diagnostic_var, 9)

        info = tk.LabelFrame(self.advanced_frame, text="System Status", padx=10, pady=10)
        info.pack(fill="x", pady=6)
        self._add_display_row(info, "Detected screen", self.resolution_var, 0)
        self._add_display_row(info, "Screen diagnostics", self.screen_diag_var, 1)
        self._add_display_row(info, "Current clock region", self.region_var, 2)
        self._add_display_row(info, "Timing ratio", self.time_ratio_var, 3)
        self._add_display_row(info, "Tesseract", self.tesseract_var, 4)
        self._add_display_row(info, "Setup", self.setup_state_var, 5)
        self._add_display_row(info, "Startup shortcut", self.startup_shortcut_state_var, 6)
        self._add_display_row(info, "Tray", self.tray_state_var, 7)
        self._add_display_row(info, "Auto-arm", self.auto_arm_state_var, 8)
        self._add_display_row(info, "Reminder enabled", self.reminders_enabled_state_var, 9)
        self._add_display_row(info, "Debug Log", self.debug_log_state_var, 10)
        self._add_display_row(info, "Status", self.status_var, 11)
        self._add_display_row(info, "Diagnostics", self.diagnostic_var, 12)
        tk.Label(info, text="Each PC may need its own clock setup.", anchor="w", justify="left").grid(row=13, column=0, columnspan=2, sticky="w", pady=(6, 0))

        self._set_advanced_visible(False)

    def _add_field(self, parent: tk.Widget, label: str, variable: tk.StringVar, row: int, width: int = 12) -> None:
        tk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=2)
        tk.Entry(parent, textvariable=variable, width=width).grid(row=row, column=1, sticky="w", padx=(8, 20), pady=2)

    def _add_option(self, parent: tk.Widget, label: str, variable: tk.StringVar, row: int, values: list[str]) -> None:
        tk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=2)
        option = tk.OptionMenu(parent, variable, *values)
        option.config(width=18)
        option.grid(row=row, column=1, sticky="w", padx=(8, 20), pady=2)

    def _add_display_row(self, parent: tk.Widget, label: str, variable: tk.StringVar, row: int) -> None:
        tk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=2)
        tk.Label(parent, textvariable=variable, anchor="w", justify="left", wraplength=520).grid(row=row, column=1, sticky="w", padx=(8, 0), pady=2)

    def _add_nudge_row(self, parent: tk.Widget, title: str, buttons: list[tuple[str, Callable[[], None]]]) -> None:
        row = tk.Frame(parent)
        row.pack(fill="x", pady=3)
        tk.Label(row, text=title, width=10, anchor="w").pack(side="left")
        for label, command in buttons:
            tk.Button(row, text=label, command=command, width=14).pack(side="left", padx=2)

    def _refresh_from_settings(self, reload_from_disk: bool = True) -> None:
        if reload_from_disk:
            self.settings = load_settings()
        region = self.settings.get("clock_region") or _default_region()
        self.left_var.set(str(region.get("left", 0)))
        self.top_var.set(str(region.get("top", 0)))
        self.width_var.set(str(region.get("width", 220)))
        self.height_var.set(str(region.get("height", 70)))
        self.region_var.set(_format_region(self.settings))
        self.tesseract_var.set(self._describe_tesseract())
        self.resolution_var.set(self._describe_screen())
        self.screen_diag_var.set(self._describe_screen_diagnostics())
        self.time_ratio_var.set(self._describe_time_ratio())
        self.setup_state_var.set(self._describe_setup_state())
        self.clock_setup_state_var.set("Ready" if self._is_clock_setup_ready() else "Needed")
        self.auto_arm_state_var.set("On" if bool(self.settings.get("auto_arm_when_palia_opens", False)) else "Off")
        self._refresh_convenience_fields()
        self._refresh_reminder_fields()
        self._refresh_popup_fields()
        self._refresh_startup_shortcut_state()
        self.dark_mode_var.set(str(self.settings.get("theme", "dark")).strip().lower() != "light")
        self._apply_theme()

    def _log_startup_state(self) -> None:
        try:
            self.logger.info("HPR %s starting", APP_VERSION)
            self.logger.info("app_root=%s", Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent)
            self.logger.info("mode=%s", "packaged" if getattr(sys, "frozen", False) else "source")
            self.logger.info("config_path=%s", config_module.SETTINGS_PATH)
            self.logger.info("log_path=%s", self.log_path or "unavailable")
            self.logger.info("start_minimized=%s", bool(self.settings.get("start_minimized", False)))
            self.logger.info("minimize_to_tray=%s", bool(self.settings.get("minimize_to_tray", False)))
            self.logger.info("close_to_tray=%s", bool(self.settings.get("close_to_tray", False)))
            self.logger.info("show_tray_notifications=%s", bool(self.settings.get("show_tray_notifications", True)))
            self.logger.info("debug_logging=%s", bool(self.settings.get("debug_logging", True)))
            self.logger.info("debug_verbose=%s", bool(self.settings.get("debug_verbose", False)))
            self.logger.info("tray_available=%s", self._tray_supported())
            self.logger.info("palia_process_poll_seconds=%s", self.settings.get("palia_process_poll_seconds", 5))
            self.logger.info("detection_method=psutil")
            self.logger.info("psutil_available=%s", PSUTIL_AVAILABLE)
            self.logger.info("watched_game_process_names=%s", list(self.settings.get("palia_process_names", [])))
            self.logger.info("watched_launcher_process_names=%s", list(self.settings.get("palia_launcher_process_names", ["PaliaClientSteam.exe"])))
            self.logger.info("initial_palia_detected=%s", self.palia_process_result.game_detected)
            self.logger.info("initial_launcher_detected=%s", self.palia_process_result.launcher_detected)
            self.logger.info("pause_when_palia_closes=%s", bool(self.settings.get("pause_when_palia_closes", True)))
            if not PSUTIL_AVAILABLE and PSUTIL_IMPORT_ERROR:
                self.logger.error("psutil import failed: %s", PSUTIL_IMPORT_ERROR)
        except Exception as exc:
            self.logger.debug("startup logging unavailable: %s", exc)

    def _describe_screen(self) -> str:
        try:
            with mss.mss() as sct:
                if len(sct.monitors) < 1:
                    return "No monitor data available."
                monitor = sct.monitors[0]
                return f"Virtual desktop: {monitor['width']} x {monitor['height']} at ({monitor['left']}, {monitor['top']})"
        except Exception as exc:
            return f"Unable to detect screen resolution: {exc}"

    def _describe_tesseract(self, *, force: bool = False) -> str:
        if self._tesseract_description and not force:
            return self._tesseract_description
        try:
            cmd = resolve_tesseract_cmd(self.settings)
            tessdata_dir = resolve_tessdata_dir(cmd)
            engine_ok, engine_message, _, _ = preflight_tesseract(self.settings)
            self._ocr_engine_ready = engine_ok
            self._ocr_preflight_result = f"ok: {engine_message}" if engine_ok else f"failed: {engine_message}"
            eng_path = tessdata_dir / "eng.traineddata"
            self._tesseract_description = (
                f"Bundled clock reader found: yes | "
                f"Language data folder found: {'yes' if tessdata_dir.exists() else 'no'} | "
                f"eng.traineddata found: {'yes' if eng_path.exists() else 'no'} | "
                f"list-langs contains eng: {'yes' if engine_ok else 'no'} | "
                f"Tesseract path used: {cmd} | Tessdata path used: {tessdata_dir}"
            )
            return self._tesseract_description
        except Exception as exc:
            self._ocr_engine_ready = False
            self._ocr_preflight_result = f"failed: {exc}"
            self._tesseract_description = f"Bundled clock reader is missing. Reinstall Palia Hotpot Reminder and keep the tesseract folder beside the EXE. Details: {exc}"
            return self._tesseract_description

    def _describe_setup_state(self) -> str:
        try:
            if not self._is_clock_setup_ready():
                return "This PC needs clock setup."
            return "Clock setup ready."
        except Exception:
            return "This PC needs clock setup."

    def _is_clock_setup_ready(self) -> bool:
        try:
            settings = self.settings
            valid, _ = validate_clock_region(settings)
            return bool(settings.get("clock_setup_completed", False)) and valid
        except Exception:
            return False

    def _persist_recall_state(self) -> None:
        if not bool(self.settings.get("smart_recall_enabled", True)):
            return
        try:
            save_recall_state(self.recall_state)
        except Exception as exc:
            self.logger.warning("Smart Recall save failed: %s", exc)

    def _mark_ocr_result_stale(self, trigger: str) -> None:
        self.raw_ocr_var.set("-")
        self.normalized_ocr_var.set("-")
        self.parsed_time_var.set("-")
        self.last_parse_candidates_var.set("-")
        self.last_parse_accepted_var.set("-")
        self.last_parse_reject_reason_var.set("-")
        self.last_parse_source_var.set(f"stale_after_{trigger}")

    def _record_good_ocr(self, parse_result: ClockParseResult) -> None:
        if not parse_result.accepted or not parse_result.parsed_display_time:
            return
        self.recall_state["last_good_ocr_time"] = parse_result.parsed_display_time
        self.recall_state["last_good_ocr_timestamp"] = parse_result.timestamp_real or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.recall_state["last_good_ocr_raw"] = parse_result.raw_ocr
        self.recall_state["last_good_ocr_normalized"] = parse_result.normalized_ocr
        self._persist_recall_state()

    def _run_smart_resume(
        self,
        trigger: str,
        *,
        refresh_detection: bool = True,
        check_engine: bool = False,
        mark_ocr_stale: bool = True,
        handle_process_transitions: bool = True,
    ) -> SmartResumeResult:
        self.settings = load_settings()
        self.readiness_var.set("Recovering")
        try:
            diagnostics = get_screen_diagnostics()
        except Exception as exc:
            diagnostics = {"monitors": []}
            self.logger.warning("Smart Resume screen diagnostics failed trigger=%s error=%s", trigger, exc)

        region_valid, region_reason = validate_clock_region(self.settings)
        setup_complete = bool(self.settings.get("clock_setup_completed", False))
        if setup_complete and region_valid:
            capture_ready, capture_reason = probe_clock_region(self.settings)
        else:
            capture_ready = False
            capture_reason = region_reason if not region_valid else "clock_setup_incomplete"

        previous_game_detected = self.palia_process_result.game_detected
        if refresh_detection:
            process_result = self._refresh_palia_detection(
                allow_session_transitions=False,
                force_log=bool(self.settings.get("debug_verbose", False)),
            )
        else:
            process_result = self.palia_process_result

        if check_engine:
            self.tesseract_var.set(self._describe_tesseract(force=True))
        ocr_result = self._ocr_preflight_result
        result = evaluate_smart_resume(
            trigger=trigger,
            settings=self.settings,
            diagnostics=diagnostics,
            region_valid=region_valid,
            region_reason=region_reason,
            capture_ready=capture_ready,
            capture_reason=capture_reason,
            palia_game_detected=process_result.game_detected,
            palia_launcher_detected=process_result.launcher_detected,
            ocr_preflight_result=ocr_result,
            recall_state=self.recall_state,
            watcher_running=bool(self.watching and self.session_watch_active),
        )
        self.last_resume_result = result
        self.readiness_var.set(result.readiness_state)
        self.status_var.set(result.user_message)
        self.diagnostic_var.set("")

        if mark_ocr_stale:
            self._mark_ocr_result_stale(trigger)

        virtual = diagnostics.get("virtual_desktop") or {}
        self.recall_state.update(
            {
                "last_resume_check_time": result.checked_at,
                "last_resume_check_result": result.readiness_state,
                "last_palia_game_detected": process_result.game_detected,
                "last_palia_launcher_detected": process_result.launcher_detected,
                "last_session_id": self.current_session_id,
                "last_recovery_action": result.recovery_action,
                "last_failure_reason": result.failure_reason,
                "last_clock_validation_status": "valid" if region_valid and capture_ready else "invalid",
                "last_clock_validation_reason": "" if region_valid and capture_ready else (capture_reason or region_reason),
            }
        )
        if setup_complete and region_valid and capture_ready:
            self.recall_state["last_good_clock_region"] = dict(self.settings.get("clock_region") or {})
            self.recall_state["last_good_monitor_fingerprint"] = result.monitor_fingerprint
            self.recall_state["last_good_screen_bounds"] = dict(virtual)
        self._persist_recall_state()

        self.logger.info(
            "Smart Resume trigger=%s geometry_refreshed=true region_valid=%s region_reason=%s capture_ready=%s capture_reason=%s "
            "game_detected=%s launcher_detected=%s ocr_preflight=%s recall_used=%s screen_geometry_changed=%s "
            "recovery_action=%s readiness=%s failure_reason=%s",
            trigger,
            region_valid,
            region_reason,
            capture_ready,
            capture_reason,
            process_result.game_detected,
            process_result.launcher_detected,
            ocr_result,
            result.recall_state_used,
            result.screen_geometry_changed,
            result.recovery_action,
            result.readiness_state,
            result.failure_reason or "-",
        )
        self._last_resume_monotonic = monotonic()
        if (
            handle_process_transitions
            and self.watching
            and process_result.game_detected != previous_game_detected
        ):
            if process_result.game_detected:
                self._handle_palia_reopened(result)
            else:
                self._handle_palia_closed()
        return result

    def _schedule_smart_resume(self, trigger: str, delay_ms: int = 150) -> None:
        if self._closing:
            return
        priority = {"focus_gained": 1, "deiconify": 2, "tray_show": 3}
        if self._resume_job is not None:
            if priority.get(trigger, 1) <= priority.get(self._pending_resume_trigger, 1):
                return
            try:
                self.root.after_cancel(self._resume_job)
            except Exception:
                pass
        self._pending_resume_trigger = trigger
        self._resume_job = self.root.after(delay_ms, self._run_scheduled_smart_resume)

    def _run_scheduled_smart_resume(self) -> None:
        trigger = self._pending_resume_trigger or "focus_gained"
        self._resume_job = None
        self._pending_resume_trigger = ""
        self._run_smart_resume(trigger)

    def _describe_time_ratio(self) -> str:
        ratio = self.settings.get("palia_minutes_per_real_second", 0.4)
        max_age = self.settings.get("max_estimated_reminder_age_seconds", 300)
        warnings = "; ".join(config_module.LAST_SETTINGS_WARNINGS)
        base = f"1 real second = {ratio} Palia minutes | max estimated age: {max_age}s"
        if warnings:
            return f"{base} | config fix: {warnings}"
        return base

    def _refresh_reminder_fields(self) -> None:
        reminders_enabled = bool(self.settings.get("reminders_enabled", True))
        stale_warning_enabled = bool(self.settings.get("stale_warning_enabled", True))
        cooldown = self.settings.get("reminder_cooldown_seconds", 300)
        hotpot_times = get_warning_times(self.settings)
        self.reminders_enabled_var.set(reminders_enabled)
        self.stale_warning_enabled_var.set(stale_warning_enabled)
        self.reminder_cooldown_var.set(str(cooldown))
        self.hotpot_warning_times_var.set(", ".join(hotpot_times))
        start_label = str(self.settings.get("hotpot_start_time", "6:00 PM"))
        end_label = str(self.settings.get("hotpot_end_time", "3:00 AM"))
        self.hotpot_window_var.set(f"{start_label} - {end_label}")
        self.reminders_enabled_state_var.set("On" if reminders_enabled else "Off")
        self.next_reminder_target_var.set(self.reminder_manager.last_reminder_target or "-")
        self.last_reminder_fired_var.set(self.reminder_manager.last_reminder_fired or "-")
        self.reminder_status_var.set(self.reminder_manager.last_status_message or "Ready")
        self.reminder_text_var.set(self._describe_reminder_text())
        self.reminder_diagnostic_var.set(self.reminder_manager.last_diagnostic or "-")

    def _refresh_convenience_fields(self) -> None:
        self.dark_mode_var.set(str(self.settings.get("theme", "dark")).strip().lower() != "light")
        self.start_with_windows_var.set(bool(self.settings.get("start_with_windows", False)))
        self.auto_arm_var.set(bool(self.settings.get("auto_arm_when_palia_opens", False)))
        self.start_minimized_var.set(bool(self.settings.get("start_minimized", False)))
        self.minimize_to_tray_var.set(bool(self.settings.get("minimize_to_tray", False)))
        self.close_to_tray_var.set(bool(self.settings.get("close_to_tray", False)))
        self.debug_logging_var.set(bool(self.settings.get("debug_logging", True)))
        self.debug_verbose_var.set(bool(self.settings.get("debug_verbose", False)))
        self.debug_log_state_var.set("Ready" if self.log_path else "Unavailable")
        self.tray_enabled = bool(self._tray_supported() and (self.settings.get("minimize_to_tray", False) or self.settings.get("close_to_tray", False)))
        if self._tray_manager is not None and self._tray_manager.icon is not None:
            self.tray_state_var.set("Active")
        else:
            self.tray_state_var.set("Available" if self.tray_enabled else "Disabled")
        self._refresh_startup_shortcut_state()

    def _refresh_startup_shortcut_state(self) -> None:
        shortcut_path = get_shortcut_path(get_startup_dir(), "Hotpot-Remind.lnk")
        enabled = bool(self.settings.get("start_with_windows", False))
        if shortcut_path.exists():
            self.startup_shortcut_state_var.set(f"Present at {shortcut_path}")
        elif enabled:
            self.startup_shortcut_state_var.set("Enabled in settings, shortcut missing")
        else:
            self.startup_shortcut_state_var.set("Not enabled")

    def _scan_palia_processes(self) -> PaliaProcessScanResult:
        return scan_palia_processes(
            self.settings.get("palia_process_names", []),
            self.settings.get("palia_launcher_process_names", ["PaliaClientSteam.exe"]),
        )

    def _format_palia_status(self, result: PaliaProcessScanResult) -> str:
        if result.game_detected:
            return "Game detected"
        if result.launcher_detected:
            return "Launcher detected"
        return "Not detected"

    def _build_palia_process_audit_lines(self) -> list[str]:
        result = self.palia_process_result
        return [
            f"detection_method={result.detection_method}",
            f"psutil_available={result.psutil_available}",
            f"last_detection_check={result.last_detection_check_time or '-'}",
            f"watched_game_process_names={list(result.watched_game_process_names)}",
            f"watched_launcher_process_names={list(result.watched_launcher_process_names)}",
            f"game_detected={result.game_detected}",
            f"launcher_detected={result.launcher_detected}",
            f"matched_game_process={result.matched_game_process_name or '-'}",
            f"matched_launcher_process={result.matched_launcher_process_name or '-'}",
            f"matched_game_pid={result.matched_game_pid if result.matched_game_pid is not None else '-'}",
            f"matched_launcher_pid={result.matched_launcher_pid if result.matched_launcher_pid is not None else '-'}",
            f"nearby_palia_like_processes={list(result.nearby_palia_like_processes)}",
            f"auto_arm_when_palia_opens={bool(self.settings.get('auto_arm_when_palia_opens', False))}",
            f"pause_when_palia_closes={bool(self.settings.get('pause_when_palia_closes', True))}",
            f"watcher_running={self.watching}",
            f"waiting_for_manual_start={self.awaiting_manual_start}",
            f"current_session_id={self.current_session_id}",
            f"last_palia_transition={self.last_palia_transition}",
            f"last_session_reset_reason={self.last_session_reset_reason or '-'}",
        ]

    def _log_palia_process_audit(self, result: PaliaProcessScanResult) -> None:
        if not bool(self.settings.get("debug_verbose", False)):
            return
        self.logger.info(
            "Palia process audit watched_game=%s watched_launcher=%s matched_game=%s matched_launcher=%s nearby=%s game_detected=%s launcher_detected=%s",
            list(result.watched_game_process_names),
            list(result.watched_launcher_process_names),
            result.matched_game_process_name or "-",
            result.matched_launcher_process_name or "-",
            list(result.nearby_palia_like_processes),
            result.game_detected,
            result.launcher_detected,
        )

    def _apply_palia_process_result(
        self,
        result: PaliaProcessScanResult,
        *,
        allow_session_transitions: bool,
        force_log: bool,
    ) -> None:
        previous = self.palia_process_result
        previous_game_detected = previous.game_detected
        previous_launcher_detected = previous.launcher_detected
        self.palia_process_result = result
        self.palia_detected = result.game_detected
        self.palia_detected_var.set(self._format_palia_status(result))

        if force_log or result.game_detected != previous_game_detected:
            if result.game_detected:
                self.logger.info(
                    "Palia game detected process=%s pid=%s auto_arm=%s",
                    result.matched_game_process_name or "-",
                    result.matched_game_pid if result.matched_game_pid is not None else "-",
                    bool(self.settings.get("auto_arm_when_palia_opens", False)),
                )
            else:
                self.logger.info("Palia game closed auto_arm=%s", bool(self.settings.get("auto_arm_when_palia_opens", False)))
        if force_log or result.launcher_detected != previous_launcher_detected:
            if result.launcher_detected:
                self.logger.info(
                    "Palia launcher detected process=%s pid=%s",
                    result.matched_launcher_process_name or "-",
                    result.matched_launcher_pid if result.matched_launcher_pid is not None else "-",
                )
            else:
                self.logger.info("Palia launcher closed")
        self._log_palia_process_audit(result)

        if allow_session_transitions and result.game_detected != previous_game_detected:
            if result.game_detected:
                self._handle_palia_reopened()
            else:
                self._handle_palia_closed()
            return

        if not allow_session_transitions and not self.watching:
            auto_arm = bool(self.settings.get("auto_arm_when_palia_opens", False))
            if result.game_detected:
                self.awaiting_manual_start = not auto_arm
                self.last_palia_transition = "Palia detected"
                if not auto_arm:
                    self.status_var.set("Watcher waiting for manual Start Watch")
                    self.diagnostic_var.set("Palia game client is detected. Click Start Reminder to begin a fresh session.")
            elif result.launcher_detected:
                self.awaiting_manual_start = not auto_arm
                self.last_palia_transition = "Palia launcher detected"
                if not auto_arm:
                    self.status_var.set("Palia launcher detected")
                    self.diagnostic_var.set("Palia launcher is open. HPR will show Game detected when the shipping client starts.")
            else:
                self.awaiting_manual_start = False
                self.last_palia_transition = "Palia not detected"
                if not auto_arm:
                    self.status_var.set("Ready")
                    self.diagnostic_var.set("Palia is not running.")

    def _refresh_palia_detection(self, *, allow_session_transitions: bool = False, force_log: bool = False) -> PaliaProcessScanResult:
        result = self._scan_palia_processes()
        self._apply_palia_process_result(
            result,
            allow_session_transitions=allow_session_transitions,
            force_log=force_log,
        )
        return result

    def _refresh_popup_fields(self) -> None:
        self.popup_style_var.set(str(self.settings.get("popup_style", "custom")))
        self.popup_duration_var.set(str(self.settings.get("popup_duration_seconds", 15)))
        self.popup_position_var.set(str(self.settings.get("popup_position", "left")))
        self.popup_asset_path_var.set(str(self.settings.get("popup_asset_path", r"assets\Message Board\popup_scroll_clean.png")))
        self.popup_width_var.set(str(self.settings.get("popup_width", 560)))
        self.popup_height_var.set(str(self.settings.get("popup_height", 420)))
        self.popup_left_margin_var.set(str(self.settings.get("popup_left_margin", 24)))
        self.popup_top_margin_var.set(str(self.settings.get("popup_top_margin", 250)))

    def _describe_screen_diagnostics(self) -> str:
        try:
            diagnostics = get_screen_diagnostics()
            virtual = diagnostics.get("virtual_desktop") or {}
            primary = diagnostics.get("primary_monitor") or {}
            parts = [
                f"monitor_count={diagnostics.get('monitor_count', 0)}",
                f"virtual={virtual.get('width', '?')}x{virtual.get('height', '?')}@({virtual.get('left', '?')},{virtual.get('top', '?')})",
            ]
            if primary:
                parts.append(
                    f"primary={primary.get('width', '?')}x{primary.get('height', '?')}@({primary.get('left', '?')},{primary.get('top', '?')})"
                )
            monitors = diagnostics.get("monitors", [])
            if len(monitors) > 1:
                monitor_details = "; ".join(
                    f"{item['index']}={item['width']}x{item['height']}@({item['left']},{item['top']})" for item in monitors[1:]
                )
                parts.append(f"monitors={monitor_details}")
            return " | ".join(parts)
        except Exception as exc:
            return f"Unable to read screen diagnostics: {exc}"

    def _read_region_fields(self) -> Optional[Dict[str, int]]:
        try:
            return {
                "left": int(self.left_var.get()),
                "top": int(self.top_var.get()),
                "width": int(self.width_var.get()),
                "height": int(self.height_var.get()),
            }
        except ValueError:
            self.status_var.set("Invalid region: left, top, width, and height must all be integers.")
            messagebox.showerror("Invalid Region", "Please enter whole numbers for all region fields.")
            return None

    def _save_region_from_fields(self) -> None:
        region = self._read_region_fields()
        if region is None:
            return

        self.settings = load_settings()
        candidate = dict(self.settings)
        candidate["clock_region"] = region
        ok, msg = validate_clock_region(candidate)
        if not ok:
            self.status_var.set(f"Invalid region: {msg}")
            messagebox.showerror("Invalid Region", msg)
            return

        self.settings = candidate
        save_settings(self.settings)
        self._refresh_from_settings(reload_from_disk=False)
        self.status_var.set("Region saved")
        self.diagnostic_var.set("")
        messagebox.showinfo("Saved", "Region saved successfully.")

    def _reload_region(self) -> None:
        self._refresh_from_settings(reload_from_disk=False)
        self.status_var.set("Region reloaded from config/settings.json")
        self.diagnostic_var.set("")

    def _nudge(self, field: str, delta: int) -> None:
        region = self._read_region_fields()
        if region is None:
            return
        if field in ("left", "top"):
            region[field] = region[field] + delta
        else:
            region[field] = max(1, region[field] + delta)
        self.left_var.set(str(region["left"]))
        self.top_var.set(str(region["top"]))
        self.width_var.set(str(region["width"]))
        self.height_var.set(str(region["height"]))
        self.status_var.set(f"Nudged {field} by {delta}px")

    def _reset_default_region(self) -> None:
        region = _default_region()
        self.left_var.set(str(region["left"]))
        self.top_var.set(str(region["top"]))
        self.width_var.set(str(region["width"]))
        self.height_var.set(str(region["height"]))
        self.status_var.set("Loaded default region values")

    def _set_advanced_visible(self, visible: bool) -> None:
        self.advanced_visible = visible
        if self.advanced_frame is None:
            return
        if visible:
            self.advanced_frame.pack(fill="x", pady=6)
        else:
            self.advanced_frame.pack_forget()

    def _toggle_advanced_settings(self) -> None:
        self._set_advanced_visible(not self.advanced_visible)
        self.status_var.set("Debug / Support shown" if self.advanced_visible else "Debug / Support hidden")

    def _start_watching(self) -> None:
        self._refresh_from_settings()
        readiness = self._run_smart_resume(
            "start_reminder_preflight",
            refresh_detection=True,
            check_engine=True,
            mark_ocr_stale=True,
            handle_process_transitions=False,
        )
        if not readiness.can_start_reminder:
            self.session_watch_active = False
            self.awaiting_manual_start = False
            self._sync_reminder_state(
                ReminderOutcome(
                    status_message=readiness.user_message,
                    reminders_enabled=False,
                    diagnostic=readiness.failure_reason,
                )
            )
            self.status_var.set(readiness.user_message)
            self.logger.info(
                "Watcher start blocked readiness=%s reason=%s",
                readiness.readiness_state,
                readiness.failure_reason or "-",
            )
            return
        if self.watching and self.session_watch_active:
            self.readiness_var.set("Running")
            self.status_var.set("Running - reminders are already active.")
            self.logger.info("Watcher start ignored: already active")
            return
        self._cancel_detection_tick()
        if not self.watching:
            self.watching = True
            self.logger.info("Watcher started")
        self._begin_new_palia_session("manual_start")
        self.readiness_var.set("Running")
        self.status_var.set("Running - reminders are active.")
        self.logger.info("Watcher waiting for manual start resolved by Start Reminder")
        self.diagnostic_var.set("")
        self._schedule_watch_tick(0)

    def _arm_auto_watcher(self) -> None:
        self._cancel_detection_tick()
        if not self.watching:
            self.watching = True
            self.logger.info("Watcher armed for automatic Palia detection")
        readiness = self._run_smart_resume(
            "auto_arm_startup",
            refresh_detection=True,
            check_engine=False,
            mark_ocr_stale=False,
        )
        if self.palia_process_result.game_detected and readiness.can_start_reminder:
            self._begin_new_palia_session("auto_arm_initial_detect")
            self.readiness_var.set("Running")
            self.status_var.set("Running - reminders are active.")
        else:
            self.session_watch_active = False
            self.awaiting_manual_start = False
        self._schedule_watch_tick(0)

    def _stop_watching(self) -> None:
        self.watching = False
        self.session_watch_active = False
        self.awaiting_manual_start = False
        if self.watch_job is not None:
            try:
                self.root.after_cancel(self.watch_job)
            except Exception:
                pass
            self.watch_job = None
        self.status_var.set("Watching stopped")
        self.readiness_var.set("Paused")
        self.diagnostic_var.set("")
        self.logger.info("Watcher stopped")
        self._schedule_detection_tick(int(max(0.1, self._get_process_poll_seconds()) * 1000))

    def _reset_volatile_watch_state(self, reason: str) -> None:
        self.tracker.reset()
        self.last_reminder_snapshot = None
        self.reminder_manager.reset_session_state()
        self.reminder_session_reset_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.last_session_reset_reason = reason
        self._sync_snapshot(TrackerSnapshot())
        self._sync_reminder_state(ReminderOutcome(status_message="Ready", reminders_enabled=False))
        self.diagnostic_var.set("")
        self.logger.info("Volatile session state reset reason=%s", reason)

    def _begin_new_palia_session(self, reason: str) -> None:
        self.current_session_id += 1
        self._reset_volatile_watch_state(reason)
        self.session_watch_active = True
        self.awaiting_manual_start = False
        self.last_palia_transition = "Palia reopened — fresh session" if self.current_session_id > 1 else "Palia detected"
        self.recall_state["last_session_id"] = self.current_session_id
        self._persist_recall_state()
        self.logger.info("New Palia session started session_id=%s reason=%s", self.current_session_id, reason)

    def _handle_palia_closed(self) -> None:
        self.last_palia_transition = "Palia closed — session reset"
        self.logger.info("Palia closed session_id=%s", self.current_session_id)
        self._reset_volatile_watch_state("palia_closed")
        self.session_watch_active = False
        auto_arm = bool(self.settings.get("auto_arm_when_palia_opens", False))
        self.awaiting_manual_start = not auto_arm
        if bool(self.settings.get("pause_when_palia_closes", True)):
            self.status_var.set("Watcher paused until Palia opens" if auto_arm else "Watcher waiting for manual Start Watch")
            self.diagnostic_var.set("Palia closed. Session-only runtime state was reset.")
        else:
            self.status_var.set("Palia closed — session reset")
            self.diagnostic_var.set("Palia closed. Old estimated time and reminder state were cleared.")
        self.readiness_var.set("Paused")
        self.recall_state["last_session_id"] = self.current_session_id
        self.recall_state["last_recovery_action"] = "session_reset_after_palia_closed"
        self.recall_state["last_failure_reason"] = ""
        self._persist_recall_state()

    def _handle_palia_reopened(self, readiness: Optional[SmartResumeResult] = None) -> None:
        auto_arm = bool(self.settings.get("auto_arm_when_palia_opens", False))
        if readiness is None:
            readiness = self._run_smart_resume(
                "palia_reopen",
                refresh_detection=False,
                check_engine=False,
                mark_ocr_stale=True,
            )
        if auto_arm and readiness.can_start_reminder:
            self._begin_new_palia_session("palia_reopened_auto_arm")
            self.readiness_var.set("Running")
            self.status_var.set("Fresh session ready - reminders are active.")
            self.diagnostic_var.set("Palia reopened. Auto-arm started a clean watcher session.")
            self.logger.info("Palia reopened session_id=%s auto_arm=True", self.current_session_id)
            return
        if auto_arm:
            self._reset_volatile_watch_state("palia_reopened_preflight_blocked")
            self.session_watch_active = False
            self.awaiting_manual_start = False
            self.status_var.set(readiness.user_message)
            self.logger.info(
                "Palia reopen auto-arm blocked readiness=%s reason=%s",
                readiness.readiness_state,
                readiness.failure_reason or "-",
            )
            return
        self._reset_volatile_watch_state("palia_reopened_waiting_manual")
        self.session_watch_active = False
        self.awaiting_manual_start = True
        self.last_palia_transition = "Palia reopened — waiting for manual Start Watch"
        self.status_var.set("Watcher waiting for manual Start Watch")
        self.diagnostic_var.set("Palia reopened. Click Start Reminder to begin a fresh session.")
        self.logger.info("Palia reopened waiting for manual start")

    def _on_close(self) -> None:
        if bool(self.settings.get("close_to_tray", False)) and self._tray_supported():
            self.logger.info("X close redirected to tray")
            self._hide_to_tray()
            return
        if bool(self.settings.get("close_to_tray", False)):
            try:
                self.root.iconify()
            except Exception:
                pass
            self.status_var.set("Tray unavailable; minimized instead")
            return
        self._exit_app()

    def _on_unmap(self, event) -> None:
        if self._closing:
            return
        if getattr(event, "widget", None) is not self.root:
            return
        try:
            state = str(self.root.state()).lower()
        except Exception:
            state = ""
        if state != "iconic":
            return
        self._window_was_hidden = True
        self.recall_state["last_known_app_visibility_state"] = "minimized"
        self._persist_recall_state()
        if self._minimize_to_tray_if_allowed():
            return

    def _on_map(self, event) -> None:
        if self._closing or getattr(event, "widget", None) is not self.root:
            return
        if self._window_was_hidden:
            self._window_was_hidden = False
            self._schedule_smart_resume("deiconify")

    def _on_focus_out(self, event) -> None:
        if self._closing or getattr(event, "widget", None) is not self.root:
            return
        self._focus_lost_at = monotonic()

    def _on_focus_in(self, event) -> None:
        if self._closing or getattr(event, "widget", None) is not self.root:
            return
        lost_at = self._focus_lost_at
        self._focus_lost_at = None
        if lost_at is None:
            return
        away_seconds = monotonic() - lost_at
        if away_seconds >= 2.0 and monotonic() - self._last_resume_monotonic >= 1.0:
            self._schedule_smart_resume("focus_gained", delay_ms=200)

    def _hide_to_tray(self) -> None:
        if not self._tray_supported():
            try:
                self.root.iconify()
            except Exception:
                pass
            self.status_var.set("Tray unavailable; minimized instead")
            return
        if self._tray_manager is None:
            self._tray_manager = TrayManager(
                root=self.root,
                settings=self.settings,
                icon_path=resolve_resource_path(r"assets\App Icon\HPR_Icon.ico"),
                on_restore=self._show_from_tray,
                on_exit=self._exit_app,
                on_start_reminders=self._start_watching,
                on_stop_reminders=self._stop_watching,
                on_test_popup=self._test_custom_popup,
                on_setup_clock=self._setup_clock,
                on_hide=self._hide_window_only,
            )
        if self._tray_manager.start():
            self.logger.info("Tray started")
            self._hide_window_only()
            self._maybe_show_tray_notification()
            return
        try:
            self.root.iconify()
        except Exception:
            pass
        self.status_var.set("Tray unavailable; minimized instead")

    def _show_from_tray(self) -> None:
        try:
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
        except Exception:
            pass
        self._window_was_hidden = False
        self.tray_state_var.set("Active" if self._tray_manager and self._tray_manager.icon is not None else "Available")
        self.logger.info("Tray show")
        self._schedule_smart_resume("tray_show", delay_ms=100)

    def _exit_app(self) -> None:
        self._closing = True
        self.logger.info("Tray exit")
        if self._clock_setup_cancel_event is not None:
            self._clock_setup_cancel_event.set()
        self.recall_state["last_known_app_visibility_state"] = "closed"
        self.recall_state["last_session_id"] = self.current_session_id
        self._persist_recall_state()
        if self._resume_job is not None:
            try:
                self.root.after_cancel(self._resume_job)
            except Exception:
                pass
            self._resume_job = None
        if self.watch_job is not None:
            try:
                self.root.after_cancel(self.watch_job)
            except Exception:
                pass
            self.watch_job = None
        if self.detection_job is not None:
            try:
                self.root.after_cancel(self.detection_job)
            except Exception:
                pass
            self.detection_job = None
        if self._tray_manager is not None:
            self._tray_manager.stop()
        self.root.after(0, self.root.destroy)

    def _hide_window_only(self) -> None:
        self._window_was_hidden = True
        self.recall_state["last_known_app_visibility_state"] = "tray"
        self._persist_recall_state()
        if self._tray_manager is not None and self._tray_manager.icon is not None:
            try:
                self.root.withdraw()
            except Exception:
                pass
            self.status_var.set("Running in tray")
            self.tray_state_var.set("Active")
            return
        try:
            self.root.iconify()
        except Exception:
            pass
        self.status_var.set("Tray unavailable; minimized instead")
        self.tray_state_var.set("Disabled" if not self.tray_enabled else "Available")
        self.logger.info("Window hidden without tray")

    def _popup_placeholder(self) -> None:
        self._test_system_popup()

    def _schedule_watch_tick(self, delay_ms: int) -> None:
        if not self.watching:
            return
        if self.watch_job is not None:
            try:
                self.root.after_cancel(self.watch_job)
            except Exception:
                pass
        self.watch_job = self.root.after(delay_ms, self._watch_tick)

    def _cancel_detection_tick(self) -> None:
        if self.detection_job is None:
            return
        try:
            self.root.after_cancel(self.detection_job)
        except Exception:
            pass
        self.detection_job = None

    def _schedule_detection_tick(self, delay_ms: int) -> None:
        if self._closing:
            return
        if self.detection_job is not None:
            try:
                self.root.after_cancel(self.detection_job)
            except Exception:
                pass
        self.detection_job = self.root.after(delay_ms, self._detection_tick)

    def _detection_tick(self) -> None:
        self.detection_job = None
        if self._closing:
            return
        if not self.watching:
            self.settings = load_settings()
            self._refresh_palia_detection(
                allow_session_transitions=False,
                force_log=bool(self.settings.get("debug_verbose", False)),
            )
        self._schedule_detection_tick(int(max(0.1, self._get_process_poll_seconds()) * 1000))

    def _clock_region_string(self, settings: Dict) -> str:
        region = settings.get("clock_region") or {}
        return _format_region({"clock_region": region})

    def _log_clock_parse(self, parse_result: ClockParseResult, *, previous_confirmed_time: str = "") -> None:
        if parse_result.accepted:
            self.logger.info(
                "Clock parse accepted source=%s raw_ocr=%r normalized_ocr=%r selected_time=%s parsed_minutes=%s accepted=%s previous_confirmed=%s region=%s",
                parse_result.source or "-",
                parse_result.raw_ocr,
                parse_result.normalized_ocr,
                parse_result.parsed_display_time or "-",
                parse_result.parsed_minutes if parse_result.parsed_minutes is not None else "-",
                parse_result.accepted,
                previous_confirmed_time or "-",
                parse_result.region_used or "-",
            )
            return
        if parse_result.reject_reason:
            self.logger.warning(
                "Clock parse rejected source=%s raw_ocr=%r normalized_ocr=%r candidates=%s reject_reason=%s region=%s",
                parse_result.source or "-",
                parse_result.raw_ocr,
                parse_result.normalized_ocr,
                list(parse_result.parse_candidates),
                parse_result.reject_reason,
                parse_result.region_used or "-",
            )
        elif bool(self.settings.get("debug_verbose", False)):
            self.logger.info(
                "Clock parse no-match source=%s raw_ocr=%r normalized_ocr=%r candidates=%s region=%s",
                parse_result.source or "-",
                parse_result.raw_ocr,
                parse_result.normalized_ocr,
                list(parse_result.parse_candidates),
                parse_result.region_used or "-",
            )

    def _snapshot_for_rejected_test(self, parse_result: ClockParseResult, diagnostic: str) -> TrackerSnapshot:
        def current(variable: tk.StringVar) -> str:
            value = variable.get()
            return "" if value == "-" else value

        mode = current(self.mode_var) or "Unknown"
        return TrackerSnapshot(
            mode=mode,
            status_message=diagnostic or "Clock check failed",
            raw_ocr=parse_result.raw_ocr,
            normalized_ocr=parse_result.normalized_ocr,
            parse_candidates=" | ".join(parse_result.parse_candidates),
            parse_accepted=False,
            parse_reject_reason=parse_result.reject_reason,
            parse_source=parse_result.source,
            parsed_time="",
            current_palia_time=current(self.current_palia_time_var),
            last_confirmed_palia_time=current(self.last_confirmed_var),
            estimated_palia_time=current(self.estimated_var),
            seconds_since_confirmed=current(self.seconds_since_confirmed_var),
        )

    def _run_clock_read(
        self,
        *,
        source: str = "watcher",
        preserve_tracker_on_reject: bool = False,
    ) -> tuple[TrackerSnapshot, str, ClockParseResult]:
        settings = load_settings()
        diagnostic = ""
        parse_result = ClockParseResult(source=source, timestamp_real=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        previous_confirmed_time = self.tracker.last_parsed_time

        try:
            engine_ok, engine_message, _, _ = preflight_tesseract(settings)
            self._ocr_engine_ready = engine_ok
            self._ocr_preflight_result = f"ok: {engine_message}" if engine_ok else f"failed: {engine_message}"
            if not engine_ok:
                snapshot = (
                    self._snapshot_for_rejected_test(parse_result, engine_message)
                    if preserve_tracker_on_reject
                    else self.tracker.update(parse_result, settings)
                )
                return (
                    snapshot,
                    engine_message,
                    parse_result,
                )
            bounds = _current_virtual_bounds()
            region = settings.get("clock_region") or {}
            if not bool(settings.get("clock_setup_completed", False)):
                diagnostic = "This PC needs clock setup. Click Setup Clock."
            elif not _is_region_valid_for_bounds(region, bounds):
                diagnostic = "This clock box was made for a different screen. Click Setup Clock."
            else:
                image_path = capture_clock_region(settings)
                parse_result = ocr_and_parse(
                    image_path,
                    source=source,
                    region_used=self._clock_region_string(settings),
                )
        except FileNotFoundError as exc:
            diagnostic = f"Missing Tesseract: {exc}"
        except Exception as exc:
            diagnostic = f"Capture/OCR failed: {exc}"

        snapshot = (
            self._snapshot_for_rejected_test(parse_result, diagnostic)
            if preserve_tracker_on_reject and not parse_result.accepted
            else self.tracker.update(parse_result, settings)
        )
        self._log_clock_parse(parse_result, previous_confirmed_time=previous_confirmed_time)
        self._record_good_ocr(parse_result)
        if not diagnostic:
            region = settings.get("clock_region", {})
            if snapshot.mode == "Confirmed":
                if not parse_result.accepted and parse_result.raw_ocr.strip():
                    diagnostic = f"Unreadable sample ignored; still confirmed. Raw OCR='{parse_result.raw_ocr}'. Region={region}"
                else:
                    diagnostic = "Visible clock confirmed"
            elif snapshot.mode in ("Estimated", "Stale"):
                if parse_result.raw_ocr.strip():
                    diagnostic = f"Clock hidden/unreadable. Raw OCR='{parse_result.raw_ocr}'. Region={region}"
                else:
                    diagnostic = f"Clock hidden/unreadable. Region={region}"
            elif not parse_result.accepted and parse_result.raw_ocr.strip():
                diagnostic = (
                    f"The clock box does not seem to contain the Palia time. Raw OCR='{parse_result.raw_ocr}'. "
                    f"Cleaned='{parse_result.normalized_ocr}'. Reject='{parse_result.reject_reason or 'no_match'}'. Region={region}"
                )
            elif not parse_result.accepted:
                diagnostic = "This clock box was made for a different screen. Click Setup Clock."
        self._append_watch_state(snapshot, diagnostic)
        return snapshot, diagnostic, parse_result

    def _watch_tick(self) -> None:
        self.watch_job = None
        if not self.watching:
            return

        self._refresh_from_settings()
        result = self._refresh_palia_detection(
            allow_session_transitions=True,
            force_log=bool(self.settings.get("debug_verbose", False)),
        )
        auto_arm = bool(self.settings.get("auto_arm_when_palia_opens", False))
        if not result.game_detected:
            self._sync_reminder_state(ReminderOutcome(status_message="Waiting for Palia...", reminders_enabled=False))
            if auto_arm:
                self.status_var.set("Watcher paused until Palia opens")
                self.diagnostic_var.set("Auto-arm is waiting for a running Palia process.")
            self._schedule_watch_tick(int(max(0.1, self._get_process_poll_seconds()) * 1000))
            return
        if not self._is_clock_setup_ready():
            self._sync_reminder_state(ReminderOutcome(status_message="Clock setup needed - click Setup Clock.", reminders_enabled=False))
            self.readiness_var.set("Needs Setup Clock")
            self.status_var.set("Clock setup needed - click Setup Clock once.")
            self.diagnostic_var.set("Clock setup is required before reminders can start.")
            self._schedule_watch_tick(int(max(0.1, self._get_process_poll_seconds()) * 1000))
            return
        if not self.session_watch_active:
            self._sync_reminder_state(ReminderOutcome(status_message="Watcher waiting for manual Start Watch", reminders_enabled=False))
            if not auto_arm:
                self.status_var.set("Watcher waiting for manual Start Watch")
                self.diagnostic_var.set("Palia is detected. Click Start Reminder to begin a fresh session.")
            self._schedule_watch_tick(int(max(0.1, self._get_process_poll_seconds()) * 1000))
            return

        snapshot, diagnostic, parse_result = self._run_clock_read(source="watcher")
        self._sync_snapshot(snapshot)
        self.diagnostic_var.set(diagnostic)
        reminder_outcome = self._evaluate_reminders(snapshot)
        self._sync_reminder_state(reminder_outcome)
        self.last_reminder_snapshot = snapshot
        self.status_var.set(reminder_outcome.status_message or snapshot.status_message)

        poll_seconds = self._get_process_poll_seconds() if auto_arm else self._get_poll_seconds()
        self._schedule_watch_tick(int(max(0.1, poll_seconds) * 1000))

    def _get_poll_seconds(self) -> float:
        try:
            return float(self.settings.get("poll_interval_seconds", 1.0))
        except (TypeError, ValueError):
            return 1.0

    def _get_process_poll_seconds(self) -> float:
        try:
            return float(self.settings.get("palia_process_poll_seconds", 5))
        except (TypeError, ValueError):
            return 5.0

    def _sync_snapshot(self, snapshot: TrackerSnapshot) -> None:
        self.mode_var.set(_format_value(snapshot.mode))
        self.raw_ocr_var.set(_format_value(snapshot.raw_ocr))
        self.normalized_ocr_var.set(_format_value(snapshot.normalized_ocr))
        self.parsed_time_var.set(_format_value(snapshot.parsed_time))
        self.current_palia_time_var.set(_format_value(snapshot.current_palia_time))
        self.last_confirmed_var.set(_format_value(snapshot.last_confirmed_palia_time))
        self.estimated_var.set(_format_value(snapshot.estimated_palia_time))
        self.seconds_since_confirmed_var.set(_format_value(snapshot.seconds_since_confirmed))
        self.last_parse_candidates_var.set(_format_value(snapshot.parse_candidates))
        self.last_parse_accepted_var.set("Yes" if snapshot.parse_accepted else "No")
        self.last_parse_reject_reason_var.set(_format_value(snapshot.parse_reject_reason))
        self.last_parse_source_var.set(_format_value(snapshot.parse_source))

    def _sync_reminder_state(self, outcome: ReminderOutcome) -> None:
        reminders_enabled = bool(outcome.reminders_enabled) if outcome.reminders_enabled is not False else False
        self.reminders_enabled_state_var.set("On" if reminders_enabled else "Off")
        self.last_reminder_fired_var.set(_format_value(outcome.last_reminder_fired or self.reminder_manager.last_reminder_fired))
        self.next_reminder_target_var.set(_format_value(outcome.next_reminder_target or self.reminder_manager.last_reminder_target))
        self.reminder_text_var.set(_format_value(self._describe_reminder_text(outcome)))
        self.reminder_status_var.set(_format_value(outcome.status_message or self.reminder_manager.last_status_message))
        self.reminder_diagnostic_var.set(_format_value(outcome.diagnostic or self.reminder_manager.last_diagnostic))

    def _evaluate_reminders(self, snapshot: TrackerSnapshot) -> ReminderOutcome:
        try:
            return self.reminder_manager.evaluate(snapshot, self.settings)
        except Exception as exc:
            return ReminderOutcome(decision="error", status_message=f"Reminder evaluation failed: {exc}", diagnostic=str(exc))

    def _append_watch_state(self, snapshot: TrackerSnapshot, diagnostic: str) -> None:
        if not bool(self.settings.get("watch_log_enabled", True)):
            return
        try:
            append_watch_log(
                mode=snapshot.mode,
                status_message=snapshot.status_message,
                raw_ocr=snapshot.raw_ocr,
                normalized_ocr=snapshot.normalized_ocr,
                parse_candidates=snapshot.parse_candidates,
                parse_accepted=snapshot.parse_accepted,
                parse_reject_reason=snapshot.parse_reject_reason,
                parse_source=snapshot.parse_source,
                parsed_time=snapshot.parsed_time,
                last_confirmed_palia_time=snapshot.last_confirmed_palia_time,
                estimated_palia_time=snapshot.estimated_palia_time,
                seconds_since_confirmed=snapshot.seconds_since_confirmed,
                diagnostic=diagnostic,
            )
        except Exception:
            pass

    def _test_region_capture(self) -> None:
        self.settings = load_settings()
        ok, msg = validate_clock_region(self.settings)
        if not ok:
            self.status_var.set(f"Capture failed: {msg}")
            self.diagnostic_var.set("")
            messagebox.showerror("Capture Failed", msg)
            return
        try:
            out_path = capture_clock_region(self.settings)
            self.status_var.set(f"Preview captured: {out_path}")
            self.diagnostic_var.set("")
            messagebox.showinfo("Preview Captured", f"Saved debug image:\n{out_path}")
        except Exception as exc:
            self.status_var.set(f"Capture failed: {exc}")
            self.diagnostic_var.set("")
            messagebox.showerror("Capture Failed", str(exc))

    def _capture_screen_diagnostic(self) -> None:
        try:
            out_path = capture_screen_diagnostic()
            self._refresh_from_settings()
            self.status_var.set(f"Screen diagnostic captured: {out_path}")
            self.diagnostic_var.set("Full-screen diagnostic captured for calibration only.")
            messagebox.showinfo("Screen Diagnostic Captured", f"Saved full-screen diagnostic image:\n{out_path}")
        except Exception as exc:
            self.status_var.set(f"Screen diagnostic failed: {exc}")
            self.diagnostic_var.set("")
            messagebox.showerror("Screen Diagnostic Failed", str(exc))

    def _open_preview_image(self) -> None:
        if not DEBUG_IMAGE_PATH.exists():
            self.status_var.set("Preview image missing. Run Preview Region Capture first.")
            messagebox.showerror("Missing Preview", "Run Preview Region Capture first.")
            return
        try:
            open_traced_path(DEBUG_IMAGE_PATH, purpose="open preview image")
            self.status_var.set(f"Opened preview image: {DEBUG_IMAGE_PATH}")
            self.diagnostic_var.set("")
        except Exception as exc:
            self.status_var.set(f"Could not open preview image: {exc}")
            messagebox.showerror("Open Failed", str(exc))

    def _open_screen_diagnostic(self) -> None:
        if not SCREEN_DIAGNOSTIC_PATH.exists():
            self.status_var.set("Screen diagnostic missing. Capture Screen Diagnostic first.")
            messagebox.showerror("Missing Diagnostic", "Capture Screen Diagnostic first.")
            return
        try:
            open_traced_path(SCREEN_DIAGNOSTIC_PATH, purpose="open screen diagnostic")
            self.status_var.set(f"Opened screen diagnostic: {SCREEN_DIAGNOSTIC_PATH}")
            self.diagnostic_var.set("")
        except Exception as exc:
            self.status_var.set(f"Could not open screen diagnostic: {exc}")
            messagebox.showerror("Open Failed", str(exc))

    def _test_ocr(self) -> None:
        readiness = self._run_smart_resume(
            "test_clock_preflight",
            refresh_detection=True,
            check_engine=True,
            mark_ocr_stale=True,
        )
        if not readiness.can_test_clock:
            self.status_var.set(readiness.user_message)
            self.logger.info(
                "Test Clock blocked readiness=%s reason=%s",
                readiness.readiness_state,
                readiness.failure_reason or "-",
            )
            messagebox.showinfo("Clock Test", readiness.user_message)
            return

        snapshot, diagnostic, parse_result = self._run_clock_read(
            source="test_clock",
            preserve_tracker_on_reject=True,
        )
        self._sync_snapshot(snapshot)
        self.diagnostic_var.set(diagnostic)
        if parse_result.accepted:
            self.readiness_var.set("Ready")
            self.status_var.set("Ready - Palia clock detected.")
        else:
            self.readiness_var.set("Clock Check Failed")
            self.status_var.set("Clock check failed - run Setup Clock.")
        self.logger.info(
            "Test Clock result accepted=%s reject_reason=%s region=%s resume_state=%s",
            parse_result.accepted,
            parse_result.reject_reason or "-",
            parse_result.region_used or self._clock_region_string(self.settings),
            readiness.readiness_state,
        )
        messagebox.showinfo(
            "Clock Test Result",
            "Raw OCR: {raw}\nNormalized OCR: {cleaned}\nParsed time: {parsed}\nAccepted: {accepted}\nReason: {reason}\nParse candidates: {candidates}\nMode: {mode}\nLast confirmed: {last_confirmed}\nEstimated: {estimated}\nSeconds since confirmed: {seconds}\nClock region: {region}".format(
                raw=snapshot.raw_ocr or "<empty>",
                cleaned=snapshot.normalized_ocr or "<empty>",
                parsed=snapshot.parsed_time or "No valid clock read",
                accepted="Yes" if parse_result.accepted else "No",
                reason=parse_result.reject_reason or "accepted",
                candidates=", ".join(parse_result.parse_candidates) or "<none>",
                mode=snapshot.mode,
                last_confirmed=snapshot.last_confirmed_palia_time or "N/A",
                estimated=snapshot.estimated_palia_time or "N/A",
                seconds=snapshot.seconds_since_confirmed or "N/A",
                region=parse_result.region_used or self._clock_region_string(self.settings),
            ),
        )

    def _setup_clock(self) -> None:
        if self._clock_setup_session_active:
            if self._clock_setup_cancel_event is not None:
                self._clock_setup_cancel_event.set()
            self.status_var.set("Cancelling Setup Clock...")
            return
        self._begin_clock_setup_session()
        self._clock_setup_cancel_event = threading.Event()
        if self.setup_clock_button is not None:
            self.setup_clock_button.configure(text="Cancel Setup")
        self.status_var.set("Setup Clock is searching this PC's screen for the Palia clock.")
        self.readiness_var.set("Checking Clock")
        self.logger.info("Clock setup background scan started")
        threading.Thread(target=self._setup_clock_worker, name="HPR-SetupClock", daemon=True).start()

    def _setup_clock_worker(self) -> None:
        try:
            region, image_path, parsed_time = setup_clock_candidate_scan(self._clock_setup_cancel_event)
        except Exception as exc:
            try:
                self.root.after(0, lambda error=exc: self._finish_setup_clock(None, None, "", error))
            except Exception:
                pass
            return
        try:
            self.root.after(
                0,
                lambda: self._finish_setup_clock(region, image_path, parsed_time, None),
            )
        except Exception:
            pass

    def _finish_setup_clock(
        self,
        region: Optional[Dict[str, int]],
        image_path: Optional[Path],
        parsed_time: str,
        error: Optional[Exception],
    ) -> None:
        if self._closing:
            return
        if parsed_time == "cancelled":
            self._restore_clock_setup_session("cancelled")
            self.readiness_var.set("Ready" if self._is_clock_setup_ready() else "Needs Setup Clock")
            self.status_var.set("Setup Clock cancelled. Previous setup restored.")
            self.logger.info("Clock setup background scan cancelled")
            return
        if error is not None:
            self._restore_clock_setup_session("failed")
            self.readiness_var.set("Clock Check Failed")
            self.status_var.set(f"Setup Clock failed: {error}")
            messagebox.showerror("Setup Clock", f"Setup Clock failed:\n{error}")
            return

        if not region or not parsed_time:
            self._restore_clock_setup_session("not found")
            self.readiness_var.set("Needs Setup Clock")
            self.status_var.set("Clock not found automatically. Open Debug / Support and use Preview Clock Box.")
            messagebox.showinfo(
                "Setup Clock",
                "Clock not found automatically. Open Debug / Support and use Preview Clock Box.",
            )
            return

        confirm = messagebox.askyesno("Setup Clock", f"Clock found at {parsed_time}.\n\nUse this clock box?")
        if not confirm:
            self._restore_clock_setup_session("cancelled")
            self.readiness_var.set("Ready" if self._is_clock_setup_ready() else "Needs Setup Clock")
            self.status_var.set("Clock box not saved.")
            return

        updated = dict(self.settings)
        updated["clock_region"] = {
            "left": int(region["left"]),
            "top": int(region["top"]),
            "width": int(region["width"]),
            "height": int(region["height"]),
        }
        updated["clock_setup_completed"] = True
        save_settings(updated)
        self.settings = load_settings()
        self.logger.info(
            "Clock setup committed old_region=%s new_region=%s",
            self._clock_setup_backup.get("clock_region") if self._clock_setup_backup else None,
            self.settings.get("clock_region", {}),
        )
        self._clear_clock_setup_session()
        self._refresh_from_settings()
        self.logger.info("Clock setup background scan finished parsed_time=%s", parsed_time)
        readiness = self._run_smart_resume(
            "setup_clock_committed",
            refresh_detection=True,
            check_engine=False,
            mark_ocr_stale=True,
        )
        if (
            bool(self.settings.get("auto_arm_when_palia_opens", False))
            and self.watching
            and self.palia_process_result.game_detected
            and readiness.can_start_reminder
            and not self.session_watch_active
        ):
            self._begin_new_palia_session("setup_clock_committed_auto_arm")
            self.readiness_var.set("Running")
            self.status_var.set("Fresh session ready - reminders are active.")
        self.status_var.set(f"Clock box saved from {image_path or DEBUG_IMAGE_PATH}")
        messagebox.showinfo("Setup Clock", f"Clock box saved.\nDetected time: {parsed_time}")

    def _begin_clock_setup_session(self) -> None:
        self.settings = load_settings()
        self._clock_setup_backup = dict(self.settings)
        staged = dict(self.settings)
        staged["clock_setup_completed"] = False
        staged["clock_region"] = {}
        self.settings = staged
        self._clock_setup_session_active = True
        self._mark_ocr_result_stale("setup_clock")
        self.logger.info(
            "Clock setup session started old_completed=%s old_region=%s",
            bool(self._clock_setup_backup.get("clock_setup_completed", False)) if self._clock_setup_backup else False,
            self._clock_setup_backup.get("clock_region") if self._clock_setup_backup else None,
        )
        self._refresh_from_settings(reload_from_disk=False)

    def _restore_clock_setup_session(self, reason: str) -> None:
        if not self._clock_setup_session_active:
            return
        if self._clock_setup_backup is not None:
            self.settings = dict(self._clock_setup_backup)
            self.logger.info(
                "Clock setup session restored reason=%s restored_region=%s restored_completed=%s",
                reason,
                self.settings.get("clock_region", {}),
                bool(self.settings.get("clock_setup_completed", False)),
            )
            self._refresh_from_settings(reload_from_disk=False)
            if not self._is_clock_setup_ready():
                self._sync_reminder_state(
                    ReminderOutcome(
                        status_message="Clock setup needed - click Setup Clock.",
                        reminders_enabled=False,
                        diagnostic="Clock setup is required before reminders can start.",
                    )
                )
        self._clear_clock_setup_session()

    def _clear_clock_setup_session(self) -> None:
        self._clock_setup_backup = None
        self._clock_setup_session_active = False
        self._clock_setup_cancel_event = None
        if self.setup_clock_button is not None:
            self.setup_clock_button.configure(text="Setup Clock")

    def _save_reminder_settings_from_fields(self) -> None:
        self.settings = load_settings()
        candidate = dict(self.settings)
        candidate["reminders_enabled"] = bool(self.reminders_enabled_var.get())
        candidate["stale_warning_enabled"] = bool(self.stale_warning_enabled_var.get())
        candidate["reminder_cooldown_seconds"] = self._read_reminder_cooldown()
        candidate["hotpot_warning_times"] = normalize_warning_times(self.hotpot_warning_times_var.get())
        candidate["reminder_minutes"] = candidate["hotpot_warning_times"]
        candidate["hotpot_start_time"] = str(self.settings.get("hotpot_start_time", "6:00 PM"))
        candidate["hotpot_end_time"] = str(self.settings.get("hotpot_end_time", "3:00 AM"))
        save_settings(candidate)
        self.settings = candidate
        self._refresh_reminder_fields()
        self.status_var.set("Reminder settings saved")
        self.diagnostic_var.set("")
        messagebox.showinfo("Saved", "Reminder settings saved successfully.")

    def _reload_reminder_settings(self) -> None:
        self._refresh_from_settings()
        self.status_var.set("Reminder settings reloaded from config/settings.json")
        self.diagnostic_var.set("")

    def _read_reminder_cooldown(self) -> int:
        try:
            return max(0, int(self.reminder_cooldown_var.get()))
        except (TypeError, ValueError):
            messagebox.showerror("Invalid Cooldown", "Reminder cooldown must be a whole number of seconds.")
            return int(self.settings.get("reminder_cooldown_seconds", 300))

    def _save_popup_settings_from_fields(self) -> None:
        self.settings = load_settings()
        candidate = dict(self.settings)
        candidate["popup_style"] = self.popup_style_var.get().strip().lower() or "custom"
        candidate["popup_duration_seconds"] = self._read_int_or_default(self.popup_duration_var, "Popup Duration", 15, minimum=1)
        candidate["popup_position"] = self.popup_position_var.get().strip().lower() or "left"
        candidate["popup_asset_path"] = self.popup_asset_path_var.get().strip() or r"assets\Message Board\popup_scroll_clean.png"
        candidate["popup_width"] = self._read_int_or_default(self.popup_width_var, "Popup Width", 560, minimum=320)
        candidate["popup_height"] = self._read_int_or_default(self.popup_height_var, "Popup Height", 420, minimum=240)
        candidate["popup_left_margin"] = self._read_int_or_default(self.popup_left_margin_var, "Popup Left Margin", 24, minimum=0)
        candidate["popup_top_margin"] = self._read_int_or_default(self.popup_top_margin_var, "Popup Top Margin", 250, minimum=0)
        save_settings(candidate)
        self.settings = candidate
        self._refresh_popup_fields()
        self.status_var.set("Popup settings saved")
        self.diagnostic_var.set("")
        messagebox.showinfo("Saved", "Popup settings saved successfully.")

    def _reload_popup_settings(self) -> None:
        self._refresh_from_settings()
        self.status_var.set("Popup settings reloaded from config/settings.json")
        self.diagnostic_var.set("")

    def _create_desktop_shortcut(self) -> None:
        try:
            exe_path = Path(sys.executable).resolve()
            if exe_path.suffix.lower() != ".exe":
                raise RuntimeError("Desktop shortcut is only available from the packaged EXE.")
            shortcut_path = get_shortcut_path(get_desktop_dir(), "Hotpot-Remind.lnk")
            create_shortcut(
                shortcut_path=shortcut_path,
                target_path=exe_path,
                working_directory=exe_path.parent,
                icon_path=resolve_resource_path(r"assets\App Icon\HPR_Icon.ico"),
                description="PaliaHotpotReminder",
            )
            self.status_var.set(f"Desktop shortcut created: {shortcut_path}")
            messagebox.showinfo("Desktop Shortcut", f"Created shortcut:\n{shortcut_path}")
        except Exception as exc:
            self.status_var.set(f"Desktop shortcut failed: {exc}")
            messagebox.showerror("Desktop Shortcut", str(exc))

    def _save_convenience_settings(self) -> None:
        self.settings = load_settings()
        previous_start_minimized = bool(self.settings.get("start_minimized", False))
        candidate = dict(self.settings)
        candidate["theme"] = "dark" if bool(self.dark_mode_var.get()) else "light"
        candidate["start_with_windows"] = bool(self.start_with_windows_var.get())
        candidate["auto_arm_when_palia_opens"] = bool(self.auto_arm_var.get())
        candidate["start_minimized"] = bool(self.start_minimized_var.get())
        candidate["minimize_to_tray"] = bool(self.minimize_to_tray_var.get())
        candidate["close_to_tray"] = bool(self.close_to_tray_var.get())
        candidate["debug_logging"] = bool(self.debug_logging_var.get())
        candidate["debug_verbose"] = bool(self.debug_verbose_var.get())
        if not previous_start_minimized and candidate["start_minimized"]:
            confirm = messagebox.askyesno(
                "Start Hidden in Tray",
                "Start hidden in tray means the app will open hidden on launch.\n\nAre you sure you want to enable it?",
            )
            if not confirm:
                self.start_minimized_var.set(False)
                self.status_var.set("Start hidden in tray not changed")
                return
        save_settings(candidate)
        self.settings = candidate
        self._sync_startup_shortcut()
        self._refresh_convenience_fields()
        self._apply_theme()
        self.status_var.set("Convenience settings saved")

    def _reload_convenience_settings(self) -> None:
        self._refresh_from_settings()
        self.status_var.set("Convenience settings reloaded from config/settings.json")
        self.diagnostic_var.set("")

    def _maybe_autostart(self) -> None:
        self._sync_startup_shortcut()
        self.tray_enabled = bool(self._tray_supported() and (self.settings.get("minimize_to_tray", False) or self.settings.get("close_to_tray", False)))
        self.tray_state_var.set("Enabled" if self.tray_enabled else "Disabled")
        self._schedule_detection_tick(0)
        if bool(self.settings.get("auto_arm_when_palia_opens", False)):
            self._arm_auto_watcher()
        if bool(self.settings.get("start_minimized", False)):
            if self.tray_enabled:
                self.logger.info("Startup decision: hidden (start_minimized=true)")
                self._hide_to_tray()
            else:
                try:
                    self.root.iconify()
                except Exception:
                    pass
                self.logger.info("Startup decision: minimized (tray unavailable)")
        else:
            self.logger.info("Startup decision: visible (start_minimized=false)")

    def _maybe_show_tray_notification(self) -> None:
        if getattr(self, "_tray_notice_sent", False):
            return
        if not bool(self.settings.get("show_tray_notifications", True)):
            return
        self._tray_notice_sent = True
        if self._tray_manager is not None:
            self._tray_manager.notify_once(
                "Palia Hotpot Reminder is still running in the tray.\nUse the tray icon to show or exit."
            )

    def _sync_startup_shortcut(self) -> None:
        shortcut_path = get_shortcut_path(get_startup_dir(), "Hotpot-Remind.lnk")
        if not bool(self.settings.get("start_with_windows", False)):
            remove_shortcut(shortcut_path)
            self._refresh_startup_shortcut_state()
            return
        exe_path = Path(sys.executable).resolve()
        if exe_path.suffix.lower() != ".exe":
            self._refresh_startup_shortcut_state()
            return
        create_shortcut(
            shortcut_path=shortcut_path,
            target_path=exe_path,
            working_directory=exe_path.parent,
            icon_path=resolve_resource_path(r"assets\App Icon\HPR_Icon.ico"),
            description="PaliaHotpotReminder",
        )
        self._refresh_startup_shortcut_state()

    def _tray_supported(self) -> bool:
        return tray_available()

    def _minimize_to_tray_if_allowed(self) -> bool:
        if not bool(self.settings.get("minimize_to_tray", False)):
            return False
        if not self._tray_supported():
            return False
        self._hide_to_tray()
        return True

    def _remove_startup_shortcut(self) -> None:
        try:
            shortcut_path = get_shortcut_path(get_startup_dir(), "Hotpot-Remind.lnk")
            remove_shortcut(shortcut_path)
            self.settings = load_settings()
            candidate = dict(self.settings)
            candidate["start_with_windows"] = False
            save_settings(candidate)
            self.settings = candidate
            self._refresh_from_settings()
            self.status_var.set("Startup shortcut removed")
            messagebox.showinfo("Startup Shortcut", f"Removed shortcut:\n{shortcut_path}")
        except Exception as exc:
            self.status_var.set(f"Remove startup shortcut failed: {exc}")
            messagebox.showerror("Startup Shortcut", str(exc))

    def _recreate_startup_shortcut(self) -> None:
        try:
            self.settings = load_settings()
            candidate = dict(self.settings)
            candidate["start_with_windows"] = True
            save_settings(candidate)
            self.settings = candidate
            self._sync_startup_shortcut()
            self._refresh_from_settings()
            self.status_var.set("Startup shortcut recreated")
            messagebox.showinfo("Startup Shortcut", "Recreated the Startup shortcut for this user.")
        except Exception as exc:
            self.status_var.set(f"Recreate startup shortcut failed: {exc}")
            messagebox.showerror("Startup Shortcut", str(exc))

    def _open_startup_folder(self) -> None:
        try:
            open_traced_path(get_startup_dir(), purpose="open startup folder")
            self.status_var.set("Opened Startup folder")
        except Exception as exc:
            self.status_var.set(f"Could not open Startup folder: {exc}")
            messagebox.showerror("Startup Folder", str(exc))

    def _open_logs_folder(self) -> None:
        latest, _ = get_log_paths()
        try:
            latest.parent.mkdir(parents=True, exist_ok=True)
            open_traced_path(latest.parent, purpose="open logs folder")
            self.status_var.set("Opened Logs folder")
        except Exception as exc:
            self.status_var.set(f"Could not open Logs folder: {exc}")
            messagebox.showerror("Logs Folder", str(exc))

    def _open_latest_log(self) -> None:
        latest, _ = get_log_paths()
        try:
            if not latest.exists():
                latest.parent.mkdir(parents=True, exist_ok=True)
                latest.touch()
            open_traced_path(latest, purpose="open latest log")
            self.status_var.set("Opened latest.log")
        except Exception as exc:
            self.status_var.set(f"Could not open latest.log: {exc}")
            messagebox.showerror("latest.log", str(exc))

    def _view_latest_log(self) -> None:
        self._open_latest_log()

    def _build_debug_report_text(self) -> str:
        latest_log, _ = get_log_paths()
        runtime_mode = "packaged" if getattr(sys, "frozen", False) else "source"
        log_lines = latest_log.read_text(encoding="utf-8", errors="replace").splitlines() if latest_log.exists() else []
        process_audit_lines = self._build_palia_process_audit_lines()
        state_lines = [
            f"Tray: {'Active' if self._tray_manager and self._tray_manager.icon is not None else ('Ready' if self.tray_enabled else 'Unavailable')}",
            f"Watcher: {'Running' if self.watching else 'Stopped'}",
            f"Palia: {self._format_palia_status(self.palia_process_result)}",
            f"palia_detection_method={self.palia_process_result.detection_method}",
        ]
        return build_debug_report(
            header_lines=[
                f"app_version={APP_VERSION}",
                f"status={self.status_var.get()}",
                f"diagnostic={self.diagnostic_var.get()}",
            ],
            settings_lines=[
                f"app_root={Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent.parent}",
                f"config_path={config_module.SETTINGS_PATH}",
                f"log_path={latest_log}",
                f"theme={self._current_theme_name()}",
                f"start_minimized={bool(self.settings.get('start_minimized', False))}",
                f"minimize_to_tray={bool(self.settings.get('minimize_to_tray', False))}",
                f"close_to_tray={bool(self.settings.get('close_to_tray', False))}",
                f"show_tray_notifications={bool(self.settings.get('show_tray_notifications', True))}",
                f"debug_logging={bool(self.settings.get('debug_logging', True))}",
                f"debug_verbose={bool(self.settings.get('debug_verbose', False))}",
                f"auto_arm={bool(self.settings.get('auto_arm_when_palia_opens', False))}",
                f"reminders_enabled={bool(self.settings.get('reminders_enabled', True))}",
                f"tray_available={self._tray_supported()}",
                f"tray_active={bool(self._tray_manager and self._tray_manager.icon is not None)}",
                f"palia_game_detected={self.palia_process_result.game_detected}",
                f"palia_launcher_detected={self.palia_process_result.launcher_detected}",
                f"palia_detection_method={self.palia_process_result.detection_method}",
                f"latest_log_path={latest_log}",
            ],
            runtime_lines=[
                f"mode={runtime_mode}",
                f"tray_available={self._tray_supported()}",
                f"tray_active={bool(self._tray_manager and self._tray_manager.icon is not None)}",
                f"watcher_running={self.watching}",
                f"palia_game_detected={self.palia_process_result.game_detected}",
                f"palia_launcher_detected={self.palia_process_result.launcher_detected}",
                f"palia_detection_method={self.palia_process_result.detection_method}",
                f"debug_log_ready={bool(self.log_path)}",
            ],
            warnings=[line for line in log_lines if "WARNING" in line or "warning" in line.lower()],
            errors=[line for line in log_lines if "ERROR" in line or "error" in line.lower()],
            state_lines=state_lines + self._build_clock_ocr_debug_lines(),
            process_audit_lines=process_audit_lines,
            session_lines=[
                f"palia_process_detected={self.palia_process_result.game_detected}",
                f"detection_method={self.palia_process_result.detection_method}",
                f"psutil_available={PSUTIL_AVAILABLE}",
                f"auto_arm_when_palia_opens={bool(self.settings.get('auto_arm_when_palia_opens', False))}",
                f"pause_when_palia_closes={bool(self.settings.get('pause_when_palia_closes', True))}",
                f"watcher_running={self.watching}",
                f"waiting_for_manual_start={self.awaiting_manual_start}",
                f"current_session_id={self.current_session_id}",
                f"last_palia_transition={self.last_palia_transition}",
                f"last_session_reset_reason={self.last_session_reset_reason}",
                f"last_confirmed_clock={self.last_confirmed_var.get()}",
                f"last_parse_source={self.last_parse_source_var.get()}",
                f"estimated_clock_active={self.mode_var.get() == 'Estimated'}",
                f"stale_state={self.mode_var.get() == 'Stale'}",
                f"reminder_session_reset_at={self.reminder_session_reset_at}",
            ],
            smart_resume_lines=self._build_smart_resume_debug_lines(),
            smart_recall_lines=self._build_smart_recall_debug_lines(),
            support_summary_lines=self._build_support_summary_lines(),
        )

    def _show_debug_report(self) -> None:
        report = self._build_debug_report_text()
        window = tk.Toplevel(self.root)
        window.title("Debug Report")
        window.geometry("900x700")
        text = tk.Text(window, wrap="word")
        text.pack(fill="both", expand=True)
        text.insert("1.0", report)
        text.configure(state="disabled")

    def _export_debug_report(self) -> None:
        try:
            report = self._build_debug_report_text()
            export_path = export_debug_report(report)
            self.status_var.set(f"Exported debug report: {export_path}")
            messagebox.showinfo("Debug Report", f"Exported debug report:\n{export_path}")
        except Exception as exc:
            self.status_var.set(f"Export debug report failed: {exc}")
            messagebox.showerror("Debug Report", str(exc))

    def _copy_debug_report(self) -> None:
        try:
            report = self._build_debug_report_text()
            self.root.clipboard_clear()
            self.root.clipboard_append(report)
            self.root.update()
            self.status_var.set("Debug report copied")
        except Exception as exc:
            self.status_var.set(f"Copy debug report failed: {exc}")
            messagebox.showerror("Debug Report", str(exc))

    def _copy_debug_summary(self) -> None:
        self._copy_debug_report()

    def _copy_palia_process_audit(self) -> None:
        try:
            audit_text = "\n".join(self._build_palia_process_audit_lines())
            self.root.clipboard_clear()
            self.root.clipboard_append(audit_text)
            self.root.update()
            self.status_var.set("Palia process audit copied")
        except Exception as exc:
            self.status_var.set(f"Copy Palia process audit failed: {exc}")
            messagebox.showerror("Palia Process Audit", str(exc))

    def _build_clock_ocr_debug_lines(self) -> list[str]:
        latest_log, _ = get_log_paths()
        return [
            f"last_raw_ocr={self.raw_ocr_var.get()}",
            f"last_normalized_ocr={self.normalized_ocr_var.get()}",
            f"last_parse_candidates={self.last_parse_candidates_var.get()}",
            f"last_selected_time={self.parsed_time_var.get()}",
            f"last_parsed_display={self.current_palia_time_var.get()}",
            f"last_parse_accepted={self.last_parse_accepted_var.get()}",
            f"last_reject_reason={self.last_parse_reject_reason_var.get()}",
            f"last_parse_source={self.last_parse_source_var.get()}",
            f"last_clock_region={self._clock_region_string(self.settings)}",
            f"last_confirmed_time={self.last_confirmed_var.get()}",
            f"estimated_time={self.estimated_var.get()}",
            f"seconds_since_confirmed={self.seconds_since_confirmed_var.get()}",
            f"debug_log_path={latest_log}",
        ]

    def _build_smart_resume_debug_lines(self) -> list[str]:
        result = self.last_resume_result
        latest_log, _ = get_log_paths()
        if result is None:
            return [
                "last_resume_trigger=-",
                "last_resume_time=-",
                f"readiness_state={self.readiness_var.get()}",
                f"latest_log_path={latest_log}",
            ]
        return [
            f"last_resume_trigger={result.trigger}",
            f"last_resume_time={result.checked_at}",
            f"last_resume_result={result.readiness_state}",
            f"last_resume_action={result.recovery_action}",
            f"readiness_state={result.readiness_state}",
            f"clock_region_valid={result.region_valid}",
            f"clock_region_reason={result.region_reason}",
            f"screen_geometry_changed={result.screen_geometry_changed}",
            f"monitor_fingerprint={result.monitor_fingerprint}",
            f"capture_ready={result.capture_ready}",
            f"capture_reason={result.capture_reason}",
            f"palia_game_detected={result.palia_game_detected}",
            f"palia_launcher_detected={result.palia_launcher_detected}",
            f"ocr_preflight_result={result.ocr_preflight_result}",
            f"recall_state_used={result.recall_state_used}",
            f"failure_reason={result.failure_reason or '-'}",
            f"latest_log_path={latest_log}",
        ]

    def _build_smart_recall_debug_lines(self) -> list[str]:
        return [
            f"recall_file_path={RECALL_PATH}",
            f"recall_load_status={self.recall_load_status}",
            f"last_good_clock_region={self.recall_state.get('last_good_clock_region') or {}}",
            f"last_good_monitor_fingerprint={self.recall_state.get('last_good_monitor_fingerprint') or '-'}",
            f"last_good_ocr_time={self.recall_state.get('last_good_ocr_time') or '-'}",
            f"last_good_ocr_timestamp={self.recall_state.get('last_good_ocr_timestamp') or '-'}",
            f"last_clock_validation_status={self.recall_state.get('last_clock_validation_status') or '-'}",
            f"last_clock_validation_reason={self.recall_state.get('last_clock_validation_reason') or '-'}",
            f"last_recovery_action={self.recall_state.get('last_recovery_action') or '-'}",
            f"last_failure_reason={self.recall_state.get('last_failure_reason') or '-'}",
            f"last_known_app_visibility_state={self.recall_state.get('last_known_app_visibility_state') or '-'}",
        ]

    def _build_support_summary_lines(self) -> list[str]:
        result = self.last_resume_result
        action = result.recovery_action if result is not None else "wait"
        next_action = {
            "start_reminder": "Click Start Reminder.",
            "setup_clock": "Click Setup Clock.",
            "open_palia": "Open Palia.",
            "continue_running": "Wait - reminders are already active.",
            "ready_auto_arm": "Wait - HPR will start automatically.",
            "open_debug_support": "Contact support with the Debug Report.",
        }.get(action, "Wait for HPR to finish checking.")
        return [
            f"readiness={self.readiness_var.get()}",
            f"normal_user_next_step={next_action}",
            "support_bundle=Export Debug Report and include latest.log when requested.",
        ]

    def _copy_smart_resume_debug(self) -> None:
        try:
            text = "\n".join(self._build_smart_resume_debug_lines() + self._build_smart_recall_debug_lines())
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.root.update()
            self.status_var.set("Smart Resume debug copied")
        except Exception as exc:
            self.status_var.set(f"Copy Smart Resume debug failed: {exc}")
            messagebox.showerror("Smart Resume Debug", str(exc))

    def _copy_clock_ocr_debug(self) -> None:
        try:
            text = "\n".join(self._build_clock_ocr_debug_lines())
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.root.update()
            self.status_var.set("Clock OCR debug copied")
        except Exception as exc:
            self.status_var.set(f"Copy Clock OCR debug failed: {exc}")
            messagebox.showerror("Clock OCR Debug", str(exc))

    def _read_int_or_default(self, variable: tk.StringVar, label: str, default: int, minimum: int = 0) -> int:
        try:
            value = int(variable.get())
        except (TypeError, ValueError):
            messagebox.showerror("Invalid Value", f"{label} must be a whole number.")
            return default
        return max(minimum, value)

    def _describe_reminder_text(self, outcome: Optional[ReminderOutcome] = None) -> str:
        target = ""
        if outcome is not None:
            target = outcome.reminder_target_time or outcome.next_reminder_target or ""
            title = outcome.reminder_title or ""
            message = outcome.reminder_message or ""
            if target or title or message:
                title_text = title.strip() or "Hotpot Reminder"
                message_text = message.strip() or "This is your reminder that Hotpot will start in 15min!"
                if target:
                    return f"{target} | {title_text} — {message_text}"
                return f"{title_text} — {message_text}"

        target = self.reminder_manager.last_reminder_target or ""
        if not target:
            configured_times = self.settings.get("hotpot_warning_times") or self.settings.get("reminder_minutes") or []
            if isinstance(configured_times, str):
                configured_times = [part.strip() for part in configured_times.split(",")]
            for candidate in configured_times:
                target = normalize_time_label(candidate)
                if target:
                    break
        title, message = get_reminder_copy(self.settings, target)
        if target:
            return f"{target} | {title} — {message}"
        return f"{title} — {message}"

    def _test_system_popup(self) -> None:
        try:
            outcome = self.reminder_manager.test_system_popup(settings=self.settings)
            self._sync_reminder_state(outcome)
            self.status_var.set(outcome.status_message)
            self.diagnostic_var.set(outcome.diagnostic or "")
            messagebox.showinfo("Test System Popup", outcome.status_message)
        except Exception as exc:
            self.status_var.set(f"Test system popup failed: {exc}")
            self.diagnostic_var.set("")
            messagebox.showerror("Test System Popup Failed", str(exc))

    def _test_custom_popup(self) -> None:
        try:
            outcome = self.reminder_manager.test_custom_popup(settings=self.settings)
            self._sync_reminder_state(outcome)
            self.status_var.set(outcome.status_message)
            self.diagnostic_var.set(outcome.diagnostic or "")
            messagebox.showinfo("Test Custom Popup", outcome.status_message)
        except Exception as exc:
            self.status_var.set(f"Test custom popup failed: {exc}")
            self.diagnostic_var.set("")
            messagebox.showerror("Test Custom Popup Failed", str(exc))
