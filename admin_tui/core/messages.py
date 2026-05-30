"""In-memory message storage for the synthetic request.

`ModelAdmin.message_user(...)` defers to Django's messages framework, which
requires `request._messages` to be a `BaseStorage` subclass. We want every
`message_user` call routed by the admin (and by user-defined actions) to be
captured so the TUI can surface them — without ever touching cookies, the
session, or a real response.

See research.md § R3 for the design rationale.
"""

from __future__ import annotations

from typing import Any

from django.contrib.messages.storage.base import BaseStorage


class _CapturingMessageStorage(BaseStorage):
    """Records every message in memory; ignores reads.

    Each captured entry is a `(level, message_str, extra_tags)` tuple in the
    order they were added.
    """

    def __init__(self, request: Any) -> None:
        super().__init__(request)
        self.captured: list[tuple[int, str, str]] = []

    # BaseStorage's persistence hooks — required overrides.
    def _get(self, *args: Any, **kwargs: Any) -> tuple[list, bool]:
        return [], True

    def _store(
        self,
        messages: list,
        response: Any,
        *args: Any,
        **kwargs: Any,
    ) -> list:
        return []

    # The public add() that `messages.add_message(...)` (and therefore
    # `ModelAdmin.message_user(...)`) ultimately calls.
    def add(
        self,
        level: int,
        message: Any,
        extra_tags: str = "",
    ) -> None:
        self.captured.append((level, str(message), extra_tags))
