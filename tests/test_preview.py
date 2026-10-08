"""tools/preview.py must keep rendering every main page with its sample data, so the documented
preview (docs/RUNNING.md) and docs/preview.gif cannot silently break when a template changes."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _preview():
    spec = importlib.util.spec_from_file_location("preview", ROOT / "tools" / "preview.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_preview_renders_every_page_and_links_them(tmp_path):
    preview = _preview()
    pages = preview.render_all(tmp_path)
    assert pages == [p[0] for p in preview.PAGES]
    assert (tmp_path / "static" / "ds" / "synapspaces.css").exists()
    for name in pages:
        html = (tmp_path / name).read_text(encoding="utf-8")
        assert 'href="static/ds/synapspaces.css"' in html, name
        assert "htmx:beforeRequest" in html, name  # no 404 polling without a server
    projects = (tmp_path / "projects.html").read_text(encoding="utf-8")
    assert 'href="editor.html"' in projects and 'href="recast.html"' in projects
