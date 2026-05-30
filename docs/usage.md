# Using the TUI

Everything is operable by **keyboard** and by **mouse** — the mouse is additive,
never required. On a terminal that doesn't report mouse events, every action is
still reachable by a key binding.

## Index

The first screen lists every app and model the web admin would show your user.

| Action | Keyboard | Mouse |
|--------|----------|-------|
| Open an app / model | arrows + `Enter` | single click |
| Quit | `q` | — |
| Help | `?` | — |

## Changelist

The list view mirrors the Django admin changelist.

### Keyboard

`q` back · `/` focus search · `s` sort · `a` add · `Space` select row ·
`x` actions · `PgUp`/`PgDn` page · `Enter` open the focused row.

### Mouse

| Action | Mouse |
|--------|-------|
| Focus a row | single click |
| Open a row | double-click (or click the focused row), or `Enter` |
| Multi-select | click the leading checkbox column |
| Sort by a column | click its header (sortable columns only) |
| Filter | click an entry in the right-hand filter sidebar |
| Page | click `‹ Prev` / `Next ›` |
| Add | click `+ Add` |
| Scroll | mouse wheel |

### Layout, truncation & preview

Columns have **fixed widths** that don't change when you move the selection.
Long values are truncated with an ellipsis (`…`); the full value of the focused
row is shown in the footer preview bar, and the whole record is on its detail
screen. When the columns are wider than the terminal, the table scrolls
horizontally — no column is ever dropped.

### Search

If the model's `ModelAdmin` declares `search_fields`, a search box appears in
the toolbar. Type a query and press `Enter` (or press `/` to jump to it). Search
uses Django's own `search_fields`, so results match the web admin exactly.

### Sorting & ordering

Sorting is controlled by your `ModelAdmin` — `ordering`, `sortable_by`, and each
field's `admin_order_field`:

- The active sort column shows `▲` (ascending) or `▼` (descending), including
  the model's default `ordering`.
- `s` cycles the sort across the **sortable** columns and directions; clicking a
  column header sorts that column directly.
- Non-sortable columns don't respond (the TUI says so), exactly as in the web
  admin.

### Filters

When the model declares `list_filter`, a filter sidebar appears on the right
built from the admin's own filter choices. Selecting an entry applies Django's
filter — identical result set to the web admin.

### Actions & selection

`Space` (or the checkbox column) selects rows across pages. `x` opens the action
picker, which lists the admin actions from `ModelAdmin.get_actions()` plus any
TUI-native bulk actions and a Delete entry (when you have delete permission).
A confirmation screen names what will change before anything runs; messages the
action emits via `message_user(...)` are surfaced with their severity.

## Detail / create / edit

Opening a record shows a read-only detail with the admin's fieldsets. From
there:

| Action | Keyboard | Mouse |
|--------|----------|-------|
| Edit | `e` | — |
| Save | `Ctrl+S` | click **Save** |
| Cancel / back | `q` / `Esc` | click **Cancel** |
| Delete | `d` | click **Delete** |

The edit/add form follows the Django change form: a breadcrumb, a
`Change <model>` / `Add <model>` heading, label-left / field-right rows that
respect the admin's fieldsets and `readonly_fields`, and a submit row with
**Save**, **Save and add another**, **Save and continue editing**, **Cancel**,
and **Delete**. Validation runs through the admin's form, so `clean_*` / `clean`
errors appear on the right fields and every successful save writes the same
`LogEntry` the web admin would.

## Errors

Database or query errors (a missing table, a permission problem, a broken
`ModelAdmin` method) surface as a notification — the app stays on a usable
screen rather than crashing.
