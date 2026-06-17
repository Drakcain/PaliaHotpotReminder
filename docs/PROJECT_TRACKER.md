# Project Tracker

## v3.1.4 Popup Solidification + Clock Hardening

- Finalized popup scaling rules:
  - `3440x1440 -> 800x600`
  - `2560x1440 -> 800x600`
  - `1920x1080 -> 640x480`
  - `3840x2160 -> 1200x900`
- Preserved popup clamp bounds at `640x480` minimum and `1200x900` maximum.
- Finalized popup title/body placement and kept divider lanes stable.
- Split the longer reminder message into two display lines.
- Reworked the footer detail lane into a compact two-line current-time/status readout.
- Hardened top-right monitor-relative Setup Clock region search and acceptance.
- Removed stale screen-diagnostic UI entry points.
- Preserved reminder timing, OCR parser behavior, process watching, tray behavior,
  startup behavior, and installer close-running-HPR logic.
- Target artifact is `PaliaHotpotReminder-Setup-v3.1.4.exe`.

## v3.1.2 Popup Alignment + Reminder Chip Flow

- Moved popup text lower so the reminder body sits in the parchment center.
- Separated footer/detail into its own lower lane so it does not crowd the main
  reminder text.
- Updated the top reminder status chip to use the operator flow:
  - `Reminder: Not Ready`
  - `Reminder: Started`
  - `Reminder: Stopped`
- Preserved reminder timing, OCR, process watching, tray behavior, startup
  behavior, and installer close-running-HPR logic.
- Target artifact is `PaliaHotpotReminder-Setup-v3.1.2.exe`.

## v3.1.1 Fixed-Window UI Polish

- Locked HPR into a fixed-size desktop window.
- Used Clock Setup as the sizing guide for the final shell dimensions.
- Kept full page content visible without relying on a visible full-page
  scrollbar in the fixed-window smoke check.
- Compacted top status chip wording so the header no longer shows clipped `...`.
- Preserved the v3.1 modular UI architecture and the installer close-running-HPR
  upgrade fix.
- Target artifact is `PaliaHotpotReminder-Setup-v3.1.1.exe`.

## v3.1 Modular CustomTkinter UI Architecture

- Checkpointed the successful v3.0 CustomTkinter shell before refactoring.
- Split the runtime UI into a modular shell/page architecture:
  - `src\ui_shell.py`
  - `src\ui_state.py`
  - `src\ui_actions.py`
  - `src\ui_pages\`
- Added real sidebar page navigation for Dashboard, Clock Setup, Reminders,
  Automation, Diagnostics, and Settings.
- Dashboard is now an at-a-glance overview only.
- Section pages now own settings/actions:
  - Clock Setup owns Setup Clock, Test Clock, region, nudge, and OCR state.
  - Reminders owns Start/Stop, Test Popup, reminder rules, and popup settings.
  - Automation owns startup, auto-arm, tray/window behavior, and shortcut repair.
  - Diagnostics owns logs, support actions, activity, and debug details.
  - Settings owns theme/window settings and the professional About HPR section.
- High-Contrast Black + Purple styling remains the active visual direction.
- Existing OCR, reminder, process watcher, tray, startup, logging, debug report,
  and installed-first behavior remain protected.
- Installer hardening now closes a running `Hotpot-Remind.exe` during upgrade so
  file replacement does not stall on the default Inno files-in-use prompt.
- Target artifact is `PaliaHotpotReminder-Setup-v3.1.exe`.

## v3.0 CustomTkinter UI Modernization

- Replaced the classic Tkinter-looking runtime shell with a CustomTkinter shell.
- Applied the `HPR High-Contrast Black Purple` visual direction inspired by the
  user's black/purple VS Code workspace.
- Added dashboard cards, status chips, sidebar navigation, modern switches, and
  a recent activity panel.
- Preserved existing Setup Clock, Test Clock, Start/Stop Reminder, Test Popup,
  Debug / Support, startup, auto-arm, tray, OCR, reminder, process watcher,
  single-instance, and installed-first behavior.
- Added `customtkinter` to the build/runtime dependency list and PyInstaller
  data collection.
- Target artifact was `PaliaHotpotReminder-Setup-v3.0.exe`.

## v2.9 Professional Repo Alignment

- Consolidated final polished documentation:
  - moved release procedure into `docs\RELEASE_PROCESS.md`
  - folded release history into `docs\CHANGELOG.md`
  - folded UI planning and theme direction into `docs\UI_ROADMAP.md`
  - folded durable handoff facts into maintained project docs and removed chat/process debris
- Added BD-AUTO-style root docs for installed-first release hygiene:
  - `BUILD.md`
  - `INSTALL-NOTICE.txt`
  - `SECURITY.md`
  - `SIGNING.md`
  - `THIRD-PARTY-NOTICES.md`
  - `VERSION`
- Added lightweight GitHub issue templates under `.github\ISSUE_TEMPLATE`.
- Updated installer script to show `INSTALL-NOTICE.txt` before install.
- Updated installer script to install `INSTALL-NOTICE.txt`, `THIRD-PARTY-NOTICES.md`, `SIGNING.md`, and `VERSION`.
- Added Start Menu links for third-party notices and signing/Windows warning documentation.
- Strengthened `scripts\Test-Repo.ps1` to validate professional repo files, installed-first language, installer notice/doc wiring, and safety-boundary claims.
- Preserved the HPR safety boundary:
  - no game memory reading
  - no injection or hooking
  - no network inspection
  - no gameplay automation
  - OCR selected screen region only
- Did not add a root `LICENSE`; project license choice remains a required owner decision.

## Current Task
The active pass is `v3.1.4`: popup solidification and clock-detection hardening on
top of the released v3.1 modular CustomTkinter architecture. Smart Resume, safe
local Smart Recall, tray/refocus recovery, Start Reminder/Test Clock preflight,
Debug / Support finalization, and asynchronous cancellable Setup Clock remain
protected.

## v2.9 Installer Behavior
- Added an Inno Setup installer wizard targeting `C:\Tools\PaliaHotpotReminder`.
- Added Start Menu shortcut support for `Palia Hotpot Reminder`.
- Added optional Desktop shortcut support.
- Added optional launch-after-install support.
- Added admin/machine-level installer metadata for the `C:\Tools` target.
- Removed portable ZIP as a release artifact; Inno now consumes a temporary `build\installer-payload` staging folder.
- Preserved runtime data on upgrade where possible: `config\settings.json`, `config\recall_state.json`, `logs`, `debug`, and `exports`.
- Added `scripts\build_installer.ps1` for reproducible installer-only builds and SHA-256 output.
- Added `scripts\Test-Repo.ps1` for repository structure/version/runtime-data validation.
- Added installer documentation and consolidated v2.9 release history in `docs\CHANGELOG.md`.

## v2.8 Smart App Behavior
- Added Smart Resume triggers for startup, tray show, deiconify, focus return, Palia reopen, Start Reminder, Test Clock, and confirmed Setup Clock replacement.
- Added local `config\recall_state.json` storage for safe HPR operational facts only.
- Added readiness states and simple next-action messages for normal users.
- Added capture-path probing and virtual-desktop-safe region validation, including negative monitor coordinates.
- Rejected Test Clock samples no longer mutate confirmed/estimated tracker state.
- Start Reminder now requires current Palia detection, completed setup, a valid region, capture readiness, and OCR preflight.
- Prevented duplicate watcher/detection timers during repeated resume/start cycles.
- Moved OCR, geometry, process, session, logs, and startup repair details into Debug / Support.
- Extended self-test coverage for recall read/write/corruption, readiness decisions, monitor fingerprints, debug report sections, and the full risky parser matrix.
- Packaging excludes runtime recall state and continues to ship a clean setup.

CustomTkinter modernization is now the active v3.1 modular UI direction. See
`docs\UI_ROADMAP.md`.

## What Was Fixed
- Replaced the placeholder Tkinter screen with a real calibration panel.
- Added editable fields for `left`, `top`, `width`, and `height`.
- Added save and reload controls for `config\settings.json`.
- Added preview capture output to `debug\clock_region_latest.png`.
- Added OCR test behavior that only runs on the saved preview image.
- Hardened Tesseract path resolution to validate the configured executable.
- Added a non-blocking Start Watching / Stop Watching loop.
- Added explicit watch modes: `Unknown`, `Confirmed`, `Estimated`, `Stale`.
- Added live tracker display fields for raw OCR, parsed time, confirmed time, estimated time, and seconds since confirmed.
- Added screen diagnostics capture for the full virtual desktop to help resolve coordinate mismatches.
- The live diagnostics now expose monitor count, virtual desktop bounds, and primary monitor geometry.
- Added state-only watch logging to `debug\watch_state_log.txt`.
- Added reminder evaluation and popup support with `winotify` fallback behavior.
- Added a custom popup renderer in `src\custom_popup.py` using the popup asset configured in settings.
- Added a transparent cleaned popup asset at `assets\Message Board\popup_scroll_clean.png` and switched the popup config to use it.
- Added `hotpot_start_time` and `hotpot_end_time` settings for the cross-midnight Hotpot window.
- Added cross-midnight time helpers and warning-target math for 6:00 PM through 3:00 AM.
- Added per-reminder custom popup text support with a user-editable `hotpot_reminder_messages` map.
- Added `max_estimated_reminder_age_seconds` so normal reminders can be suppressed when an estimated clock has gone stale for too long.
- Locked the estimator ratio to `0.4` and hardened invalid ratio recovery back to the safe default.
- Added frozen-mode resource resolution helper so packaged builds can load assets, config, and bundled Tesseract from the EXE folder.
- Added a proper Windows ICO asset for the EXE and window icon.
- Fixed bundled OCR invocation to preflight the packaged Tesseract engine with explicit `--tessdata-dir`, `lang="eng"`, and bundled `TESSDATA_PREFIX` handling before OCR runs.
- Added `--self-test` so the EXE can validate packaged resources and bundled OCR health without needing Palia to run.

## What Was Improved
- Added nudge buttons for:
  - Left / Right / Up / Down by 5 px
  - Left / Right / Up / Down by 25 px
  - Wider / Narrower by 10 px
  - Taller / Shorter by 10 px
- Added visible status fields for:
  - current region
  - detected screen resolution
  - Tesseract path state
- Added watch status and diagnostics fields.
- Added full-screen diagnostic capture/open controls.
- Added Open Preview Image when the debug capture exists.
- Kept the app passive and external.
- The current crop again produced valid OCR during live validation.
- Added unreadable-read tolerance so a single OCR miss does not immediately flip Confirmed into Estimated.
- Added reminder UI fields for enabled state, last fired reminder, next target, reminder status, and reminder details.
- Added a dedicated reminder detail field that shows current mode, current Palia time, reminder target, title, message, next target, cooldown state, reminders_enabled state, popup_style state, ratio, source mode, and hotpot window state.
- Added a simple reminder text row so the active per-time popup copy is visible without building a full message editor, and the idle preview follows the configured Hotpot schedule order.
- Added a visible timing ratio field so the UI shows the exact estimator conversion and max estimated age guard.
- Added a Test Popup button and reminder settings save/reload controls.
- Added a guided `Setup Clock` button that scans likely clock boxes and only saves after user confirmation.
- Added beginner convenience controls for desktop shortcut creation, Start with Windows, auto-arm on Palia process detection, start minimized, and minimize-to-tray.
- Added startup fail-safe controls for status reporting, removal, recreation, and opening the current-user Startup folder.
- Added Windows process-name polling so auto-arm can detect `PaliaClientSteam-Win64-Shipping.exe`, `PaliaClient-Win64-Shipping.exe`, and `Palia.exe` without relying on install paths.
- Replaced recurring process polling with `psutil` so the runtime watcher no longer relies on `tasklist`, `powershell`, or any visible shell helper.
- Added popup settings controls for style, duration, position, asset path, size, and margins.
- Added separate `Test System Popup` and `Test Custom Popup` buttons.
- Added a clear Hotpot Window display in the UI.
- Polished the packaged release to use a visible `Hotpot-Remind.exe` and matching `Hotpot-Remind.ico` in the installed folder.
- Added a simple Dark Mode / Light Mode toggle with dark default packaging.
- Improved Dark Mode into a high-contrast AMOLED / Discord-on-onyx style palette with bright readable text and stronger borders.
- Added a native dark Windows title bar request so the frame better matches the existing Dark Mode styling without replacing the standard window chrome.
- Added an opt-in `Close to tray` setting and tightened tray fallback behavior so the app does not trap the user in an invisible state.
- Added clearer convenience/status reporting for startup shortcut, tray, auto-arm, and reminder-enabled state.
- Added a Minecraft-style file logger with `logs\latest.log` and `logs\previous.log` rotation for startup, tray, watcher, and runtime diagnostics.
- Added low-risk debug tools for opening the logs folder, opening `latest.log`, and copying a debug summary.
- Added a single-instance guard so a second launch exits instead of spawning another copy.
- Hardened `Setup Clock` so a clean temporary session is staged first, old clock data is restored on cancel/failure, and a confirmed new setup atomically replaces the old region.
- Hardened Palia close/reopen handling so session-only OCR, tracker, and reminder state reset when the game closes and a reopened game starts fresh.
- Confirmed the app shell still launches with the current settings.
- Confirmed the custom popup smoke test auto-closes successfully on the left side.
- Confirmed the system popup test still succeeds and reports a notification backend.
- Confirmed the 6:00 PM and 3:00 AM reminder copy renders correctly through the custom popup smoke path.
- Confirmed the system-fallback reminder path receives the same reminder title/message pair.
- Added a reminder text preview row so the active copy is visible in the UI.
- Added a window icon so the app matches the packaged EXE icon in source and installed mode.

## Hardening Added
- Region validation rejects invalid or zero-sized regions.
- Capture errors are surfaced safely in the UI.
- Missing preview image is reported clearly before OCR.
- Invalid Tesseract configuration now reports the exact bad path and fix direction.
- OCR results are treated as wrong region / no readable time unless a strict `h:mm AM/PM` parse succeeds.
- State transitions are explicit and do not estimate unless a valid clock has been confirmed at least once.
- The estimated Palia time wraps cleanly across midnight.
- Live OCR failures now distinguish blank capture, wrong region, missing Tesseract, and capture errors.
- Watch logging records only app state, timestamps, raw OCR, parsed time, and mode.
- Confirmed mode now tolerates a small number of unreadable samples before treating the clock as hidden.
- Reminder decisions are logged without screenshots to `debug\reminder_log.txt`.
- Reminder decisions now log the full decision context, including current time, target time, title, message, next target, cooldown state, popup style, and hotpot window status.
- Reminder decisions now log the Palia time ratio, source mode, estimated Palia time, and seconds since last confirmation.
- Reminder cooldown prevents repeated popups for the same window.
- Unknown mode suppresses reminders.
- Stale mode can show one warning per stale period when enabled.
- Estimated mode now suppresses normal reminders after `max_estimated_reminder_age_seconds` by default when the estimate gets too old.
- The `3:00 AM` end reminder is allowed as a valid trigger even though it lands on the hotpot window boundary.
- Cross-midnight hotpot timing now treats 11:59 PM, 12:00 AM, and 2:59 AM as active while 3:01 AM is inactive.
- Custom popup closes automatically and reuses the left-side desktop placement.
- Missing artwork now falls back to a styled Tkinter popup instead of crashing.
- Custom popup title now renders as `Hotpot` / `Reminder` with the reminder sentence beneath it.
- The popup default vertical position was moved down by roughly an inch for better artwork framing.
- The UI labels were tightened for readability: `Clock State`, `Reminder details`, `Timing ratio`, and `System Status`.
- The live reminder copy can now be read directly from the UI for the next scheduled reminder.
- Added a note in the UI that each PC may need its own clock setup.
- The original `assets\Message Board\popup_scroll.png` was inspected with Pillow and found to be `RGB` with no alpha channel and zero transparent pixels, so the checkerboard was baked into the file rather than real transparency.
- A cleaned transparent copy was generated with 567,390 background pixels removed from the 1,448 x 1,086 source image.
- The popup window now uses a transparent color key and the canvas background is transparent-keyed as well so only the artwork cutout remains visible.
- A GUI smoke test confirmed the custom popup opens with the cleaned artwork asset and auto-closes successfully.
- A code-path validation of the 5:45 PM reminder branch confirmed one fire followed by cooldown suppression with the new diagnostics.
- Custom reminder text now exists for `5:45 PM`, `6:00 PM`, `12:00 AM`, `2:50 AM`, and `3:00 AM`.
- The installer build script now verifies Python 3.12, installs the explicit build/runtime Python package list, verifies bundled Tesseract, builds an onedir EXE, and stages an Inno payload.
- The installer build script now builds the EXE in `--windowed` mode to avoid the black console window.
- Added an Inno Setup installer for `C:\Tools\PaliaHotpotReminder`.
- The installer payload now rewrites the visible release EXE name to `Hotpot-Remind.exe` and updates the root icon name to match.
- The installed release now ships with `theme: dark` by default so new installs open in Dark Mode.
- Dark Mode contrast was increased to avoid muddy gray-on-gray text and keep labels readable on black backgrounds.
- The `assets\App Icon\HPR_Icon.ico` file was converted into a real multi-size ICO so the EXE icon is reliable in Explorer and PyInstaller.
- The installer payload excludes `desktop.ini` and runtime state so the installed app starts clean.
- The packaged OCR path now reports bundled engine health clearly before attempting a clock read, so language-load failures surface as plain-English setup guidance instead of a raw OCR crash.
- The main window is now scrollable and resizable so small screens can reach the bottom controls.
- The `Setup Clock` path is beginner-safe and does not save a clock box unless the user confirms the detected time.
- Packaged validation passed with bundled `tesseract.exe --list-langs --tessdata-dir ".\\tesseract\\tessdata"` returning `eng`, and the EXE `--self-test` confirming the app root, assets, config, and bundled tessdata.
- The new auto-arm logic intentionally avoids Palia file access, memory inspection, packet inspection, overlays, or input automation.
- Tray support is optional and falls back safely if the dependency is unavailable.
- Recurring runtime polling now uses `psutil` only; if `psutil` is unavailable the app logs the failure and reports Palia as not detected rather than falling back to shell commands.

## Current Blocker
- No code blocker remains.
- Live Palia-window validation has now been completed by the user: confirmed and estimated clock modes both behaved correctly with the corrected ratio.
- The v2.8 source and packaged EXE self-tests pass.
- HPR-only GUI, tray restore/exit, single-instance, Smart Resume, and Setup Clock cancel validation pass.
- The final installed-mode payload has clean default settings and no runtime logs, recall state, or source files.

## Next Safe Step
- Run v3.1 repo validation and installer build.
- If Inno Setup is missing, install it with `winget install JRSoftware.InnoSetup` and rerun `scripts\build_installer.ps1`.
- Do not publish v3.1 until the manual UI test checklist passes.
