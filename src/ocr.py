import os
import re
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Sequence

from PIL import Image, ImageEnhance, ImageOps

from config import load_settings
from paths import get_app_root, is_frozen, resolve_path
from runtime_trace import run_traced_subprocess


TIME_TOKEN_PATTERN = re.compile(r"(?<!\d)(\d{1,2})\s*[:\-\s]\s*([0-5]\d)(?:\s*([AP]M))?(?!\d)", re.IGNORECASE)
INLINE_AMPM_PATTERN = re.compile(r"(?<!\d)(\d{1,2})[:\-\s]?([0-5]\d)([AP]M)(?!\d)", re.IGNORECASE)
LEADING_DOUBLE_DIGIT_PATTERN = re.compile(r"\b(10|11|12)\s*[:\-\s]\s*([0-5]\d)\b", re.IGNORECASE)
DEFAULT_TESSERACT_PATHS = (
    Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
    Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
)
PORTABLE_TESSERACT_PATH = Path("tesseract") / "tesseract.exe"
PARSER_VERSION = "v2.7-canonical"


@dataclass(frozen=True)
class ClockParseCandidate:
    original_text: str
    display_time: str
    parsed_minutes: int
    hour: int
    minute: int
    meridiem: str
    preserved_leading_digits: bool
    suspicion_flags: tuple[str, ...] = ()


@dataclass(frozen=True)
class ClockParseResult:
    raw_ocr: str = ""
    normalized_ocr: str = ""
    parse_candidates: tuple[str, ...] = ()
    selected_time_text: str = ""
    hour: Optional[int] = None
    minute: Optional[int] = None
    meridiem: str = ""
    parsed_minutes: Optional[int] = None
    parsed_display_time: str = ""
    confidence: str = ""
    source: str = ""
    accepted: bool = False
    reject_reason: str = ""
    timestamp_real: str = ""
    region_used: str = ""


def preprocess_clock_image(image_path: Path) -> Image.Image:
    image = Image.open(image_path).convert("L")
    image = ImageEnhance.Contrast(image).enhance(2.2)
    image = image.resize((image.width * 2, image.height * 2), Image.Resampling.LANCZOS)
    image = ImageOps.autocontrast(image)
    image = image.point(lambda p: 255 if p > 145 else 0)
    return image


def resolve_tesseract_cmd(settings: Optional[dict] = None) -> str:
    settings = settings or load_settings()
    if is_frozen():
        bundled = resolve_path(PORTABLE_TESSERACT_PATH)
        if bundled.exists():
            return str(bundled)
        raise FileNotFoundError(
            "Bundled clock reader is missing. Re-extract the full ZIP and keep the tesseract folder beside the EXE."
        )

    configured = settings.get("tesseract_cmd")
    if isinstance(configured, str) and configured.strip():
        configured_path = Path(configured.strip())
        if not configured_path.is_absolute():
            configured_path = get_app_root() / configured_path
        if configured_path.exists():
            return str(configured_path)
        searched = ", ".join(str(path) for path in DEFAULT_TESSERACT_PATHS)
        raise FileNotFoundError(
            f"Configured tesseract_cmd does not exist: {configured_path}. "
            f"Fix config/settings.json or install Tesseract. Searched: {searched}"
        )

    for candidate in DEFAULT_TESSERACT_PATHS:
        if candidate.exists():
            return str(candidate)

    searched = ", ".join(str(path) for path in DEFAULT_TESSERACT_PATHS)
    raise FileNotFoundError(
        "Could not find tesseract.exe. Set 'tesseract_cmd' in config/settings.json "
        f"or add Tesseract to PATH. Searched: {searched}"
    )


def resolve_tessdata_dir(tesseract_cmd: Optional[str] = None) -> Path:
    if tesseract_cmd:
        return Path(tesseract_cmd).resolve().parent / "tessdata"
    if is_frozen():
        return resolve_path(PORTABLE_TESSERACT_PATH).resolve().parent / "tessdata"
    return Path(resolve_tesseract_cmd()).resolve().parent / "tessdata"


def preflight_tesseract(settings: Optional[dict] = None):
    settings = settings or load_settings()
    tesseract_cmd = resolve_tesseract_cmd(settings)
    tessdata_dir = resolve_tessdata_dir(tesseract_cmd)

    if not Path(tesseract_cmd).exists():
        return False, "Bundled clock reader not found.", "", tessdata_dir
    if not tessdata_dir.exists():
        return False, "Language data folder not found.", "", tessdata_dir

    env = os.environ.copy()
    env["TESSDATA_PREFIX"] = str(tessdata_dir.parent)
    cmd = [tesseract_cmd, "--list-langs", "--tessdata-dir", str(tessdata_dir)]
    completed = run_traced_subprocess(cmd, purpose="tesseract preflight", recurring=False, hidden=True, env=env)
    output = f"{completed.stdout}\n{completed.stderr}".strip()
    if completed.returncode != 0:
        return False, f"Clock reader engine is bundled, but OCR call failed. Please report this build.", output, tessdata_dir
    if re.search(r"(?im)^\s*eng\s*$", completed.stdout) is None:
        return False, "Clock reader data could not be loaded. Re-extract the full ZIP and keep the tesseract folder beside the EXE.", output, tessdata_dir
    return True, "ok", output, tessdata_dir


def run_ocr(image_path: Path) -> str:
    tesseract_cmd = resolve_tesseract_cmd()
    prepared = preprocess_clock_image(image_path)
    tessdata_dir = resolve_tessdata_dir(tesseract_cmd)
    previous_prefix = os.environ.get("TESSDATA_PREFIX")
    os.environ["TESSDATA_PREFIX"] = str(tessdata_dir.parent)
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        temp_image_path = Path(tmp.name)
    try:
        prepared.save(temp_image_path)
        cmd = [
            tesseract_cmd,
            str(temp_image_path),
            "stdout",
            "--psm",
            "11",
            "--oem",
            "1",
            "--tessdata-dir",
            str(tessdata_dir),
            "-l",
            "eng",
        ]
        completed = run_traced_subprocess(cmd, purpose="tesseract ocr", recurring=False, hidden=True)
        if completed.returncode != 0:
            raise RuntimeError(
                completed.stderr.strip()
                or completed.stdout.strip()
                or "Clock reader engine could not process the image."
            )
        text = completed.stdout
    except Exception as exc:
        raise RuntimeError(
            "Clock reader data could not be loaded. Re-extract the full ZIP and keep the tesseract folder beside the EXE."
        ) from exc
    finally:
        try:
            if temp_image_path.exists():
                temp_image_path.unlink()
        except Exception:
            pass
        if previous_prefix is None:
            os.environ.pop("TESSDATA_PREFIX", None)
        else:
            os.environ["TESSDATA_PREFIX"] = previous_prefix
    return " ".join(text.split())


def normalize_clock_text(raw_text: str) -> str:
    text = (raw_text or "").strip()
    if not text:
        return ""

    replacements = {
        "O": "0",
        "o": "0",
        "l": "1",
        "I": "1",
        "|": "1",
        "S": "5",
    }
    translated = "".join(replacements.get(char, char) for char in text)
    translated = re.sub(r"(?i)\bA\s*M\b", "AM", translated)
    translated = re.sub(r"(?i)\bP\s*M\b", "PM", translated)
    translated = re.sub(r"(?i)(\d)(AM|PM)\b", r"\1 \2", translated)
    translated = re.sub(r"(?i)\b(AM|PM)(\d)", r"\1 \2", translated)
    translated = re.sub(r"\s+", " ", translated).strip()
    return translated


def _display_time(hour: int, minute: int, meridiem: str) -> str:
    parsed = datetime.strptime(f"{hour}:{minute:02d} {meridiem}", "%I:%M %p")
    return parsed.strftime("%I:%M %p").lstrip("0")


def _parsed_minutes(hour: int, minute: int, meridiem: str) -> int:
    parsed = datetime.strptime(f"{hour}:{minute:02d} {meridiem}", "%I:%M %p")
    return parsed.hour * 60 + parsed.minute


def _digit_loss_suspected(original_text: str, hour: int) -> bool:
    match = LEADING_DOUBLE_DIGIT_PATTERN.search(original_text)
    if not match:
        return False
    original_hour = int(match.group(1))
    if original_hour in (10, 11, 12) and hour not in (10, 11, 12):
        return True
    return False


def _candidate_flags(original_text: str, hour: int, meridiem_present: bool) -> tuple[str, ...]:
    flags: list[str] = []
    if _digit_loss_suspected(original_text, hour):
        flags.append("digit_loss_suspect")
    if not meridiem_present:
        flags.append("missing_meridiem")
    return tuple(flags)


def _candidate_from_match(original_text: str, hour_text: str, minute_text: str, meridiem_text: Optional[str]) -> Optional[ClockParseCandidate]:
    try:
        hour = int(hour_text)
        minute = int(minute_text)
    except ValueError:
        return None
    if not (1 <= hour <= 12 and 0 <= minute <= 59):
        return None
    meridiem = (meridiem_text or "").upper()
    if meridiem and meridiem not in {"AM", "PM"}:
        return None
    if not meridiem:
        return None
    return ClockParseCandidate(
        original_text=original_text,
        display_time=_display_time(hour, minute, meridiem),
        parsed_minutes=_parsed_minutes(hour, minute, meridiem),
        hour=hour,
        minute=minute,
        meridiem=meridiem,
        preserved_leading_digits=not _digit_loss_suspected(original_text, hour),
        suspicion_flags=_candidate_flags(original_text, hour, bool(meridiem)),
    )


def _extract_candidates(normalized_text: str) -> list[ClockParseCandidate]:
    candidates: list[ClockParseCandidate] = []
    seen: set[tuple[int, int, str]] = set()

    for match in INLINE_AMPM_PATTERN.finditer(normalized_text):
        candidate = _candidate_from_match(match.group(0), match.group(1), match.group(2), match.group(3))
        if candidate is None:
            continue
        key = (candidate.hour, candidate.minute, candidate.meridiem)
        if key not in seen:
            seen.add(key)
            candidates.append(candidate)

    for match in TIME_TOKEN_PATTERN.finditer(normalized_text):
        candidate = _candidate_from_match(match.group(0), match.group(1), match.group(2), match.group(3))
        if candidate is None:
            continue
        key = (candidate.hour, candidate.minute, candidate.meridiem)
        if key not in seen:
            seen.add(key)
            candidates.append(candidate)
    return candidates


def _select_candidate(candidates: Sequence[ClockParseCandidate]) -> tuple[Optional[ClockParseCandidate], str]:
    if not candidates:
        return None, "no_time_pattern_found"
    ranked = sorted(
        candidates,
        key=lambda item: (
            0 if item.preserved_leading_digits else 1,
            0 if "digit_loss_suspect" not in item.suspicion_flags else 1,
            -len(item.original_text),
            item.parsed_minutes,
        ),
    )
    selected = ranked[0]
    if "digit_loss_suspect" in selected.suspicion_flags:
        return None, "digit_loss_suspect"
    return selected, ""


def parse_clock_result(
    raw_text: str,
    *,
    source: str = "watcher",
    region_used: str = "",
    timestamp_real: Optional[datetime] = None,
) -> ClockParseResult:
    normalized = normalize_clock_text(raw_text)
    candidates = _extract_candidates(normalized)
    selected, reject_reason = _select_candidate(candidates)
    timestamp = (timestamp_real or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
    candidate_labels = tuple(
        f"{candidate.display_time} [{','.join(candidate.suspicion_flags) or 'ok'}]"
        for candidate in candidates
    )
    if selected is None:
        return ClockParseResult(
            raw_ocr=raw_text or "",
            normalized_ocr=normalized,
            parse_candidates=candidate_labels,
            selected_time_text="",
            hour=None,
            minute=None,
            meridiem="",
            parsed_minutes=None,
            parsed_display_time="",
            confidence="rejected",
            source=source,
            accepted=False,
            reject_reason=reject_reason or "no_accepted_candidate",
            timestamp_real=timestamp,
            region_used=region_used,
        )

    return ClockParseResult(
        raw_ocr=raw_text or "",
        normalized_ocr=normalized,
        parse_candidates=candidate_labels,
        selected_time_text=selected.display_time,
        hour=selected.hour,
        minute=selected.minute,
        meridiem=selected.meridiem,
        parsed_minutes=selected.parsed_minutes,
        parsed_display_time=selected.display_time,
        confidence="accepted",
        source=source,
        accepted=True,
        reject_reason="",
        timestamp_real=timestamp,
        region_used=region_used,
    )


def parse_clock_text(raw_text: str) -> Optional[str]:
    result = parse_clock_result(raw_text)
    if not result.accepted:
        return None
    return result.parsed_display_time


def ocr_and_parse(image_path: Path, *, source: str = "watcher", region_used: str = "") -> ClockParseResult:
    raw_text = run_ocr(image_path)
    return parse_clock_result(raw_text, source=source, region_used=region_used)
