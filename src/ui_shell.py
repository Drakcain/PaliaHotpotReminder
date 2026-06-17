from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from app_version import APP_VERSION
from theme import APP_HEIGHT, APP_WIDTH, HEADER_BOTTOM_PAD, SHELL_PAD, SIDEBAR_WIDTH
from ui_components import StatusChip, section_header, sidebar_button


PAGE_NAMES = ("Dashboard", "Clock Setup", "Reminders", "Automation", "Diagnostics", "Settings")


class UIShell:
    def __init__(self, root, app, colors: dict[str, str], builders: dict[str, Callable]) -> None:
        self.root = root
        self.app = app
        self.colors = colors
        self.builders = builders
        self.pages: dict[str, ctk.CTkFrame] = {}
        self.sidebar_buttons: dict[str, ctk.CTkButton] = {}
        self.page_container = None
        self.current_page = ""

    def build(self) -> None:
        ctk.set_appearance_mode("dark" if self.app._current_theme_name() == "dark" else "light")
        ctk.set_default_color_theme("dark-blue")
        self.root.geometry(f"{APP_WIDTH}x{APP_HEIGHT}")
        self.root.minsize(APP_WIDTH, APP_HEIGHT)
        self.root.maxsize(APP_WIDTH, APP_HEIGHT)
        self.root.resizable(False, False)

        self.shell = ctk.CTkFrame(self.root, fg_color=self.colors["root_bg"], corner_radius=0)
        self.shell.pack(fill="both", expand=True)
        self.shell.grid_columnconfigure(1, weight=1)
        self.shell.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main()
        self.show_page("Dashboard", record_activity=False)

    def _build_sidebar(self) -> None:
        sidebar = ctk.CTkFrame(
            self.shell,
            width=SIDEBAR_WIDTH,
            fg_color=self.colors["section_bg"],
            border_color=self.colors["border"],
            border_width=1,
            corner_radius=0,
        )
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)

        ctk.CTkLabel(
            sidebar,
            text="HPR",
            text_color=self.colors["accent_bright"],
            font=ctk.CTkFont(size=26, weight="bold"),
        ).pack(anchor="w", padx=18, pady=(20, 0))
        ctk.CTkLabel(
            sidebar,
            text="Black Purple\nOCR Helper",
            text_color=self.colors["muted_fg"],
            justify="left",
            font=ctk.CTkFont(size=12),
        ).pack(anchor="w", padx=18, pady=(2, 18))

        for label in PAGE_NAMES:
            btn = sidebar_button(
                sidebar,
                label,
                lambda name=label: self.show_page(name),
                colors=self.colors,
                active=(label == "Dashboard"),
            )
            btn.pack(fill="x", padx=14, pady=4)
            self.sidebar_buttons[label] = btn

        ctk.CTkLabel(
            sidebar,
            text="OCR selected clock region only\nNo memory reads\nNo hooks or automation",
            text_color=self.colors["dim_fg"],
            justify="left",
            font=ctk.CTkFont(size=11),
        ).pack(side="bottom", anchor="w", padx=18, pady=18)

    def _build_main(self) -> None:
        main = ctk.CTkFrame(self.shell, fg_color=self.colors["root_bg"], corner_radius=0)
        main.grid(row=0, column=1, sticky="nsew", padx=SHELL_PAD, pady=SHELL_PAD)
        main.grid_rowconfigure(1, weight=1)
        main.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(main, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, HEADER_BOTTOM_PAD))
        header.grid_columnconfigure(0, weight=1)
        title = section_header(
            header,
            f"Palia Hotpot Reminder {APP_VERSION}",
            "Installer-first Windows utility · External OCR-only helper",
            colors=self.colors,
        )
        title.grid(row=0, column=0, sticky="w")

        chips = ctk.CTkFrame(header, fg_color="transparent")
        chips.grid(row=1, column=0, sticky="w", pady=(10, 0))
        self.app.palia_chip = StatusChip(chips, "Palia: Offline", colors=self.colors)
        self.app.palia_chip.pack(side="left", padx=(0, 8))
        self.app.reminder_chip = StatusChip(chips, "Reminder: Not Ready", colors=self.colors)
        self.app.reminder_chip.pack(side="left", padx=(0, 8))
        self.app.clock_chip = StatusChip(chips, "Clock: Needed", colors=self.colors)
        self.app.clock_chip.pack(side="left")

        self.page_container = ctk.CTkFrame(main, fg_color="transparent")
        self.page_container.grid(row=1, column=0, sticky="nsew")
        self.page_container.grid_rowconfigure(0, weight=1)
        self.page_container.grid_columnconfigure(0, weight=1)

        for name in PAGE_NAMES:
            page = ctk.CTkFrame(
                self.page_container,
                fg_color=self.colors["root_bg"],
            )
            page.grid_anchor("n")
            page.grid_columnconfigure((0, 1), weight=1, uniform="cards")
            self.builders[name](page, self.app, self.colors)
            self.pages[name] = page

    def show_page(self, page_name: str, *, record_activity: bool = True) -> None:
        if page_name not in self.pages:
            page_name = "Dashboard"
        for name, page in self.pages.items():
            if name == page_name:
                page.grid(row=0, column=0, sticky="nsew")
            else:
                page.grid_remove()
        self.current_page = page_name
        if hasattr(self.app, "ui_state"):
            self.app.ui_state.current_page = page_name
        self._sync_sidebar()
        if record_activity:
            self.app._add_activity(f"Opened {page_name}")

    def _sync_sidebar(self) -> None:
        for label, widget in self.sidebar_buttons.items():
            active = label == self.current_page
            widget.configure(
                fg_color=self.colors["accent_dark"] if active else "transparent",
                border_color=self.colors["accent_fg"] if active else self.colors["border"],
                border_width=1 if active else 0,
                text_color=self.colors["text_fg"] if active else self.colors["muted_fg"],
            )
