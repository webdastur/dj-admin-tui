# Feature Specification: Django Admin TUI — v1

**Feature Branch**: `001-admin-tui-mvp`

**Created**: 2026-05-30

**Status**: Draft

**Input**: User description: build a terminal UI that drives the Django admin — browse,
search, filter, create, edit, delete, and run admin actions — honoring admin
permissions and audit, designed so other developers can extend it the same way they
extend `ModelAdmin`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Operator browses admin data from the terminal (Priority: P1) 🎯 MVP

A site operator who manages a Django project over SSH launches the admin TUI from the
project root, picks a model from the index, and navigates a read-only changelist:
search, filter, sort, page through records, and open a single record to see its
fields. They never leave the terminal, and they only see apps, models, columns, and
rows the web admin would have shown to their account.

**Why this priority**: this is the smallest useful slice. Most production debugging is
"open this model, find this record." Read-only is also the strictest fidelity test
of the underlying permission and column-resolution behavior; the rest of the feature
is built on this foundation.

**Independent Test**: against the in-repo sample project, launching the TUI as a
superuser MUST list every app and model the web admin lists; launching as a user with
view-only on one model MUST hide every other model and every mutating affordance.
Search, filter, sort, and pagination MUST produce the same result set as the web
admin's changelist for the same query parameters.

**Acceptance Scenarios**:

1. **Given** the sample project is installed with several apps and `ModelAdmin`
   registrations, **When** an operator launches the TUI as the default superuser,
   **Then** the index lists exactly the apps and models the web admin's index would
   list for that user.
2. **Given** an operator viewing a model's changelist with a `search_fields`
   declaration on its `ModelAdmin`, **When** they enter a search query, **Then** the
   visible result set is identical to what the web admin would show for the same
   query.
3. **Given** an operator whose account has `view` on `Book` but no permissions on
   `Author`, **When** they launch the TUI as that user, **Then** `Author` is not
   present anywhere in the index or model picker.
4. **Given** a model with `list_filter` and a non-default `list_per_page`, **When**
   the operator filters and pages through the changelist, **Then** filter
   combinations and page boundaries match the web admin's exactly.

---

### User Story 2 - Operator creates and edits records with admin validation (Priority: P2)

An operator opens a model's changelist, creates a new record using the same form
fields and validation rules as the web admin, fixes any validation errors inline, and
saves. They can also open an existing record, edit it, and save. Every successful
save is attributed to their session user in the Django audit log.

**Why this priority**: edits are the second-most-common production task after
look-ups, and they exercise the form, validation, and audit paths end-to-end. Without
this, the tool is a read-only viewer.

**Independent Test**: against the sample project, an operator MUST be able to create
and edit instances of models that have custom `ModelAdmin` forms (custom fieldsets,
`readonly_fields`, `clean_*` methods, foreign keys); the resulting validation errors,
saved values, and audit entries MUST match what the web admin produces for the same
inputs.

**Acceptance Scenarios**:

1. **Given** a model whose `ModelAdmin` defines custom `fieldsets` and
   `readonly_fields`, **When** the operator opens the create form, **Then** the form
   shows the same fieldsets in the same order with the same readonly markings as the
   web admin.
2. **Given** a `clean_*` method on the admin form that rejects a value, **When** the
   operator submits that value, **Then** the same error message appears next to the
   same field and the record is not saved.
3. **Given** a successful save, **When** the operation completes, **Then** a Django
   `LogEntry` for the corresponding action (addition or change) exists, attributed to
   the session user, with a change message equivalent to the web admin's.
4. **Given** a foreign-key field, **When** the operator picks a related record,
   **Then** the candidate list respects the related model's permission scope and
   `ModelAdmin` configuration.

---

### User Story 3 - Operator deletes records and runs admin actions (Priority: P3)

An operator selects one or more records on a changelist, runs an admin action (built-in
or model-specific) or deletes the selection, sees a confirmation screen that lists
exactly what will change, and confirms. Action messages produced by the underlying
`ModelAdmin` (e.g. "3 books were updated") are surfaced in the TUI. Deletions and
action runs are written to the audit log.

**Why this priority**: completes "full CRUD + actions." Until this lands the operator
must still drop to the web admin for destructive operations.

**Independent Test**: against the sample project, the operator MUST be able to run a
custom admin action defined on a `ModelAdmin` and a model-level delete on a multi-row
selection; the produced messages, side effects, and audit log entries MUST match the
web admin for the same selection.

**Acceptance Scenarios**:

1. **Given** a model with a custom admin action, **When** the operator selects rows
   and chooses that action, **Then** a confirmation screen describes the action,
   selection size, and any messages the action surfaces; on confirm, the action runs
   exactly once against the selection.
2. **Given** an account that lacks `delete` permission on the model, **When** the
   operator tries to delete rows, **Then** the delete affordance is hidden and any
   programmatic attempt is refused with the same permission error the web admin
   would raise.
3. **Given** a successful action or delete, **When** the operation completes, **Then**
   a `LogEntry` of the corresponding type exists, attributed to the session user.
4. **Given** an action that calls `message_user(...)`, **When** the action completes,
   **Then** every message it produced is displayed in the TUI with the same level
   distinctions (info / warning / error) the web admin uses.

---

### User Story 4 - Developer extends the TUI for their own model (Priority: P3)

A developer adopting the package adds a `tui.py` file to one of their apps that
registers a per-model overlay, declares a TUI-native action and a per-row key binding,
and registers a custom field-rendering widget for one of their model's fields. The
overlay does not require them to repeat any `ModelAdmin` configuration; declaring it
is purely additive.

**Why this priority**: extensibility is the central differentiator. The same priority
as US3 because the sample app exercises this story as a regression test for the
public extension surface, and the public surface MUST be frozen before v1.

**Independent Test**: the in-repo sample project MUST register a TUI overlay, a
custom field widget, and a TUI-native action. CI MUST fail if any of those three
extension points break. A model that has a `ModelAdmin` but no overlay MUST still
render and operate fully in the TUI.

**Acceptance Scenarios**:

1. **Given** a model with a registered `ModelAdmin` and no TUI overlay, **When** the
   operator browses it in the TUI, **Then** every aspect (columns, search, filters,
   actions, permissions, audit) behaves exactly as if an overlay were present with no
   declarations.
2. **Given** a TUI overlay that adds a TUI-native action and a key binding, **When**
   the operator presses the bound key on a row, **Then** the action runs against
   that row and lifecycle hooks (before / after action) fire in order.
3. **Given** a custom field widget registered for a custom field class, **When** that
   field appears on a detail form, **Then** the registered widget is used to render
   and capture input.
4. **Given** an operator without `change` permission on the model, **When** they open
   a record, **Then** mutating overlay affordances (TUI-native actions, edit binds)
   are hidden in addition to the web admin's own mutating affordances.

---

### Edge Cases

- An operator passes `--user <name>` for a user who does not exist, is inactive, or
  is not a staff user — the TUI MUST refuse to launch with a clear message and a
  non-zero exit code; no session is opened.
- A `ModelAdmin` overrides `change_view`, `get_urls`, custom templates, or admin JS
  to add behavior not expressible via the standard `ModelAdmin` declarations — the
  TUI MUST cover the standard surface only, MUST NOT silently drop the custom
  behavior in a way the operator can't detect, and the docs MUST direct the
  developer to reproduce that behavior via a TUI overlay.
- A model has hundreds of thousands of rows — the TUI MUST page using the model's
  configured page size and MUST never load full querysets.
- An action raises an exception mid-run — the TUI MUST surface the error, MUST NOT
  attribute success in the audit log for the failed work, and MUST leave the operator
  on a state from which they can retry or back out.
- A field's value contains terminal control sequences or characters that would
  corrupt the display — the TUI MUST render the value safely without breaking the
  surrounding layout.
- An operator's terminal is too narrow for the configured columns — the TUI MUST
  remain usable (truncation, horizontal navigation, or both) and MUST NOT crash.

## Requirements *(mandatory)*

### Functional Requirements

**Launch, identity, and trust model**

- **FR-001**: The package MUST install as a Django app and contribute a single
  management command that operators run from the project root to start the TUI.
- **FR-002**: The command MUST accept a `--user <username>` argument. When omitted,
  it MUST default to a superuser (with a clear error if no superuser exists or the
  default is ambiguous).
- **FR-003**: The command MUST refuse to launch when the requested user does not
  exist, is inactive, or is not a staff user, and MUST exit non-zero with a clear,
  actionable message.
- **FR-004**: The TUI v1 MUST NOT open a network port, accept a token, or expose a
  remote API. It runs in-process and is reached over the operator's existing shell
  or SSH access.
- **FR-005**: User documentation MUST state the v1 trust model explicitly: `--user`
  scopes permissions and attributes audit entries, but is NOT an access-control
  boundary; access control is the host's responsibility.

**Reusing admin behavior**

- **FR-006**: Querysets, search, filtering, ordering, pagination, form construction,
  validation, permissions, actions, and audit message construction MUST be produced
  by the registered `ModelAdmin` and Django admin internals. No code path MUST
  re-derive any of these.
- **FR-007**: Every read and every mutation MUST pass the same
  `has_view_permission`, `has_add_permission`, `has_change_permission`, and
  `has_delete_permission` checks the web admin would apply, scoped to the session
  user.
- **FR-008**: Every create, edit, delete, and action run MUST write a Django
  `LogEntry` attributed to the session user with a change message equivalent to
  what the web admin would record.

**Index and changelist**

- **FR-009**: The index screen MUST list apps and models exactly as the web admin
  index would list them for the session user.
- **FR-010**: The changelist MUST present the columns declared on the model's
  `ModelAdmin` (`list_display`) using the labels the admin would render.
- **FR-011**: The changelist MUST support search using the admin's `search_fields`,
  filtering using `list_filter`, sorting using admin column behavior, and pagination
  using the admin's per-page setting; result sets MUST match the web admin's.
- **FR-012**: Selecting a row MUST open a detail view that shows the same fieldsets,
  field ordering, and `readonly_fields` the web admin would show.

**Create, edit, delete**

- **FR-013**: A create form MUST be built from the admin's `get_form(request)` and
  MUST present and validate fields identically to the web admin, including
  field-level errors from `clean_*` methods and form-level errors from `clean()`.
- **FR-014**: An edit form MUST be built from `get_form(request, obj)` and MUST
  enforce `readonly_fields` so that the operator cannot edit fields the web admin
  would protect.
- **FR-015**: Saving MUST attribute the change to the session user via the
  appropriate admin audit hook (`log_addition` / `log_change`) and MUST fire the
  documented lifecycle hooks (before / after save, with a `created` flag).
- **FR-016**: Deleting a single record or a multi-row selection MUST require an
  explicit confirmation step that names the affected records, MUST refuse the
  operation if the session user lacks `delete` permission, and MUST emit
  `log_deletion` entries on success.

**Admin actions**

- **FR-017**: The TUI MUST surface the actions reported by
  `ModelAdmin.get_actions(request)` for the session user and MUST run them by
  calling the admin's own action callables.
- **FR-018**: Messages emitted by an action via `message_user(...)` MUST be captured
  and surfaced in the TUI with their original severity level.
- **FR-019**: An action that raises an exception MUST surface the error to the
  operator, MUST NOT write a `LogEntry` claiming success for the failed work, and
  MUST leave the operator on a recoverable state.

**Extensibility (`TuiAdmin` overlay) and defaults**

- **FR-020**: A per-model overlay class MUST exist whose only purpose is to add
  TUI-specific behavior; it MUST NEVER require re-declaring `ModelAdmin`
  configuration the operator already wrote (`list_display`, `search_fields`,
  `list_filter`, fieldsets, etc.).
- **FR-021**: A project that has registered `ModelAdmin` classes and NO overlay
  files MUST function fully — the index, changelist, detail, create, edit, delete,
  and actions all MUST work without any TUI-specific configuration.
- **FR-022**: Default rendering and behavior MUST be produced by the same registry
  and synthesized overlay path that third-party extensions use; there MUST NOT be a
  privileged internal code path that bypasses the public extension surface.
- **FR-023**: Overlays MUST autodiscover from each installed app under a fixed
  module name (parallel to how `ModelAdmin` is autodiscovered).
- **FR-024**: Overlays MUST expose declarative slots and request-aware hooks for:
  custom per-row and bulk actions; TUI-only key bindings; per-column rendering;
  per-model widget overrides; full-screen replacement of the changelist or detail
  view; and lifecycle hooks around save and action runs.

**Field widget registry**

- **FR-025**: A widget registry MUST map model-field classes to terminal renderers,
  MUST walk the field class's MRO so that subclasses of registered field types
  inherit a renderer without explicit registration, and MUST allow per-model
  overrides via the overlay.
- **FR-026**: The registry MUST ship default renderers covering the field types the
  default admin form produces (text, boolean, choice/enum, foreign key, date /
  datetime, JSON, numeric).

**Settings, theming, and the App surface**

- **FR-027**: All package-level configuration MUST live under a single project
  settings dict so the public surface stays small.
- **FR-028**: The whole TUI application MUST be subclassable so a downstream
  project can replace it wholesale; selection of the application class MUST be
  configurable via the settings dict and overridable per-invocation by a command
  flag.
- **FR-029**: Theming MUST be expressed in the TUI framework's own theming language;
  the package MUST NOT introduce a parallel theming abstraction.

**Public API surface and stability**

- **FR-030**: The documented public surface MUST consist only of:
  the `register` decorator, the overlay base class, the registry singleton, the
  field-widget registry, the application class, and the documented hook methods on
  the overlay. Everything else MUST be considered internal.
- **FR-031**: Adding a name to the public surface MUST require a written
  justification, a regression test, and a documentation entry.
- **FR-032**: Public API changes MUST follow SemVer with a documented deprecation
  path.

**Sample app coverage**

- **FR-033**: The repository MUST ship a sample Django project that registers at
  least one TUI overlay, at least one custom field widget, and at least one
  TUI-native action.
- **FR-034**: The project's automated checks MUST fail if any of the sample app's
  extension points stop working.

**Distribution and compatibility**

- **FR-035**: The package MUST be a single pip-installable distribution that does
  not require a non-Python build step at install time for end users.
- **FR-036**: The package MUST support the current Django LTS and the latest stable
  Django release; the supported Python floor MUST track Django's minimum.
- **FR-037**: The project MUST ship under the MIT license, and all bundled
  scaffolding MUST be MIT-compatible.

### Key Entities *(include if feature involves data)*

- **Session**: an in-process TUI run scoped to one Django staff/superuser. Carries
  the synthesized request used for every admin call. Ends when the operator exits.
- **Site registry (TUI)**: the project-wide registry mapping models to their TUI
  overlays. The default overlay is synthesized from the registered `ModelAdmin` when
  none is declared; explicit registrations override the default.
- **TUI overlay (`TuiAdmin`)**: the per-model extension object. Holds declarative
  TUI-only slots and the request-aware hooks listed in FR-024. NEVER duplicates
  `ModelAdmin` data.
- **Widget registry**: maps model-field classes to terminal renderers, with MRO
  walking and per-model override support (FR-025).
- **Audit entry**: a Django `LogEntry` written by the underlying admin hooks; the
  TUI never writes audit entries directly, it always routes through those hooks.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For models with no TUI overlay declared, the index, changelist, detail
  view, save, delete, and action paths MUST produce, for the same session user and
  inputs, results indistinguishable from the web admin's — measured by an automated
  test matrix exercising the sample project's apps across all four user stories.
- **SC-002**: In the sample project, an operator browsing 100,000-row tables MUST
  navigate the changelist (search, filter, sort, page) at p95 page-transition latency
  under 300 ms on a developer laptop, with memory use bounded by the configured page
  size rather than total table size.
- **SC-003**: An operator with view-only permission on one model and no permissions
  on the rest MUST see exactly that model in the index, and MUST be unable, through
  any documented action, to read or mutate any other model — verified by an
  automated permission-fidelity test that mirrors the web admin's behavior on the
  same fixture.
- **SC-004**: Every create, edit, delete, and action run in the sample project's
  test matrix MUST produce a `LogEntry` whose user, action flag, content type, and
  change message match those the web admin would produce for the same inputs.
- **SC-005**: A new contributor MUST be able to extend the TUI for one model by
  registering an overlay with a custom action, a key binding, and a per-cell render
  override, in under 30 minutes of reading the documentation — measured by an
  in-repo task that walks a contributor through it and is run during release
  candidates.
- **SC-006**: The public API surface MUST contain no more names than the list in
  FR-030 at v1.0.0; CI MUST fail on the introduction of a new top-level public name
  that lacks a justification, test, and docs entry.
- **SC-007**: First-time install (`pip install <package>`, add to `INSTALLED_APPS`,
  run the management command on an existing Django project) MUST succeed without any
  per-model configuration, on the supported Django and Python matrix.
- **SC-008**: When the operator launches with an invalid `--user`, the TUI MUST exit
  within 1 second with a non-zero status and a one-line, actionable error message —
  no Textual screen is presented and no session is opened.

## Assumptions

- The project's `ModelAdmin` registrations are the canonical source of truth for
  what's editable in the terminal; if a model is not registered with the web admin,
  it is not addressable via the TUI in v1.
- The operator has shell or SSH access to a host that can run `manage.py`. The TUI
  is not the access-control boundary (see FR-005); it relies on the host's own
  authentication.
- All work happens against the project's currently configured Django database in
  the current process; the TUI does not introduce its own data store, cache, or
  background workers in v1.
- The terminal supports ANSI colors and a reasonable size (at minimum 80 × 24);
  graceful degradation is in scope (see Edge Cases), but optimization for unusual
  terminals (e.g. Windows legacy consoles) is not.
- Custom `ModelAdmin` behavior that lives outside the standard declarative surface
  (custom `change_view`, custom URL routes, custom admin templates, admin JS) is
  EXPLICITLY OUT OF SCOPE for v1; developers reproduce that behavior via a TUI
  overlay if they need it in the terminal.
- Inlines are in scope for v1 but isolated to the final phase; if implementation
  cost forces a cut, inlines may be deferred to a point release with a documented
  workaround.
- A "remote/headless" client (a separate process, a network protocol, multiple
  concurrent operators) is OUT OF SCOPE for v1. Any such mode would be a future
  opt-in, authenticated addition (Constitution Principle VII).
- The PyPI distribution name is not yet chosen — `django-admin-tui` is taken. The
  working title is "Django Admin TUI"; a final name is selected before publishing.

## Dependencies

- Existing Django installation and project; `django.contrib.admin` enabled; one or
  more apps with `ModelAdmin` registrations.
- A Python interpreter capable of running the project (Django's supported floor).
- A modern terminal emulator with ANSI color support.

## Out of Scope (v1)

- A remote, headless, or multi-user mode (no network port, no token, no
  cross-process protocol).
- Customizations of the underlying admin that live outside its standard declarative
  surface (custom `change_view`, custom admin URLs/templates/JS).
- Non-Django data stores or non-admin-registered models.
- A built-in plug-in marketplace, telemetry, or update mechanism.
