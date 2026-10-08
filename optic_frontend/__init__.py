"""Synaps Optic Frontend: the HTMX/Jinja2 templates and static assets of the
Synaps Optic video editor, packaged as data.

The backend (synaps-optic-backend) mounts ``STATIC_DIR`` at ``/static`` and
renders ``TEMPLATES_DIR`` with Jinja2 (``Jinja2Templates(directory=TEMPLATES_DIR)``),
registering a ``fromjson`` filter (``json.loads``) that the templates rely on.
``MUSIC_DIR`` is the bundled music library served under ``/static/music``.
"""
from importlib.resources import files
from pathlib import Path

__version__ = "0.3.1"

_ROOT = Path(str(files("optic_frontend")))

TEMPLATES_DIR: Path = _ROOT / "templates"
STATIC_DIR: Path = _ROOT / "static"
MUSIC_DIR: Path = STATIC_DIR / "music"

__all__ = ["__version__", "TEMPLATES_DIR", "STATIC_DIR", "MUSIC_DIR"]
