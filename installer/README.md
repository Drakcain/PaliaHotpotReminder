# PaliaHotpotReminder Installer

The installer is built with Inno Setup and installs the app to:

```text
C:\Tools\PaliaHotpotReminder
```

Build from the repo root:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_installer.ps1
```

The build script stages app files under `build\installer-payload`, compiles `installer\PaliaHotpotReminder.iss`, and writes:

```text
dist\PaliaHotpotReminder-Setup-v2.9.exe
dist\PaliaHotpotReminder-Setup-v2.9.exe.sha256
```

If Inno Setup is missing, install it with:

```powershell
winget install JRSoftware.InnoSetup
```
