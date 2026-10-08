# Synaps Optic Frontend

The HTMX/Jinja2 templates and static assets of the **Synaps Optic** video
editor, packaged as an installable Python distribution (`synaps-optic-frontend`,
import name `optic_frontend`). It contains no application code: only the
template tree, `htmx.min.js`, the Synapspaces design-system stylesheet and fonts
(`static/ds/`), a dark mode built on the same tokens, and the bundled music library.

![A tour of the preview: the home prompt, the editor, the Recast page and dark mode](docs/preview.gif)

**To run it**, see [docs/RUNNING.md](docs/RUNNING.md): a one-minute preview of every page with sample
data (`python tools/preview.py --serve`), or the full editor with the backend and a local database.

## How the backend consumes it

`synaps-optic-backend` depends on this package and reads three paths from it:

```python
from optic_frontend import TEMPLATES_DIR, STATIC_DIR, MUSIC_DIR

templates = Jinja2Templates(directory=TEMPLATES_DIR)
templates.env.filters["fromjson"] = json.loads   # templates rely on this filter
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
# MUSIC_DIR == STATIC_DIR / "music": the bundled tracks, served under /static/music
```

### Route contract

The templates hard-code the URL paths they talk to. The backend must serve:

- `/api/...` — JSON and HTMX form endpoints
- `/partials/...` — HTMX partial renders (polling, swaps)
- `/recast/...`, `/projects/...`, `/admin/...`, `/auth/...` — full pages
- `/static/htmx.min.js` — the only static reference in `base.html`

Rendering a page passes `request` (the templates read `request.url.path` and
`request.headers`) plus the per-page context the backend supplies. Changing a
path in a template is a contract change for the backend and needs a version bump.

## Tests

```sh
python -m venv .venv
.venv/Scripts/python -m pip install -e .[test]      # or .venv/bin/python on POSIX
.venv/Scripts/python -m pytest
```

The tests render the templates through the same Jinja2 setup the backend uses
(see `tests/conftest.py`) and check that the packaged data is complete.

Browser tests (Playwright, `tests/e2e/`) open the pages in Chromium: `pip install -e .[e2e]`,
`python -m playwright install chromium`, then `pytest -m e2e`. See [docs/RUNNING.md](docs/RUNNING.md).

## Releasing

The backend pins this package by git tag (currently `v0.3.1`).

1. Bump `version` in `pyproject.toml` and `__version__` in `optic_frontend/__init__.py`.
2. Commit, then tag: `git tag v0.1.1 && git push --tags`.
3. Update the pin in `synaps-optic-backend`.
