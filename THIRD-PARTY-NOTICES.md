# Third-Party Notices

Current release: v3.0

PaliaHotpotReminder is an independent external helper utility. It is not
affiliated with, authorized by, sponsored by, or endorsed by Palia, Singularity 6,
Daybreak Game Company, or any third-party dependency author.

Palia and related names, artwork, and game content belong to their respective
rights holders.

## Project License Status

No root project license has been selected in this repository yet. Do not assume
permission to redistribute or commercially reuse PaliaHotpotReminder source code
or assets until a license is explicitly added by the project owner.

## Runtime And Build Dependencies

Current Python packages used by the build/runtime:

```text
mss
customtkinter
pillow
pytesseract
winotify
pyinstaller
pystray
psutil
```

These dependencies remain subject to their own licenses and upstream terms.
Review their official package metadata before redistribution.

## OCR Engine

PaliaHotpotReminder uses Tesseract OCR through `pytesseract`. Installed builds
bundle a local Tesseract OCR runtime so normal users do not need to install
Tesseract separately.

Tesseract OCR remains subject to its own upstream licenses and notices.

## Inno Setup

The Windows installer is built with Inno Setup. Review Inno Setup's current
license terms before redistribution or commercial use.

## Safety Boundary

PaliaHotpotReminder does not modify Palia, read game memory, inject code, hook
the game process, inspect network traffic, or automate gameplay. It only reads
the user-selected visible clock region through screen capture and OCR.
