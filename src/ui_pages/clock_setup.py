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


def build_clock_setup_page(parent, app, colors: dict[str, str]) -> None:
    parent.grid_columnconfigure((0, 1), weight=1, uniform="clock")

    setup = card(parent, "Clock Setup", colors=colors, columns=2)
    setup.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=8)
    app._add_display_row(setup, "Clock setup", app.clock_setup_state_var, 1)
    app._add_display_row(setup, "Setup detail", app.setup_state_var, 2)
    app._add_display_row(setup, "Current region", app.region_var, 3)
    app._add_display_row(setup, "Tesseract", app.tesseract_var, 4)
    actions = ctk.CTkFrame(setup, fg_color="transparent")
    actions.grid(row=5, column=0, columnspan=2, sticky="ew", padx=16, pady=(10, 14))
    button(actions, "Test Clock", app.ui_actions.test_clock, colors=colors).pack(side="left", padx=(0, 8))
    app.setup_clock_button = button(actions, "Setup Clock", app.ui_actions.setup_clock, colors=colors, variant="primary")
    app.setup_clock_button.pack(side="left")

    region = card(parent, "Clock Region", colors=colors, columns=2)
    region.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=8)
    app._add_field(region, "Left", app.left_var, 0)
    app._add_field(region, "Top", app.top_var, 1)
    app._add_field(region, "Width", app.width_var, 2)
    app._add_field(region, "Height", app.height_var, 3)
    button(region, "Reset to Default Region", app._reset_default_region, colors=colors).grid(
        row=5, column=0, columnspan=2, sticky="ew", padx=16, pady=(10, 14)
    )

    nudge = card(parent, "Nudge Controls", colors=colors, columns=1)
    nudge.grid(row=1, column=0, sticky="nsew", padx=(0, 8), pady=8)
    app._add_nudge_row(nudge, "Move", [
        ("Left -5", lambda: app._nudge("left", -5)),
        ("Left +5", lambda: app._nudge("left", 5)),
        ("Up -5", lambda: app._nudge("top", -5)),
        ("Down +5", lambda: app._nudge("top", 5)),
    ])
    app._add_nudge_row(nudge, "Big Move", [
        ("Left -25", lambda: app._nudge("left", -25)),
        ("Left +25", lambda: app._nudge("left", 25)),
        ("Up -25", lambda: app._nudge("top", -25)),
        ("Down +25", lambda: app._nudge("top", 25)),
    ])
    app._add_nudge_row(nudge, "Size", [
        ("Wider +10", lambda: app._nudge("width", 10)),
        ("Narrower -10", lambda: app._nudge("width", -10)),
        ("Taller +10", lambda: app._nudge("height", 10)),
        ("Shorter -10", lambda: app._nudge("height", -10)),
    ])
    ctk.CTkLabel(
        nudge,
        text="Use small moves for cleanup and big moves when the initial scan lands far from the live clock.",
        text_color=colors["muted_fg"],
        justify="left",
        wraplength=520,
    ).grid(row=4, column=0, sticky="w", padx=16, pady=(8, 14))

    ocr = card(parent, "OCR Validation", colors=colors, columns=2)
    ocr.grid(row=1, column=1, sticky="nsew", padx=(8, 0), pady=8)
    app._add_display_row(ocr, "Mode", app.mode_var, 1)
    app._add_display_row(ocr, "Raw OCR", app.raw_ocr_var, 2)
    app._add_display_row(ocr, "Normalized OCR", app.normalized_ocr_var, 3)
    app._add_display_row(ocr, "Parsed time", app.parsed_time_var, 4)
    app._add_display_row(ocr, "Current Palia time", app.current_palia_time_var, 5)
    app._add_display_row(ocr, "Last confirmed", app.last_confirmed_var, 6)
    app._add_display_row(ocr, "Estimated time", app.estimated_var, 7)
    app._add_display_row(ocr, "Seconds since confirmed", app.seconds_since_confirmed_var, 8)

    tools = card(parent, "Preview Tools", colors=colors, columns=2)
    tools.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=8)
    for index, (text, command) in enumerate((
        ("Open Preview Image", app._open_preview_image),
        ("Open Screen Diagnostic", app._open_screen_diagnostic),
        ("Copy Clock OCR Debug", app._copy_clock_ocr_debug),
        ("Screen Diagnostics", lambda: app._focus_section("Diagnostics")),
    )):
        button(tools, text, command, colors=colors).grid(row=1 + index // 2, column=index % 2, sticky="ew", padx=16, pady=4)
    ctk.CTkLabel(
        tools,
        text="Clock setup uses the selected visible clock region only. It does not read game memory or hook Palia.",
        text_color=colors["muted_fg"],
        justify="left",
        wraplength=860,
    ).grid(row=3, column=0, columnspan=2, sticky="w", padx=16, pady=(10, 14))
