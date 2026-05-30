from django.apps import AppConfig


class LibraryConfig(AppConfig):
    name = "sample_project.library"
    label = "library"
    verbose_name = "Library"
    default_auto_field = "django.db.models.BigAutoField"
