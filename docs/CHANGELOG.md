# Changelog

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
