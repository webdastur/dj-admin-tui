# Quickstart

The operator-facing quickstart lives in
[`specs/001-admin-tui-mvp/quickstart.md`](../specs/001-admin-tui-mvp/quickstart.md).
That document is the source of truth and ships with each release-candidate
read-through (see [`release-checklist.md`](./release-checklist.md) for
the SC-005 gate).

If you're reading this in the rendered docs, follow that link.

If you want the short answer:

```bash
pip install django-admin-tui-mvp     # name TBD; import name is `admin_tui`
# in settings.py:
INSTALLED_APPS += ["admin_tui"]
# from project root:
python manage.py admin_tui
```

That's enough to launch the TUI against any existing Django project that
already uses `django.contrib.admin`. No `tui.py` required — zero-config
is the default (FR-021).

See the full quickstart for the trust model, keymap, overlay registration
example, custom widget registration, and the supported Python/Django matrix.

## v2 — mouse & theming

The TUI is fully mouse-drivable (every action also has a key binding):

- **Index**: click an app/model to open it.
- **Changelist**: single-click a row to focus it (its full focused-row value
  shows in the footer bar), double-click (or click the focused row) to open the
  detail, click the checkbox column to multi-select, click a column header to
  sort, click a filter entry (right sidebar, shown when the model has
  `list_filter`), click `‹ Prev` / `Next ›` / `+ Add`; the wheel scrolls.
- **Forms**: click a field to focus it, click **Save** / **Cancel**.

Long cells stay truncated (`…`) and the table never reflows on selection — read
the full value in the footer bar or open the record.

Appearance is optional, via the `ADMIN_TUI` settings dict (defaults to a
Django-admin-styled theme):

```python
ADMIN_TUI = {
    "THEME_NAME": "django",            # default; or "textual-dark", etc.
    "THEME": "/path/to/custom.tcss",   # optional .tcss override, layered on top
}
```

Per launch: `python manage.py admin_tui --theme-name textual-dark`. An unknown
theme name fails fast with `ImproperlyConfigured`. See
[`specs/002-ui-redesign-django-parity/quickstart.md`](../specs/002-ui-redesign-django-parity/quickstart.md)
and that feature's `contracts/theming.md` for registering your own theme.

Edits now save correctly for every default field type — including
many-to-many and nullable foreign-key/choice fields, which previously failed.
