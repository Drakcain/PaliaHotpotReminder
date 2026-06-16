# Release Process

PaliaHotpotReminder is an installer-first Windows utility. Normal releases
publish the Inno Setup installer and its checksum only.

## Release Truth

- Current version: `v3.1`
- Primary artifact: `PaliaHotpotReminder-Setup-v3.1.exe`
- Checksum artifact: `PaliaHotpotReminder-Setup-v3.1.exe.sha256`
- Install target: `C:\Tools\PaliaHotpotReminder`
- Main executable: `C:\Tools\PaliaHotpotReminder\Hotpot-Remind.exe`

Portable ZIP files are not the normal release path.

Installer upgrades should pre-close `Hotpot-Remind.exe` before file
replacement. The installer targets only HPR's own EXE and does not target
Palia or unrelated processes.

## Before Publishing

Run the repository and build validation from the repo root:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\Test-Repo.ps1
py -3.12 -m compileall -q src
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_installer.ps1
git diff --check
```

Confirm:

- The installer builds successfully.
- The installer hash file matches the built installer.
- No generated artifacts are staged for source commits.
- No personal config, recall state, logs, debug files, or support exports are tracked.
- The release tag points to the intended commit.
- The safety boundary is unchanged.
- The installer installs the expected payload.
- Install and uninstall were manually tested before calling the release fully passed.

## GitHub Publishing

For `v3.1`, publish these release assets:

```text
PaliaHotpotReminder-Setup-v3.1.exe
PaliaHotpotReminder-Setup-v3.1.exe.sha256
```

Use `docs\CHANGELOG.md` as the source of release history and release-note facts.
Release notes may summarize the current version, but they should not contradict
the changelog, installer target, or safety boundary.

## Safety Boundary

Each release must preserve these claims:

- No Palia memory reading.
- No injection or hooking.
- No network inspection.
- No gameplay automation.
- No game file edits.
- Only OCRs the user-selected visible clock region.

## Do Not Publish

- Do not publish a portable ZIP as the normal release artifact.
- Do not publish local config, logs, debug exports, recall state, or screenshots.
- Do not claim code signing exists unless Authenticode signing is actually in use.
- Do not claim official Palia, Singularity 6, or Daybreak affiliation.
