# Nanus UI Design Tokens

Source of truth: `styles.css`.

## Color

- Background: `--bg`, `--app`, `--sidebar`
- Surfaces: `--surface`, `--surface-2`, `--surface-3`, `--elevated`
- Lines: `--line`, `--line-strong`
- Text: `--text`, `--text-soft`, `--muted`, `--faint`
- Actions: `--primary`, `--primary-strong`, `--on-primary`
- States: `--success`, `--warning`, `--danger`
- Accents: `--violet`, `--pink`

Both `dark` and `light` themes are driven by the same semantic variables on `.app-shell[data-theme]`.

## Shape

- Small controls: `--radius-sm` = 8px
- Standard buttons/cards: `--radius-md` = 12px
- Panels: `--radius-lg` = 18px
- Composer surface: `--radius-xl` = 24px

## Interaction

- Focus ring: `--focus`
- Motion: 160-180ms for state changes
- Reduced motion: `prefers-reduced-motion` disables long transitions
- Touch targets: primary icon/text controls are 38-50px high

## Components

- `Sidebar`: persistent desktop navigation, drawer on mobile, collapsible on desktop.
- `ComposerStack`: textarea and recommendations share one joined surface.
- `SkillHub`: tabbed install/review panel with permission review.
- `RunInspector`: active run state, pause/resume, copy log, export actions.
- `SettingsPanel`: theme, execution mode, and density controls.
- `CommandPalette`: searchable command and skill launcher.
- `ToastViewport`: aria-live status feedback for all lightweight actions.
