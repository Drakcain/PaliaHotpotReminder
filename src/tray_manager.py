from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, Optional

try:  # pragma: no cover - optional tray dependency
    import pystray
    from PIL import Image, ImageDraw
    try:
        from winotify import Notification
    except Exception:  # pragma: no cover - optional tray dependency
        Notification = None
except Exception:  # pragma: no cover - optional tray dependency
    pystray = None
    Image = None
    ImageDraw = None
    Notification = None


def _generate_fallback_icon():
    if Image is None or ImageDraw is None:
        return None
    image = Image.new("RGBA", (64, 64), (18, 18, 24, 255))
    draw = ImageDraw.Draw(image)
    draw.ellipse((10, 10, 54, 54), fill=(88, 101, 242, 255))
    draw.text((23, 18), "H", fill=(255, 255, 255, 255))
    return image


def tray_available() -> bool:
    return pystray is not None and Image is not None


class TrayManager:
    def __init__(
        self,
        root,
        settings: dict,
        icon_path: Optional[Path],
        on_restore: Callable[[], None],
        on_exit: Callable[[], None],
        on_start_reminders: Callable[[], None],
        on_stop_reminders: Callable[[], None],
        on_test_popup: Callable[[], None],
        on_setup_clock: Callable[[], None],
        on_hide: Callable[[], None],
    ) -> None:
        self.root = root
        self.settings = settings
        self.icon_path = icon_path
        self.on_restore = on_restore
        self.on_exit = on_exit
        self.on_start_reminders = on_start_reminders
        self.on_stop_reminders = on_stop_reminders
        self.on_test_popup = on_test_popup
        self.on_setup_clock = on_setup_clock
        self.on_hide = on_hide
        self.icon = None
        self.is_exiting = False
        self._notification_sent = False
        self.logger = logging.getLogger(__name__)

    def supported(self) -> bool:
        return tray_available()

    def start(self) -> bool:
        if not self.supported():
            return False
        if self.icon is not None:
            return True
        image = self._load_icon_image()
        if image is None:
            return False

        menu = pystray.Menu(
            pystray.MenuItem("Show HPR", lambda *args: self.restore(), default=True),
            pystray.MenuItem("Hide HPR", lambda *args: self.hide()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Start Reminder", lambda *args: self._dispatch(self.on_start_reminders)),
            pystray.MenuItem("Stop Reminder", lambda *args: self._dispatch(self.on_stop_reminders)),
            pystray.MenuItem("Test Popup", lambda *args: self._dispatch(self.on_test_popup)),
            pystray.MenuItem("Setup Clock", lambda *args: self._dispatch(self.on_setup_clock)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit HPR", lambda *args: self.exit()),
        )
        self.icon = pystray.Icon("PaliaHotpotReminder", image, "Palia Hotpot Reminder", menu)
        try:
            self.icon.run_detached()
        except Exception as exc:
            self.logger.warning("Tray icon failed to start: %s", exc)
            self.icon = None
            return False
        return True

    def _load_icon_image(self):
        if self.icon_path is not None and self.icon_path.exists():
            try:
                return Image.open(self.icon_path)
            except Exception:
                self.logger.warning("Tray icon file invalid: %s", self.icon_path)
        return _generate_fallback_icon()

    def _dispatch(self, callback: Callable[[], None]) -> None:
        try:
            self.root.after(0, callback)
        except Exception as exc:
            self.logger.debug("Skipped tray callback during shutdown: %s", exc)

    def minimize(self) -> None:
        self._dispatch(self.on_hide)
        self.start()

    def hide(self) -> None:
        self._dispatch(self.on_hide)
        self.start()

    def restore(self, icon=None, item=None) -> None:
        self._dispatch(self.on_restore)

    def exit(self, icon=None, item=None) -> None:
        self._dispatch(self._exit_on_tk_thread)

    def _exit_on_tk_thread(self) -> None:
        self.is_exiting = True
        self.stop()
        self.on_exit()

    def stop(self) -> None:
        if self.icon is None:
            return
        try:
            self.icon.stop()
        except Exception:
            pass
        self.icon = None

    def notify_once(self, message: str) -> None:
        if self._notification_sent:
            return
        if not bool(self.settings.get("show_tray_notifications", True)):
            return
        if Notification is None:
            return
        try:
            notification = Notification(app_id="PaliaHotpotReminder", title="Palia Hotpot Reminder", msg=message)
            notification.show()
            self._notification_sent = True
        except Exception as exc:
            self.logger.debug("Tray notification unavailable: %s", exc)
