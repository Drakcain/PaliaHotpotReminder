# GitHub Release Checklist

## Before Tagging
- Run source self-test or normal local validation.
- Run packaged self-test on the portable build.
- Confirm the final ZIP hash matches the intended release hash.
- Confirm the ZIP contents are clean and portable.
- Confirm no personal config, logs, recall state, or debug artifacts are being committed.

## GitHub Steps
- Create tag `v2.8`.
- Create GitHub Release for `v2.8`.
- Upload `PaliaHotpotReminder-v2.8-portable.zip`.
- Paste the contents of `docs/RELEASE_NOTES-v2.8.md`.
- Include SHA-256: `5A9EF47E2C55FB1B1FF322326A6FED1300E5248D6DBB3641CFEA7028FF2A0165`
