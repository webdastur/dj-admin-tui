# Django Admin TUI

A terminal UI that drives the Django admin: browse, search, filter,
create, edit, delete, and run admin actions — all from the terminal,
honoring admin permissions.

> **Working title.** PyPI distribution name TBD (`django-admin-tui` is
> taken); the Python import name is `admin_tui` and is stable regardless
> of the final distribution name.

## Trust model — read first

The TUI runs **in-process** as a `manage.py` subcommand. There is no
network port, no token, no remote API in v1.

> Whoever can run `manage.py` on the host already has full database
> access. The `--user` flag scopes which records the operator sees and
> attributes audit entries to that account — it is **NOT** an
> access-control boundary. Access control is the host's responsibility
> (Unix permissions, SSH, etc.).

If you need a remote, multi-operator TUI, that is a future opt-in mode
([Constitution VII](.specify/memory/constitution.md)); v1 does not
provide it.

## Install

```bash
# uv (recommended)
uv add django-admin-tui-mvp

# pip
pip install django-admin-tui-mvp
```

```python
# settings.py
INSTALLED_APPS += ["admin_tui"]
```

That's it. The package autodiscovers any `tui.py` module under each
installed app — same pattern as `admin.py`.

## Launch

From the project root, with the venv active:

```bash
python manage.py admin_tui                # runs as the lone superuser
python manage.py admin_tui --user alice   # runs as alice (must be is_staff)
```

You'll see an **index** of every app and model the web admin would show
that user. Arrows + Enter to drill in. `q` quits. `?` opens the help.

**What if I have a `ModelAdmin` but no `tui.py`?** The TUI works fully —
that's the zero-config promise. You write a `tui.py` only when you want
TUI-specific behavior.

See [`specs/001-admin-tui-mvp/quickstart.md`](./specs/001-admin-tui-mvp/quickstart.md)
for the full operator walkthrough (keymap, overlay registration, custom
field widget, custom screen replacement).

## Supported versions

- **Python:** 3.12, 3.13, 3.14
- **Django:** 4.2 LTS, 5.2 LTS, 6.0 (the cross-product CI matrix, with
  upstream-forbidden cells excluded)
- **Textual:** `>=8.2,<9` (pinned major; bump after testing)

See [`pyproject.toml`](./pyproject.toml) for the exact ranges and the
[`research.md`](./specs/001-admin-tui-mvp/research.md) decisions for
the rationale.

## Stability

Public API surface (FR-030 / Constitution V — these five names only):

```python
from admin_tui import register, TuiAdmin, tui_site, field_widgets, AdminTuiApp
```

Everything else under `admin_tui.*` is internal and may change without
notice. Public changes follow SemVer with a deprecation path. See
[`specs/001-admin-tui-mvp/contracts/public-api.md`](./specs/001-admin-tui-mvp/contracts/public-api.md)
for the full surface and the deprecation policy.

## Documentation

| File | What it covers |
|---|---|
| [`docs/quickstart.md`](./docs/quickstart.md) → [`specs/001-admin-tui-mvp/quickstart.md`](./specs/001-admin-tui-mvp/quickstart.md) | Install, launch, overlay registration, custom widget, custom screen |
| [`docs/architecture.md`](./docs/architecture.md) | One-page object graph + the synthetic-request explainer |
| [`docs/release-checklist.md`](./docs/release-checklist.md) | The SC-005 timed-contributor gate + per-release acceptance items |
| [`specs/001-admin-tui-mvp/contracts/`](./specs/001-admin-tui-mvp/contracts/) | Public API, CLI flags + exit codes, settings, Django surface |
| [`.specify/memory/constitution.md`](.specify/memory/constitution.md) | The 8 principles that bind the design |

## Status

Pre-1.0. The implementation is driven from
[`specs/001-admin-tui-mvp/`](./specs/001-admin-tui-mvp/) following Spec
Kit. The current test suite covers every FR-024 extension class and
every documented SC criterion at the call-path level.

## License

[MIT](./LICENSE).
