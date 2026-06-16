from __future__ import annotations

import customtkinter as ctk

from ui_components import button, card


def _note(parent, text: str, row: int, colors: dict[str, str]) -> None:
    ctk.CTkLabel(
        parent,
        text=text,
        text_color=colors["muted_fg"],
        justify="left",
        wraplength=520,
    ).grid(row=row, column=0, columnspan=2, sticky="w", padx=16, pady=(2, 12))


def build_dashboard_page(parent, app, colors: dict[str, str]) -> None:
    parent.grid_columnconfigure((0, 1), weight=1, uniform="dashboard")

    palia = card(parent, "Palia Overview", colors=colors, columns=2)
    palia.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=8)
    app._add_display_row(palia, "Readiness", app.readiness_var, 1)
    app._add_display_row(palia, "Palia process", app.palia_detected_var, 2)
    app._add_display_row(palia, "Auto-arm", app.auto_arm_state_var, 3)
    app._add_display_row(palia, "Watcher status", app.status_var, 4)
    _note(
        palia,
        "HPR only watches process names and the selected clock region. Open Automation for startup and tray policy.",
        5,
        colors,
    )
    button(palia, "Open Automation", lambda: app._focus_section("Automation"), colors=colors).grid(
        row=6, column=0, columnspan=2, sticky="ew", padx=16, pady=(2, 14)
    )

    clock = card(parent, "Clock Overview", colors=colors, columns=2)
    clock.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=8)
    app._add_display_row(clock, "Clock setup", app.clock_setup_state_var, 1)
    app._add_display_row(clock, "Current region", app.region_var, 2)
    app._add_display_row(clock, "Current time", app.current_palia_time_var, 3)
    app._add_display_row(clock, "Last confirmed", app.last_confirmed_var, 4)
    _note(
        clock,
        "If Clock Setup is still Needed, run Setup Clock once on this PC, then use Test Clock to verify OCR before running reminders.",
        5,
        colors,
    )
    button(clock, "Open Clock Setup", lambda: app._focus_section("Clock Setup"), colors=colors).grid(
        row=6, column=0, columnspan=2, sticky="ew", padx=16, pady=(2, 14)
    )

    reminder = card(parent, "Reminder Overview", colors=colors, columns=2)
    reminder.grid(row=1, column=0, sticky="nsew", padx=(0, 8), pady=8)
    app._add_display_row(reminder, "Reminder", app.reminder_status_var, 1)
    app._add_display_row(reminder, "Next reminder", app.next_reminder_target_var, 2)
    app._add_display_row(reminder, "Last fired", app.last_reminder_fired_var, 3)
    app._add_display_row(reminder, "Reminder details", app.reminder_diagnostic_var, 4)
    _note(
        reminder,
        "Reminder behavior depends on Clock Setup, warning times, cooldown, and popup settings. Use Test Popup for a safe UI check.",
        5,
        colors,
    )
    button(reminder, "Open Reminders", lambda: app._focus_section("Reminders"), colors=colors).grid(
        row=6, column=0, columnspan=2, sticky="ew", padx=16, pady=(2, 14)
    )

    automation = card(parent, "Automation Overview", colors=colors, columns=2)
    automation.grid(row=1, column=1, sticky="nsew", padx=(8, 0), pady=8)
    app._add_display_row(automation, "Startup shortcut", app.startup_shortcut_state_var, 1)
    app._add_display_row(automation, "Tray", app.tray_state_var, 2)
    app._add_display_row(automation, "Debug Log", app.debug_log_state_var, 3)
    app._add_display_row(automation, "Support status", app.diagnostic_var, 4)
    _note(
        automation,
        "Installer builds are meant to live in the installed path. Automation stays external and does not hook, inject, or automate gameplay.",
        5,
        colors,
    )
    button(automation, "Open Diagnostics", lambda: app._focus_section("Diagnostics"), colors=colors).grid(
        row=6, column=0, columnspan=2, sticky="ew", padx=16, pady=(2, 14)
    )

    activity = card(parent, "Recent Activity Preview", colors=colors, columns=1)
    activity.grid(row=2, column=0, sticky="nsew", padx=(0, 8), pady=8)
    app.activity_textbox = ctk.CTkTextbox(
        activity,
        height=165,
        fg_color=colors["field_bg"],
        border_color=colors["border"],
        border_width=1,
        text_color=colors["text_fg"],
        corner_radius=10,
    )
    app.activity_textbox.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 14))
    app.activity_textbox.configure(state="disabled")

    guidance = card(parent, "Operator Guidance", colors=colors, columns=2)
    guidance.grid(row=2, column=1, sticky="nsew", padx=(8, 0), pady=8)
    app._add_display_row(guidance, "Current status", app.status_var, 1)
    app._add_display_row(guidance, "Support detail", app.diagnostic_var, 2)
    app._add_display_row(guidance, "Next action", app.readiness_var, 3)
    _note(
        guidance,
        "Use Dashboard for quick truth only. For real fixes, go to Clock Setup for OCR calibration, Reminders for timing rules, and Diagnostics for support output.",
        4,
        colors,
    )
    button(guidance, "Open Settings", lambda: app._focus_section("Settings"), colors=colors).grid(
        row=5, column=0, sticky="ew", padx=16, pady=(2, 14)
    )
    button(guidance, "Open Diagnostics", lambda: app._focus_section("Diagnostics"), colors=colors).grid(
        row=5, column=1, sticky="ew", padx=(8, 16), pady=(2, 14)
    )
    app._add_activity("UI shell ready")
