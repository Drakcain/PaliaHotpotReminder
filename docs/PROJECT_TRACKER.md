# Project Tracker

## Current Task
`v2.8` is complete, validated, and staged as the current portable release. Smart Resume, safe local Smart Recall, tray/refocus recovery, Start Reminder/Test Clock preflight, Debug / Support finalization, asynchronous cancellable Setup Clock, and final portable validation are complete. The confirmed v2.7 parser, tray, process detection, Setup Clock transaction, Palia close/reopen reset, logging, high-contrast Dark Mode, and native dark title bar baselines remain protected.

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

CustomTkinter modernization has been researched and documented as future work.
No production dependency, runtime code, build behavior, or release artifact was
changed for that research. See `docs/CUSTOMTKINTER_MODERNIZATION_PLAN.md`.

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
- Added a transparent cleaned popup asset at `assets\popup_scroll_clean.png` and switched the popup config to use it.
- Added `hotpot_start_time` and `hotpot_end_time` settings for the cross-midnight Hotpot window.
- Added cross-midnight time helpers and warning-target math for 6:00 PM through 3:00 AM.
- Added per-reminder custom popup text support with a user-editable `hotpot_reminder_messages` map.
- Added `max_estimated_reminder_age_seconds` so normal reminders can be suppressed when an estimated clock has gone stale for too long.
- Locked the estimator ratio to `0.4` and hardened invalid ratio recovery back to the safe default.
- Added frozen-mode resource resolution helper so portable builds can load assets, config, and bundled Tesseract from the EXE folder.
- Added a proper Windows ICO asset for the EXE and window icon.
- Fixed bundled OCR invocation to preflight the portable Tesseract engine with explicit `--tessdata-dir`, `lang="eng"`, and bundled `TESSDATA_PREFIX` handling before OCR runs.
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
- Polished the portable release to use a visible `Hotpot-Remind.exe` and matching `Hotpot-Remind.ico` in the extracted release folder.
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
- Added a window icon so the app matches the packaged EXE icon in source and portable mode.

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
- The original `assets\popup_scroll.png` was inspected with Pillow and found to be `RGB` with no alpha channel and zero transparent pixels, so the checkerboard was baked into the file rather than real transparency.
- A cleaned transparent copy was generated with 567,390 background pixels removed from the 1,448 x 1,086 source image.
- The popup window now uses a transparent color key and the canvas background is transparent-keyed as well so only the artwork cutout remains visible.
- A GUI smoke test confirmed the custom popup opens with the cleaned artwork asset and auto-closes successfully.
- A code-path validation of the 5:45 PM reminder branch confirmed one fire followed by cooldown suppression with the new diagnostics.
- Custom reminder text now exists for `5:45 PM`, `6:00 PM`, `12:00 AM`, `2:50 AM`, and `3:00 AM`.
- The portable build script now verifies Python 3.12, installs requirements, verifies bundled Tesseract, builds an onedir EXE, copies assets/config/Tesseract, and writes a portable quick-start file.
- The portable build script now builds the EXE in `--windowed` mode to avoid the black console window.
- Added an installer scaffold for Inno Setup so a per-user installer can be built without removing portable ZIP output.
- The portable build now rewrites the visible release EXE name to `Hotpot-Remind.exe` and updates the root icon name to match.
- The portable release now ships with `theme: dark` by default so new installs open in Dark Mode.
- Dark Mode contrast was increased to avoid muddy gray-on-gray text and keep labels readable on black backgrounds.
- The `assets\app_icon.ico` file was converted into a real multi-size ICO so the EXE icon is reliable in Explorer and PyInstaller.
- The portable ZIP now preserves the release folder root and excludes `desktop.ini` so the archive stays clean after extraction.
- The packaged OCR path now reports bundled engine health clearly before attempting a clock read, so language-load failures surface as plain-English setup guidance instead of a raw OCR crash.
- The main window is now scrollable and resizable so small screens can reach the bottom controls.
- The `Setup Clock` path is beginner-safe and does not save a clock box unless the user confirms the detected time.
- Fresh-extracted portable validation passed from a Desktop test folder with bundled `tesseract.exe --list-langs --tessdata-dir ".\\tesseract\\tessdata"` returning `eng`, and the EXE `--self-test` confirming the extracted app root, assets, config, and bundled tessdata.
- The new auto-arm logic intentionally avoids Palia file access, memory inspection, packet inspection, overlays, or input automation.
- Tray support is optional and falls back safely if the dependency is unavailable.
- Recurring runtime polling now uses `psutil` only; if `psutil` is unavailable the app logs the failure and reports Palia as not detected rather than falling back to shell commands.

## Current Blocker
- No code blocker remains.
- Live Palia-window validation has now been completed by the user: confirmed and estimated clock modes both behaved correctly with the corrected ratio.
- The v2.8 source and packaged EXE self-tests pass.
- HPR-only GUI, tray restore/exit, single-instance, Smart Resume, and Setup Clock cancel validation pass.
- The final portable ZIP has a clean root, clean default settings, no runtime logs/recall state/source files, and a matching Downloads copy.

## Next Safe Step
- Distribute `dist\PaliaHotpotReminder-v2.8-portable.zip` as the current release.
- Keep CustomTkinter modernization as a separate future prototype; do not mix it into the validated v2.8 release.

