"""The ai_generate_status partial's done -> window.location.reload() branch must only render on
the htmx poll response. editor.html includes the same partial on the full page, so emitting the
reload there made every project with a finished generation reload itself forever (seen live on
2026-10-06 right after the first generation on a fresh project)."""
import pytest

from dashboard import templates

pytestmark = pytest.mark.nodb


class _Req:
    def __init__(self, headers: dict | None = None):
        self.headers = headers or {}
        self.url = "http://test/projects/p1"


def _render(status: str, hx: bool) -> str:
    tpl = templates.env.get_template("partials/ai_generate_status.html")
    return tpl.render(
        request=_Req({"HX-Request": "true"} if hx else {}),
        project_id="p1",
        ai_generation={"id": "g1", "status": status, "progress": 100, "error": None},
        scenes=[],
        gpu_online=True,
        queue_position=None,
        oob_timeline=False,
    )


def test_done_on_full_page_render_does_not_reload():
    html = _render("done", hx=False)
    assert "location.reload" not in html


def test_done_on_htmx_poll_reloads_once():
    html = _render("done", hx=True)
    assert "location.reload" in html
    assert 'hx-trigger="every' not in html  # the reload box must not keep polling


def test_running_keeps_polling_without_reload():
    html = _render("running", hx=False)
    assert 'hx-trigger="every 3s"' in html
    assert "location.reload" not in html
