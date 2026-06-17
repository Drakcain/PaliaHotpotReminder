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
    ).grid(row=row, column=0, columnspan=2, sticky="w", padx=16, pady=(2, 14))


def build_reminders_page(parent, app, colors: dict[str, str]) -> None:
    parent.grid_columnconfigure((0, 1), weight=1, uniform="reminders")

    controls = card(parent, "Reminder Controls", colors=colors, columns=2)
    controls.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=8)
    app._add_display_row(controls, "Reminder", app.reminder_status_var, 1)
    app._add_display_row(controls, "Reminder text", app.reminder_text_var, 2)
    app._add_display_row(controls, "Details", app.reminder_diagnostic_var, 3)
    app._add_display_row(controls, "Readiness", app.readiness_var, 4)
    actions = ctk.CTkFrame(controls, fg_color="transparent")
    actions.grid(row=5, column=0, columnspan=2, sticky="ew", padx=16, pady=(10, 10))
    button(actions, "Start Reminder", app.ui_actions.start_reminder, colors=colors, variant="primary").pack(side="left", padx=(0, 8))
    button(actions, "Stop Reminder", app.ui_actions.stop_reminder, colors=colors, variant="danger").pack(side="left", padx=(0, 8))
    button(actions, "Test Popup", app.ui_actions.test_popup, colors=colors).pack(side="left")
    _note(
        controls,
        "Start Reminder uses the current clock state and reminder rules. Test Popup is a UI-only check and does not touch the real game client.",
        6,
        colors,
    )

    state = card(parent, "Reminder State", colors=colors, columns=2)
    state.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=8)
    app._add_display_row(state, "Palia status", app.palia_detected_var, 1)
    app._add_display_row(state, "Clock setup", app.clock_setup_state_var, 2)
    app._add_display_row(state, "Reminders enabled", app.reminders_enabled_state_var, 3)
    app._add_display_row(state, "Next reminder target", app.next_reminder_target_var, 4)
    app._add_display_row(state, "Last reminder fired", app.last_reminder_fired_var, 5)
    app._add_display_row(state, "Estimated clock", app.estimated_var, 6)
    app._add_display_row(state, "Current Palia time", app.current_palia_time_var, 7)
    app._add_display_row(state, "Last confirmed", app.last_confirmed_var, 8)
    app._add_display_row(state, "Seconds since confirmed", app.seconds_since_confirmed_var, 9)
    _note(
        state,
        "If reminders are waiting, confirm Palia is detected, Clock Setup is Ready, and the current warning window still applies.",
        10,
        colors,
    )

    rules = card(parent, "Reminder Rules", colors=colors, columns=2)
    rules.grid(row=1, column=0, sticky="nsew", padx=(0, 8), pady=8)
    app._add_switch(rules, "Reminders Enabled", app.reminders_enabled_var, 1, 0, command=lambda: None)
    app._add_switch(rules, "Stale Warning Enabled", app.stale_warning_enabled_var, 1, 1, command=lambda: None)
    app._add_field(rules, "Reminder Cooldown (sec)", app.reminder_cooldown_var, 2)
    app._add_display_row(rules, "Hotpot Window", app.hotpot_window_var, 4)
    ctk.CTkLabel(rules, text="Hotpot Warning Times", text_color=colors["muted_fg"]).grid(row=5, column=0, sticky="w", padx=16, pady=4)
    ctk.CTkEntry(
        rules,
        textvariable=app.hotpot_warning_times_var,
        fg_color=colors["field_bg"],
        border_color=colors["border"],
        text_color=colors["text_fg"],
        width=260,
    ).grid(row=5, column=1, sticky="ew", padx=(8, 16), pady=4)
    button(rules, "Save Reminder Settings", app._save_reminder_settings_from_fields, colors=colors).grid(row=6, column=0, sticky="ew", padx=16, pady=(10, 14))
    button(rules, "Reload Reminder Settings", app._reload_reminder_settings, colors=colors).grid(row=6, column=1, sticky="ew", padx=(8, 16), pady=(10, 14))
    _note(
        rules,
        "Cooldown prevents duplicate firings, while warning times define when HPR should alert before Hotpot windows open.",
        7,
        colors,
    )

    popup = card(parent, "Popup Settings", colors=colors, columns=2)
    popup.grid(row=1, column=1, sticky="nsew", padx=(8, 0), pady=8)
    app._add_option(popup, "Popup Style", app.popup_style_var, 0, ["custom", "system", "auto"])
    app._add_field(popup, "Popup Duration (sec)", app.popup_duration_var, 1)
    app._add_field(popup, "Popup Position", app.popup_position_var, 2)
    app._add_field(popup, "Popup Asset Path", app.popup_asset_path_var, 3, width=30)
    app._add_field(popup, "Popup Width", app.popup_width_var, 4)
    app._add_field(popup, "Popup Height", app.popup_height_var, 5)
    app._add_field(popup, "Popup Left Margin", app.popup_left_margin_var, 6)
    app._add_field(popup, "Popup Top Margin", app.popup_top_margin_var, 7)
    button(popup, "Save Popup Settings", app._save_popup_settings_from_fields, colors=colors).grid(row=8, column=0, sticky="ew", padx=16, pady=(10, 14))
    button(popup, "Reload Popup Settings", app._reload_popup_settings, colors=colors).grid(row=8, column=1, sticky="ew", padx=(8, 16), pady=(10, 14))
    _note(
        popup,
        "Custom popup mode uses the local scroll asset path. Width and height act as minimum size only; HPR scales larger automatically for monitor resolution and display scaling. Keep asset changes paired with Test Popup so position and margins stay visually correct.",
        9,
        colors,
    )
