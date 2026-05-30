# Research: Django Admin TUI — v1

**Branch**: `001-admin-tui-mvp` | **Date**: 2026-05-30 | **Status**: complete

This file resolves every open question from `plan.md` Technical Context and
locks the design choices that downstream `data-model.md`, `contracts/`, and
`quickstart.md` rely on. There are no remaining `NEEDS CLARIFICATION` items.

Each entry: **Decision** — what we chose. **Rationale** — why. **Alternatives
considered** — what else was on the table and why we rejected it.

---

## R1. Python version floor

**Decision**: Python 3.12 minimum; CI matrix runs 3.12, 3.13, 3.14.

**Rationale**: This is forced by R2's Django range, not chosen independently.
Django 6.0 (current stable on 2026-05-30) requires Python 3.12+, and FR-036
obliges us to support the current stable. The 5.2 LTS release notes also state
explicitly that *5.2.x is the last series to support Python 3.10/3.11*, so any
package wanting to install cleanly against the 5.2-LTS + 6.0 pair must floor at
3.12 anyway. The user's original `3.12+` preference matches this constraint
exactly. The CI matrix runs (3.12, 3.13, 3.14) × (4.2 LTS, 5.2 LTS, 6.0),
dropping cells the upstream matrices forbid (4.2 doesn't support 3.13/3.14;
5.2 doesn't support 3.14).

**Alternatives considered**:
- 3.11 floor — would force dropping Django 6.0 from the matrix, which fails
  FR-036. I held this position briefly in an earlier draft; correcting it.
- 3.13 floor — gains us nothing since 5.2 LTS still runs on 3.12, and pushes
  the floor past the recommended Python for projects pinned to 5.2.
- Lock to the user's exact `3.12+` and skip the matrix discussion — leaves
  unstated *why* 3.12 specifically; the matrix is the reason.

---

## R2. Django version matrix

**Decision**: support Django 4.2 LTS, 5.2 LTS, and 6.0. CI runs the
cross-product with each Python in R1, dropping cells the upstream matrices
forbid.

**Rationale**: FR-036 mandates "current Django LTS and the latest stable
Django." As of 2026-05-30 those are **5.2 LTS** (current LTS) and **6.0**
(current stable, released December 2025). 4.2 LTS reached EOL in April 2026 but
is still widely deployed; including it costs little and is the courtesy floor
most operators care about during their migration windows. Django 5.1 is EOL
since 5.2 LTS shipped (April 2025) and adding it would burn CI minutes without
buying real-world fidelity.

**Per the Django 6.0 release notes**: no admin signature changes affect us;
the listed backwards-incompatible items are the Python floor (already accounted
for in R1) and the MariaDB 10.5 drop (irrelevant — we don't touch storage).
Every method enumerated in `contracts/internal-django-surface.md` is documented
unchanged in the 6.0 reference. CI will catch any drift if a future 6.x
release breaks an assumption.

**Alternatives considered**:
- 5.2 + 6.0 only (drop 4.2) — cleanest matrix, but cuts off the still-large
  4.2-LTS install base mid-migration. Reconsider for v1.1 once 4.2 has been
  EOL for ≥12 months.
- Add 6.1 when it ships (expected August 2026) — yes; that's an additive matrix
  bump that doesn't require a spec amendment.
- Also support 5.1 — EOL; no fidelity payoff.

---

## R3. The synthetic request — confirmed approach

**Decision**: use `django.test.RequestFactory` for the bare request, attach the
session user, and attach a custom `BaseStorage` subclass at `request._messages`
that captures messages in memory and never tries to read or write cookies/session.
Mark a stable `request._tui_session = TuiSession(...)` attribute for our own code
to recognize the request (admin code never reads it).

**Rationale**: `ModelAdmin.message_user(...)` defers to
`django.contrib.messages.add_message(request, ...)`, which requires
`request._messages` to be a `BaseStorage` subclass. Without it, `add_message`
either raises `MessageFailure` or silently drops messages when `fail_silently=True`
— neither of which preserves the message-capture acceptance criterion (US3 #4).
`RequestFactory` gives us a real `HttpRequest` object that any first- or
third-party `ModelAdmin` will recognize.

**Implementation sketch (validated against Django 4.2 + 5.2 docs)**:

```python
# core/request.py
from django.contrib.messages.storage.base import BaseStorage
from django.test import RequestFactory


class _CapturingMessageStorage(BaseStorage):
    def __init__(self, request):
        super().__init__(request)
        self.captured: list[tuple[int, str, str]] = []

    def _get(self, *a, **k):                 # required by BaseStorage
        return [], True

    def _store(self, messages, response, *a, **k):  # required by BaseStorage
        return []                            # nothing to persist

    def add(self, level, message, extra_tags=""):
        self.captured.append((level, str(message), extra_tags))


def build_request(user, query=None, *, path="/"):
    request = RequestFactory().get(path, data=query or {})
    request.user = user
    request._messages = _CapturingMessageStorage(request)
    return request
```

**Alternatives considered**:
- Mock the messages framework via `fail_silently=True` everywhere — discards
  messages that action authors deliberately surface. Fails US3 #4.
- Patch every `ModelAdmin.message_user` we encounter — invasive; violates
  Constitution I (we'd be redirecting admin logic).
- Build a fake `HttpRequest` from scratch — `RequestFactory` already does it and
  is part of the public Django test API, which is stable across versions.

---

## R4. Changelist construction — which API to call

**Decision**: call `model_admin.get_changelist_instance(request)`. Do NOT
construct `django.contrib.admin.views.main.ChangeList` directly.

**Rationale**: `ChangeList.__init__` takes 12+ positional args and its signature
has changed across Django versions (notably the `search_help_text` addition).
`get_changelist_instance` wraps that constructor with the version-correct argument
list and is the supported API. Verified in both `/websites/djangoproject_en_4_2`
and `/websites/djangoproject_en_5_2` docs.

**Alternatives considered**:
- Direct `ChangeList(...)` — fragile; couples us to internal signature.
- Reimplement search/filter/sort against `model_admin.get_queryset(request)` — a
  Constitution I violation and a maintenance liability.

---

## R5. Form rendering — admin form, our widgets

**Decision**: call `model_admin.get_form(request, obj=None)` to get the
`ModelForm` class, instantiate it bound to the object (or unbound for create),
then iterate `form.fields.items()` and dispatch each `(name, field, bound_field)`
through `FieldWidgetRegistry.resolve(...)`. The registry returns a Textual widget
that knows how to render the bound field and produce a value on submit. Validation
is `form.is_valid()` — we do not reimplement it.

**Rationale**: this preserves admin form behavior end-to-end:
- `get_form` honours `fieldsets`, `readonly_fields`, custom `formfield_overrides`,
  and the `Media` declarations (which we ignore for the TUI but record so we can
  warn the operator that admin JS won't run).
- `form.is_valid()` runs `clean_*` methods and `clean()` exactly as the web admin
  does, satisfying US2 #2.
- Iterating `bound_field`s rather than model fields preserves overrides like
  `formfield_for_choice_field` and `formfield_for_foreignkey`.

**Alternatives considered**:
- Iterate `model._meta.get_fields()` — bypasses `formfield_for_*` overrides and
  drops admin-form-specific fields. Violates Constitution I.
- Build a "TUI form" superclass — wraps a `ModelForm`; pointless layer.

---

## R6. Actions — call the admin's own callables, capture messages

**Decision**: get the actions dict from `model_admin.get_actions(request)`. Run a
chosen action by calling `func(model_admin, request, queryset)`. Surface anything
added to `request._messages.captured` after the call as a Textual `notify(...)`
per message, mapped by level (info / success / warning / error).

**Rationale**: `get_actions` is documented in both 4.2 and 5.2 admin refs and
already filters by `has_*_permission`. Calling the function with the model_admin
as the first arg matches admin behavior. The capturing storage from R3 means we
collect every `message_user` call without monkey-patching anything.

**Alternatives considered**:
- Run the action with a custom request that has no `_messages` and read return
  values — most admin actions return `None` and rely on `message_user`. Would
  lose context. Fails US3 #4.

---

## R7. Audit — pass-through, do not synthesize

**Decision**: call `model_admin.log_addition(request, obj, message)`,
`log_change(...)`, `log_deletion(...)` directly. Build the `message` parameter
with `model_admin.construct_change_message(request, form, formsets, add)` so the
text matches the web admin character-for-character.

**Rationale**: SC-004 requires "user, action flag, content type, and change
message match those the web admin would produce for the same inputs." The only
way to satisfy this is to call the admin's own helpers. The Django docs for both
4.2 and 5.2 confirm these helper signatures are stable.

**Alternatives considered**:
- Write `LogEntry` rows ourselves — duplicate logic; drifts from admin behavior.
  Fails Constitution II's audit-fidelity gate.

---

## R8. Permissions — Django's hooks, end of story

**Decision**: every read path consults `has_view_permission` (or
`has_module_permission` for the index, mirroring the web admin's behavior); every
mutation path consults `has_add/change/delete_permission`. The index screen filters
apps via `has_module_permission` and models via `has_view_permission`. We do not
introduce a "TUI permission" concept.

**Rationale**: FR-007, FR-021, and the entirety of US1 #3 and US4 #4 hinge on
fidelity with web-admin permission scoping. Adding a parallel concept would be a
Constitution I/II violation and a backdoor risk (Constitution VII).

---

## R9. `TuiSite` and default overlay synthesis

**Decision**: `TuiSite` keeps a `{Model: TuiAdmin}` registry, separate from
`admin.site._registry`. On first access to a model, if no overlay is registered,
synthesize one with `TuiAdmin._synthesize(model_admin)` and cache it in the
registry. Synthesis returns a `TuiAdmin` instance whose `model_admin` attribute
points at the source `ModelAdmin`; every declarative slot defaults to reading from
`self.model_admin`. There is NO parallel "default renderer" code path.

**Rationale**: Constitution IV ("defaults travel the extension path"). The same
instance flows through the same screens whether it was hand-written or
synthesized.

**Alternatives considered**:
- Two registries (defaults + overlays), looked up in priority — works, but allows
  defaults to render via code paths overlays don't exercise. Fails Constitution IV.

---

## R10. Autodiscovery

**Decision**: in `apps.AdminTuiConfig.ready()`, call
`django.utils.module_loading.autodiscover_modules("tui")`. Each installed app's
optional `tui.py` runs at import and registers overlays via the `@register`
decorator or `tui_site.register(...)`.

**Rationale**: identical to how `django.contrib.admin` autodiscovers `admin.py`.
Familiar to Django devs (mental-model goal in spec §US4) and is the documented
extension pattern.

**Alternatives considered**:
- Settings-list of overlay modules — verbose, drifts from admin convention.
- Entry points (`importlib.metadata`) — overkill for a same-process integration.

---

## R11. Textual version pin and CSS theming

**Decision**: pin Textual to `>=8.2,<9` for v1. Current stable on 2026-05-30 is
**8.2.7** (released 2026-05-19). Theming via Textual's own CSS (`.tcss`) and
`App.CSS_PATH` / `App.CSS`. The `ADMIN_TUI["THEME"]` setting points at a `.tcss`
file path that we pass to the app's `CSS_PATH`.

**Rationale**: Textual moves fast (3.x → 4.x → 6.x → 8.x in roughly 24 months)
and reserves the right to break between majors. Pinning a single major lets us
test against a real surface and bump deliberately. The relevant API surface for
this design — `App` subclass init, `Screen` subclass, `DataTable` (`add_column`,
`add_row`, `cursor_type`, `RowSelected` event, `coordinate_to_cell_key`),
`BINDINGS`, `CSS_PATH` — has **no breaking changes** between 7.0.0 and 8.2.7
per the upstream CHANGELOG. Two notable evolutions to be aware of:

1. **`Pilot.click` accepts widgets directly** (not only selector strings) — our
   tests can keep using selectors but may simplify by passing widgets.
2. **`App.push_screen` returns an Awaitable** since v0.71.0 — our internal
   call sites that push screens must be `await`ed. This is a fix-on-write, not
   a hazard.
3. **Textual markup replaced Rich markup in v2.0.** The `[tag]...[/]` syntax in
   `quickstart.md`'s `render_cell` example works in both, so the example is
   accurate; if we ever need Rich-only features (e.g. `Group`), we'd route them
   through `Rich.console.Console` explicitly rather than markup strings.

CSS theming hits Constitution VI directly: we don't introduce a parallel
theming layer.

**Alternatives considered**:
- Float Textual — guaranteed mid-cycle breakage; user docs would constantly lie.
- Stay on 6.6 — current default in some forks/caches but two majors behind the
  active release line; no payoff for the lag.
- Vendor a theming abstraction — Constitution VI violation.

---

## R12. Testing strategy

**Decision**: three layers, all driven by `pytest`. Floor versions verified
from PyPI on 2026-05-30:

- `pytest >=9.0` (current 9.0.3)
- `pytest-django >=4.12` (current 4.12.0 — its README explicitly lists support
  for Django 4.2, 5.1, 5.2, 6.0, matching our matrix)
- `pytest-asyncio >=1.4` (current 1.4.0; first post-1.0 stable line — picks up
  the `asyncio_mode` settling and removes the deprecation churn from 0.x)

CI does not pin these any tighter than the floor: if pytest 9.1 ships and
breaks us, we want CI to surface it on the same day, not after a manual bump.

Layers:

1. **Unit** (`tests/unit/`) — synthetic request, capturing message storage,
   widget registry MRO walk, default-overlay synthesis. Fast; no Django app
   loaded for the registry tests (use lightweight fakes).
2. **Integration** (`tests/integration/sample_project/`) — `pytest-django` boots
   `sample_project.settings`; tests assert per-user-permission scoping, action +
   audit parity with the web admin, overlay registration.
3. **TUI behaviour** — same `sample_project`, driven via Textual's `Pilot`:
   `async with AdminTuiApp(...).run_test() as pilot: await pilot.press(...)`.
   Asserts on key bindings, screen transitions, and what's rendered in the
   `DataTable`. No SVG snapshot tests in v1; we keep them out of scope to avoid
   the maintenance overhead.

**Rationale**: Pilot is the documented Textual test harness and is async; it gives
us deterministic input simulation with no real terminal. Pairing it with
`pytest-django` lets us run real ORM and permission checks. The three-layer split
keeps fast tests fast and isolates failures.

**Alternatives considered**:
- `pytest-textual-snapshot` for SVG diffs — useful, but high-noise (every theme
  tweak invalidates). Defer to a later milestone.
- Cypress / Playwright over `textual-web` — heavyweight; only justified if we
  ever ship a remote mode (out of scope for v1).

---

## R13. Packaging and the `uv` toolchain

**Decision**: `pyproject.toml` is the single source of truth (PEP 621). Build
backend: `hatchling >=1.29` (current 1.29.0). `uv` is the recommended dev
toolchain (`uv sync`, `uv run pytest`); `pip install <name>` must also work
end-to-end without `uv`. Pin top-level versions in `pyproject.toml`; commit
`uv.lock` for reproducible CI.

**Rationale**: FR-035 requires single pip-installable. Hatchling is pure-Python,
fast, no compilation, MIT-friendly, and is the build backend the broader Python
ecosystem has standardised on (used by FastAPI, Pydantic, Starlette, Httpx).
`uv` is the user's preference for dev ergonomics and is consistent with the
"fast-moving deps are pinned" rule in Technical Standards.

**Alternatives considered**:
- Poetry — works, but slower and harder to drive in CI. uv is the user's pick.
- Setuptools + setup.cfg — legacy; no reason to choose over PEP 621.
- Flit — also pure-Python and minimal, but hatchling has the larger maintainer
  base and feature set we'll grow into (entry-points, sdists with
  `force-include`, etc.).

---

## R14. PyPI distribution name

**Decision**: park the name. The working title is "Django Admin TUI"; the
constitution's `TODO(PACKAGE_NAME)` and the spec's Assumptions section both flag
it. v1 ships under whatever name we register before publish; the codebase imports
`admin_tui` regardless so the public Python API stays stable across a rename.

**Rationale**: a name decision is a marketing/branding call, not an engineering
blocker. The Python import name (`admin_tui`) is what code touches; the PyPI
distribution name only matters at `pip install` time.

**Alternatives considered**:
- Fork `valberg/django-admin-tui` — would inherit the existing PyPI name and an
  audience. Considered, but the codebase is at v0.0.1 with a different
  architecture (no `TuiSite`, no extension surface). Greenfield is cheaper.
  Action: open a courtesy issue on the upstream repo before v1.0 ratification.

---

## R15. Inlines

**Decision**: in scope for v1, isolated to Phase 4 (the extensibility/hardening
phase). Implementation: respect `get_inline_instances(request, obj)` and render
each inline as a nested `DataTable` editable region within the detail screen.
Reuse `get_form` for each inline's formset.

**Rationale**: the spec keeps inlines in scope but flags them as the most likely
deferral candidate (Assumptions). Pushing them to Phase 4 means the MVP
(US1) and the core CRUD (US2, US3) ship without inline complexity blocking them,
and we can decide to defer at the Phase 4 gate without retracting earlier scope.

**Alternatives considered**:
- Punt inlines to v1.1 unconditionally — would invalidate the FR set; we'd need a
  spec amendment. Premature.

---

## R16. The "custom `ModelAdmin` overrides we can't honour" surface

**Decision**: at startup, walk each registered `ModelAdmin` and detect overrides
of `change_view`, `get_urls`, `change_form_template`, `Media`, etc. Record them
in `_internal.compat.report` and surface a one-time warning on the first access
to that model — a Textual `notify(...)` plus a written line in the index.

**Rationale**: Edge case in spec § "Edge Cases" ("must not silently drop the
custom behavior in a way the operator can't detect"). A loud, single notification
gives operators a way to know what's missing without a runtime exception.

**Alternatives considered**:
- Refuse to launch on detection — punishes users for `ModelAdmin`s the TUI's
  defaults would handle fine.
- Silent — fails the Edge Cases requirement.

---

## Open items intentionally NOT in v1

- Remote / multi-user mode (Constitution VII — opt-in future).
- A plug-in marketplace, telemetry, or update channel (spec § Out of Scope).
- SVG snapshot tests (deferred from R12).
- A built-in "command palette" beyond Textual's default — no concrete need yet
  (Constitution V).

All of the above can be reopened post-v1 with a spec amendment.
