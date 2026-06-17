from dataclasses import dataclass, replace
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


def _format_minutes(total_minutes: int) -> str:
    wrapped = total_minutes % (24 * 60)
    anchor = datetime.now().replace(hour=wrapped // 60, minute=wrapped % 60, second=0, microsecond=0)
    return _format_time(anchor)


def _clock_distance_minutes(left_minutes: int, right_minutes: int) -> int:
    direct = abs((left_minutes % 1440) - (right_minutes % 1440))
    return min(direct, 1440 - direct)


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
        self.last_effective_parse_result: ClockParseResult = ClockParseResult()
        self.mode: str = "Unknown"
        self.unreadable_streak: int = 0
        self.pending_suspicious_time: str = ""
        self.pending_suspicious_count: int = 0

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
        self.last_effective_parse_result = ClockParseResult()
        self.mode = "Unknown"
        self.unreadable_streak = 0
        self.pending_suspicious_time = ""
        self.pending_suspicious_count = 0

    def _guard_clock_candidate(
        self,
        parse_result: ClockParseResult,
        *,
        now: datetime,
        minutes_per_real_second: float,
    ) -> ClockParseResult:
        if not parse_result.accepted or parse_result.parsed_minutes is None:
            return parse_result
        if self.last_confirmed_palia_dt is None or self.last_confirmed_real_dt is None:
            self.pending_suspicious_time = ""
            self.pending_suspicious_count = 0
            return parse_result

        elapsed_real_seconds = max(0.0, (now - self.last_confirmed_real_dt).total_seconds())
        expected_dt = _wrap_palia_time(self.last_confirmed_palia_dt, elapsed_real_seconds, minutes_per_real_second)
        expected_minutes = expected_dt.hour * 60 + expected_dt.minute
        candidate_minutes = int(parse_result.parsed_minutes)
        allowed_distance = max(6, min(30, int(elapsed_real_seconds * minutes_per_real_second) + 6))
        distance = _clock_distance_minutes(candidate_minutes, expected_minutes)
        if distance <= allowed_distance:
            self.pending_suspicious_time = ""
            self.pending_suspicious_count = 0
            return parse_result

        corrected = self._maybe_correct_missing_leading_one(parse_result, expected_minutes, allowed_distance)
        if corrected is not None:
            corrected_hour, corrected_minutes, corrected_label = corrected
            self.pending_suspicious_time = ""
            self.pending_suspicious_count = 0
            return replace(
                parse_result,
                hour=corrected_hour,
                parsed_minutes=corrected_minutes,
                parsed_display_time=corrected_label,
                selected_time_text=corrected_label,
                confidence="corrected_missing_leading_digit",
                parse_candidates=tuple(parse_result.parse_candidates) + (
                    f"{corrected_label} [corrected_missing_leading_digit]",
                ),
            )

        candidate_label = parse_result.parsed_display_time
        if candidate_label == self.pending_suspicious_time:
            self.pending_suspicious_count += 1
        else:
            self.pending_suspicious_time = candidate_label
            self.pending_suspicious_count = 1

        if self.pending_suspicious_count >= 3:
            self.pending_suspicious_time = ""
            self.pending_suspicious_count = 0
            return replace(parse_result, confidence="accepted_after_repeated_suspicious_confirmation")

        return replace(
            parse_result,
            accepted=False,
            reject_reason=(
                "continuity_suspicious_jump "
                f"candidate={candidate_label} expected={_format_minutes(expected_minutes)} "
                f"distance={distance}m allowed={allowed_distance}m "
                f"confirmations={self.pending_suspicious_count}/3"
            ),
            confidence="held_for_continuity_confirmation",
        )

    def _maybe_correct_missing_leading_one(
        self,
        parse_result: ClockParseResult,
        expected_minutes: int,
        allowed_distance: int,
    ) -> Optional[tuple[int, int, str]]:
        if parse_result.hour != 1 or parse_result.minute is None or parse_result.meridiem not in {"AM", "PM"}:
            return None
        corrected_hour = 11
        corrected_dt = datetime.strptime(f"{corrected_hour}:{parse_result.minute:02d} {parse_result.meridiem}", "%I:%M %p")
        corrected_minutes = corrected_dt.hour * 60 + corrected_dt.minute
        if _clock_distance_minutes(corrected_minutes, expected_minutes) > allowed_distance:
            return None
        return corrected_hour, corrected_minutes, _format_time(corrected_dt)

    def update(self, parse_result: ClockParseResult, settings: Optional[Dict[str, Any]] = None, now: Optional[datetime] = None) -> TrackerSnapshot:
        settings = settings or DEFAULT_SETTINGS
        now = now or datetime.now()
        minutes_per_real_second = _setting_as_float(settings, "palia_minutes_per_real_second", 0.4)
        stale_after_seconds = _setting_as_int(settings, "stale_after_seconds", 900)
        unreadable_reads_before_hidden = max(1, _setting_as_int(settings, "unreadable_reads_before_hidden", 2))

        parse_result = self._guard_clock_candidate(
            parse_result,
            now=now,
            minutes_per_real_second=minutes_per_real_second,
        )
        self.last_effective_parse_result = parse_result

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
