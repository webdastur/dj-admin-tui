"""Index permission scoping + zero-config rendering.

`tui_site.models_for(request)` is what `IndexScreen` reads. Asserting on
its output is the cleanest way to verify permission fidelity that mirrors
the web admin's behavior on the same fixture:
the same Django permission hooks (`has_module_permission`,
`has_view_permission`) drive both the web admin index and our index.
"""

from __future__ import annotations

import pytest
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from dj_admin_tui._internal.session import TuiSession
from dj_admin_tui.app import AdminTuiApp
from dj_admin_tui.core.request import build_request
from dj_admin_tui.sites import tui_site
from sample_project.library.models import Author, Book, Tag
from sample_project.plain_app.models import Note


@pytest.fixture(autouse=True)
def _reset_tui_site():
    """Clean TuiSite between tests so registrations don't leak."""
    tui_site._registry.clear()
    tui_site._synth_cache.clear()
    tui_site._screens.clear()
    return


def _grant_view(user, model_cls) -> None:
    ct = ContentType.objects.get_for_model(model_cls)
    perm = Permission.objects.get(
        codename=f"view_{model_cls._meta.model_name}",
        content_type=ct,
    )
    user.user_permissions.add(perm)


def _model_set(triples):
    return {model for _label, model, _overlay in triples}


@pytest.mark.django_db
def test_superuser_sees_every_registered_sample_model(superuser):
    """Superuser sees the four sample models (plus whatever else
    Django auto-registers — auth.User, auth.Group, etc.)."""
    request = build_request(superuser)
    visible = _model_set(tui_site.models_for(request))
    assert {Book, Author, Tag, Note}.issubset(visible)


@pytest.mark.django_db
def test_view_only_on_one_model_hides_the_rest(staff_only_user):
    """A view-only-on-Book user sees ONLY Book."""
    _grant_view(staff_only_user, Book)
    request = build_request(staff_only_user)
    visible = _model_set(tui_site.models_for(request))
    assert visible == {Book}, f"Expected only Book, got {visible}"


@pytest.mark.django_db
def test_view_on_two_models_in_same_app(staff_only_user):
    """Module-perm derives from having ANY perm in the app."""
    _grant_view(staff_only_user, Book)
    _grant_view(staff_only_user, Author)
    request = build_request(staff_only_user)
    visible = _model_set(tui_site.models_for(request))
    assert visible == {Book, Author}


@pytest.mark.django_db
def test_no_perms_user_sees_nothing(staff_only_user):
    """A staff user with no perms sees an empty index."""
    request = build_request(staff_only_user)
    visible = _model_set(tui_site.models_for(request))
    assert visible == set()


@pytest.mark.django_db
def test_plain_app_note_is_visible_with_zero_config(superuser):
    """A model in an app with NO tui.py still shows up."""
    request = build_request(superuser)
    visible = _model_set(tui_site.models_for(request))
    assert Note in visible


@pytest.mark.django_db
def test_models_for_returns_app_label_grouping(superuser):
    request = build_request(superuser)
    triples = tui_site.models_for(request)
    app_labels = {t[0] for t in triples}
    # Sample-project apps must appear; auth ships with Django's admin.
    assert {"library", "plain_app"}.issubset(app_labels)


@pytest.mark.django_db
def test_models_for_results_are_sorted_stably(superuser):
    """Same inputs → same output ordering."""
    request_a = build_request(superuser)
    request_b = build_request(superuser)
    triples_a = tui_site.models_for(request_a)
    triples_b = tui_site.models_for(request_b)
    assert [(label, model.__name__) for label, model, _o in triples_a] == [
        (label, model.__name__) for label, model, _o in triples_b
    ]


# -- One Pilot smoke test: the App really mounts to IndexScreen. ----


@pytest.mark.django_db
async def test_app_boots_to_index_screen_for_superuser(superuser):
    from dj_admin_tui.screens.index import IndexScreen

    session = TuiSession(user=superuser, app_class=AdminTuiApp)
    app = AdminTuiApp(session=session)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert isinstance(app.screen, IndexScreen)
