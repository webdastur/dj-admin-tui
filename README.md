# Django Admin TUI

A terminal UI that drives the Django admin: browse, search, filter, sort,
create, edit, delete, and run admin actions — all from the terminal, honoring
the same permissions and audit as the web admin.

> **Working title.** The PyPI distribution name is TBD (`django-admin-tui` is
> taken); the Python import name is `admin_tui` and is stable regardless of the
> final distribution name.

## Trust model — read first

The TUI runs **in-process** as a `manage.py` subcommand. There is no network
port, no token, no remote API.

> Whoever can run `manage.py` on the host already has full database access. The
> `--user` flag scopes which records the operator sees and attributes audit
> entries to that account — it is **NOT** an access-control boundary. Access
> control is the host's responsibility (Unix permissions, SSH, etc.).

## Install

```bash
pip install django-admin-tui-mvp     # name TBD; import name is `admin_tui`
```

```python
# settings.py
INSTALLED_APPS += ["admin_tui"]
```

## Launch

```bash
python manage.py admin_tui                # run as the lone superuser
python manage.py admin_tui --user alice   # run as alice (must be is_staff)
```

You land on an index of every app and model the web admin would show that user.
Arrows + Enter (or the mouse) to drill in, `q` to quit, `?` for help. A project
with `ModelAdmin`s and **no** `tui.py` works fully — that's the zero-config
promise; you write a `tui.py` only to add TUI-specific behaviour.

## Documentation

| Doc | What it covers |
|-----|----------------|
| [docs/installation.md](./docs/installation.md) | Requirements, install, first launch, trust model |
| [docs/usage.md](./docs/usage.md) | Keymap, mouse map, search / sort / filter, the screens |
| [docs/configuration.md](./docs/configuration.md) | The `ADMIN_TUI` settings dict |
| [docs/cli.md](./docs/cli.md) | The `manage.py admin_tui` command, flags, exit codes |
| [docs/theming.md](./docs/theming.md) | Bundled themes, custom themes, `.tcss` overrides |
| [docs/extending.md](./docs/extending.md) | `TuiAdmin` overlays, hooks, custom widgets & screens |
| [docs/api.md](./docs/api.md) | The public Python API and stability policy |
| [docs/architecture.md](./docs/architecture.md) | How it fits together; reuse-the-admin design |

## Supported versions

- **Python:** 3.12, 3.13, 3.14
- **Django:** 4.2 LTS, 5.2 LTS, 6.0
- **Textual:** `>=8.2,<9`

See [`pyproject.toml`](./pyproject.toml) for the exact ranges.

## Stability

The entire public API is five names; everything else under `admin_tui.*` is
internal and may change without notice:

```python
from admin_tui import register, TuiAdmin, tui_site, field_widgets, AdminTuiApp
```

Public changes follow SemVer with a deprecation path — see
[docs/api.md](./docs/api.md).

## License

[MIT](./LICENSE).
