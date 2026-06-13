# PaliaHotpotReminder v2.8

## Title
Smart Resume + Local Recall + Tray Restore Hardening

## Release Artifact
- File: `PaliaHotpotReminder-v2.8-portable.zip`
- SHA-256: `5A9EF47E2C55FB1B1FF322326A6FED1300E5248D6DBB3641CFEA7028FF2A0165`

## Main Fixes
- Smart Resume after tray restore and refocus.
- Local Recall for safe operational state.
- Async `Setup Clock`.
- Canceling `Setup Clock` restores the prior config state.
- `Test Clock` preserves reminder/watch state.
- Single-instance guard.
- Timer deduplication.
- Clean portable package baseline.

## Safety Notes
- Windows portable release.
- Does not modify Palia.
- Does not read game memory.
- Does not inject or hook.
- Does not automate gameplay.
- Only OCRs the user-selected on-screen clock region.

## Known Limitations
- Windows portable release only.
- User must run `Setup Clock` at least once per PC or monitor layout.
