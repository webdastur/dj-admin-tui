"""CLI exit-code contract.

We invoke the command in-process via `call_command(...)`, which forwards
`sys.exit(N)` as `SystemExit(N)`. This gives us pytest-django's transactional
DB fixtures (so the user-resolution logic can actually find users created in
the test) without subprocess/test-DB isolation problems.

The SC-008 "exits within 1 second" bound is validated via `time.perf_counter()`
around each call. In-process latency is dominated by Django setup which has
already happened by the time the first test runs, so this is a fast bound.
"""

from __future__ import annotations

import sys
import time

import pytest
from django.core.management import call_command


def _call_admin_tui(*args: str) -> tuple[int, str, float]:
    """Invoke `admin_tui` command in-process, return (exit_code, stderr, elapsed).

    The command uses `sys.exit(N)`; we catch SystemExit and report the code.
    Stderr is captured via redirection.
    """
    import io

    captured_stderr = io.StringIO()
    original_stderr = sys.stderr
    sys.stderr = captured_stderr
    started = time.perf_counter()
    try:
        try:
            call_command("admin_tui", *args)
        except SystemExit as exc:
            return int(exc.code or 0), captured_stderr.getvalue(), time.perf_counter() - started
        return 0, captured_stderr.getvalue(), time.perf_counter() - started
    finally:
        sys.stderr = original_stderr


@pytest.mark.django_db
def test_nonexistent_user_exits_with_code_2(db):
    code, stderr, elapsed = _call_admin_tui("--user", "does_not_exist_xyz")
    assert code == 2, stderr
    assert "does not exist" in stderr.lower()
    assert elapsed < 1.0, f"Exit took {elapsed:.2f}s (SC-008 bound: 1s)"


@pytest.mark.django_db
def test_inactive_user_exits_with_code_2(inactive_staff_user):
    code, stderr, elapsed = _call_admin_tui("--user", inactive_staff_user.username)
    assert code == 2, stderr
    assert "inactive" in stderr.lower()
    assert elapsed < 1.0


@pytest.mark.django_db
def test_non_staff_user_exits_with_code_2(non_staff_user):
    code, stderr, elapsed = _call_admin_tui("--user", non_staff_user.username)
    assert code == 2, stderr
    assert "staff" in stderr.lower()
    assert elapsed < 1.0


@pytest.mark.django_db
def test_no_superuser_exits_with_code_3(db, django_user_model):
    # Ensure no active superuser exists in the test DB.
    django_user_model.objects.filter(is_superuser=True).delete()
    code, stderr, elapsed = _call_admin_tui()
    assert code == 3, stderr
    assert "superuser" in stderr.lower()
    assert elapsed < 1.0


@pytest.mark.django_db
def test_multiple_superusers_exits_with_code_3(db, django_user_model):
    django_user_model.objects.filter(is_superuser=True).delete()
    django_user_model.objects.create_superuser(
        username="su1", email="su1@test.example", password="x"
    )
    django_user_model.objects.create_superuser(
        username="su2", email="su2@test.example", password="x"
    )
    code, stderr, elapsed = _call_admin_tui()
    assert code == 3, stderr
    assert "multiple" in stderr.lower() or "specify one" in stderr.lower()
    assert elapsed < 1.0


@pytest.mark.django_db
def test_invalid_app_dotted_path_exits_with_code_4(superuser):
    code, stderr, elapsed = _call_admin_tui(
        "--user",
        superuser.username,
        "--app",
        "pkg.does.not.exist.NotAClass",
    )
    assert code == 4, stderr
    assert "could not be resolved" in stderr.lower() or "not a subclass" in stderr.lower()
    assert elapsed < 1.0


@pytest.mark.django_db
def test_app_value_that_is_not_a_subclass_exits_with_code_4(superuser):
    code, stderr, elapsed = _call_admin_tui(
        "--user",
        superuser.username,
        "--app",
        "admin_tui.options.TuiAdmin",  # not an AdminTuiApp
    )
    assert code == 4, stderr
    assert "not a subclass" in stderr.lower() or "could not be resolved" in stderr.lower()
    assert elapsed < 1.0
