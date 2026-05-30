# Release Checklist

Codifies the SC-005 release-candidate gate from the spec: **a new
contributor MUST be able to extend the TUI for one model by registering
an overlay with a custom action, a key binding, and a per-cell render
override, in under 30 minutes of reading the documentation.**

Run this list against every release candidate. Failing items block the
release until fixed.

## Quality gates

- [ ] `uv run pytest -q` is green on every supported (Python, Django) cell.
- [ ] `uv run pytest -q -m slow` (performance suite) — page-transition
      p95 under 300 ms on 100k rows (SC-002).
- [ ] `uv run ruff check && uv run ruff format --check` — clean.
- [ ] `tests/unit/test_public_api.py` passes — public API surface still
      exactly the 5 documented names (FR-030 / SC-006).
- [ ] `uv build` succeeds; the resulting wheel installs cleanly into a
      fresh `uv` env and the bundled command runs against a one-line
      Django project (SC-007).
- [ ] CI matrix is green for every (Python × Django) cell — see
      `.github/workflows/ci.yml`.

## SC-005 contributor walkthrough (timed)

Pick a contributor unfamiliar with the codebase. Hand them only this:

1. The package install command.
2. `docs/quickstart.md` (no other docs, no codebase tour).

Time them from `pip install` to a working overlay in their own Django
project. The overlay must include:

- A registered `TuiAdmin` overlay for one of their models.
- A custom `row_actions` entry that the operator can run from the
  changelist.
- A per-cell `render_cell` override visible in at least one column.

**Target: ≤ 30 minutes.**

If the timing fails:
- Note where the contributor stalled.
- Update `docs/quickstart.md` to remove the friction.
- Re-run the gate against a fresh contributor.

Record the most recent timed run + contributor name + duration here for
each release:

| Release | Contributor | Duration | Notes |
|---|---|---|---|
| _(none yet)_ | — | — | — |

## Constitution review

- [ ] No principle from `.specify/memory/constitution.md` is violated by
      the build.
- [ ] If any deviation has been accepted, the deviation note is in the
      relevant PR and the PR description quotes the principle being
      deviated from.

## Final operator-facing check

- [ ] `manage.py admin_tui --user <some-staff-user>` boots into the index
      against the sample project. The 5 keymap categories (browse,
      search/sort/paginate, create/edit, delete + actions, tool screens)
      all work for a manual five-minute walkthrough.
