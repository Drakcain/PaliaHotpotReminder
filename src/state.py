from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any

from config import DEFAULT_SETTINGS
from ocr import ClockParseResult


VALID_MODES = ("Unknown", "Confirmed", "Estimated", "Stale")


@dataclass
class TrackerSnapshot:
    mode: str = "Unknown"
    status_message: str = "No valid clock yet"
    raw_ocr: str = ""
    normalized_ocr: str = ""
    parse_candidates: str = ""
    parse_accepted: bool = False
    parse_reject_reason: str = ""
    parse_source: str = ""
    parsed_time: str = ""
    current_palia_time: str = ""
    last_confirmed_palia_time: str = ""
    estimated_palia_time: str = ""
    last_confirmed_real_timestamp: str = ""
    seconds_since_confirmed: str = ""


def _setting_as_float(settings: Dict[str, Any], key: str, default: float) -> float:
    value = settings.get(key, default)
    try:
        result = float(value)
        if result <= 0:
            return float(default)
        return result
    except (TypeError, ValueError):
        return float(default)


def _setting_as_int(settings: Dict[str, Any], key: str, default: int) -> int:
    value = settings.get(key, default)
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _format_time(value: datetime) -> str:
    return value.strftime("%I:%M %p").lstrip("0")


def _combine_today(now: datetime, time_label: str) -> datetime:
    parsed = datetime.strptime(time_label, "%I:%M %p")
    return now.replace(
        hour=parsed.hour,
        minute=parsed.minute,
        second=0,
        microsecond=0,
    )


def _wrap_palia_time(anchor: datetime, elapsed_real_seconds: float, minutes_per_real_second: float) -> datetime:
    anchor_seconds = anchor.hour * 3600 + anchor.minute * 60
    elapsed_palia_seconds = elapsed_real_seconds * minutes_per_real_second * 60.0
    wrapped_seconds = (anchor_seconds + elapsed_palia_seconds) % (24 * 3600)
    total_seconds = int(wrapped_seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    return anchor.replace(hour=hours, minute=minutes, second=0, microsecond=0)


class PaliaTimeTracker:
    def __init__(self) -> None:
        self.last_confirmed_palia_dt: Optional[datetime] = None
        self.last_confirmed_real_dt: Optional[datetime] = None
        self.last_raw_ocr: str = ""
        self.last_normalized_ocr: str = ""
        self.last_parse_candidates: str = ""
        self.last_parse_accepted: bool = False
        self.last_parse_reject_reason: str = ""
        self.last_parse_source: str = ""
        self.last_parsed_time: str = ""
        self.last_estimated_palia_dt: Optional[datetime] = None
        self.mode: str = "Unknown"
        self.unreadable_streak: int = 0

    def reset(self) -> None:
        self.last_confirmed_palia_dt = None
        self.last_confirmed_real_dt = None
        self.last_raw_ocr = ""
        self.last_normalized_ocr = ""
        self.last_parse_candidates = ""
        self.last_parse_accepted = False
        self.last_parse_reject_reason = ""
        self.last_parse_source = ""
        self.last_parsed_time = ""
        self.last_estimated_palia_dt = None
        self.mode = "Unknown"
        self.unreadable_streak = 0

    def update(self, parse_result: ClockParseResult, settings: Optional[Dict[str, Any]] = None, now: Optional[datetime] = None) -> TrackerSnapshot:
        settings = settings or DEFAULT_SETTINGS
        now = now or datetime.now()
        minutes_per_real_second = _setting_as_float(settings, "palia_minutes_per_real_second", 0.4)
        stale_after_seconds = _setting_as_int(settings, "stale_after_seconds", 900)
        unreadable_reads_before_hidden = max(1, _setting_as_int(settings, "unreadable_reads_before_hidden", 2))

        self.last_raw_ocr = parse_result.raw_ocr or ""
        self.last_normalized_ocr = parse_result.normalized_ocr or ""
        self.last_parse_candidates = " | ".join(parse_result.parse_candidates)
        self.last_parse_accepted = bool(parse_result.accepted)
        self.last_parse_reject_reason = parse_result.reject_reason or ""
        self.last_parse_source = parse_result.source or ""

        if parse_result.accepted and parse_result.parsed_display_time:
            parsed_time = parse_result.parsed_display_time
            self.unreadable_streak = 0
            confirmed_dt = _combine_today(now, parsed_time)
            self.last_confirmed_palia_dt = confirmed_dt
            self.last_confirmed_real_dt = now
            self.last_parsed_time = parsed_time
            self.last_estimated_palia_dt = confirmed_dt
            self.mode = "Confirmed"
            return TrackerSnapshot(
                mode="Confirmed",
                status_message="Confirmed clock",
                raw_ocr=self.last_raw_ocr,
                normalized_ocr=self.last_normalized_ocr,
                parse_candidates=self.last_parse_candidates,
                parse_accepted=True,
                parse_reject_reason="",
                parse_source=self.last_parse_source,
                parsed_time=parsed_time,
                current_palia_time=parsed_time,
                last_confirmed_palia_time=_format_time(confirmed_dt),
                estimated_palia_time=_format_time(confirmed_dt),
                last_confirmed_real_timestamp=now.strftime("%Y-%m-%d %H:%M:%S"),
                seconds_since_confirmed="0.0",
            )

        if self.last_confirmed_palia_dt is None or self.last_confirmed_real_dt is None:
            self.unreadable_streak = 0
            self.mode = "Unknown"
            self.last_estimated_palia_dt = None
            self.last_parsed_time = ""
            return TrackerSnapshot(
                mode="Unknown",
                status_message="No valid clock yet",
                raw_ocr=self.last_raw_ocr,
                normalized_ocr=self.last_normalized_ocr,
                parse_candidates=self.last_parse_candidates,
                parse_accepted=self.last_parse_accepted,
                parse_reject_reason=self.last_parse_reject_reason,
                parse_source=self.last_parse_source,
                parsed_time="",
                current_palia_time="",
                last_confirmed_palia_time="",
                estimated_palia_time="",
                last_confirmed_real_timestamp="",
                seconds_since_confirmed="",
            )

        self.unreadable_streak += 1
        elapsed_real_seconds = max(0.0, (now - self.last_confirmed_real_dt).total_seconds())
        estimated_dt = _wrap_palia_time(self.last_confirmed_palia_dt, elapsed_real_seconds, minutes_per_real_second)
        self.last_estimated_palia_dt = estimated_dt
        if self.mode == "Confirmed" and self.unreadable_streak < unreadable_reads_before_hidden:
            if elapsed_real_seconds > stale_after_seconds:
                self.mode = "Stale"
                status_message = "Stale estimate"
                return TrackerSnapshot(
                    mode="Stale",
                    status_message=status_message,
                    raw_ocr=self.last_raw_ocr,
                    normalized_ocr=self.last_normalized_ocr,
                    parse_candidates=self.last_parse_candidates,
                    parse_accepted=self.last_parse_accepted,
                    parse_reject_reason=self.last_parse_reject_reason,
                    parse_source=self.last_parse_source,
                    parsed_time="",
                    current_palia_time=_format_time(estimated_dt),
                    last_confirmed_palia_time=_format_time(self.last_confirmed_palia_dt),
                    estimated_palia_time=_format_time(estimated_dt),
                    last_confirmed_real_timestamp=self.last_confirmed_real_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    seconds_since_confirmed=f"{elapsed_real_seconds:.1f}",
                )
            self.mode = "Confirmed"
            return TrackerSnapshot(
                mode="Confirmed",
                status_message="Confirmed clock",
                raw_ocr=self.last_raw_ocr,
                normalized_ocr=self.last_normalized_ocr,
                parse_candidates=self.last_parse_candidates,
                parse_accepted=self.last_parse_accepted,
                parse_reject_reason=self.last_parse_reject_reason,
                parse_source=self.last_parse_source,
                parsed_time=self.last_parsed_time,
                current_palia_time=self.last_parsed_time,
                last_confirmed_palia_time=_format_time(self.last_confirmed_palia_dt),
                estimated_palia_time=_format_time(self.last_confirmed_palia_dt),
                last_confirmed_real_timestamp=self.last_confirmed_real_dt.strftime("%Y-%m-%d %H:%M:%S"),
                seconds_since_confirmed=f"{elapsed_real_seconds:.1f}",
            )

        self.mode = "Stale" if elapsed_real_seconds > stale_after_seconds else "Estimated"

        status_message = "Stale estimate" if self.mode == "Stale" else "Clock hidden, estimating"
        return TrackerSnapshot(
            mode=self.mode,
            status_message=status_message,
            raw_ocr=self.last_raw_ocr,
            normalized_ocr=self.last_normalized_ocr,
            parse_candidates=self.last_parse_candidates,
            parse_accepted=self.last_parse_accepted,
            parse_reject_reason=self.last_parse_reject_reason,
            parse_source=self.last_parse_source,
            parsed_time="",
            current_palia_time=_format_time(estimated_dt),
            last_confirmed_palia_time=_format_time(self.last_confirmed_palia_dt),
            estimated_palia_time=_format_time(estimated_dt),
            last_confirmed_real_timestamp=self.last_confirmed_real_dt.strftime("%Y-%m-%d %H:%M:%S"),
            seconds_since_confirmed=f"{elapsed_real_seconds:.1f}",
        )
