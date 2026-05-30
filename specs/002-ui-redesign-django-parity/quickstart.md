# Quickstart (v2 delta) — Theming & Mouse

This covers only what v2 adds on top of the v1 quickstart (install / launch / extend in
`specs/001-admin-tui-mvp/quickstart.md` and `docs/quickstart.md`). Nothing in the v1 launch
flow changes.

---

## Using the mouse

The TUI is mouse-drivable everywhere; every action also has a key binding, so a
mouse-less terminal loses nothing.

- **Index:** click an app or model to open it.
- **Changelist:**
  - **single click** a row → focus it (its full focused-cell value shows in the footer
    bar);
  - **double click** a row → open its detail;
  - click the **checkbox column** → toggle that row in your multi-selection;
  - click a **column header** → sort by it;
  - click a **filter entry** (right sidebar, shown when the model has `list_filter`) →
    apply/clear that filter;
  - click **‹ Prev / Next ›** to page, **+ Add** to create;
  - **wheel** scrolls without changing your selection.
- **Forms:** click a field to focus it, click **Save** / **Cancel**.

Long cell values stay truncated (`…`) in the table — the table never reflows when you move
the selection. To see a full value, read the footer preview bar or open the record.

---

## Choosing the look (theming via settings)

Appearance is optional and lives in the existing `ADMIN_TUI` dict. With no config you get
the Django-admin-styled default.

### Pick a bundled theme by name

```python
# settings.py
ADMIN_TUI = {
    "THEME_NAME": "django",        # default; evokes the Django admin palette
    # "THEME_NAME": "textual-dark",  # a neutral fallback
}
```

Per launch, override with `--theme-name`:

```bash
python manage.py admin_tui --theme-name textual-dark
```

An unknown theme name fails fast at startup with a clear `ImproperlyConfigured` message —
no broken screen is shown.

### Fine-tune with a CSS override (layered on top)

```python
ADMIN_TUI = {
    "THEME_NAME": "django",
    "THEME": "/path/to/myproject/admin_tui.tcss",   # existing key; .tcss only
}
```

The named theme provides the palette; your `.tcss` rules (referencing `$primary`,
`$surface`, …) override anything where they overlap. A `.tcss` file alone is enough if you
want full control.

### Ship your own named theme

Subclass `AdminTuiApp`, register a `textual.theme.Theme`, and select it by name — see
`contracts/theming.md` for the full example. This uses only the public `AdminTuiApp`
subclass point and Textual's own theming API.

---

## What did NOT change

- Result sets, search, filters, sorting, pagination, validation, saves, deletes, actions,
  and audit are exactly as in v1 — the redesign is presentation/interaction/bug-fix only.
- The public Python API (six names + hooks) is unchanged; v2 adds only the `THEME_NAME`
  settings key.
- Edits now save correctly for every default field type (including many-to-many and split
  date/time widgets), which previously failed — but the save path itself (Django's
  `get_form` → `save_model` → `LogEntry`) is unchanged.
