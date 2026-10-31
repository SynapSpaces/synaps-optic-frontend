"""The app shell (static/app): manifest, icons, offline page, service worker, and base.html's install tags."""
import json
import re

import optic_frontend

APP = optic_frontend.STATIC_DIR / "app"


def test_manifest_is_valid_and_points_at_shipped_icons():
    data = json.loads((APP / "manifest.webmanifest").read_text(encoding="utf-8"))
    assert data["name"] == "Synaps Optic" and data["short_name"] == "Optic"
    assert data["display"] == "standalone" and data["scope"] == "/" and data["start_url"].startswith("/projects")
    sizes = {i["sizes"] for i in data["icons"]}
    assert {"192x192", "512x512"} <= sizes
    assert any(i["purpose"] == "maskable" for i in data["icons"])
    for icon in data["icons"]:
        assert icon["src"].startswith("/static/app/")
        assert (optic_frontend.STATIC_DIR / icon["src"].removeprefix("/static/")).is_file(), icon["src"]
    assert (APP / "apple-touch-icon.png").is_file()


def test_service_worker_precaches_only_files_that_exist_and_skips_writes():
    sw = (APP / "sw.js").read_text(encoding="utf-8")
    shell = re.findall(r'"(/static/[^"]+)"', sw.split("const NEVER")[0])
    assert "/static/app/offline.html" in shell and "/static/ds/synapspaces.css" in shell
    for path in shell:
        assert (optic_frontend.STATIC_DIR / path.removeprefix("/static/")).is_file(), path
    assert 'req.method !== "GET"' in sw
    never = sw.split("const NEVER")[1].split("\n")[0]  # the regex list: /^\/api\//, ...
    for path in ("api", "auth", "admin", "static\\/music"):
        assert f"\\/{path}\\/" in never, path  # never cached


def test_base_template_installs_the_shell():
    # the tags are static text in the head, so the source is asserted (a render needs the backend's request)
    html = (optic_frontend.TEMPLATES_DIR / "base.html").read_text(encoding="utf-8")
    assert '<link rel="manifest" href="/static/app/manifest.webmanifest">' in html
    assert '<link rel="apple-touch-icon" href="/static/app/apple-touch-icon.png">' in html
    assert '<meta name="apple-mobile-web-app-capable" content="yes">' in html
    assert 'navigator.serviceWorker.register("/sw.js", { scope: "/" })' in html
    assert 'location.protocol === "https:"' in html  # no registration on plain http


def test_offline_page_is_self_contained():
    page = (APP / "offline.html").read_text(encoding="utf-8")
    assert "<!doctype html>" in page.lower() and "/static/ds/synapspaces.css" in page
    assert "location.reload()" in page
