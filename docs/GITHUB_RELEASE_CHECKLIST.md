# GitHub Release Checklist

## Before Tagging
- Run source self-test or normal local validation.
- Run installer build validation.
- Confirm the installer hash matches the intended release hash.
- Confirm the installer installs the expected app payload.
- Confirm no personal config, logs, recall state, or debug artifacts are being committed.

## GitHub Steps
- Create tag `v2.9`.
- Create GitHub Release for `v2.9`.
- Upload `PaliaHotpotReminder-Setup-v2.9.exe`.
- Upload `PaliaHotpotReminder-Setup-v2.9.exe.sha256`.
- Paste the contents of `docs/RELEASE-NOTES-v2.9.md`.
- Include SHA-256 hashes generated during release validation.
