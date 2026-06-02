# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project follows
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.0.1] — 2026-06-02

Initial public release.

### Added

- Terminal UI for the Django admin built on [Textual](https://textual.textualize.io/):
  index, changelist, change/add/edit, and action-confirmation screens.
- **Zero-config** operation — any project with `ModelAdmin`s works without a
  `tui.py`, via a default `TuiAdmin` overlay synthesised from the `ModelAdmin`.
- Full CRUD that reuses the admin's `get_form` → validation → `save_model` →
  `save_related` → `log_addition`/`log_change` sequence, including foreign keys,
  many-to-many, and multi-line text fields.
- Search, sort, and filtering driven by `search_fields`, `list_filter`, and
  Django's ordering internals.
- Bulk admin actions and per-row actions, with confirmation.
- Permission scoping and audit (`LogEntry`) matching the web admin, via a single
  synthetic-request choke point.
- The `manage.py admin_tui` management command (`--user`, `--app`, `--theme`,
  `--theme-name`, `--debug`).
- A bundled `django` theme plus a single-stylesheet design system that can be
  overridden with a project `.tcss`.
- Public API of five names: `register`, `TuiAdmin`, `tui_site`, `field_widgets`,
  `AdminTuiApp`.
- Documentation site (MkDocs Material) published on Read the Docs.

[Unreleased]: https://github.com/webdastur/dj-admin-tui/compare/v0.0.1...HEAD
[0.0.1]: https://github.com/webdastur/dj-admin-tui/releases/tag/v0.0.1
