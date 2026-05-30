# Installation & first launch

Django Admin TUI is a terminal UI that drives the Django admin: browse, search,
filter, sort, create, edit, delete, and run admin actions — all from the
terminal, honoring the same permissions and audit as the web admin.

## Requirements

- **Python:** 3.12, 3.13, or 3.14
- **Django:** 4.2 LTS, 5.2 LTS, or 6.0
- **Textual:** `>=8.2,<9`
- A terminal with ANSI colour and at least an 80×24 size (mouse optional).

## Install

```bash
# uv (recommended)
uv add django-admin-tui-mvp

# pip
pip install django-admin-tui-mvp
```

> The PyPI distribution name is a working title; the **import name is
> `admin_tui`** and is stable regardless of the final distribution name.

Add the app to your project:

```python
# settings.py
INSTALLED_APPS += ["admin_tui"]
```

That's all. The package autodiscovers any `tui.py` module under each installed
app — the same pattern as `admin.py`. A project with `ModelAdmin`s and **no**
`tui.py` works fully; you write a `tui.py` only to add TUI-specific behaviour
(see [extending.md](./extending.md)).

## Launch

From the project root with your virtualenv active:

```bash
python manage.py admin_tui                # run as the lone superuser
python manage.py admin_tui --user alice   # run as alice (must be is_staff)
```

You land on an **index** of every app and model the web admin would show that
user. Arrow keys + Enter to drill in, the mouse to click, `q` to quit, `?` for
help. See [usage.md](./usage.md) for the full keymap and mouse map, and
[cli.md](./cli.md) for every flag and exit code.

## Trust model — read first

The TUI runs **in-process** as a `manage.py` subcommand. There is no network
port, no token, and no remote API.

> Whoever can run `manage.py` on the host already has full database access. The
> `--user` flag scopes which records the operator sees and attributes audit
> entries to that account — it is **NOT** an access-control boundary. Access
> control is the host's responsibility (Unix permissions, SSH, etc.).

If you need a remote, multi-operator TUI, that would be a future opt-in,
authenticated mode; it is not provided today.
