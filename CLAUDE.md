<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan at
[specs/001-admin-tui-mvp/plan.md](specs/001-admin-tui-mvp/plan.md).

Companion artifacts in the same folder:
- `spec.md` — the feature spec (WHAT/WHY).
- `research.md` — Phase 0 decisions with rationale and rejected alternatives.
- `data-model.md` — in-memory entities and state transitions (no persistent storage).
- `contracts/` — public Python API, CLI, settings, and the internal Django surface we depend on.
- `quickstart.md` — operator-facing install / launch / extend walkthrough.

Project principles live in `.specify/memory/constitution.md` (v1.0.0); the
plan's Constitution Check section maps each principle to the design choice
that satisfies it. Reuse Django's admin internals; never reimplement them.
<!-- SPECKIT END -->
