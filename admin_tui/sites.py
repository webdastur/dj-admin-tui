"""TuiSite — the per-process registry mapping models to TuiAdmin overlays.

Mirrors `django.contrib.admin.site` in shape: a `register()` method, a
`_registry` dict, plus per-model overlay lookup. The default singleton
`tui_site` is what `register()` and `@register(...)` write to. Synthesised
defaults travel the same code path as third-party overlays (Constitution
Principle IV).

See data-model.md § 2 and research.md § R9 for the contract.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.contrib import admin as django_admin
from django.core.exceptions import ImproperlyConfigured

if TYPE_CHECKING:
    from django.db.models import Model
    from django.http import HttpRequest
    from textual.screen import Screen

    from admin_tui.options import TuiAdmin


class AlreadyRegistered(Exception):
    """Raised when the same model is registered twice on a TuiSite."""


class TuiSite:
    """A process-wide registry mapping Django models to TuiAdmin overlays.

    The default singleton is `admin_tui.tui_site`. Custom sites are not
    part of the public API at v1.0 (Constitution V — Deferred additions).
    """

    def __init__(self) -> None:
        from django.db.models import Model

        self._registry: dict[type[Model], "TuiAdmin"] = {}
        self._screens: dict[str, type["Screen"]] = {}
        # Cache so re-synthesising for the same ModelAdmin instance returns
        # the same TuiAdmin instance (identity stability matters for tests
        # and for "is" comparisons in screen routing).
        self._synth_cache: dict[Any, "TuiAdmin"] = {}

    # -- registration -------------------------------------------------------

    def register(
        self,
        model: "type[Model]",
        overlay_cls: "type[TuiAdmin] | None" = None,
    ) -> None:
        """Register an overlay class for `model`.

        If `overlay_cls` is `None`, instantiate the base `TuiAdmin` against
        the model's `ModelAdmin`. Raises `AlreadyRegistered` on duplicates.
        Raises `ImproperlyConfigured` if the model isn't registered with
        django.contrib.admin.
        """
        from admin_tui.options import TuiAdmin

        if model in self._registry:
            raise AlreadyRegistered(
                f"{model.__module__}.{model.__name__} is already registered "
                f"on this TuiSite."
            )
        model_admin = self._lookup_model_admin(model)
        cls = overlay_cls if overlay_cls is not None else TuiAdmin
        self._registry[model] = cls(model_admin)

    def unregister(self, model: "type[Model]") -> None:
        """Drop the overlay (if any). Idempotent."""
        self._registry.pop(model, None)

    def is_registered(self, model: "type[Model]") -> bool:
        return model in self._registry

    # -- global tool screens -----------------------------------------------

    def register_screen(self, slug: str, screen_cls: "type[Screen]") -> None:
        """Register a global "tool" screen reachable from the index.

        Raises if `slug` collides. The default `g <slug>` binding on the
        index opens the registered screen.
        """
        if slug in self._screens:
            raise AlreadyRegistered(
                f"Global tool screen slug {slug!r} is already registered."
            )
        self._screens[slug] = screen_cls

    # -- lookup / synthesis -------------------------------------------------

    def get_or_synthesize(self, model: "type[Model]") -> "TuiAdmin":
        """Return the registered overlay, or synthesise a default.

        The default is a vanilla `TuiAdmin(model_admin)` whose declarative
        slots delegate to the underlying `ModelAdmin` (Constitution III —
        zero-config). Cached so successive lookups return the same instance.
        """
        if model in self._registry:
            return self._registry[model]

        model_admin = self._lookup_model_admin(model)
        cached = self._synth_cache.get(model_admin)
        if cached is not None:
            return cached

        from admin_tui.options import TuiAdmin

        synth = TuiAdmin._synthesize(model_admin)
        self._synth_cache[model_admin] = synth
        return synth

    def models_for(
        self,
        request: "HttpRequest",
    ) -> list[tuple[str, "type[Model]", "TuiAdmin"]]:
        """Return `(app_label, model, overlay)` triples visible to the user.

        Filters by `has_module_permission` (per-app) and
        `has_view_permission` (per-model), exactly like the web admin index.
        """
        results: list[tuple[str, "type[Model]", "TuiAdmin"]] = []
        for model, model_admin in django_admin.site._registry.items():
            if not model_admin.has_module_permission(request):
                continue
            if not model_admin.has_view_permission(request):
                continue
            overlay = self.get_or_synthesize(model)
            results.append((model._meta.app_label, model, overlay))
        # Stable sort: app_label, then model name (matches admin.site).
        results.sort(key=lambda triple: (triple[0], triple[1]._meta.object_name))
        return results

    # -- internal -----------------------------------------------------------

    def _lookup_model_admin(self, model: "type[Model]") -> Any:
        try:
            return django_admin.site._registry[model]
        except KeyError as exc:
            raise ImproperlyConfigured(
                f"{model.__module__}.{model.__name__} is not registered "
                f"with django.contrib.admin.site. The TUI mirrors the admin "
                f"registry — see specs/.../spec.md § Assumptions."
            ) from exc


#: The default process-wide TuiSite. Public API (Constitution V).
tui_site = TuiSite()
