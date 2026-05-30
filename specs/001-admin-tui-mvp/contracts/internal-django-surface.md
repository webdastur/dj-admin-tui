# Contract: Internal Django admin surface we depend on

**This is not a public contract** — it's the *inverse*: the list of Django admin
APIs the package relies on, so we can detect, in CI, when a Django release
changes one. Every entry here is reused per Constitution I, never reimplemented.

If Django removes or changes any of these, we MUST update the wrapper code
(`admin_tui/core/*`), bump the supported Django range, and document the
adaptation. We MUST NOT silently fork the behaviour.

---

## ModelAdmin methods we call

| Method | Where we call it | Why |
|--------|-----------------|-----|
| `get_changelist_instance(request)` | `core/changelist.py` | Builds `ChangeList` with the version-correct args; **only** supported way to get one (R4). |
| `get_list_display(request)` | overlay default `get_list_columns` | Column names. |
| `get_search_fields(request)` | `core/changelist.py` | Search field list, passed to the changelist instance. |
| `get_list_filter(request)` | `core/changelist.py` | Filter spec. |
| `get_queryset(request)` | overlay default `get_queryset` | Base queryset. |
| `get_form(request, obj=None, change=False, fields=None)` | `core/forms.py` | Build the `ModelForm`. |
| `get_fieldsets(request, obj=None)` | overlay default | Fieldset ordering. |
| `get_readonly_fields(request, obj=None)` | overlay default | Readonly enforcement (FR-014). |
| `get_inline_instances(request, obj=None)` | `core/forms.py` (Phase 4) | Inlines (R15). |
| `get_actions(request)` | `core/actions.py` | The `{name: (func, name, desc)}` map. |
| `has_view_permission(request, obj=None)` | `_internal/permissions.py` | FR-007. |
| `has_module_permission(request)` | `screens/index.py` | Index filtering (US1 #1). |
| `has_add_permission(request)` | `screens/change.py`, action gate | FR-007. |
| `has_change_permission(request, obj=None)` | `screens/change.py`, row actions | FR-007. |
| `has_delete_permission(request, obj=None)` | action confirm + delete | FR-007. |
| `log_addition(request, obj, message)` | `core/audit.py` | FR-008. |
| `log_change(request, obj, message)` | `core/audit.py` | FR-008. |
| `log_deletion(request, obj, object_repr)` | `core/audit.py` | FR-008. |
| `construct_change_message(request, form, formsets, add=False)` | `core/audit.py` | SC-004 (parity). |
| `message_user(request, message, level, extra_tags="", fail_silently=False)` | called by actions — we capture, don't override | R6. |
| `save_model(request, obj, form, change)` | `core/forms.py` save path | Honour custom save hooks. |
| `delete_model(request, obj)` / `delete_queryset(request, queryset)` | action / delete path | Honour custom delete hooks. |

## Django internals we read

| Attribute / function | Where | Why |
|----------------------|-------|-----|
| `django.contrib.admin.site._registry` | `screens/index.py`, `sites.py` synthesis | Source of `{Model: ModelAdmin}`. The leading underscore is Django's convention but the registry is the documented integration point. |
| `django.contrib.admin.AdminSite.get_app_list(request)` | optionally, for the index ordering | Reuse the admin's grouping. |
| `django.utils.module_loading.autodiscover_modules` | `_internal/autodiscover.py` | R10. |
| `django.contrib.messages.storage.base.BaseStorage` | `core/messages.py` | R3 — base for `_CapturingMessageStorage`. |
| `django.test.RequestFactory` | `core/request.py` | R3 — build the synthetic `HttpRequest`. |
| `django.contrib.auth.get_user_model()` | `management/commands/admin_tui.py` | Resolve `--user`. |
| `django.contrib.contenttypes.ContentType.objects.get_for_model` | indirectly via `log_*` helpers | Audit. |

## API stability assumptions

Each row above is verified to be present and signature-stable in **Django 4.2
LTS, 5.2 LTS, and 6.0** as of 2026-05-30. The Django 6.0 release notes list
only two backwards-incompatible changes (the Python 3.12 floor and the MariaDB
10.5 drop) — neither touches our admin reuse surface. The CI matrix (R1, R2)
runs every test under the real Django release, so any signature drift surfaces
immediately.

If a future Django release deprecates or removes any of these (most likely
candidates: the `_registry` leading underscore, the `ChangeList` constructor),
the response order is:
1. Adapt `core/*` to the new shape behind the existing public surface.
2. Bump the supported Django range in `pyproject.toml`.
3. Note the adaptation in `docs/changelog.md`.
4. NEVER fork the behaviour: keep calling Django's helpers.

That's Constitution Principle I as a contract.
