from __future__ import annotations

import atexit
import ctypes
import logging


class SingleInstanceGuard:
    def __init__(self, name: str) -> None:
        self.name = name
        self._handle = None
        self.logger = logging.getLogger(__name__)

    def acquire(self) -> bool:
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.CreateMutexW(None, False, self.name)
        if not handle:
            self.logger.warning("Single-instance mutex creation failed for %s", self.name)
            return True
        self._handle = handle
        if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
            self.logger.info("Another instance is already running (%s)", self.name)
            self.release()
            return False
        atexit.register(self.release)
        return True

    def release(self) -> None:
        if not self._handle:
            return
        try:
            ctypes.windll.kernel32.CloseHandle(self._handle)
        except Exception:
            pass
        self._handle = None
