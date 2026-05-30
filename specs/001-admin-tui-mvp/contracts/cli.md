# Contract: CLI surface (`manage.py admin_tui`)

The only externally observable entry point. Covers FR-001 / FR-002 / FR-003 /
FR-028.

---

## Synopsis

```text
python manage.py admin_tui [--user USERNAME] [--app DOTTED_PATH] [--theme PATH]
                           [--no-color] [--debug]
```

## Arguments

| Flag | Required | Type | Default | Description |
|------|----------|------|---------|-------------|
| `--user USERNAME` | no | str | resolved per `--user` resolution rules below | The Django user whose permissions and audit attribution the session uses. |
| `--app DOTTED_PATH` | no | str (import path) | `ADMIN_TUI["APP_CLASS"]`, default `admin_tui.app.AdminTuiApp` | The `AdminTuiApp` subclass to launch. |
| `--theme PATH` | no | path | `ADMIN_TUI["THEME"]`, default builtin | Textual `.tcss` to apply via `App.CSS_PATH`. |
| `--no-color` | no | flag | off | Pass through to Textual's no-color mode. For accessibility / SSH terminals that mishandle 24-bit. |
| `--debug` | no | flag | off | Enable Textual devtools and verbose logging to `./.admin_tui_debug.log`. |

## `--user` resolution

1. If `--user` is given:
   - Resolve the user by `username`. If no row exists → exit code 2.
   - If `user.is_active is False` → exit code 2.
   - If `user.is_staff is False` → exit code 2.
2. If `--user` is omitted:
   - Find all `User.objects.filter(is_superuser=True, is_active=True, is_staff=True)`.
   - If exactly one → use it.
   - If zero → exit code 3, message: "No active superuser found. Create one with
     `manage.py createsuperuser` or pass `--user <username>`."
   - If more than one → exit code 3, message: "Multiple active superusers
     exist; please specify one with `--user <username>`. Found: [...]".

All resolution errors print a single-line, actionable message to stderr and
exit BEFORE any Textual screen is presented (SC-008).

## Exit codes

| Code | Meaning |
|------|---------|
| 0    | Normal exit (operator pressed quit, Ctrl-C). |
| 1    | Unexpected error reached the top of the app loop. Stack trace printed to stderr. |
| 2    | `--user` resolution failed (does not exist / inactive / not staff). |
| 3    | Default-superuser resolution failed (none or multiple). |
| 4    | `--app` could not be imported, or imported value is not a subclass of `AdminTuiApp`. |
| 5    | `--theme` path could not be opened or is not a valid `.tcss`. |
| 64   | Unrecognised arguments (Django's BaseCommand default for usage errors). |

## Behavioural guarantees

- The command MUST exit within ~1 second on any code 2 / 3 / 4 / 5 failure on a
  developer laptop, with no Textual screen rendered (SC-008).
- The command MUST NOT open a network port for any reason (FR-004,
  Constitution VII). Textual's devtools (`--debug`) is allowed because it binds
  to localhost-only on a user-chosen port; we will document the bind and prefer
  Unix sockets if Textual makes that available.
- The command MUST honor Django's standard `--settings`, `--pythonpath`,
  `--traceback`, and `--verbosity` flags inherited from `BaseCommand`.

## Worked examples

```bash
# Default — launch as the single superuser
python manage.py admin_tui

# Explicit user
python manage.py admin_tui --user alice

# Reskinned app with a custom theme
python manage.py admin_tui --app myproject.tui.MyAdminTuiApp --theme themes/dark.tcss

# Debug mode (writes ./.admin_tui_debug.log)
python manage.py admin_tui --debug --user alice
```
