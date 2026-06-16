# CustomTkinter UI Modernization Plan

Status: Research and design groundwork only  
Current release candidate: v2.9
Implementation approval: Not yet granted

## Reference Direction

- Library: https://github.com/TomSchimansky/CustomTkinter
- Visual reference: https://github.com/TomSchimansky/CustomTkinter/blob/master/documentation_images/complex_example_dark_Windows.png
- Official documentation: https://customtkinter.tomschimansky.com/documentation/

The target is a modern dark desktop dashboard inspired by the official
`complex_example.py` screenshot:

- persistent left navigation
- rounded, clearly separated cards
- compact status summaries
- modern switches and buttons
- strong dark-panel contrast
- restrained blue accent color
- readable spacing at Windows display scaling above 100%

This is visual inspiration, not a request to copy the example layout or replace
HPR's identity.

## Why It Fits HPR

CustomTkinter stays within the Python/Tkinter ecosystem and can coexist with
normal Tkinter widgets. It provides modern widgets, light/dark appearance modes,
and Windows HighDPI scaling without requiring a move to C#, Qt, or a web UI.

The migration risk is moderate because HPR's current UI and application behavior
are concentrated in `src/ui.py`. The safe path is to prove a separate UI shell
before connecting it to production callbacks.

## Proposed HPR Layout

### Sidebar

- Dashboard
- Clock Setup
- Reminders
- Diagnostics
- Settings

The sidebar should also show:

- HPR name and version
- Palia detected/not detected
- watcher running/stopped
- compact tray status

### Dashboard

- Clock status card
  - mode
  - detected/estimated Palia time
  - clock setup status
- Reminder status card
  - reminders enabled
  - next reminder
  - last reminder
- Quick actions
  - Setup Clock
  - Start/Stop Watch
  - Test Popup
- Runtime health card
  - Palia process state
  - OCR/Tesseract state
  - tray state

### Clock Setup

- Setup Clock action and explanation
- current saved region
- setup state
- preview/diagnostic controls
- advanced coordinate controls in a clearly labeled secondary area

### Reminders

- reminder enable switch
- Hotpot window and warning times
- popup style and test actions
- reminder status/details

### Diagnostics

- Debug Report
- Export Debug Report
- Copy Debug Report
- Open Logs Folder
- Open latest.log
- screen and OCR diagnostics

### Settings

- Start with Windows
- Auto-arm when Palia opens
- Start hidden in tray
- Minimize to tray
- Close to tray
- theme/appearance
- debug logging controls

## Locked Boundaries

The prototype and migration must not change:

- OCR or Tesseract behavior
- clock setup replacement semantics
- reminder calculations or timing
- tray lifecycle or menu behavior
- psutil process detection
- settings keys or file format
- runtime logging or debug report content
- single-instance behavior
- installed folder structure
- passive/external safety boundaries

The production `PaliaHotpotReminderUI` remains the active UI until a prototype
passes all acceptance checks.

## Prototype Strategy

Create a separate, non-production prototype module. It should use static sample
data and no production callbacks.

Recommended future location:

`prototypes/customtkinter_ui/`

The prototype should:

- reproduce the current HPR information architecture
- use the official complex dark example as the visual reference
- contain no OCR, tray, reminder, config-write, or process-detection code
- make no changes to the production entry point
- use fake status values for layout evaluation
- demonstrate both dark and light appearance modes
- demonstrate 100%, 125%, and 150% Windows scaling

Do not add `customtkinter` to the production dependency list during the visual
prototype. Use prototype-specific setup notes until migration is approved.

## Migration Strategy

If the prototype is approved:

1. Define a small UI callback/state contract around the existing backend
   behavior.
2. Add a production CustomTkinter view without deleting the current Tkinter UI.
3. Connect one screen at a time, starting with read-only Dashboard state.
4. Connect Clock Setup and verify the released replacement/rollback behavior.
5. Connect Reminders, Diagnostics, Settings, and tray callbacks.
6. Run full source and installer regression checks.
7. Remove the old UI only after the new UI passes release acceptance.

Avoid a mixed long-term UI where arbitrary parts of the same screen use both
widget libraries. Temporary coexistence is acceptable only during migration.

## Packaging Requirements

HPR already uses PyInstaller `--onedir`, which is compatible with the documented
CustomTkinter packaging approach. A future build must also include
CustomTkinter's package data, including its theme JSON and font resources.

The prototype must prove:

- source launch works
- installed EXE launch works
- CustomTkinter package data is present
- dark/light appearance works in the packaged app
- Windows scaling does not clip controls
- `Hotpot-Remind.ico` and native dark title bar still work
- no console window appears
- startup and tray behavior are unchanged

Do not adopt CustomTkinter in production until the packaged prototype passes.

## Acceptance Criteria

- The UI visibly follows the selected modern dark dashboard direction.
- Every current user action has an obvious destination.
- Beginner actions remain prominent.
- Advanced diagnostics remain available without crowding the Dashboard.
- Keyboard navigation and readable contrast are preserved.
- The app remains usable at 125% and 150% Windows scaling.
- Source and packaged behavior match.
- No backend regression is introduced.

## Roadmap Recommendation

- v2.8: Smart Resume + Local Recall + Debug / Support finalization
- v2.9: installer wizard + `C:\Tools\PaliaHotpotReminder` layout
- v3.0: isolated CustomTkinter visual prototype or later release status, depending on priority
- Later: production migration only if the isolated prototype passes

This roadmap can be reordered later, but the prototype must remain separate from
the stable production UI.
