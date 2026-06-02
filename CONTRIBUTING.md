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
uv run ruff check           # lint (CI runs this with no path args)
uv run ruff format          # auto-format
uv run ruff format --check  # verify formatting (what CI runs)
```

CI runs `ruff check`, `ruff format --check`, a `mkdocs build --strict`, and the
test matrix across the supported Python and Django versions.

## Trying it against the sample project

The repo ships a small Django project under `sample_project/` for manual testing:

```bash
uv run python sample_project/manage.py migrate
uv run python sample_project/manage.py createsuperuser
uv run python sample_project/manage.py admin_tui
```

## Building the docs

```bash
uv run --extra docs mkdocs serve            # live-reload at http://127.0.0.1:8000
uv run --extra docs mkdocs build --strict
```

## Design principle

The core rule: **reuse Django's admin; never reimplement it.** Querysets,
search, filtering, ordering, pagination, form construction, validation,
permissions, actions, and audit must all come from the registered `ModelAdmin`
and Django's own internals. The TUI renders that output and adds
presentation/interaction only.

## Public API stability

The public surface is exactly five names (`register`, `TuiAdmin`, `tui_site`,
`field_widgets`, `AdminTuiApp`); a regression test freezes it. Adding a public
name needs justification, a test, and docs. Changes follow SemVer with a
deprecation path.

## Releasing (maintainers)

Releases publish to PyPI via **Trusted Publishing (OIDC)** — there is no API
token in the repository. The `.github/workflows/release.yml` workflow runs on a
version tag, builds the sdist + wheel, runs `twine check`, and publishes.

One-time PyPI setup (per project):

1. On PyPI, go to the project (or "pending publishers" for a not-yet-created
   project) and add a **GitHub Actions** trusted publisher with:
   - Owner: `webdastur`
   - Repository: `dj-admin-tui`
   - Workflow name: `release.yml`
   - Environment: `pypi`
2. Confirm the distribution name `dj-admin-tui` is available on PyPI.

To cut a release:

```bash
# 1. Bump `version` in pyproject.toml and add a CHANGELOG.md entry.
# 2. Commit, then tag and push the tag:
git tag v0.0.1
git push origin v0.0.1
```

Pushing the tag triggers the release workflow.
