"""Top-level pytest configuration for admin_tui's test suite.

- Ensures `sample_project` is importable as a package (parent on sys.path).
- Configures Django via pytest-django (settings module set in pyproject.toml).
- Provides reusable user fixtures (superuser, staff-only user with scoped perms).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# The sample project lives under `sample_project/` at repo root. Its inner
# settings module is imported as `sample_project.sample_project.settings`,
# which means `sample_project` (the outer dir) needs to be a package, i.e.
# repo_root needs to be on sys.path. Pytest may not put it there for us
# depending on how it's invoked.
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


@pytest.fixture
def superuser(db, django_user_model):
    """Active superuser. Use for happy-path admin-fidelity tests."""
    return django_user_model.objects.create_superuser(
        username="superadmin",
        email="super@example.test",
        password="not-secret-test-only",
    )


@pytest.fixture
def staff_only_user(db, django_user_model):
    """Staff user with NO model permissions. Tests permission filtering."""
    return django_user_model.objects.create_user(
        username="staff_no_perms",
        email="staff@example.test",
        password="not-secret-test-only",
        is_staff=True,
        is_active=True,
    )


@pytest.fixture
def inactive_staff_user(db, django_user_model):
    """Inactive staff user — should be refused at CLI resolution."""
    return django_user_model.objects.create_user(
        username="staff_inactive",
        email="inactive@example.test",
        password="not-secret-test-only",
        is_staff=True,
        is_active=False,
    )


@pytest.fixture
def non_staff_user(db, django_user_model):
    """Active non-staff user — also refused at CLI resolution."""
    return django_user_model.objects.create_user(
        username="not_staff",
        email="notstaff@example.test",
        password="not-secret-test-only",
        is_staff=False,
        is_active=True,
    )
