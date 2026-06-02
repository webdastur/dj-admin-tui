#!/usr/bin/env python
"""Django management entry point for the sample_project test fixture."""

import os
import sys
from pathlib import Path

# Make the sample_project package importable regardless of cwd: the settings
# path is `sample_project.sample_project.settings`, which resolves only if the
# repo root (the parent of `sample_project/`) is on sys.path. Running this file
# as a script also puts its own directory (`<repo>/sample_project`) on sys.path,
# which would shadow the outer `sample_project` package with the inner one — so
# drop that entry (and the empty cwd entry) before adding the repo root.
SCRIPT_DIR = str(Path(__file__).resolve().parent)
REPO_ROOT = str(Path(__file__).resolve().parent.parent)
sys.path[:] = [p for p in sys.path if p not in ("", SCRIPT_DIR)]
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sample_project.sample_project.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
