# Changelog

## v3.1.5

### Changed

- Hardened the installer build script so Python 3.12 can be resolved from the launcher, registry, or standard install paths instead of failing on a missing `py -3.12` path.
- Preserved the fixed-window CustomTkinter runtime shell and the existing installed-first release model.

### Preserved

- No OCR engine replacement.
- No Palia memory reading, packet inspection, injection, hooks, or gameplay automation.
- No reminder timing, tray/startup behavior, or installer close-running-HPR behavior rewrite.

### Distribution

- Primary release artifact is `PaliaHotpotReminder-Setup-v3.1.5.exe`.
- Checksum artifact is `PaliaHotpotReminder-Setup-v3.1.5.exe.sha256`.

## v3.1.4

### Changed

- Hardened clock OCR confidence for small in-game time reads.
- Added multi-pass Tesseract preprocessing for the Palia clock crop.
- Added a clock-character constrained OCR mode.
- Added left-digit crop protection to reduce `11:MM` being read as `1:MM`.
- Added continuity protection against suspicious time jumps.
- Added missing-leading-digit correction when recent clock continuity strongly
  supports `11:MM` instead of `1:MM`.
- Added repeated-confirmation handling before accepting suspicious OCR candidates.
- Added rejected OCR debug sample capture when debug logging is enabled.
- Polished popup footer/status display into clearer two-line output.

### Preserved

- No OCR engine replacement.
- No BetterOCR, RapidOCR, PaddleOCR, cloud OCR, or LLM OCR.
- No Palia memory reading, packet inspection, injection, hooks, or gameplay
  automation.
- No reminder timing, tray/startup behavior, or installer close-running-HPR
  behavior rewrite.

### Distribution

- Primary release artifact is `PaliaHotpotReminder-Setup-v3.1.4.exe`.
- Checksum artifact is `PaliaHotpotReminder-Setup-v3.1.4.exe.sha256`.

## v3.1.3

### Changed

- Tuned custom popup scaling so 1440p-height displays target `800x600` instead of
  the oversized `1152x864` layout.
- Preserved `640x480` as the minimum popup bound and `1200x900` as the maximum.
- Refined popup title/body placement while keeping the divider lanes stable.
- Split longer reminder body text into two readable display lines.
- Reworked popup footer details into a compact two-line `Current Time` plus
  `Confirmed` or `Estimated` lane.
- Hardened Setup Clock around monitor-relative top-right scanning, faster retry
  cadence, and repeated OCR confirmation before accepting a region.
- Removed the stale screen-diagnostic button path that no longer had live support.

### Preserved

- No OCR parser, reminder timing, process detection, tray behavior, startup
  behavior, or installer close-running-HPR behavior changes.

### Distribution

- Primary release artifact is `PaliaHotpotReminder-Setup-v3.1.3.exe`.
- Checksum artifact is `PaliaHotpotReminder-Setup-v3.1.3.exe.sha256`.

## v3.1.2

### Changed

- Updated the reminder status chip wording to follow the app flow: `Reminder: Not Ready`,
  `Reminder: Started`, and `Reminder: Stopped`.
- Refined the popup board layout so the reminder body sits lower and feels centered
  in the parchment area while footer/detail text stays in its own lower lane.

### Preserved

- No reminder timing, OCR, tray, startup, or installer behavior changes.

### Distribution

- Primary release artifact is `PaliaHotpotReminder-Setup-v3.1.2.exe`.
- Checksum artifact is `PaliaHotpotReminder-Setup-v3.1.2.exe.sha256`.

## v3.1.1

### Fixed-Window UI Polish

- Locked HPR to a fixed-size desktop window and disabled resizing.
- Sized the shell around the Clock Setup page, which remains the densest page.
- Tightened the header layout so status chips stay readable without `...`.
- Switched chip display text to compact UI labels such as `Palia: Offline`,
  `Reminder: Waiting`, and `Clock: Needed`.
- Kept the modular v3.1 CustomTkinter architecture intact.
- Preserved OCR, reminder timing, process watching, tray behavior, startup
  behavior, and installer close-running-HPR logic.

### Distribution

- Primary release artifact is `PaliaHotpotReminder-Setup-v3.1.1.exe`.
- Checksum artifact is `PaliaHotpotReminder-Setup-v3.1.1.exe.sha256`.

## v3.1

### Modular UI Architecture

- Refined the v3.0 CustomTkinter shell into a modular UI architecture.
- Added `src\ui_shell.py`, `src\ui_state.py`, `src\ui_actions.py`, and a real
  `src\ui_pages\` package.
- Added real sidebar page navigation for Dashboard, Clock Setup, Reminders,
  Automation, Diagnostics, and Settings.
- Converted Dashboard into an at-a-glance overview instead of a dump of every
  control.
- Moved clock/OCR controls, reminder controls, automation/tray settings,
  diagnostics, and Settings/About content into focused section pages.
- Added a professional About HPR section with app identity, installer-first
  release facts, support guidance, affiliation disclaimer, and OCR-only safety
  boundary.

### Distribution

- Installer-first distribution remains unchanged.
- Primary release artifact is `PaliaHotpotReminder-Setup-v3.1.exe`.
- Checksum artifact is `PaliaHotpotReminder-Setup-v3.1.exe.sha256`.
- Installs to `C:\Tools\PaliaHotpotReminder`.
- Installer upgrades now pre-close a running `Hotpot-Remind.exe` before file
  replacement, with a graceful-close attempt followed by a force-close fallback
  limited to HPR's own EXE.

### Safety Boundary

- No OCR, reminder, process watcher, tray, startup, or config backend behavior
  was rewritten.
- No gameplay automation was added.
- No game memory reading, injection, hooking, network inspection, or game file
  edits were added.

## v3.0

### UI Modernization

- Introduced a modern CustomTkinter runtime shell.
- Added the `HPR High-Contrast Black Purple` visual direction.
- Replaced the old groupbox-heavy layout with a dashboard shell, sidebar,
  cards, status chips, modern switches, and a recent activity panel.
- Preserved Setup Clock, Test Clock, Start/Stop Reminder, Test Popup, Debug /
  Support, startup, auto-arm, tray, OCR, reminder, and process-watcher behavior.

### Distribution

- Installer-first distribution remains unchanged.
- Primary release artifact is `PaliaHotpotReminder-Setup-v3.0.exe`.
- Checksum artifact is `PaliaHotpotReminder-Setup-v3.0.exe.sha256`.
- Installs to `C:\Tools\PaliaHotpotReminder`.
- Runs from `C:\Tools\PaliaHotpotReminder\Hotpot-Remind.exe`.

### Safety Boundary

- No gameplay automation was added.
- No game memory reading was added.
- No injection, hooking, network inspection, or game file edits were added.
- HPR remains an external helper app that OCRs only the user-selected visible
  clock region.

## v2.9

### Distribution

- Changed PaliaHotpotReminder to an installer-first Windows utility.
- Primary release artifact is `PaliaHotpotReminder-Setup-v2.9.exe`.
- Checksum artifact is `PaliaHotpotReminder-Setup-v2.9.exe.sha256`.
- Installs to `C:\Tools\PaliaHotpotReminder`.
- Runs from `C:\Tools\PaliaHotpotReminder\Hotpot-Remind.exe`.
- Portable ZIP is no longer the normal release path.

### Added

- Added an Inno Setup installer wizard.
- Added Start Menu shortcut support.
- Added optional Desktop shortcut support.
- Added optional launch-after-install support.
- Added installer-only build script at `scripts\build_installer.ps1`.
- Added installer documentation at `docs\INSTALLER.md`.
- Added repository validation script at `scripts\Test-Repo.ps1`.
- Added professional root documentation for build, install notice, security,
  signing, third-party notices, and version truth.
- Organized assets into app icon, branding, and message board folders.

### Preserved

- `Hotpot-Remind.exe` remains the installed run target.
- User runtime data is preserved on upgrades where possible:
  - `config\settings.json`
  - `config\recall_state.json`
  - `logs\`
  - `debug\`
  - `exports\`
- Existing OCR, tray, startup, Smart Resume, debug/support, and single-instance
  behavior remain protected.

### Safety Boundary

- No gameplay automation was added.
- No game memory reading was added.
- No injection, hooking, network inspection, or game file edits were added.
- HPR remains an external helper app that OCRs only the user-selected visible
  clock region.

## v2.8

### Title

Smart Resume + Local Recall + Tray Restore Hardening.

### Release Artifact

- Historical artifact: `PaliaHotpotReminder-v2.8-portable.zip`
- SHA-256: `5A9EF47E2C55FB1B1FF322326A6FED1300E5248D6DBB3641CFEA7028FF2A0165`

### Main Fixes

- Added Smart Resume after tray restore and refocus.
- Added local recall for safe operational state.
- Added asynchronous `Setup Clock`.
- Canceling `Setup Clock` restores the prior config state.
- `Test Clock` preserves reminder/watch state.
- Added single-instance guard.
- Added timer deduplication.
- Established the clean packaged baseline that v2.9 later moved to installer-first.

### Safety Notes

- Does not modify Palia.
- Does not read game memory.
- Does not inject or hook.
- Does not automate gameplay.
- Only OCRs the user-selected on-screen clock region.

### Known Limitations

- Historical v2.8 distribution was Windows portable.
- User must run `Setup Clock` at least once per PC or monitor layout.
