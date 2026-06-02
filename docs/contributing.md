# Contributing

Thanks for your interest in improving **dj-admin-tui**. Issues and pull requests
are welcome.

## Development setup

The project uses [uv](https://docs.astral.sh/uv/) for environment and dependency
management.

```bash
git clone https://github.com/webdastur/dj-admin-tui
cd dj-admin-tui
uv sync --dev            # create .venv and install dev dependencies
```

## Running the tests

```bash
uv run pytest -q                       # full suite
uv run pytest -k m2m                   # by name
uv run pytest -m "not slow"            # skip the slow performance tests
```

Integration tests drive the real app headlessly with Textual's `Pilot`. They run
the app in a worker thread, so tests that launch it use the `transactional_db`
fixture (not `db`) — the app's database connection only sees committed rows.

## Linting and formatting

```bash
uv run ruff check           # lint
uv run ruff format          # auto-format
uv run ruff format --check  # verify formatting (what CI runs)
```

CI runs `ruff check`, `ruff format --check`, and the test matrix across the
supported Python and Django versions.

## Trying it against the sample project

The repo ships a small Django project under `sample_project/` for manual testing:

```bash
uv run python sample_project/manage.py migrate
uv run python sample_project/manage.py createsuperuser
uv run python sample_project/manage.py admin_tui
```

## Building the docs

```bash
uv run --extra docs mkdocs serve     # live-reload at http://127.0.0.1:8000
uv run --extra docs mkdocs build --strict
```

## Design principle

The core rule: **reuse Django's admin; never reimplement it.** Querysets,
search, filtering, ordering, pagination, form construction, validation,
permissions, actions, and audit must all come from the registered `ModelAdmin`
and Django's own internals. The TUI renders that output and adds
presentation/interaction only. If a change re-derives admin behaviour, prefer
bridging to Django instead.

## Public API stability

The public surface is exactly five names (`register`, `TuiAdmin`, `tui_site`,
`field_widgets`, `AdminTuiApp`); a regression test freezes it. Adding a public
name needs justification, a test, and docs. Changes follow SemVer with a
deprecation path — see the [API reference](api.md).
