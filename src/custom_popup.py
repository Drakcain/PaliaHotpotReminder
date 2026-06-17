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


DEFAULT_POPUP_SIZE = (760, 580)
DEFAULT_LEFT_MARGIN = 24
DEFAULT_TOP_MARGIN = 250
DEFAULT_DURATION_SECONDS = 8
DEFAULT_ASSET_PATH = PROJECT_ROOT / "assets" / "Message Board" / "popup_scroll_clean.png"
TRANSPARENT_COLOR = "#010203"
ART_MIN_POPUP_SIZE = (760, 580)
CONTENT_X_RATIO = 0.15
CONTENT_Y_RATIO = 0.295
CONTENT_W_RATIO = 0.70
CONTENT_H_RATIO = 0.53
TITLE_GLOBAL_Y_RATIO = 0.455
UPPER_DIVIDER_GLOBAL_Y_RATIO = 0.530
BODY_LINE_1_GLOBAL_Y_RATIO = 0.595
BODY_LINE_2_GLOBAL_Y_RATIO = 0.655
LOWER_DIVIDER_GLOBAL_Y_RATIO = 0.735
DETAIL_GLOBAL_Y_RATIO = 0.775
CONTENT_INSET_X = 20
CONTENT_INSET_Y = 14
TITLE_SHADOW_OFFSET = 1
BODY_SHADOW_OFFSET = 0
TITLE_FILL = "#3A2413"
TITLE_SHADOW = "#EAD2A6"
BODY_FILL = "#3A2413"
BODY_SHADOW = "#FFF3D4"
DETAIL_FILL = "#4A2E18"
DIVIDER_FILL = "#9A7648"
DIVIDER_FADE = "#E7D3AA"
ART_ASPECT_RATIO = 1448 / 1086


def _content_box(width: int, height: int) -> tuple[int, int, int, int]:
    left = int(width * CONTENT_X_RATIO)
    top = int(height * CONTENT_Y_RATIO)
    content_width = int(width * CONTENT_W_RATIO)
    content_height = int(height * CONTENT_H_RATIO)
    return left, top, content_width, content_height


def _fit_font_size(base: int, minimum: int, text: str, width: int, height: int) -> int:
    text_len = len((text or "").strip())
    if text_len > 140:
        return max(minimum, base - 4)
    if text_len > 95:
        return max(minimum, base - 2)
    if width < 560 or height < 440:
        return max(minimum, base - 1)
    return base


def _serif_font(preferred_size: int, weight: str = "normal", slant: str = "roman") -> tuple[str, int, str]:
    family = "Georgia"
    style = weight if slant == "roman" else f"{weight} {slant}"
    return (family, preferred_size, style)


def _split_message_lines(message: str) -> list[str]:
    raw_lines = [line.strip() for line in str(message or "").splitlines() if line.strip()]
    if raw_lines:
        return raw_lines[:2]
    return ["Reminder"]


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


def _display_scale(master: tk.Misc | None = None) -> float:
    if master is None:
        return 1.0
    try:
        pixels_per_inch = float(master.winfo_fpixels("1i"))
        if pixels_per_inch > 0:
            return max(1.0, min(1.75, pixels_per_inch / 96.0))
    except Exception:
        pass
    return 1.0


def _smart_popup_target_size(
    monitor: dict[str, int],
    requested_width: int,
    requested_height: int,
    display_scale: float = 1.0,
) -> tuple[int, int]:
    monitor_width = max(1280, int(monitor.get("width", 1280)))
    monitor_height = max(720, int(monitor.get("height", 720)))
    aspect_ratio = monitor_width / max(1, monitor_height)
    dpi_boost = max(1.0, min(1.20, float(display_scale)))

    height_ratio = 0.56
    if aspect_ratio >= 2.3:
        height_ratio = 0.60
    elif aspect_ratio >= 2.0:
        height_ratio = 0.58
    elif aspect_ratio <= 1.65:
        height_ratio = 0.54

    smart_height = round(monitor_height * height_ratio * dpi_boost)
    smart_height = _clamp(smart_height, ART_MIN_POPUP_SIZE[1], int(monitor_height * 0.72))
    smart_width = round(smart_height * ART_ASPECT_RATIO)

    final_height = max(requested_height, smart_height)
    final_width = max(requested_width, smart_width)
    return final_width, final_height


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
        requested_width = max(ART_MIN_POPUP_SIZE[0], requested_width)
        requested_height = max(ART_MIN_POPUP_SIZE[1], requested_height)
        smart_width, smart_height = _smart_popup_target_size(
            monitor,
            requested_width,
            requested_height,
            _display_scale(self.master),
        )
        width = min(smart_width, max(ART_MIN_POPUP_SIZE[0], monitor["width"] - left_margin * 2))
        height = min(smart_height, max(ART_MIN_POPUP_SIZE[1], monitor["height"] - top_margin * 2))
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
        composed = fitted
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

        content_left, content_top, content_width, content_height = _content_box(width, height)
        content_center_x = width // 2
        wrap_width = max(340, content_width - CONTENT_INSET_X * 2)
        title_size = min(22, max(18, round(height * 0.038)))
        body_size = min(16, max(14, round(height * 0.028)))
        detail_text = _collect_details(details)
        detail_size = min(12, max(10, round(height * 0.019)))
        title_y = round(height * TITLE_GLOBAL_Y_RATIO)
        upper_divider_y = round(height * UPPER_DIVIDER_GLOBAL_Y_RATIO)
        body_line_1_y = round(height * BODY_LINE_1_GLOBAL_Y_RATIO)
        body_line_2_y = round(height * BODY_LINE_2_GLOBAL_Y_RATIO)
        lower_divider_y = round(height * LOWER_DIVIDER_GLOBAL_Y_RATIO)
        detail_y = round(height * DETAIL_GLOBAL_Y_RATIO)
        detail_text = _collect_details(details)
        body_lines = _split_message_lines(message)

        self._draw_divider(canvas, content_center_x, upper_divider_y, wrap_width, max(12, title_size // 2))
        self._draw_divider(canvas, content_center_x, lower_divider_y, wrap_width, max(8, detail_size))

        canvas.create_text(
            content_center_x,
            title_y + TITLE_SHADOW_OFFSET,
            text=title.strip() or "Reminder",
            fill=TITLE_SHADOW,
            font=_serif_font(title_size, "bold"),
            justify="center",
            anchor="n",
        )
        canvas.create_text(
            content_center_x,
            title_y,
            text=title.strip() or "Reminder",
            fill=TITLE_FILL,
            font=_serif_font(title_size, "bold"),
            justify="center",
            anchor="n",
        )
        canvas.create_text(
            content_center_x,
            body_line_1_y + BODY_SHADOW_OFFSET,
            text=body_lines[0],
            fill=BODY_SHADOW,
            font=_serif_font(body_size),
            width=wrap_width,
            justify="center",
            anchor="center",
        )
        canvas.create_text(
            content_center_x,
            body_line_1_y,
            text=body_lines[0],
            fill=BODY_FILL,
            font=_serif_font(body_size),
            width=wrap_width,
            justify="center",
            anchor="center",
        )
        if len(body_lines) > 1:
            canvas.create_text(
                content_center_x,
                body_line_2_y + BODY_SHADOW_OFFSET,
                text=body_lines[1],
                fill=BODY_SHADOW,
                font=_serif_font(body_size),
                width=wrap_width,
                justify="center",
                anchor="center",
            )
            canvas.create_text(
                content_center_x,
                body_line_2_y,
                text=body_lines[1],
                fill=BODY_FILL,
                font=_serif_font(body_size),
                width=wrap_width,
                justify="center",
                anchor="center",
            )
        if detail_text:
            canvas.create_text(
                content_center_x,
                detail_y,
                text=detail_text,
                fill=DETAIL_FILL,
                font=_serif_font(detail_size, "normal", "italic"),
                width=wrap_width,
                justify="center",
                anchor="s",
            )

        self._canvas = canvas

    def _draw_divider(self, canvas: tk.Canvas, center_x: int, y: int, width: int, ornament_size: int) -> None:
        half_gap = max(16, ornament_size)
        line_half = max(80, (width // 2) - half_gap - 14)
        left_start = center_x - half_gap - line_half
        left_end = center_x - half_gap
        right_start = center_x + half_gap
        right_end = center_x + half_gap + line_half
        canvas.create_line(left_start, y, left_end, y, fill=DIVIDER_FILL, width=2)
        canvas.create_line(right_start, y, right_end, y, fill=DIVIDER_FILL, width=2)
        canvas.create_line(left_start, y + 2, left_end, y + 2, fill=DIVIDER_FADE, width=1)
        canvas.create_line(right_start, y + 2, right_end, y + 2, fill=DIVIDER_FADE, width=1)
        diamond = max(8, ornament_size // 2)
        points = [
            center_x,
            y - diamond,
            center_x + diamond,
            y,
            center_x,
            y + diamond,
            center_x - diamond,
            y,
        ]
        canvas.create_polygon(points, outline=DIVIDER_FILL, fill="", width=2)

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
