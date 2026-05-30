"""The bundled ``django`` theme — evokes the Django admin palette (v2 / FR-006a).

Maps the admin's signature colors (the blue/grey header family, link blue, the
django yellow accent, the admin error red and success green) onto Textual theme
variables, so every screen reads as the web admin within the terminal. This is
the default look with no appearance configuration.

Expressed purely as a ``textual.theme.Theme`` — no parallel theming abstraction
(Constitution VI).
"""

from __future__ import annotations

from textual.theme import Theme

#: The classic Django admin palette.
#:   header / secondary blue   #417690
#:   lighter accent blue       #79aec8
#:   django yellow             #f5dd5d
#:   link blue                 #447e9b
#:   success green             #70bf2b
#:   error red                 #ba2121
DJANGO_THEME = Theme(
    name="django",
    primary="#417690",
    secondary="#79aec8",
    accent="#f5dd5d",
    foreground="#303030",
    background="#ffffff",
    surface="#f8f8f8",
    panel="#dfe7eb",
    success="#70bf2b",
    warning="#efb80b",
    error="#ba2121",
    dark=False,
    variables={
        "block-cursor-foreground": "#ffffff",
        "block-cursor-background": "#417690",
        "footer-key-foreground": "#417690",
    },
)
