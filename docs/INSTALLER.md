# PaliaHotpotReminder Installed Mode

## Purpose
`v2.9` transitions PaliaHotpotReminder to an installed-first Windows utility, matching the BD-AUTO-style distribution model.

Normal users should use:

```text
PaliaHotpotReminder-Setup-v2.9.exe
```

## Install Path
The installer targets:

```text
C:\Tools\PaliaHotpotReminder
```

Main executable:

```text
C:\Tools\PaliaHotpotReminder\Hotpot-Remind.exe
```

## Shortcuts
- Start Menu folder: `Palia Hotpot Reminder`
- Start Menu shortcut: `Palia Hotpot Reminder`
- Optional Desktop shortcut controlled by the installer checkbox
- Optional launch-after-install checkbox

The shortcut working directory is the install folder so relative config, asset, and Tesseract paths resolve correctly.

## Build Requirements
- Windows 64-bit
- Python 3.12
- Inno Setup 6

Install Inno Setup if needed:

```powershell
winget install JRSoftware.InnoSetup
```

## Build Process
From the repo root:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\Test-Repo.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_installer.ps1
```

Expected outputs:

```text
dist\PaliaHotpotReminder-Setup-v2.9.exe
dist\PaliaHotpotReminder-Setup-v2.9.exe.sha256
```

The build script stages app files under `build\installer-payload` for Inno Setup. That staging folder is disposable and is not a release artifact.

## Upgrade Behavior
The installer updates app files but preserves personal runtime data:

```text
config\settings.json
config\recall_state.json
logs\
debug\
exports\
```

`config\settings.example.json` may be updated by new releases. `config\settings.json` is only installed when missing.

## Uninstall Behavior
The installer creates a normal Windows uninstall entry. User runtime data is not aggressively deleted by default, so support logs, exports, and personal settings can survive uninstall/reinstall workflows.

## Safety Boundary
Installer support does not change the runtime safety model:
- no game memory reading
- no injection or hooking
- no network inspection
- no gameplay automation
- no game file edits
- OCR selected screen region only

## Not Included
- No forced Start with Windows task
- No AppData migration
- No GitHub release upload
- No source ZIP release path
