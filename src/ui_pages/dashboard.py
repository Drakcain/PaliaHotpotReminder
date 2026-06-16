from __future__ import annotations

import customtkinter as ctk

from ui_components import button, card


def build_dashboard_page(parent, app, colors: dict[str, str]) -> None:
    parent.grid_columnconfigure((0, 1), weight=1, uniform="dashboard")

    palia = card(parent, "Palia Overview", colors=colors, columns=2)
    palia.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=8)
    app._add_display_row(palia, "Readiness", app.readiness_var, 1)
    app._add_display_row(palia, "Palia process", app.palia_detected_var, 2)
    app._add_display_row(palia, "Auto-arm", app.auto_arm_state_var, 3)
    button(palia, "Open Automation", lambda: app._focus_section("Automation"), colors=colors).grid(
        row=4, column=0, columnspan=2, sticky="ew", padx=16, pady=(10, 14)
    )

    clock = card(parent, "Clock Overview", colors=colors, columns=2)
    clock.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=8)
    app._add_display_row(clock, "Clock setup", app.clock_setup_state_var, 1)
    app._add_display_row(clock, "Current region", app.region_var, 2)
    app._add_display_row(clock, "Current time", app.current_palia_time_var, 3)
    button(clock, "Open Clock Setup", lambda: app._focus_section("Clock Setup"), colors=colors).grid(
        row=4, column=0, columnspan=2, sticky="ew", padx=16, pady=(10, 14)
    )

    reminder = card(parent, "Reminder Overview", colors=colors, columns=2)
    reminder.grid(row=1, column=0, sticky="nsew", padx=(0, 8), pady=8)
    app._add_display_row(reminder, "Reminder", app.reminder_status_var, 1)
    app._add_display_row(reminder, "Next reminder", app.next_reminder_target_var, 2)
    app._add_display_row(reminder, "Last fired", app.last_reminder_fired_var, 3)
    button(reminder, "Open Reminders", lambda: app._focus_section("Reminders"), colors=colors).grid(
        row=4, column=0, columnspan=2, sticky="ew", padx=16, pady=(10, 14)
    )

    automation = card(parent, "Automation Overview", colors=colors, columns=2)
    automation.grid(row=1, column=1, sticky="nsew", padx=(8, 0), pady=8)
    app._add_display_row(automation, "Startup shortcut", app.startup_shortcut_state_var, 1)
    app._add_display_row(automation, "Tray", app.tray_state_var, 2)
    app._add_display_row(automation, "Debug Log", app.debug_log_state_var, 3)
    button(automation, "Open Diagnostics", lambda: app._focus_section("Diagnostics"), colors=colors).grid(
        row=4, column=0, columnspan=2, sticky="ew", padx=16, pady=(10, 14)
    )

    activity = card(parent, "Recent Activity Preview", colors=colors, columns=1)
    activity.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=8)
    app.activity_textbox = ctk.CTkTextbox(
        activity,
        height=150,
        fg_color=colors["field_bg"],
        border_color=colors["border"],
        border_width=1,
        text_color=colors["text_fg"],
        corner_radius=10,
    )
    app.activity_textbox.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 14))
    app.activity_textbox.configure(state="disabled")
    app._add_activity("UI shell ready")
