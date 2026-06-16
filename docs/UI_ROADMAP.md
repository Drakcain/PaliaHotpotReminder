# UI Roadmap

This document tracks the current HPR UI rules and the deferred CustomTkinter
modernization direction. It is planning documentation only; no production UI
migration is approved in the current release.

## Current UI State

- Production UI is Python/Tkinter.
- Styling is centralized through `src\theme.py`.
- `src\ui.py` should read theme values from `src\theme.py`.
- `theme` remains a persisted config value and defaults to `dark`.
- Dark Mode requests the native Windows dark title bar on supported builds while
  preserving the standard window frame and controls.

## Theme Direction

### Dark Mode

- Window background: `#000000`
- Panel background: `#0B0B0F`
- Raised panel background: `#111217`
- Field background: `#050505`
- Primary text: `#F5F5F7`
- Secondary text: `#C9CDD6`
- Muted text: `#9BA1AD`
- Border: `#2A2D35`
- Strong border: `#3B3F4A`
- Button background: `#151720`
- Button hover/active: `#1E2230`
- Button text: `#FFFFFF`
- Accent: `#5865F2`
- Good/status text: `#7DD3FC`
- Warning text: `#FACC15`
- Error text: `#F87171`

### Light Mode

Keep the same layout and contrast rules, but use a readable bright theme with
clear panel separation.

## Current Theme Rules

- Keep LabelFrame titles bright and readable.
- Never leave default black widget text on dark backgrounds.
- Keep buttons visibly separated from panels.
- Keep fields darker than panels for clear input distinction.
- Apply the theme consistently to the main window, scroll area, panels, labels,
  buttons, checkboxes, and entry fields.
- Prefer small centralized theme changes over ad hoc per-widget color tweaks.

## CustomTkinter Modernization Notes

Future visual reference:

- https://github.com/TomSchimansky/CustomTkinter
- https://customtkinter.tomschimansky.com/documentation/
- https://github.com/TomSchimansky/CustomTkinter/blob/master/documentation_images/complex_example_dark_Windows.png

The target direction is a modern dark desktop dashboard inspired by the official
CustomTkinter complex example:

- persistent left navigation
- rounded, clearly separated cards
- compact status summaries
- modern switches and buttons
- strong dark-panel contrast
- restrained blue accent color
- readable spacing at Windows display scaling above 100%

This is visual inspiration, not a request to copy the example layout or replace
HPR's identity.

## Proposed Future Layout

Sidebar:

- Dashboard
- Clock Setup
- Reminders
- Diagnostics
- Settings

Dashboard cards:

- Clock status
- Reminder status
- Quick actions
- Runtime health

Settings and diagnostics should remain available without crowding the beginner
Dashboard path.

## Asset And Branding Rules

- App icon assets live under `assets\App Icon`.
- Repository branding assets live under `assets\Branding`.
- Popup/message board art lives under `assets\Message Board`.
- Do not flatten the organized asset folders.
- Preserve legacy asset path compatibility until all callers use the organized
  paths.

## Deferred Ideas

- Isolated CustomTkinter visual prototype under `prototypes\customtkinter_ui`.
- Static sample data only for the first prototype.
- No production callbacks, config writes, OCR, tray, reminder, or process
  detection inside the prototype.
- Dark and light appearance checks.
- 100%, 125%, and 150% Windows scaling checks.

## Do Not Change Without Testing

Do not change these as part of UI modernization without full regression testing:

- OCR or Tesseract behavior.
- Clock setup replacement semantics.
- Reminder calculations or timing.
- Tray lifecycle or menu behavior.
- `psutil` process detection.
- Settings keys or file format.
- Runtime logging or debug report content.
- Single-instance behavior.
- Installed folder structure.
- Passive external safety boundaries.

## Acceptance Criteria For Future Migration

- The UI visibly follows the selected modern dark dashboard direction.
- Every current user action has an obvious destination.
- Beginner actions remain prominent.
- Advanced diagnostics remain available.
- Keyboard navigation and readable contrast are preserved.
- The app remains usable at 125% and 150% Windows scaling.
- Source and packaged behavior match.
- No backend regression is introduced.
