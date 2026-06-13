# UI Theme Guide

This app uses a small Tkinter theme layer. Keep the styling centralized and avoid scattering color constants across `ui.py`.

## Palette Targets

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
- Keep the same layout and contrast rules, but use a readable bright theme with standard panel separation.

## Rules

- Keep LabelFrame titles bright and readable.
- Never leave default black widget text on dark backgrounds.
- Keep buttons visibly separated from panels.
- Keep fields darker than panels for clear input distinction.
- Apply the theme consistently to the main window, scroll area, panels, labels, buttons, checkboxes, and entry fields.
- Prefer small, centralized theme changes over ad hoc per-widget color tweaks.

## Implementation Notes

- `src/theme.py` is the palette source of truth.
- `src/ui.py` should read theme values from `src/theme.py`.
- `theme` remains a persisted config value and should continue to default to `dark`.
- When Dark Mode is active, the app should also request the native Windows dark title bar on supported builds, but it must keep the standard window frame and controls.

## Future Modernization Direction

The preferred future visual direction is the official CustomTkinter complex dark
example:

- https://github.com/TomSchimansky/CustomTkinter
- https://github.com/TomSchimansky/CustomTkinter/blob/master/documentation_images/complex_example_dark_Windows.png

The intended HPR interpretation is a left-sidebar dashboard with rounded status
cards, modern switches, clear primary actions, and restrained blue accents.
This is currently research only. Do not add the dependency or migrate production
widgets until the isolated prototype described in
`docs/CUSTOMTKINTER_MODERNIZATION_PLAN.md` passes.
