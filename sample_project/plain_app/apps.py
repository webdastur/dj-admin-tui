from django.apps import AppConfig


class PlainAppConfig(AppConfig):
    name = "sample_project.plain_app"
    label = "plain_app"
    verbose_name = "Plain App (no tui.py)"
    default_auto_field = "django.db.models.BigAutoField"
