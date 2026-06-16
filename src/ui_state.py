from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class UIState:
    current_page: str = "Dashboard"
    activity_items: list[str] = field(default_factory=list)
    _last_activity: str = ""
    _repeat_count: int = 0

    def add_activity(self, message: str, *, limit: int = 12) -> list[str]:
        clean = str(message).strip()
        if not clean:
            return list(self.activity_items)

        if clean == self._last_activity:
            self._repeat_count += 1
            display = f"{clean} (x{self._repeat_count + 1})"
            if self.activity_items:
                timestamp = self.activity_items[0].split("] ", 1)[0].lstrip("[")
                self.activity_items[0] = f"[{timestamp}] {display}"
            return list(self.activity_items)

        self._last_activity = clean
        self._repeat_count = 0
        timestamp = datetime.now().strftime("%H:%M")
        self.activity_items.insert(0, f"[{timestamp}] {clean}")
        self.activity_items = self.activity_items[:limit]
        return list(self.activity_items)
