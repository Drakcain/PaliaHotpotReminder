from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence

import tkinter as tk

from config import PROJECT_ROOT
from paths import resolve_resource_path

try:  # pragma: no cover - optional dependency fallback
    from PIL import Image, ImageOps, ImageTk
except Exception:  # pragma: no cover - optional dependency fallback
    Image = None
    ImageOps = None
    ImageTk = None

try:  # pragma: no cover - optional dependency fallback
    import mss
except Exception:  # pragma: no cover - optional dependency fallback
    mss = None


DEFAULT_POPUP_SIZE = (560, 420)
DEFAULT_LEFT_MARGIN = 24
DEFAULT_TOP_MARGIN = 250
DEFAULT_DURATION_SECONDS = 8
DEFAULT_ASSET_PATH = PROJECT_ROOT / "assets" / "Message Board" / "popup_scroll_clean.png"
TRANSPARENT_COLOR = "#010203"


@dataclass
class PopupResult:
    shown: bool
    backend: str = ""
    diagnostic: str = ""
    geometry: str = ""


def _to_int(settings: dict[str, Any], key: str, default: int) -> int:
    value = settings.get(key, default)
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _to_str(settings: dict[str, Any], key: str, default: str) -> str:
    value = settings.get(key, default)
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _resolve_asset_path(settings: dict[str, Any]) -> Path:
    raw = _to_str(settings, "popup_asset_path", str(DEFAULT_ASSET_PATH))
    return resolve_resource_path(raw)


def _primary_monitor_geometry(master: tk.Misc | None = None) -> dict[str, int]:
    if mss is not None:
        try:
            with mss.mss() as sct:
                monitors = list(getattr(sct, "monitors", []))
                if len(monitors) > 1:
                    monitor = monitors[1]
                elif monitors:
                    monitor = monitors[0]
                else:
                    monitor = {}
                if monitor:
                    return {
                        "left": int(monitor.get("left", 0)),
                        "top": int(monitor.get("top", 0)),
                        "width": int(monitor.get("width", 0)),
                        "height": int(monitor.get("height", 0)),
                    }
        except Exception:
            pass

    if master is not None:
        try:
            master.update_idletasks()
            return {
                "left": 0,
                "top": 0,
                "width": int(master.winfo_screenwidth()),
                "height": int(master.winfo_screenheight()),
            }
        except Exception:
            pass

    return {"left": 0, "top": 0, "width": 1280, "height": 720}


def _clamp(value: int, low: int, high: int) -> int:
    if high < low:
        return low
    return max(low, min(value, high))


def _collect_details(details: Optional[Sequence[str]]) -> str:
    if not details:
        return ""
    cleaned = [str(item).strip() for item in details if str(item).strip()]
    return "\n".join(cleaned)


class CustomPopupController:
    def __init__(self, master: tk.Misc | None) -> None:
        self.master = master
        self._window: Optional[tk.Toplevel] = None
        self._canvas: Optional[tk.Canvas] = None
        self._photo = None
        self._close_after_id: Optional[str] = None
        self._slide_after_id: Optional[str] = None

    def close(self) -> None:
        if self._window is None:
            return
        try:
            if self._close_after_id is not None:
                self._window.after_cancel(self._close_after_id)
        except Exception:
            pass
        try:
            if self._slide_after_id is not None:
                self._window.after_cancel(self._slide_after_id)
        except Exception:
            pass
        try:
            if self._window.winfo_exists():
                self._window.destroy()
        except Exception:
            pass
        self._window = None
        self._canvas = None
        self._photo = None
        self._close_after_id = None
        self._slide_after_id = None

    def show(
        self,
        settings: dict[str, Any],
        title: str,
        message: str,
        details: Optional[Sequence[str]] = None,
    ) -> PopupResult:
        if self.master is None:
            return PopupResult(False, backend="custom", diagnostic="No Tk master available")

        self.close()

        try:
            self.master.update_idletasks()
        except Exception:
            pass

        monitor = _primary_monitor_geometry(self.master)
        left_margin = max(0, _to_int(settings, "popup_left_margin", DEFAULT_LEFT_MARGIN))
        top_margin = max(0, _to_int(settings, "popup_top_margin", DEFAULT_TOP_MARGIN))
        requested_width = max(320, _to_int(settings, "popup_width", DEFAULT_POPUP_SIZE[0]))
        requested_height = max(240, _to_int(settings, "popup_height", DEFAULT_POPUP_SIZE[1]))
        width = min(requested_width, max(320, monitor["width"] - left_margin * 2))
        height = min(requested_height, max(240, monitor["height"] - top_margin * 2))
        popup_position = _to_str(settings, "popup_position", "left").lower()
        target_x = monitor["left"] + left_margin
        if popup_position not in {"left", "left-side"}:
            target_x = monitor["left"] + _clamp((monitor["width"] - width) // 2, 0, max(0, monitor["width"] - width))
        target_y = monitor["top"] + _clamp(top_margin, 0, max(0, monitor["height"] - height))
        start_x = target_x - width - 40
        geometry = f"{width}x{height}+{target_x}+{target_y}"

        try:
            self._window = tk.Toplevel(self.master)
            self._window.overrideredirect(True)
            try:
                self._window.attributes("-topmost", True)
            except Exception:
                pass
            try:
                self._window.attributes("-alpha", 0.99)
            except Exception:
                pass
            try:
                self._window.wm_attributes("-toolwindow", True)
            except Exception:
                pass
            try:
                self._window.wm_attributes("-transparentcolor", TRANSPARENT_COLOR)
            except Exception:
                pass
            self._window.geometry(f"{width}x{height}+{start_x}+{target_y}")
            self._window.configure(bg=TRANSPARENT_COLOR)
            self._window.protocol("WM_DELETE_WINDOW", self.close)
        except Exception as exc:
            self.close()
            return PopupResult(False, backend="custom", diagnostic=f"Unable to create popup window: {exc}")

        asset_path = _resolve_asset_path(settings)
        has_art = Image is not None and ImageTk is not None and asset_path.exists()
        backend = "custom-art" if has_art else "custom-fallback"
        diagnostic = ""
        try:
            if has_art:
                self._render_art_popup(width, height, asset_path, title, message, details)
            else:
                diagnostic = "Artwork missing or Pillow unavailable; using styled Tk fallback"
                self._render_fallback_popup(width, height, title, message, details)
        except Exception as exc:
            try:
                self._render_fallback_popup(width, height, title, message, details)
                backend = "custom-fallback"
                diagnostic = f"Artwork render failed; using styled Tk fallback ({exc})"
            except Exception as fallback_exc:
                self.close()
                return PopupResult(False, backend="custom", diagnostic=f"Popup fallback failed: {fallback_exc}")

        self._window.update_idletasks()
        try:
            self._window.deiconify()
            self._window.lift()
        except Exception:
            pass

        slide_duration_ms = 240
        slide_steps = 12
        try:
            self._animate_slide(start_x, target_x, target_y, width, height, slide_duration_ms, slide_steps)
        except Exception:
            try:
                self._window.geometry(geometry)
            except Exception:
                pass

        duration_seconds = max(1, _to_int(settings, "popup_duration_seconds", DEFAULT_DURATION_SECONDS))
        try:
            self._close_after_id = self._window.after(duration_seconds * 1000, self.close)
        except Exception:
            pass

        return PopupResult(True, backend=backend, diagnostic=diagnostic, geometry=geometry)

    def _animate_slide(self, start_x: int, target_x: int, target_y: int, width: int, height: int, duration_ms: int, steps: int) -> None:
        if self._window is None or not self._window.winfo_exists():
            return

        interval = max(1, duration_ms // max(1, steps))

        def step(index: int) -> None:
            if self._window is None or not self._window.winfo_exists():
                return
            progress = min(1.0, (index + 1) / max(1, steps))
            eased = 1 - (1 - progress) * (1 - progress)
            current_x = round(start_x + (target_x - start_x) * eased)
            try:
                self._window.geometry(f"{width}x{height}+{current_x}+{target_y}")
            except Exception:
                pass
            if progress < 1.0:
                self._slide_after_id = self._window.after(interval, lambda: step(index + 1))

        step(0)

    def _render_art_popup(
        self,
        width: int,
        height: int,
        asset_path: Path,
        title: str,
        message: str,
        details: Optional[Sequence[str]],
    ) -> None:
        if self._window is None:
            raise RuntimeError("Popup window is not available")

        image = Image.open(asset_path).convert("RGBA")
        fitted = ImageOps.fit(image, (width, height), method=Image.LANCZOS)
        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        from PIL import ImageDraw  # local import to keep fallback path small

        overlay_draw = ImageDraw.Draw(overlay)
        box_left = int(width * 0.14)
        box_top = int(height * 0.18)
        box_right = int(width * 0.86)
        box_bottom = int(height * 0.82)
        box = (box_left, box_top, box_right, box_bottom)
        try:
            overlay_draw.rounded_rectangle(
                box,
                radius=max(12, min(width, height) // 18),
                fill=(255, 246, 223, 210),
                outline=(85, 64, 34, 200),
                width=2,
            )
        except Exception:
            overlay_draw.rectangle(
                box,
                fill=(255, 246, 223, 210),
                outline=(85, 64, 34, 200),
                width=2,
            )
        composed = Image.alpha_composite(fitted, overlay)
        self._photo = ImageTk.PhotoImage(composed, master=self._window)

        canvas = tk.Canvas(
            self._window,
            width=width,
            height=height,
            highlightthickness=0,
            bd=0,
            bg=TRANSPARENT_COLOR,
        )
        canvas.pack(fill="both", expand=True)
        canvas.create_image(0, 0, image=self._photo, anchor="nw")

        title_size = max(20, height // 14)
        body_size = max(13, height // 22)
        detail_size = max(11, height // 26)
        text_color = "#3a2714"
        wrap_width = int(width * 0.62)
        text_center_x = width // 2
        title_y = int(height * 0.27) + 12
        body_y = int(height * 0.48) + 12
        detail_y = int(height * 0.69) + 12
        detail_text = _collect_details(details)

        canvas.create_text(
            text_center_x,
            title_y,
            text=title.strip() or "Reminder",
            fill=text_color,
            font=("Georgia", title_size, "bold"),
            width=wrap_width,
            justify="center",
        )
        canvas.create_text(
            text_center_x,
            body_y,
            text=message.strip() or "Reminder",
            fill=text_color,
            font=("Georgia", body_size, "normal"),
            width=wrap_width,
            justify="center",
        )
        if detail_text:
            canvas.create_text(
                text_center_x,
                detail_y,
                text=detail_text,
                fill=text_color,
                font=("Georgia", detail_size, "normal"),
                width=wrap_width,
                justify="center",
            )

        self._canvas = canvas

    def _render_fallback_popup(
        self,
        width: int,
        height: int,
        title: str,
        message: str,
        details: Optional[Sequence[str]],
    ) -> None:
        if self._window is None:
            raise RuntimeError("Popup window is not available")

        frame = tk.Frame(self._window, bg="#f4e3b8", bd=2, relief="solid")
        frame.pack(fill="both", expand=True)

        content = tk.Frame(frame, bg="#f4e3b8", padx=24, pady=22)
        content.pack(fill="both", expand=True)

        tk.Label(
            content,
            text=title.strip() or "Reminder",
            bg="#f4e3b8",
            fg="#3a2714",
            font=("Georgia", max(20, height // 14), "bold"),
            wraplength=int(width * 0.68),
            justify="center",
        ).pack(fill="x", pady=(8, 10))

        tk.Label(
            content,
            text=message.strip() or "Reminder",
            bg="#f4e3b8",
            fg="#3a2714",
            font=("Georgia", max(13, height // 22)),
            wraplength=int(width * 0.68),
            justify="center",
        ).pack(fill="x", pady=(0, 8))

        detail_text = _collect_details(details)
        if detail_text:
            tk.Label(
                content,
                text=detail_text,
                bg="#f4e3b8",
                fg="#3a2714",
                font=("Georgia", max(11, height // 26)),
                wraplength=int(width * 0.68),
                justify="center",
            ).pack(fill="x", pady=(0, 4))

        self._canvas = None
