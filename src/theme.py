from __future__ import annotations

HPR_THEME_NAME = "HPR High-Contrast Black Purple"

APP_WIDTH = 1440
APP_HEIGHT = 1040
SIDEBAR_WIDTH = 208
SHELL_PAD = 18
HEADER_BOTTOM_PAD = 12
CARD_GAP = 8
DISPLAY_WRAP = 380
LONG_DISPLAY_WRAP = 500
STATUS_CHIP_HEIGHT = 34
STATUS_CHIP_CORNER_RADIUS = 14
STATUS_CHIP_PAD_X = 11
STATUS_CHIP_PAD_Y = 5

BG_MAIN = "#000000"
BG_PANEL = "#050509"
BG_CARD = "#080812"
BG_ELEVATED = "#0D0A14"

PURPLE = "#8A5CFF"
PURPLE_BRIGHT = "#B07CFF"
PURPLE_DARK = "#3B236D"
PURPLE_MUTED = "#5E3AA8"

TEXT_MAIN = "#FFFFFF"
TEXT_SOFT = "#E8E1FF"
TEXT_MUTED = "#A99BC8"

BORDER = "#2B174D"
BORDER_ACTIVE = "#8A5CFF"

SUCCESS = "#65E572"
WARNING = "#FFD166"
ERROR = "#FF5C8A"
INFO = "#66D9EF"

THEMES = {
    "dark": {
        "theme_name": HPR_THEME_NAME,
        "window_bg": BG_MAIN,
        "panel_bg": BG_PANEL,
        "panel_raised": BG_ELEVATED,
        "card_bg": BG_CARD,
        "field_bg": BG_MAIN,
        "text": TEXT_MAIN,
        "text_secondary": TEXT_SOFT,
        "text_muted": TEXT_MUTED,
        "border": BORDER,
        "strong_border": BORDER_ACTIVE,
        "button_bg": PURPLE_MUTED,
        "button_hover": PURPLE_BRIGHT,
        "button_text": TEXT_MAIN,
        "accent": PURPLE,
        "accent_bright": PURPLE_BRIGHT,
        "accent_dark": PURPLE_DARK,
        "good": SUCCESS,
        "warning": WARNING,
        "error": ERROR,
        "info": INFO,
    },
    "light": {
        "window_bg": "#f4f4f4",
        "panel_bg": "#ffffff",
        "panel_raised": "#ffffff",
        "field_bg": "#ffffff",
        "text": "#1f1f1f",
        "text_secondary": "#4f4f4f",
        "text_muted": "#666666",
        "border": "#d0d0d0",
        "strong_border": "#a8a8a8",
        "button_bg": "#e6e6e6",
        "button_hover": "#d8d8d8",
        "button_text": "#1f1f1f",
        "accent": "#3b82f6",
        "accent_bright": "#2563eb",
        "accent_dark": "#93c5fd",
        "good": "#0ea5e9",
        "warning": "#b45309",
        "error": "#dc2626",
        "info": "#0ea5e9",
    },
}
