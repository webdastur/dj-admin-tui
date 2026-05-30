"""manage.py admin_tui — the only externally observable entry point.

Implements contracts/cli.md exactly:

  --user USERNAME    resolved per the rules below; default = lone superuser
  --app DOTTED       AdminTuiApp subclass to launch (overrides settings)
  --theme PATH       .tcss file to apply via App.CSS_PATH
  --no-color         pass through to Textual's no-color mode
  --debug            verbose logging to ./.admin_tui_debug.log

Exit codes:
  0  normal exit (operator quit or Ctrl-C)
  1  unexpected error reached the top of the loop
  2  --user resolution failed (does not exist / inactive / not staff)
  3  default-superuser resolution failed (none or multiple)
  4  --app could not be imported, or value is not an AdminTuiApp subclass
  5  --theme could not be opened or is not a valid .tcss
  64 unrecognised arguments (BaseCommand default)

Resolution and validation failures print a one-line stderr message and
exit BEFORE Textual is constructed (SC-008).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand
from django.utils.module_loading import import_string


def _stderr(message: str) -> None:
    print(message, file=sys.stderr)


class Command(BaseCommand):
    help = "Launch the admin TUI."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--user",
            default=None,
            help="The Django user to run as (default: the lone active superuser).",
        )
        parser.add_argument(
            "--app",
            default=None,
            help="Dotted import path of an AdminTuiApp subclass to launch.",
        )
        parser.add_argument(
            "--theme",
            default=None,
            help="Path to a Textual .tcss file applied as App.CSS_PATH.",
        )
        parser.add_argument(
            "--theme-name",
            default=None,
            help="Name of a bundled/registered theme (e.g. 'django').",
        )
        # --no-color and --force-color are provided by BaseCommand; we read
        # `options["no_color"]` in handle() (or check `self.style` directly)
        # rather than declaring our own.
        parser.add_argument(
            "--debug",
            action="store_true",
            help="Enable Textual devtools and verbose logging.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        from admin_tui import conf
        from admin_tui._internal.session import TuiSession

        # Make sure settings are loaded (in case AppConfig.ready hasn't fired
        # in this invocation path — e.g. a test that imports the command).
        conf._load()

        # --- user resolution (FR-002, FR-003) ------------------------------
        user = _resolve_user(options["user"])

        # --- app class resolution (FR-028) ---------------------------------
        try:
            if options["app"] is not None:
                app_class = import_string(options["app"])
                from admin_tui.app import AdminTuiApp

                if not isinstance(app_class, type) or not issubclass(
                    app_class, AdminTuiApp
                ):
                    _stderr(
                        f"--app value {options['app']!r} is not a subclass of "
                        f"admin_tui.AdminTuiApp."
                    )
                    sys.exit(4)
            else:
                app_class = conf.resolve_app_class()
        except (ImproperlyConfigured, ImportError, AttributeError) as exc:
            _stderr(f"--app could not be resolved: {exc}")
            sys.exit(4)

        # --- theme resolution (FR-029) -------------------------------------
        theme_path: Path | None = None
        theme_arg = options["theme"] or conf._loaded.get("THEME")
        if theme_arg is not None:
            theme_path = Path(theme_arg)
            if not theme_path.is_file() or theme_path.suffix != ".tcss":
                _stderr(
                    f"--theme path {theme_path} is not a readable .tcss file."
                )
                sys.exit(5)

        # --- theme-name resolution (FR-015/018) ----------------------------
        theme_name = options["theme_name"] or conf._loaded.get("THEME_NAME")
        if theme_name is not None:
            from admin_tui.themes import valid_theme_names

            if theme_name not in valid_theme_names():
                _stderr(
                    f"--theme-name {theme_name!r} is not a registered theme."
                )
                sys.exit(5)

        # --- build session and launch --------------------------------------
        session = TuiSession(
            user=user,
            app_class=app_class,
            theme_path=theme_path,
            theme_name=theme_name,
        )

        try:
            app_class(session=session).run()
        except KeyboardInterrupt:
            sys.exit(0)


# -- user resolution ----------------------------------------------------


def _resolve_user(requested: str | None) -> Any:
    """Resolve `--user` per contracts/cli.md. Exits the process on failure."""
    User = get_user_model()

    if requested is not None:
        try:
            user = User.objects.get(**{User.USERNAME_FIELD: requested})
        except User.DoesNotExist:
            _stderr(f"User {requested!r} does not exist.")
            sys.exit(2)
        if not user.is_active:
            _stderr(f"User {requested!r} is inactive.")
            sys.exit(2)
        if not user.is_staff:
            _stderr(f"User {requested!r} is not a staff user.")
            sys.exit(2)
        return user

    # --user omitted: find the single active staff superuser.
    candidates = list(
        User.objects.filter(is_superuser=True, is_active=True, is_staff=True)
    )
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        _stderr(
            "No active superuser found. Create one with "
            "`manage.py createsuperuser` or pass `--user <username>`."
        )
        sys.exit(3)
    names = ", ".join(getattr(u, User.USERNAME_FIELD) for u in candidates)
    _stderr(
        "Multiple active superusers exist; please specify one with "
        f"--user <username>. Found: {names}"
    )
    sys.exit(3)
