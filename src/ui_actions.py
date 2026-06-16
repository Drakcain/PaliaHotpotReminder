from __future__ import annotations


class UIActions:
    """Thin UI-facing wrappers around the existing controller callbacks."""

    def __init__(self, app) -> None:
        self.app = app

    def show_page(self, page_name: str) -> None:
        self.app._focus_section(page_name)

    def setup_clock(self) -> None:
        self.app._setup_clock()

    def test_clock(self) -> None:
        self.app._test_ocr()

    def start_reminder(self) -> None:
        self.app._start_watching()

    def stop_reminder(self) -> None:
        self.app._stop_watching()

    def test_popup(self) -> None:
        self.app._test_custom_popup()

    def debug_report(self) -> None:
        self.app._show_debug_report()

    def reload_settings(self) -> None:
        self.app._reload_convenience_settings()
