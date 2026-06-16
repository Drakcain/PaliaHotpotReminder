from __future__ import annotations

import customtkinter as ctk

from app_version import APP_VERSION
from ui_components import button, card


def _add_info(parent, label: str, value: str, row: int, colors: dict[str, str]) -> None:
    ctk.CTkLabel(parent, text=label, text_color=colors["muted_fg"], anchor="w").grid(row=row, column=0, sticky="w", padx=16, pady=4)
    ctk.CTkLabel(parent, text=value, text_color=colors["text_fg"], anchor="w", justify="left", wraplength=620).grid(
        row=row, column=1, sticky="ew", padx=(8, 16), pady=4
    )


def build_settings_page(parent, app, colors: dict[str, str]) -> None:
    parent.grid_columnconfigure((0, 1), weight=1, uniform="settings")

    window = card(parent, "Window / Theme", colors=colors, columns=2)
    window.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=8)
    app._add_switch(window, "Dark Mode", app.dark_mode_var, 1, 0)
    app._add_switch(window, "Start hidden in tray", app.start_minimized_var, 1, 1)
    app._add_switch(window, "Minimize to tray", app.minimize_to_tray_var, 2, 0)
    app._add_switch(window, "Close to tray", app.close_to_tray_var, 2, 1)
    button(window, "Show Window", app._show_from_tray, colors=colors).grid(row=3, column=0, sticky="ew", padx=16, pady=(10, 14))
    button(window, "Reload Settings", app.ui_actions.reload_settings, colors=colors).grid(row=3, column=1, sticky="ew", padx=(8, 16), pady=(10, 14))

    release = card(parent, "Release Info", colors=colors, columns=2)
    release.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=8)
    _add_info(release, "Version", APP_VERSION, 1, colors)
    _add_info(release, "Build type", "Installer-first Windows desktop utility", 2, colors)
    _add_info(release, "Install path", r"C:\Tools\PaliaHotpotReminder", 3, colors)
    _add_info(release, "Signing", "Unsigned unless a future signing pass is completed.", 4, colors)
    _add_info(release, "Verification", "Verify the installer SHA from GitHub Releases before install.", 5, colors)

    about = card(parent, "About HPR", colors=colors, columns=2)
    about.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=8)
    ctk.CTkLabel(
        about,
        text="Palia Hotpot Reminder",
        text_color=colors["accent_bright"],
        font=ctk.CTkFont(size=22, weight="bold"),
    ).grid(row=1, column=0, columnspan=2, sticky="w", padx=16, pady=(2, 2))
    ctk.CTkLabel(
        about,
        text="External OCR-only Hotpot reminder utility for Windows.",
        text_color=colors["text_fg"],
        justify="left",
        wraplength=860,
    ).grid(row=2, column=0, columnspan=2, sticky="w", padx=16, pady=(0, 12))

    _add_info(about, "Project identity", "Local desktop utility that OCRs the user-selected visible clock region.", 3, colors)
    _add_info(about, "Data model", "Local settings and local logs only. No gameplay automation or game modification.", 4, colors)
    _add_info(about, "Support", "Use Diagnostics > Debug / Support for support bundles and logs.", 5, colors)
    _add_info(about, "Repository", "GitHub: Drakcain/PaliaHotpotReminder", 6, colors)
    _add_info(about, "Affiliation", "Not affiliated with Palia, Singularity 6, Daybreak, or the official game client.", 7, colors)

    safety = card(parent, "Safety Boundary", colors=colors, columns=2)
    safety.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=8)
    safety_items = (
        "No game memory reading",
        "No hooks or injection",
        "No network inspection",
        "No gameplay automation",
        "No game file edits",
        "OCR selected visible clock region only",
    )
    for index, text in enumerate(safety_items):
        ctk.CTkLabel(
            safety,
            text=f"- {text}",
            text_color=colors["text_fg"],
            anchor="w",
        ).grid(row=1 + index // 2, column=index % 2, sticky="w", padx=16, pady=4)
    ctk.CTkLabel(
        safety,
        text="HPR is designed as an external reminder utility. It does not control Palia and does not bypass game systems.",
        text_color=colors["muted_fg"],
        justify="left",
        wraplength=860,
    ).grid(row=5, column=0, columnspan=2, sticky="w", padx=16, pady=(10, 14))
