from __future__ import annotations

import customtkinter as ctk

from ui_components import button, card


def _note(parent, text: str, row: int, colors: dict[str, str]) -> None:
    ctk.CTkLabel(
        parent,
        text=text,
        text_color=colors["muted_fg"],
        justify="left",
        wraplength=860,
    ).grid(row=row, column=0, columnspan=2, sticky="w", padx=16, pady=(2, 14))


def build_automation_page(parent, app, colors: dict[str, str]) -> None:
    parent.grid_columnconfigure((0, 1), weight=1, uniform="automation")

    startup = card(parent, "Startup Automation", colors=colors, columns=2)
    startup.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=8)
    app._add_switch(startup, "Start with Windows", app.start_with_windows_var, 1, 0)
    app._add_switch(startup, "Auto-arm when Palia opens", app.auto_arm_var, 1, 1)
    app._add_switch(startup, "Start hidden in tray", app.start_minimized_var, 2, 0)
    app._add_display_row(startup, "Startup shortcut", app.startup_shortcut_state_var, 3)
    app._add_display_row(startup, "Auto-arm", app.auto_arm_state_var, 4)
    app._add_display_row(startup, "Readiness", app.readiness_var, 5)
    actions = ctk.CTkFrame(startup, fg_color="transparent")
    actions.grid(row=6, column=0, columnspan=2, sticky="ew", padx=16, pady=(10, 10))
    button(actions, "Create Desktop Shortcut", app._create_desktop_shortcut, colors=colors, width=170).pack(side="left", padx=(0, 8))
    button(actions, "Open Startup Folder", app._open_startup_folder, colors=colors).pack(side="left")
    _note(
        startup,
        "Start with Windows controls the shortcut path. Auto-arm only watches approved process names through psutil and waits for a clean session.",
        7,
        colors,
    )

    tray = card(parent, "Tray / Window Behavior", colors=colors, columns=2)
    tray.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=8)
    app._add_switch(tray, "Minimize to tray", app.minimize_to_tray_var, 1, 0)
    app._add_switch(tray, "Close to tray", app.close_to_tray_var, 1, 1)
    app._add_display_row(tray, "Tray", app.tray_state_var, 2)
    app._add_display_row(tray, "Palia process", app.palia_detected_var, 3)
    app._add_display_row(tray, "Window status", app.status_var, 4)
    tray_actions = ctk.CTkFrame(tray, fg_color="transparent")
    tray_actions.grid(row=5, column=0, columnspan=2, sticky="ew", padx=16, pady=(10, 10))
    button(tray_actions, "Show Window", app._show_from_tray, colors=colors).pack(side="left", padx=(0, 8))
    button(tray_actions, "Hide to Tray", app._hide_to_tray, colors=colors).pack(side="left", padx=(0, 8))
    button(tray_actions, "Reload Settings", app.ui_actions.reload_settings, colors=colors).pack(side="left")
    _note(
        tray,
        "Window close can hide to tray, but full shutdown is still the tray Exit path. That keeps watcher state alive without forcing a visible window.",
        6,
        colors,
    )

    shortcuts = card(parent, "Shortcut Repair", colors=colors, columns=2)
    shortcuts.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=8)
    for index, (text, command) in enumerate((
        ("Remove Startup Shortcut", app._remove_startup_shortcut),
        ("Recreate Startup Shortcut", app._recreate_startup_shortcut),
        ("Create Desktop Shortcut", app._create_desktop_shortcut),
        ("Refresh Palia Detection", lambda: app._refresh_palia_detection(force_log=True)),
    )):
        button(shortcuts, text, command, colors=colors).grid(row=1 + index // 2, column=index % 2, sticky="ew", padx=16, pady=4)
    ctk.CTkLabel(
        shortcuts,
        text="Automation watches process names through psutil only. It does not hook, inject, inspect memory, or control Palia.",
        text_color=colors["muted_fg"],
        justify="left",
        wraplength=860,
    ).grid(row=3, column=0, columnspan=2, sticky="w", padx=16, pady=(10, 14))

    policy = card(parent, "Automation Policy", colors=colors, columns=2)
    policy.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=8)
    app._add_display_row(policy, "Current status", app.status_var, 1)
    app._add_display_row(policy, "Support detail", app.diagnostic_var, 2)
    app._add_display_row(policy, "Debug log", app.debug_log_state_var, 3)
    app._add_display_row(policy, "Reminder state", app.reminder_status_var, 4)
    app._add_display_row(policy, "Session readiness", app.readiness_var, 5)
    _note(
        policy,
        "Use this page to control startup, tray, and shortcut behavior only. Reminder rules, OCR calibration, and support exports stay on their own pages to keep automation predictable.",
        6,
        colors,
    )
