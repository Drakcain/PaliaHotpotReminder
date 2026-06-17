from pathlib import Path
from threading import Event
from time import sleep
from typing import Any, Dict, List, Optional, Tuple

import mss
from PIL import Image

from config import PROJECT_ROOT


DEBUG_DIR = PROJECT_ROOT / "debug"
DEBUG_IMAGE_PATH = DEBUG_DIR / "clock_region_latest.png"
OCR_LEFT_PAD_RATIO = 0.18
OCR_MAX_LEFT_PAD = 48
OCR_RIGHT_PAD = 6
BASELINE_MONITOR_WIDTH = 3440
BASELINE_MONITOR_HEIGHT = 1440
BASELINE_CLOCK_WIDTH = 240
BASELINE_CLOCK_HEIGHT = 84
BASELINE_TOP_MARGIN = 10
BASELINE_RIGHT_MARGIN = 256
BASELINE_RIGHT_MARGIN_CANDIDATES = (224, 240, 256, 272, 287, 304)
BASELINE_TOP_MARGIN_CANDIDATES = (6, 10, 14, 18)


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
    monitor = _expanded_clock_region_for_ocr(region)

    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    with mss.mss() as sct:
        shot = sct.grab(monitor)
        image = Image.frombytes("RGB", shot.size, shot.rgb)
        image.save(DEBUG_IMAGE_PATH)
    return DEBUG_IMAGE_PATH


def _expanded_clock_region_for_ocr(region: Dict[str, int]) -> Dict[str, int]:
    bounds = _get_virtual_bounds()
    left = int(region["left"])
    top = int(region["top"])
    width = int(region["width"])
    height = int(region["height"])
    left_pad = min(OCR_MAX_LEFT_PAD, max(8, round(width * OCR_LEFT_PAD_RATIO)))
    right_pad = OCR_RIGHT_PAD
    expanded_left = left - left_pad
    expanded_width = width + left_pad + right_pad

    if bounds is not None:
        min_left = int(bounds["left"])
        max_right = int(bounds["left"] + bounds["width"])
        if expanded_left < min_left:
            expanded_width -= min_left - expanded_left
            expanded_left = min_left
        if expanded_left + expanded_width > max_right:
            expanded_width = max(1, max_right - expanded_left)

    return {
        "left": int(expanded_left),
        "top": top,
        "width": int(expanded_width),
        "height": height,
    }

def _scaled_clock_regions_for_monitor(monitor: Dict[str, int]) -> List[Dict[str, int]]:
    left = int(monitor["left"])
    top = int(monitor["top"])
    width = int(monitor["width"])
    height = int(monitor["height"])
    if width <= 0 or height <= 0:
        return []

    height_scale = height / BASELINE_MONITOR_HEIGHT
    base_box_height = max(56, round(BASELINE_CLOCK_HEIGHT * height_scale))
    base_box_width = max(160, round(base_box_height * (BASELINE_CLOCK_WIDTH / BASELINE_CLOCK_HEIGHT)))
    size_scales = [1.0, 0.96, 1.04, 0.9, 1.1, 1.18]
    right_margins = [max(24, round(candidate * height_scale)) for candidate in BASELINE_RIGHT_MARGIN_CANDIDATES]
    top_margins = [max(2, round(candidate * height_scale)) for candidate in BASELINE_TOP_MARGIN_CANDIDATES]
    x_offsets = [0, -20, 20, -40, 40, -64, 64, -96, 96]
    y_offsets = [0, 4, 8, 12, 18, 26]
    regions: List[Dict[str, int]] = []
    seen: set[tuple[int, int, int, int]] = set()
    for size_scale in size_scales:
        box_height = max(56, round(base_box_height * size_scale))
        box_width = max(160, round(base_box_width * size_scale))
        max_left = left + max(0, width - box_width)
        max_top = top + max(0, height - box_height)
        for right_margin in right_margins:
            for top_margin in top_margins:
                base_left = left + width - right_margin - box_width
                base_top = top + top_margin
                for offset_x in x_offsets:
                    region_left = min(max(left, base_left + round(offset_x * height_scale)), max_left)
                    for offset_y in y_offsets:
                        region_top = min(max(top, base_top + round(offset_y * height_scale)), max_top)
                        key = (int(region_left), int(region_top), int(box_width), int(box_height))
                        if key in seen:
                            continue
                        seen.add(key)
                        regions.append(
                            {
                                "left": key[0],
                                "top": key[1],
                                "width": key[2],
                                "height": key[3],
                            }
                        )
    return regions


def _candidate_clock_regions(monitors: List[Dict[str, int]]) -> List[Dict[str, int]]:
    regions: List[Dict[str, int]] = []
    for monitor in monitors:
        regions.extend(_scaled_clock_regions_for_monitor(monitor))
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
                confirmations: list[str] = []
                for attempt in range(3):
                    parse_source = "setup_clock" if attempt == 0 else f"setup_clock_confirm_{attempt}"
                    result = ocr_and_parse(DEBUG_IMAGE_PATH, source=parse_source)
                    if result.accepted and result.parsed_display_time:
                        confirmations.append(result.parsed_display_time)
                    if cancel_event is not None and cancel_event.is_set():
                        return None, None, "cancelled"
                    if attempt < 2:
                        sleep(0.2)
                        shot = sct.grab(region)
                        image = Image.frombytes("RGB", shot.size, shot.rgb)
                        image.save(DEBUG_IMAGE_PATH)
                if len(confirmations) < 3:
                    continue
                if confirmations[0] == confirmations[1] == confirmations[2]:
                    return region, DEBUG_IMAGE_PATH, confirmations[0]
            except Exception:
                continue
    return None, None, "No readable clock found."
