"""A model in an app with NO tui.py — exercises FR-021 zero-config (SC-001).

The TUI must render and operate this model fully with no TUI-specific
declarations anywhere. The default-overlay synthesis path is the only
machinery in play.
"""

from __future__ import annotations

from django.db import models


class Note(models.Model):
    title = models.CharField(max_length=128)
    body = models.TextField(blank=True, default="")

    class Meta:
        ordering = ("title",)

    def __str__(self) -> str:
        return self.title
