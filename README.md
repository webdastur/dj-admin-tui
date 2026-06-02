# dj-admin-tui

[![PyPI version](https://img.shields.io/pypi/v/dj-admin-tui.svg)](https://pypi.org/project/dj-admin-tui/)
[![Python versions](https://img.shields.io/pypi/pyversions/dj-admin-tui.svg)](https://pypi.org/project/dj-admin-tui/)
[![Django versions](https://img.shields.io/badge/django-4.2%20%7C%205.2%20%7C%206.0-0C4B33.svg)](https://www.djangoproject.com/)
[![CI](https://github.com/webdastur/dj-admin-tui/actions/workflows/ci.yml/badge.svg)](https://github.com/webdastur/dj-admin-tui/actions/workflows/ci.yml)
[![Docs](https://readthedocs.org/projects/dj-admin-tui/badge/?version=latest)](https://dj-admin-tui.readthedocs.io)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)

A [Textual](https://textual.textualize.io/) terminal UI that drives the **Django
admin** from your terminal: browse, search, filter, sort, create, edit, delete,
and run admin actions — honoring the **same permissions and audit log** as the
web admin, because it reuses Django's own admin internals rather than
reimplementing them.

It works with **zero configuration**: any project that has `ModelAdmin`s gets a
working terminal admin with no extra code. Write a `tui.py` only when you want
TUI-specific behaviour.

![dj-admin-tui — the changelist screen: a sortable books table, a filter sidebar, pagination, and a keymap footer](https://raw.githubusercontent.com/webdastur/dj-admin-tui/main/docs/dj_admin_tui.png)

## Why

Servers, CI shells, and SSH sessions don't have a browser. `dj-admin-tui` gives
you the day-to-day admin workflows — find a record, fix a field, run a bulk
action — over a plain terminal, with the exact permission scoping and audit
trail the web admin would apply.

## Features

- **Reuses the admin, never reimplements it.** Querysets, search, filtering,
  ordering, pagination, form construction & validation, permissions, actions,
  and audit all come from your registered `ModelAdmin` and Django's own
  internals. The TUI only renders and adds interaction.
- **Zero-config.** A project with `ModelAdmin`s and no `tui.py` works fully.
- **Full CRUD** — create / edit / delete with the admin's fieldsets, widgets,
  and validation, including foreign keys, many-to-many, and multi-line text.
- **Search, sort, and filter** — driven by `search_fields`, `list_filter`, and
  `get_ordering_field_columns`, identical to the web changelist.
- **Admin actions** — bulk actions and per-row actions, with confirmation.
- **Permission-scoped & audited** — every operation runs as a chosen user and
  writes `LogEntry` rows, exactly like the web admin.
- **Keyboard and mouse** — arrows/Enter or click; `?` shows the keymap.
- **Themeable** — bundled themes plus a single-stylesheet design system you can
  override with your own `.tcss`.

## Trust model — read first

The TUI runs **in-process** as a `manage.py` subcommand. There is no network
port, no token, no remote API.

> Whoever can run `manage.py` on the host already has full database access. The
> `--user` flag scopes which records the operator sees and attributes audit
> entries to that account — it is **NOT** an access-control boundary. Access
> control is the host's responsibility (Unix permissions, SSH, etc.).

## Install

```bash
pip install dj-admin-tui
```

```python
# settings.py
INSTALLED_APPS += ["dj_admin_tui"]
```

## Launch

```bash
python manage.py admin_tui                # run as the lone superuser
python manage.py admin_tui --user alice   # run as alice (must be is_staff)
```

You land on an index of every app and model the web admin would show that user.
Arrows + Enter (or the mouse) to drill in, `q` to quit, `?` for help.

## Customising (optional)

Drop a `tui.py` next to your `admin.py` — it is autodiscovered like `admin.py`:

```python
# myapp/tui.py
from dj_admin_tui import register, TuiAdmin

@register(Book)
class BookTui(TuiAdmin):
    row_actions = ["mark_featured"]   # TUI-only per-row actions
```

The public API is exactly five names; everything else under `dj_admin_tui.*`
is internal and may change without notice:

```python
from dj_admin_tui import register, TuiAdmin, tui_site, field_widgets, AdminTuiApp
```

## Documentation

Full docs live at **[dj-admin-tui.readthedocs.io](https://dj-admin-tui.readthedocs.io)**:

| Topic | What it covers |
|-------|----------------|
| [Installation](https://dj-admin-tui.readthedocs.io/en/latest/installation/) | Requirements, install, first launch, trust model |
| [Usage](https://dj-admin-tui.readthedocs.io/en/latest/usage/) | Keymap, mouse map, search / sort / filter, the screens |
| [Configuration](https://dj-admin-tui.readthedocs.io/en/latest/configuration/) | The `ADMIN_TUI` settings dict |
| [CLI](https://dj-admin-tui.readthedocs.io/en/latest/cli/) | The `manage.py admin_tui` command, flags, exit codes |
| [Theming](https://dj-admin-tui.readthedocs.io/en/latest/theming/) | Bundled themes, custom themes, `.tcss` overrides |
| [Extending](https://dj-admin-tui.readthedocs.io/en/latest/extending/) | `TuiAdmin` overlays, hooks, custom widgets & screens |
| [API](https://dj-admin-tui.readthedocs.io/en/latest/api/) | The public Python API and stability policy |
| [Architecture](https://dj-admin-tui.readthedocs.io/en/latest/architecture/) | How it fits together; the reuse-the-admin design |

## Supported versions

- **Python:** 3.12, 3.13, 3.14
- **Django:** 4.2 LTS, 5.2 LTS, 6.0
- **Textual:** `>=8.2,<9`

See [`pyproject.toml`](./pyproject.toml) for the exact ranges.

## Contributing

Issues and pull requests are welcome. See [CONTRIBUTING.md](./CONTRIBUTING.md)
for the dev setup, test, and lint workflow. Public-API changes follow SemVer
with a deprecation path.

## License

[MIT](./LICENSE).
