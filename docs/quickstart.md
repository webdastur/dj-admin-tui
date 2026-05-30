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
