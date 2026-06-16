# PaliaHotpotReminder v2.9

## Distribution Change
`v2.9` transitions PaliaHotpotReminder from a portable-first utility to an installed-first Windows utility.

Primary release artifact:

```text
PaliaHotpotReminder-Setup-v2.9.exe
```

Primary install path:

```text
C:\Tools\PaliaHotpotReminder
```

## Added
- Added an Inno Setup installer wizard.
- Added install target `C:\Tools\PaliaHotpotReminder`.
- Added Start Menu shortcut support.
- Added optional Desktop shortcut support.
- Added optional launch-after-install support.
- Added installer-only build script at `scripts\build_installer.ps1`.
- Added installer documentation at `docs\INSTALLER.md`.
- Added repository validation script at `scripts\Test-Repo.ps1`.

## Preserved
- `Hotpot-Remind.exe` remains the run target.
- User runtime data is preserved on installer upgrades where possible:
  - `config\settings.json`
  - `config\recall_state.json`
  - `logs\`
  - `debug\`
  - `exports\`

## Safety Boundary
- No gameplay automation was added.
- No game memory reading was added.
- No injection, hooking, network inspection, or game file edits were added.
- HPR remains an external helper app that OCRs only the user-selected clock region.

## Expected Artifacts
```text
dist\PaliaHotpotReminder-Setup-v2.9.exe
dist\PaliaHotpotReminder-Setup-v2.9.exe.sha256
```
