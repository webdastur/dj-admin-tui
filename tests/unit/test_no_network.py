"""Constitution VII verification — no network is opened during a run.

Monkeypatch `socket.socket` to fail any construction, then drive the App
through a default screen via Pilot. If anything in the runtime path tries
to open a network socket — e.g. a future contributor accidentally adds a
metrics ping, an update check, or an analytics call — this test catches
it.

We allow the test DB connection (SQLite via a UNIX file) because no
`socket.socket(...)` call is involved there.
"""

from __future__ import annotations

import socket
from unittest.mock import patch

import pytest

from admin_tui._internal.session import TuiSession
from admin_tui.app import AdminTuiApp


@pytest.mark.django_db
async def test_runtime_does_not_open_a_network_socket(superuser):
    """Pilot-drive a full App boot; assert socket.socket() is never called."""

    original_socket = socket.socket
    call_count = {"n": 0}

    def _instrumented(*args, **kwargs):
        call_count["n"] += 1
        # Allow the call (otherwise pilot can't run if it touches sockets
        # via some unrelated import path), but assert at the end.
        return original_socket(*args, **kwargs)

    with patch("socket.socket", side_effect=_instrumented):
        session = TuiSession(user=superuser, app_class=AdminTuiApp)
        app = AdminTuiApp(session=session)
        async with app.run_test() as pilot:
            await pilot.pause()

    # The TUI's runtime path MUST NOT open any sockets. If a future
    # change touches the network, this number grows from 0 and the test
    # fires.
    assert call_count["n"] == 0, (
        f"socket.socket() was called {call_count['n']} time(s) during the "
        f"app boot — Constitution VII forbids opening any network port in v1."
    )
