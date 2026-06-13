# PaliaHotpotReminder

PaliaHotpotReminder is a portable Windows reminder utility for Palia Hotpot. It uses safe screen OCR on a user-selected clock region so it can track the in-game time and fire reminder popups without modifying the game.

## Current Version
- `v2.8`
- Release ZIP: `PaliaHotpotReminder-v2.8-portable.zip`
- SHA-256: `5A9EF47E2C55FB1B1FF322326A6FED1300E5248D6DBB3641CFEA7028FF2A0165`

## What It Does
- Lets the user select the visible Palia clock region once with `Setup Clock`.
- OCRs only that selected clock area on screen.
- Tracks current hotpot timing state.
- Shows reminder popups for configured hotpot times.
- Supports tray behavior, startup options, Smart Resume, and safe local recall.
- Stays single-instance so duplicate launches do not stack.

## Portable Windows Setup
1. Download `PaliaHotpotReminder-v2.8-portable.zip` from GitHub Releases.
2. Extract the ZIP.
3. Run `Hotpot-Remind.exe`.
4. Open Palia.
5. Click `Setup Clock` once.
6. Click `Start Reminder`.

## Tray Behavior
- `Close to tray` controls the X button.
- `Minimize to tray` controls the minimize button.
- `Show HPR` restores the window from tray.
- `Exit HPR` fully closes the app.

## Safety / TOS Boundary
- Does not modify Palia.
- Does not read game memory.
- Does not inject or hook.
- Does not inspect network traffic.
- Does not automate gameplay.
- Only OCRs the selected clock area on the user’s screen.

## Troubleshooting
- Use `Debug / Support` for OCR checks, state inspection, and support exports.
- `Test Clock` uses the same parser as the live reminder loop.
- If OCR is noisy, export a Debug Report for support.
- `config/settings.json` is local-only and should not be shared as source because it can contain personal clock-region setup.

## Repo Notes
- Tracked template config lives at `config/settings.example.json`.
- Local runtime config should stay untracked at `config/settings.json`.
- Local safe recall state should stay untracked at `config/recall_state.json`.
- Build and release artifacts belong in GitHub Releases, not normal source commits.

## Development
- Source code: `src/`
- Assets: `assets/`
- Build script: `tools/build_portable.ps1`
- Requirements: `requirements.txt`

This project is an external helper utility. It is not a Palia mod, even though the local parent folder uses `Mods` as an organizational label.


