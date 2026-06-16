from __future__ import annotations

import customtkinter as ctk

from ui_components import button, card


def build_diagnostics_page(parent, app, colors: dict[str, str]) -> None:
    parent.grid_columnconfigure((0, 1), weight=1, uniform="diagnostics")

    support = card(parent, "Debug / Support", colors=colors, columns=2)
    support.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=8)
    app._add_display_row(support, "Debug Log", app.debug_log_state_var, 1)
    app._add_display_row(support, "Status", app.status_var, 2)
    app._add_display_row(support, "Diagnostics", app.diagnostic_var, 3)
    app._add_switch(support, "Debug logging", app.debug_logging_var, 4, 0)
    app._add_switch(support, "Debug verbose", app.debug_verbose_var, 4, 1)
    for index, (text, command) in enumerate((
        ("Debug Report", app.ui_actions.debug_report),
        ("Export Debug Report", app._export_debug_report),
        ("Copy Debug Report", app._copy_debug_report),
        ("Open Logs Folder", app._open_logs_folder),
        ("View Debug Log", app._view_latest_log),
        ("Open latest.log", app._open_latest_log),
    )):
        button(support, text, command, colors=colors).grid(row=5 + index // 2, column=index % 2, sticky="ew", padx=16, pady=4)

    system = card(parent, "System Status", colors=colors, columns=2)
    system.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=8)
    app._add_display_row(system, "Detected screen", app.resolution_var, 1)
    app._add_display_row(system, "Screen diagnostics", app.screen_diag_var, 2)
    app._add_display_row(system, "Current clock region", app.region_var, 3)
    app._add_display_row(system, "Timing ratio", app.time_ratio_var, 4)
    app._add_display_row(system, "Tesseract", app.tesseract_var, 5)
    app._add_display_row(system, "Setup", app.setup_state_var, 6)
    app._add_display_row(system, "Tray", app.tray_state_var, 7)

    activity = card(parent, "Full Recent Activity", colors=colors, columns=1)
    activity.grid(row=1, column=0, sticky="nsew", padx=(0, 8), pady=8)
    app.diagnostics_activity_textbox = ctk.CTkTextbox(
        activity,
        height=190,
        fg_color=colors["field_bg"],
        border_color=colors["border"],
        border_width=1,
        text_color=colors["text_fg"],
        corner_radius=10,
    )
    app.diagnostics_activity_textbox.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 14))
    app.diagnostics_activity_textbox.configure(state="disabled")

    details = card(parent, "Copy Diagnostics", colors=colors, columns=2)
    details.grid(row=1, column=1, sticky="nsew", padx=(8, 0), pady=8)
    for index, (text, command) in enumerate((
        ("Copy Palia Process Audit", app._copy_palia_process_audit),
        ("Copy Clock OCR Debug", app._copy_clock_ocr_debug),
        ("Copy Smart Resume Debug", app._copy_smart_resume_debug),
        ("Test System Popup", app._test_system_popup),
        ("Test Custom Popup", app._test_custom_popup),
        ("Open Screen Diagnostic", app._open_screen_diagnostic),
    )):
        button(details, text, command, colors=colors).grid(row=1 + index // 2, column=index % 2, sticky="ew", padx=16, pady=4)

    app.advanced_frame = ctk.CTkFrame(parent, fg_color="transparent")
    app.advanced_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=8)
    app.advanced_frame.grid_columnconfigure((0, 1), weight=1, uniform="advanced")

    parse = card(app.advanced_frame, "Clock Parse Diagnostics", colors=colors, columns=2)
    parse.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=8)
    app._add_display_row(parse, "Last parse candidates", app.last_parse_candidates_var, 1)
    app._add_display_row(parse, "Last parse accepted", app.last_parse_accepted_var, 2)
    app._add_display_row(parse, "Last reject reason", app.last_parse_reject_reason_var, 3)
    app._add_display_row(parse, "Last parse source", app.last_parse_source_var, 4)

    reminder = card(app.advanced_frame, "Reminder Diagnostics", colors=colors, columns=2)
    reminder.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=8)
    app._add_display_row(reminder, "Palia status", app.palia_detected_var, 1)
    app._add_display_row(reminder, "Auto-arm", app.auto_arm_state_var, 2)
    app._add_display_row(reminder, "Clock setup", app.clock_setup_state_var, 3)
    app._add_display_row(reminder, "Reminder status", app.reminder_status_var, 4)
    app._add_display_row(reminder, "Reminder details", app.reminder_diagnostic_var, 5)
