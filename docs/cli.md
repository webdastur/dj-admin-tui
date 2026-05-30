# Command-line reference

The TUI is launched by a single management command — the only externally
observable entry point.

## Synopsis

```text
python manage.py admin_tui [--user USERNAME] [--app DOTTED_PATH]
                           [--theme PATH] [--theme-name NAME]
                           [--no-color] [--debug]
```

## Arguments

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--user USERNAME` | str | the lone active superuser | The Django user whose permissions and audit attribution the session uses. Must be active and `is_staff`. |
| `--app DOTTED_PATH` | import path | `ADMIN_TUI["APP_CLASS"]` | The `AdminTuiApp` subclass to launch. |
| `--theme PATH` | path | `ADMIN_TUI["THEME"]` | A Textual `.tcss` applied via `App.CSS_PATH`, layered on the selected theme. |
| `--theme-name NAME` | str | `ADMIN_TUI["THEME_NAME"]` (→ `django-dark`) | The colour theme to apply. See [theming.md](./theming.md). |
| `--no-color` | flag | off | Textual's no-colour mode (accessibility / SSH terminals). |
| `--debug` | flag | off | Verbose logging to `./.admin_tui_debug.log`. |

Standard Django `BaseCommand` flags (`--settings`, `--pythonpath`,
`--traceback`, `--verbosity`) are honoured.

## `--user` resolution

1. If `--user` is given: resolve by username. Non-existent, inactive, or
   non-staff users are refused (exit code 2).
2. If `--user` is omitted: use the single active staff superuser. Zero or more
   than one → exit code 3 with an actionable message.

All resolution failures print a one-line message to stderr and exit **before**
any screen is rendered (within ~1 second).

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Normal exit (quit / Ctrl-C). |
| 1 | Unexpected error at the top of the app loop (stack trace to stderr). |
| 2 | `--user` resolution failed (missing / inactive / not staff). |
| 3 | Default-superuser resolution failed (none, or more than one). |
| 4 | `--app` could not be imported or isn't an `AdminTuiApp` subclass. |
| 5 | `--theme` isn't a readable `.tcss`, or `--theme-name` isn't registered. |
| 64 | Unrecognised arguments (Django's usage-error default). |

## Examples

```bash
# Default — launch as the single superuser
python manage.py admin_tui

# Explicit user
python manage.py admin_tui --user alice

# A different bundled theme
python manage.py admin_tui --theme-name django

# Reskinned app with a custom .tcss override
python manage.py admin_tui --app myproject.tui.MyAdminTuiApp --theme themes/dark.tcss

# Debug logging
python manage.py admin_tui --debug --user alice
```
