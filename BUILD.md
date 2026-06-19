# Building PaliaHotpotReminder

Current release: v3.1.5

## Requirements

* Windows 10/11
* PowerShell 5.1 or later
* Python 3.12
* Inno Setup 6
* Git

Install Inno Setup with:

```powershell
winget install --id JRSoftware.InnoSetup -e
```

`winget` is only a convenience for developers installing Inno Setup. The produced PaliaHotpotReminder installer does not require `winget`.

## Validate

From the repository root:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\Test-Repo.ps1
py -3.12 -m compileall -q src
```

The validation checks:

* required professional repository files
* installed-first documentation references
* installer target and runtime-data preservation rules
* organized asset folders
* legacy asset path compatibility
* absence of tracked generated/runtime files
* HPR safety-boundary documentation

## Build Installer

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_installer.ps1
```

Expected output for the current release line:

```text
dist\PaliaHotpotReminder-Setup-v3.1.5.exe
dist\PaliaHotpotReminder-Setup-v3.1.5.exe.sha256
```

The build script validates the repository, builds the Python/Tkinter app with PyInstaller, stages installer payload files under ignored `build\`, bundles local Tesseract OCR, and compiles the Inno Setup installer.

## Release Model

PaliaHotpotReminder is installer-first.

Normal GitHub Releases should publish:

```text
PaliaHotpotReminder-Setup-v3.1.5.exe
PaliaHotpotReminder-Setup-v3.1.5.exe.sha256
```

Do not reintroduce a portable ZIP as the normal release path.

## Do Not Commit

* `dist/`
* `build/`
* logs
* debug exports
* `config/settings.json`
* `config/recall_state.json`
* generated installers, ZIPs, checksum files, or local runtime state
