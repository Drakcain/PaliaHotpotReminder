from pathlib import Path
from threading import Event
from time import sleep
from typing import Any, Dict, List, Optional, Tuple

import mss
from PIL import Image

from config import PROJECT_ROOT


DEBUG_DIR = PROJECT_ROOT / "debug"
DEBUG_IMAGE_PATH = DEBUG_DIR / "clock_region_latest.png"
SCREEN_DIAGNOSTIC_PATH = DEBUG_DIR / "screen_diagnostic.png"


def _get_virtual_bounds() -> Optional[Dict[str, int]]:
    try:
        with mss.mss() as sct:
            if len(sct.monitors) < 1:
                return None
            monitor = sct.monitors[0]
            return {
                "left": int(monitor["left"]),
                "top": int(monitor["top"]),
                "width": int(monitor["width"]),
                "height": int(monitor["height"]),
            }
    except Exception:
        return None


def get_screen_diagnostics() -> Dict[str, Any]:
    diagnostics: Dict[str, Any] = {
        "monitor_count": 0,
        "virtual_desktop": None,
        "primary_monitor": None,
        "monitors": [],
    }
    with mss.mss() as sct:
        diagnostics["monitor_count"] = max(0, len(sct.monitors) - 1)
        for index, monitor in enumerate(sct.monitors):
            entry = {
                "index": index,
                "left": int(monitor["left"]),
                "top": int(monitor["top"]),
                "width": int(monitor["width"]),
                "height": int(monitor["height"]),
            }
            diagnostics["monitors"].append(entry)
        if diagnostics["monitors"]:
            diagnostics["virtual_desktop"] = diagnostics["monitors"][0]
        if len(diagnostics["monitors"]) > 1:
            diagnostics["primary_monitor"] = diagnostics["monitors"][1]
    return diagnostics


def validate_clock_region(settings: Dict) -> Tuple[bool, str]:
    region = settings.get("clock_region")
    if not isinstance(region, dict):
        return False, "clock_region is missing."

    required = ("left", "top", "width", "height")
    for key in required:
        if key not in region:
            return False, f"clock_region missing '{key}'."
        if not isinstance(region[key], int):
            return False, f"clock_region '{key}' must be an integer."

    if region["width"] <= 0 or region["height"] <= 0:
        return False, "clock_region width/height must be > 0."

    bounds = _get_virtual_bounds()
    if bounds is not None:
        if region["left"] < bounds["left"]:
            return False, "clock_region extends past the left edge of the virtual desktop."
        if region["top"] < bounds["top"]:
            return False, "clock_region extends past the top edge of the virtual desktop."
        if region["left"] + region["width"] > bounds["left"] + bounds["width"]:
            return False, "clock_region extends past the right edge of the virtual desktop."
        if region["top"] + region["height"] > bounds["top"] + bounds["height"]:
            return False, "clock_region extends past the bottom edge of the virtual desktop."
    return True, "ok"


def probe_clock_region(settings: Dict) -> Tuple[bool, str]:
    ok, message = validate_clock_region(settings)
    if not ok:
        return False, message
    region = settings["clock_region"]
    try:
        with mss.mss() as sct:
            shot = sct.grab(
                {
                    "left": region["left"],
                    "top": region["top"],
                    "width": region["width"],
                    "height": region["height"],
                }
            )
            if shot.width <= 0 or shot.height <= 0:
                return False, "Clock capture returned an empty image."
    except Exception as exc:
        return False, f"Clock capture failed: {exc}"
    return True, "ok"


def capture_clock_region(settings: Dict) -> Path:
    ok, msg = validate_clock_region(settings)
    if not ok:
        raise ValueError(msg)

    region = settings["clock_region"]
    monitor = {
        "left": region["left"],
        "top": region["top"],
        "width": region["width"],
        "height": region["height"],
    }

    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    with mss.mss() as sct:
        shot = sct.grab(monitor)
        image = Image.frombytes("RGB", shot.size, shot.rgb)
        image.save(DEBUG_IMAGE_PATH)
    return DEBUG_IMAGE_PATH


def capture_screen_diagnostic() -> Path:
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    with mss.mss() as sct:
        if len(sct.monitors) < 1:
            raise RuntimeError("No screen monitors detected.")
        shot = sct.grab(sct.monitors[0])
        image = Image.frombytes("RGB", shot.size, shot.rgb)
        image.save(SCREEN_DIAGNOSTIC_PATH)
    return SCREEN_DIAGNOSTIC_PATH


def _candidate_clock_regions(monitors: List[Dict[str, int]]) -> List[Dict[str, int]]:
    sizes = [
        (240, 84),
        (220, 70),
        (260, 90),
        (300, 100),
        (340, 110),
    ]
    x_offsets = [0, -80, -160, -240, -320, -420, -540, -700]
    y_offsets = [0, 10, 20, 40, 60, 80, 100]
    anchors = [0.98, 0.93, 0.88, 0.83, 0.75, 0.65]
    regions: List[Dict[str, int]] = []
    for monitor in monitors:
        left = int(monitor["left"])
        top = int(monitor["top"])
        width = int(monitor["width"])
        height = int(monitor["height"])
        for box_width, box_height in sizes:
            max_left = left + max(0, width - box_width)
            max_top = top + max(0, height - box_height)
            for anchor in anchors:
                base_left = int(left + max(0, width - box_width) * anchor)
                for offset_x in x_offsets:
                    region_left = min(max(left, base_left + offset_x), max_left)
                    for offset_y in y_offsets:
                        region_top = min(max(top, top + offset_y), max_top)
                        regions.append(
                            {
                                "left": int(region_left),
                                "top": int(region_top),
                                "width": int(box_width),
                                "height": int(box_height),
                            }
                        )
    return regions


def setup_clock_candidate_scan(
    cancel_event: Optional[Event] = None,
) -> Tuple[Optional[Dict[str, int]], Optional[Path], str]:
    try:
        from ocr import ocr_and_parse
    except Exception as exc:
        return None, None, f"OCR unavailable: {exc}"

    with mss.mss() as sct:
        monitors = []
        for monitor in sct.monitors[1:] or sct.monitors[:1]:
            monitors.append(
                {
                    "left": int(monitor["left"]),
                    "top": int(monitor["top"]),
                    "width": int(monitor["width"]),
                    "height": int(monitor["height"]),
                }
            )
        for region in _candidate_clock_regions(monitors):
            if cancel_event is not None and cancel_event.is_set():
                return None, None, "cancelled"
            try:
                shot = sct.grab(region)
                image = Image.frombytes("RGB", shot.size, shot.rgb)
                DEBUG_DIR.mkdir(parents=True, exist_ok=True)
                image.save(DEBUG_IMAGE_PATH)
                first_result = ocr_and_parse(DEBUG_IMAGE_PATH, source="setup_clock")
                if not (first_result.accepted and first_result.parsed_display_time):
                    continue
                if cancel_event is not None and cancel_event.is_set():
                    return None, None, "cancelled"
                sleep(0.15)
                shot_confirm = sct.grab(region)
                image_confirm = Image.frombytes("RGB", shot_confirm.size, shot_confirm.rgb)
                image_confirm.save(DEBUG_IMAGE_PATH)
                second_result = ocr_and_parse(DEBUG_IMAGE_PATH, source="setup_clock_confirm")
                if second_result.accepted and second_result.parsed_display_time == first_result.parsed_display_time:
                    return region, DEBUG_IMAGE_PATH, first_result.parsed_display_time
            except Exception:
                continue
    return None, None, "No readable clock found."
