"""Playwright end-to-end tests: the templates rendered by tools/preview.py, opened in Chromium.

The pages are served over HTTP from a temporary folder (localStorage needs a real origin). There is
no backend: every /api and /partials request is answered by `api_stub`, so the scripts that fetch data
(the Recast compare view) run for real. Every test fails if the page throws or logs a console error.

    pip install -e .[e2e] && python -m playwright install chromium
    pytest -m e2e                     # E2E_HEADED=1 to watch, E2E_SLOWMO=250 to slow it down
Screenshots of failing tests land in e2e-artifacts/. E2E_VIDEO=1 records every test to
e2e-artifacts/videos/ (numbered in run order); tools/e2e_video.py joins them into one MP4.
"""
from __future__ import annotations

import functools
import http.server
import itertools
import importlib.util
import json
import os
import socketserver
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "e2e-artifacts"
VIDEO = os.environ.get("E2E_VIDEO") == "1"
VIDEO_DIR = ARTIFACTS / "videos"
VIEWPORT = {"width": 1280, "height": 800}
_order = itertools.count(1)


def new_context(browser, **kw):
    """A browser context; with E2E_VIDEO=1 it records a video of every page it opens."""
    if VIDEO:
        kw.update(record_video_dir=str(VIDEO_DIR / "_raw"), record_video_size=VIEWPORT)
    return browser.new_context(viewport=VIEWPORT, **kw)


def keep_video(page, test_name: str) -> None:
    """After the context is closed: file the test's video under its run-order number and name."""
    if not VIDEO or page.video is None:
        return
    safe = "".join(c if c.isalnum() or c in "-_[]." else "_" for c in test_name)
    try:
        page.video.save_as(str(VIDEO_DIR / f"{next(_order):03d}_{safe}.webm"))
        page.video.delete()
    except Exception:  # noqa: BLE001
        pass

playwright_sync = pytest.importorskip("playwright.sync_api", reason="pip install -e .[e2e] to run the e2e tests")


def pytest_collection_modifyitems(items):
    here = Path(__file__).parent
    for item in items:
        if here in Path(str(item.fspath)).parents:
            item.add_marker(pytest.mark.e2e)


def _preview_module():
    spec = importlib.util.spec_from_file_location("preview", ROOT / "tools" / "preview.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@pytest.fixture(scope="session")
def site(tmp_path_factory):
    """Base URL of the rendered preview pages."""
    out = tmp_path_factory.mktemp("site")
    _preview_module().render_all(out)
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), functools.partial(_Quiet, directory=str(out)))
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


@pytest.fixture(scope="session")
def browser():
    with playwright_sync.sync_playwright() as p:
        try:
            b = p.chromium.launch(headless=os.environ.get("E2E_HEADED") != "1",
                                  slow_mo=int(os.environ.get("E2E_SLOWMO", "0")))
        except Exception as e:  # noqa: BLE001
            pytest.skip(f"Chromium is not installed for Playwright ({e}); run: python -m playwright install chromium")
        yield b
        b.close()


# a 4x3 grey frame per index, so the compare view has real images to show
def _frame(i: int) -> str:
    shade = 40 + (i * 7) % 180
    svg = f"<svg xmlns='http://www.w3.org/2000/svg' width='40' height='30'><rect width='40' height='30' fill='rgb({shade},{shade},{shade})'/></svg>"
    return "data:image/svg+xml;utf8," + svg.replace("<", "%3C").replace(">", "%3E").replace("#", "%23")


def api_stub(route):
    """Stand-in backend. lane_urls returns 181 frames; everything else an empty 200."""
    url = route.request.url
    if "/lane_urls" in url:
        body = {"urls": [_frame(i) for i in range(181)], "ttl": 300}
        return route.fulfill(status=200, content_type="application/json", body=json.dumps(body))
    return route.fulfill(status=200, content_type="text/html", body="")


class Session:
    """One browser context (light or dark system setting) with error collection."""

    def __init__(self, browser, site, scheme: str):
        self.site = site
        self.ctx = new_context(browser, color_scheme=scheme)
        self.ctx.route("**/api/**", api_stub)
        self.ctx.route("**/partials/**", api_stub)
        self.page = self.ctx.new_page()
        self.errors: list[str] = []
        self.page.on("pageerror", lambda e: self.errors.append(f"pageerror: {e}"))
        self.page.on("console", self._console)

    def _console(self, msg):
        # a missing image or video in the static preview is not a front-end bug
        if msg.type == "error" and "Failed to load resource" not in msg.text:
            self.errors.append(f"console: {msg.text}")

    def open(self, name: str):
        self.page.goto(f"{self.site}/{name}", wait_until="load")
        self.ready()
        return self.page

    def ready(self):
        """Tailwind's CDN script styles the page after load: wait for it and the fonts."""
        self.page.wait_for_function(
            "() => [...document.querySelectorAll('style')].some(s => s.textContent.includes('--tw-'))", timeout=60000)
        self.page.evaluate("document.fonts.ready")

    def theme(self) -> str:
        return self.page.evaluate("document.documentElement.dataset.theme")

    def css(self, selector: str, prop: str) -> str:
        return self.page.eval_on_selector(selector, f"el => getComputedStyle(el).getPropertyValue('{prop}')")


@pytest.fixture
def session(browser, site, request):
    s = Session(browser, site, getattr(request, "param", "light"))
    yield s
    failed = getattr(request.node, "rep_call", None) is not None and request.node.rep_call.failed
    if failed:
        ARTIFACTS.mkdir(exist_ok=True)
        try:
            s.page.screenshot(path=str(ARTIFACTS / f"{request.node.name}.png"), full_page=True)
        except Exception:  # noqa: BLE001
            pass
    errors = list(s.errors)
    s.ctx.close()
    keep_video(s.page, request.node.name)
    if not failed:
        assert not errors, "the page reported errors:\n" + "\n".join(errors)


@pytest.fixture
def dark_session(browser, site, request):
    s = Session(browser, site, "dark")
    yield s
    errors = list(s.errors)
    s.ctx.close()
    keep_video(s.page, request.node.name)
    assert not errors, "the page reported errors:\n" + "\n".join(errors)


@pytest.fixture
def raw_page(browser, request):
    """A bare page for tests that set up their own routing; recorded like the others."""
    ctx = new_context(browser)
    page = ctx.new_page()
    yield page
    ctx.close()
    keep_video(page, request.node.name)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)
