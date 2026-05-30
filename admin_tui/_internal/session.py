"""TuiSession — per-run context attached to every synthetic request.

Holds the resolved session user, the start timestamp, the selected App class
and theme, and the cumulative messages-log + compat report. Created by the
management command (`admin_tui/management/commands/admin_tui.py`) after
`--user` is resolved, and passed to `AdminTuiApp(session=...)`.

Internal — see data-model.md § 1 for the contract.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from admin_tui.app import AdminTuiApp


@dataclass
class TuiSession:
    """One run of `manage.py admin_tui`. Single instance, in-memory."""

    user: Any
    """Resolved Django user. `user.is_active and user.is_staff` invariants
    are enforced at the CLI layer (FR-003); we don't re-check here."""

    app_class: "type[AdminTuiApp]"
    """The AdminTuiApp subclass to instantiate (`ADMIN_TUI["APP_CLASS"]` or
    overridden by `--app`)."""

    started_at: datetime = field(default_factory=datetime.now)
    """Wall-clock start; never persisted."""

    theme_path: Path | None = None
    """Resolved `--theme` path (or `ADMIN_TUI["THEME"]`); `None` for builtin."""

    messages_log: list[tuple[int, str, str]] = field(default_factory=list)
    """Cumulative `(level, message, extra_tags)` from every action's
    `message_user` call across the session."""

    compat_report: dict[Any, list[str]] = field(default_factory=dict)
    """`{Model: [override_name, ...]}` populated once by
    `admin_tui._internal.compat.scan(admin.site)` (Phase 7 / T078)."""

    compat_warned: set[Any] = field(default_factory=set)
    """Models the operator has already been warned about. Set entries are
    added on first access; the set is checked before surfacing a notify."""
