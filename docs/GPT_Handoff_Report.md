# Detailed Handoff Report: Palia (Steam) Clock-Based Hotpot Reminder

## 1) Mission
Build a standalone Windows external passive reminder app (`PaliaHotpotReminder.exe`) that:
- OCRs only the user-defined in-game clock region.
- Uses confirmed time when visible.
- Uses estimated time when the clock is hidden.
- Sends popup reminders only.

## 2) Core Product Decisions (Locked)
- Platform: Windows native (not WSL).
- Input: Screen capture of small clock rectangle only.
- Detection model: Binary
  - Clock readable -> Confirmed mode
  - Clock unreadable -> Estimated mode
- No detection of specific game activity (Hotpot/fishing/menu/etc.).
- No sound, no overlay, no automation.

## 3) Safety/Compliance Guardrails
Hard constraints:
- No modification of Palia files/process.
- No memory reads, injection, DLL hooks, packets.
- No auto input (clicking/typing) into game.
- No card parsing or gameplay solver logic.

## 4) Functional Requirements
- Buttons:
  - Start Watching
  - Stop Watching
  - Set Clock Region
  - Test Popup
- Status outputs:
  - Palia Time (`hh:mm AM/PM`)
  - Mode (`Confirmed | Estimated | Unknown | Stale`)
  - Hotpot Status (`Soon | Active | Not active`)
- Behavior:
  - On readable OCR clock: resync time source immediately.
  - On unreadable clock: estimate forward from last confirmed anchor.
  - If hidden too long: `Stale` until next successful resync.

## 5) Technical Foundation Already Prepared
Project root:`n- `C:\GITHUB BUILDS\PC Game Tools\Mods\PaliaHotpotReminder`

Created files:
- `README.md`
- `requirements.txt`
- `config/settings.example.json`
- `docs/GPT_Handoff_Report.md`
- `src/` (empty scaffold)

Dependencies pinned for first pass (in requirements):
- `mss` (screen capture)
- `pillow` (image prep)
- `pytesseract` (OCR binding)
- `winotify` (Windows notifications)
- `pyinstaller` (exe packaging)

System prerequisites confirmed by user:
- Python 3.12 installed
- Git installed
- Tesseract OCR installed (UB-Mannheim)

## 6) Data Model Proposal
`settings.json`
- `clock_region`: `{left, top, width, height}`
- `palia_time_scale`: integer (default `6`; 1 real min = 6 Palia mins)
- `stale_timeout_seconds`: integer (default `900`)
- `reminder_minutes`: list of daily Palia trigger times (24h strings, e.g. `17:50`, `18:00`)
- `notifications.enabled`: bool
- `notifications.sound`: bool (false in v1)

Runtime state:
- `last_confirmed_palia_dt`
- `last_confirmed_real_dt`
- `current_mode`
- `last_ocr_raw`
- `last_successful_read_real_dt`

## 7) OCR Strategy
- Capture only `clock_region` with `mss`.
- Preprocess image:
  - grayscale
  - contrast boost
  - threshold
  - optional scale-up 2x
- Tesseract config tuned for short strings (`--psm 7`).
- Parse regex:
  - `^(1[0-2]|[1-9]):[0-5][0-9]\s?(AM|PM)$`
- If parse fails N consecutive times, treat as hidden.

## 8) Time Estimation Logic
When confirmed:
- Parse OCR clock to Palia time today.
- Save anchor:
  - `last_confirmed_palia_dt = parsed`
  - `last_confirmed_real_dt = now`
- Mode = `Confirmed`

When hidden:
- If no anchor -> `Unknown`
- Else:
  - `elapsed_real_minutes = (now - last_confirmed_real_dt).total_seconds()/60`
  - `elapsed_palia_minutes = elapsed_real_minutes * palia_time_scale`
  - `estimated = last_confirmed_palia_dt + elapsed_palia_minutes`
  - Mode = `Estimated`
- If `(now - last_successful_read_real_dt) > stale_timeout_seconds`: Mode = `Stale`

## 9) Reminder Engine (v1)
- Poll loop every 0.5-1.0 seconds.
- Derive current Palia hh:mm each loop.
- Fire popup once per trigger minute (debounce by key `date+minute`).
- Example popup:
  - Title: `Hotpot Reminder`
  - Body: `Hotpot time is starting soon. Estimated Palia time: 6:00 PM`

## 10) UI Recommendation
Simple Tkinter desktop app:
- Minimal controls and labels.
- Keep window always normal (not overlay).
- Optional small log box for OCR debug.

## 11) Milestone Plan for GPT
1. Implement config loader/saver and defaults.
2. Implement region picker (`Set Clock Region`) and persist selection.
3. Implement OCR loop for configured region.
4. Implement mode switching and estimator.
5. Implement reminder trigger engine + popup.
6. Implement packaging script for PyInstaller.
7. Add defensive error handling and status messages.

## 12) Acceptance Criteria
- App can be started/stopped reliably.
- User can set clock region once and reuse it.
- While open world clock visible: mode stays `Confirmed` and reads valid times.
- While clock hidden: mode switches to `Estimated` and time continues smoothly.
- After long hidden interval: mode can show `Stale`.
- Popup reminders trigger at configured Palia times without duplicates.
- No game automation or invasive behavior.

## 13) Known Risks + Mitigations
- OCR misses due to font/brightness/UI scaling.
  - Mitigate with preprocessing and per-user region calibration.
- Wrong region selection.
  - Mitigate with `Test Read` helper and reset region button (next step).
- Multi-monitor coordinate mismatch.
  - Mitigate by storing monitor index and normalized coordinates later.

## 14) Next Build Request You Can Give GPT
"Implement v1 in Python under this project scaffold. Start with clock region calibration, then OCR + mode state machine + popup reminders. Keep code modular (`src/config.py`, `src/ocr.py`, `src/time_model.py`, `src/notifier.py`, `src/app.py`)."


## 15) Workspace Clarification
- This project is an external desktop reminder app.
- It is NOT a real Palia mod folder.
- Mods is a personal organization label only.

