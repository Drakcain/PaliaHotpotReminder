# Security

Current release: v3.1.1

## Reporting

Report suspected security issues through GitHub Issues or the repository's
security reporting tools. Do not post secrets, private logs, personal screenshots,
or full support bundles publicly.

## Credentials

PaliaHotpotReminder does not need:

- Palia account credentials
- game credentials
- Discord credentials
- API keys
- tokens

Never enter game credentials into PaliaHotpotReminder.

## Scope

PaliaHotpotReminder is an external desktop helper. It does not:

- modify Palia
- edit game files
- read game memory
- inject or hook
- inspect network traffic
- automate gameplay
- click, press keys, or control the mouse

It only reads the user-selected visible clock region on the screen through screen
capture and OCR.

## Support Data

`config/settings.json` can contain personal screen-region coordinates and local
preferences. Debug exports may include OCR diagnostics and local runtime state.
Treat these files as personal support data.

Before sharing support material publicly, review it and remove anything personal.
