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

#: The Django admin **dark** palette (the admin's own dark mode), the default
#: look — high-contrast dark surfaces with the admin's blue/teal accents.
DJANGO_DARK_THEME = Theme(
    name="django-dark",
    primary="#79aec8",
    secondary="#417690",
    accent="#f5dd5d",
    foreground="#e6e6e6",
    background="#121212",
    surface="#1e2226",
    panel="#264b5d",
    success="#8fd14f",
    warning="#efb80b",
    error="#e9573f",
    dark=True,
    variables={
        "block-cursor-foreground": "#0c1116",
        "block-cursor-background": "#79aec8",
        "footer-key-foreground": "#79aec8",
        "input-selection-background": "#417690 60%",
    },
)
