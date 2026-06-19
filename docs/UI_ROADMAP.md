# UI Roadmap

This document tracks the current HPR UI rules and the v3.1.5 fixed-window modular
CustomTkinter direction.

## Current UI State

- Production UI is Python with a fixed-size modular CustomTkinter runtime shell.
- Styling is centralized through `src\theme.py`.
- `src\ui.py` is the coordinator/controller and should not own large layout
  blocks.
- `src\ui_shell.py` owns the app shell, header, sidebar, page container, and
  active page switching.
- The main window is fixed-size and should not be user-resizable.
- `src\ui_pages\` owns the focused section page layouts.
- `src\ui_state.py` owns UI-only display/activity state.
- `src\ui_actions.py` owns thin UI callback wrappers around existing app
  methods.
- `theme` remains a persisted config value and defaults to `dark`.
- Dark Mode requests the native Windows dark title bar on supported builds while
  preserving the standard window frame and controls.

## Theme Direction

### HPR High-Contrast Black Purple

- Window background: `#000000`
- Panel background: `#050509`
- Card background: `#080812`
- Raised panel background: `#0D0A14`
- Field background: `#000000`
- Primary text: `#FFFFFF`
- Secondary text: `#E8E1FF`
- Muted text: `#A99BC8`
- Border: `#2B174D`
- Strong border: `#8A5CFF`
- Button background: `#5E3AA8`
- Button hover/active: `#B07CFF`
- Button text: `#FFFFFF`
- Accent: `#8A5CFF`
- Good/status text: `#65E572`
- Warning text: `#FFD166`
- Error text: `#FF5C8A`

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

The v3.1.5 direction is a black/purple desktop dashboard inspired by the official
CustomTkinter complex example and the user's black/purple VS Code workspace:

- persistent left navigation
- real page switching
- active sidebar highlight
- rounded, clearly separated cards
- compact status summaries
- modern switches and buttons
- true black shell
- strong purple borders and focus states
- high-contrast white/lavender text
- readable spacing at Windows display scaling above 100%

This is visual inspiration, not a request to copy the example layout or replace
HPR's identity.

## Current Layout

Sidebar:

- Dashboard
- Clock Setup
- Reminders
- Automation
- Diagnostics
- Settings

Dashboard:

- At-a-glance overview only.
- Palia, clock, reminder, automation, and recent activity summary.
- Shortcut buttons that send the user to the correct section page.

Section pages:

- Clock Setup owns Setup Clock, Test Clock, region, nudge, and OCR tools.
- Reminders owns Start/Stop, Test Popup, reminder rules, and popup settings.
- Automation owns startup, auto-arm, tray/window behavior, and shortcut repair.
- Diagnostics owns logs, support exports, activity, and debug details.
- Settings owns theme/window settings and the professional About HPR section.

Dashboard should not become a dump of every control again.

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
