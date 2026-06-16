from __future__ import annotations

from ui_pages.automation import build_automation_page
from ui_pages.clock_setup import build_clock_setup_page
from ui_pages.dashboard import build_dashboard_page
from ui_pages.diagnostics import build_diagnostics_page
from ui_pages.reminders import build_reminders_page
from ui_pages.settings import build_settings_page


PAGE_BUILDERS = {
    "Dashboard": build_dashboard_page,
    "Clock Setup": build_clock_setup_page,
    "Reminders": build_reminders_page,
    "Automation": build_automation_page,
    "Diagnostics": build_diagnostics_page,
    "Settings": build_settings_page,
}
