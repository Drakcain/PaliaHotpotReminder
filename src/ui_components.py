from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk


def card(parent, title: str, *, colors: dict[str, str], columns: int = 1):
    frame = ctk.CTkFrame(
        parent,
        fg_color=colors["card_bg"],
        border_color=colors["border"],
        border_width=1,
        corner_radius=14,
    )
    frame.grid_columnconfigure(tuple(range(columns)), weight=1)
    label = ctk.CTkLabel(
        frame,
        text=title,
        text_color=colors["text_fg"],
        font=ctk.CTkFont(size=16, weight="bold"),
    )
    label.grid(row=0, column=0, columnspan=max(1, columns), sticky="w", padx=16, pady=(14, 8))
    return frame


def section_header(parent, title: str, subtitle: str = "", *, colors: dict[str, str]):
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    title_label = ctk.CTkLabel(
        frame,
        text=title,
        text_color=colors["text_fg"],
        font=ctk.CTkFont(size=22, weight="bold"),
    )
    title_label.pack(anchor="w")
    if subtitle:
        subtitle_label = ctk.CTkLabel(
            frame,
            text=subtitle,
            text_color=colors["muted_fg"],
            font=ctk.CTkFont(size=12),
        )
        subtitle_label.pack(anchor="w", pady=(2, 0))
    return frame


class StatusChip(ctk.CTkFrame):
    def __init__(self, parent, label: str, *, colors: dict[str, str]):
        super().__init__(
            parent,
            fg_color=colors["field_bg"],
            border_color=colors["border"],
            border_width=1,
            corner_radius=999,
        )
        self.colors = colors
        self.label = ctk.CTkLabel(
            self,
            text=label,
            text_color=colors["text_fg"],
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.label.pack(padx=12, pady=5)

    def set_state(self, label: str, state: str = "neutral") -> None:
        color_map = {
            "good": self.colors["good_fg"],
            "warning": self.colors["warning_fg"],
            "error": self.colors["error_fg"],
            "info": self.colors["info_fg"],
            "neutral": self.colors["accent_fg"],
        }
        border = color_map.get(state, self.colors["accent_fg"])
        try:
            self.configure(border_color=border)
            self.label.configure(text=label, text_color=border)
        except Exception:
            pass


def button(
    parent,
    text: str,
    command: Callable[[], None],
    *,
    colors: dict[str, str],
    variant: str = "secondary",
    width: int = 128,
):
    if variant == "primary":
        fg = colors["accent_fg"]
        hover = colors["accent_bright"]
        border = colors["accent_fg"]
        text_color = colors["text_fg"]
    elif variant == "danger":
        fg = colors["field_bg"]
        hover = colors["raised_bg"]
        border = colors["error_fg"]
        text_color = colors["error_fg"]
    else:
        fg = colors["field_bg"]
        hover = colors["raised_bg"]
        border = colors["accent_dark"]
        text_color = colors["text_fg"]
    return ctk.CTkButton(
        parent,
        text=text,
        command=command,
        width=width,
        height=34,
        fg_color=fg,
        hover_color=hover,
        border_color=border,
        border_width=1,
        text_color=text_color,
        corner_radius=10,
    )


def sidebar_button(
    parent,
    text: str,
    command: Callable[[], None],
    *,
    colors: dict[str, str],
    active: bool = False,
):
    return ctk.CTkButton(
        parent,
        text=text,
        command=command,
        anchor="w",
        height=34,
        fg_color=colors["accent_dark"] if active else "transparent",
        hover_color=colors["raised_bg"],
        border_color=colors["accent_fg"] if active else colors["border"],
        border_width=1 if active else 0,
        text_color=colors["text_fg"] if active else colors["muted_fg"],
        corner_radius=9,
    )


def switch(parent, text: str, variable, command: Optional[Callable[[], None]], *, colors: dict[str, str]):
    return ctk.CTkSwitch(
        parent,
        text=text,
        variable=variable,
        command=command,
        progress_color=colors["accent_fg"],
        button_color=colors["text_fg"],
        button_hover_color=colors["accent_bright"],
        fg_color=colors["field_bg"],
        border_color=colors["border"],
        border_width=1,
        text_color=colors["text_fg"],
    )
