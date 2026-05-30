"""Wrap `ModelAdmin.get_changelist_instance(...)` — Constitution I in code.

`get_changelist_instance` is the documented, version-stable way to build a
`ChangeList` for the active Django version. We never instantiate
`ChangeList` directly — its `__init__` signature has changed between
Django releases.

Callers pass a `query` dict whose keys are Django's standard changelist
parameters (`q` for search, `p` for page, `o` for ordering, plus the
filter-spec keys like `featured__exact`); we rewrite `request.GET` to that
QueryDict so the ChangeList sees them.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.http import QueryDict

if TYPE_CHECKING:
    from django.contrib.admin.views.main import ChangeList
    from django.contrib.admin import ModelAdmin
    from django.http import HttpRequest


def _build_changelist(
    model_admin: "ModelAdmin",
    request: "HttpRequest",
    *,
    query: dict[str, Any] | None = None,
) -> "ChangeList":
    """Return a `ChangeList` honoring `query` (search / filter / sort / page).

    Mutates `request.GET` on the passed request. Callers should treat
    `request` as exclusively theirs for the duration of the call (we don't
    snapshot/restore — the synthetic request is rebuilt per interaction).
    """
    if query is not None:
        qd = QueryDict(mutable=True)
        for k, v in query.items():
            if v is None:
                continue
            # QueryDict expects str values; we coerce ints and bools.
            qd[k] = str(v)
        qd._mutable = False
        request.GET = qd
    return model_admin.get_changelist_instance(request)
