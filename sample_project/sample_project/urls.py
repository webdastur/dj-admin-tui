from django.contrib import admin
from django.urls import path

# The TUI is reached via `manage.py admin_tui`, not over HTTP. The web admin
# is wired up for parity testing only — tests compare TUI behaviour against
# the web admin running in the same process.
urlpatterns = [
    path("admin/", admin.site.urls),
]
