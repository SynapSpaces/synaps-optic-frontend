"""The platform module pages (platform/module.html, platform/item.html, platform/approvals.html) and the runs
partial (partials/platform_runs.html) pin the contract the backend's platform_routes.py relies on: the forms
and their actions, the chips, the polling attribute and the inline approve confirm. Rendered with minimal fake
contexts through the same Jinja2 setup the backend uses (tests/conftest.py).

Context keys the templates read:
    module page:   request, module, mod, items, status, needs, statuses, is_owner, modules_nav
    item page:     request, module, mod, item, runs, polling, latest, statuses, next_status, attention,
                   is_policy, agents, is_owner, modules_nav
    runs partial:  module, item, runs, polling
    approvals:     request, items, show, is_owner, modules_nav
"""
import pytest

STATUSES = ["draft", "review", "approved", "done"]
MODULES_NAV = [("knowledge", "Knowledge"), ("marketing", "Marketing")]


class _Req:
    """Enough of starlette's Request for base.html's nav highlighting."""
    def __init__(self, path="/m/knowledge"):
        self.url = type("url", (), {"path": path})()
        self.headers = {}


def _mod(**over):
    base = {"label": "Knowledge", "blurb": "What every agent reads first.", "statuses": STATUSES,
            "agents": {"writer": {"label": "Draft with the writer"}, "reviewer": {"label": "Review"}}}
    base.update(over)
    return base


def _item(**over):
    base = {"id": "it1", "title": "Refund policy", "body": "Refunds within 30 days.", "status": "review",
            "updated_at": "2026-10-31 09:00", "meta": {}, "attention": "needs_you",
            "latest_run": {"status": "done", "agent": "writer"}}
    base.update(over)
    return base


def _run(status, **over):
    base = {"id": "run1", "label": "Draft with the writer", "agent": "writer", "status": status, "position": None,
            "error": None, "model": "gemma-4-e4b", "tokens_in": 120, "tokens_out": 340, "seconds": 4.2,
            "created_at": "2026-10-31 09:00", "output": None}
    base.update(over)
    return base


def _confirm(html, url):
    """The inline confirm block posting to `url` (its question and buttons), or None."""
    for block in html.split('<details class="confirm">')[1:]:
        block = block.split("</details>")[0]
        if f'action="{url}"' in block:
            return block
    return None


def _module_ctx(module="knowledge", **over):
    ctx = dict(request=_Req(f"/m/{module}"), module=module, mod=_mod(), items=[_item()], status="", needs="",
               statuses=STATUSES, is_owner=True, modules_nav=MODULES_NAV)
    ctx.update(over)
    return ctx


def _item_ctx(**over):
    item = over.pop("item", _item())
    ctx = dict(request=_Req("/m/knowledge/items/it1"), module="knowledge", mod=_mod(), item=item, runs=[],
               polling=False, latest=None, statuses=STATUSES, next_status="approved", attention=item["attention"],
               is_policy=False, agents=[("writer", "Draft with the writer"), ("reviewer", "Review")],
               is_owner=True, modules_nav=MODULES_NAV)
    ctx.update(over)
    return ctx


# ---- module page ----------------------------------------------------------------------------------------

def test_module_page_lists_items_with_chips_and_filters(jinja_env):
    html = jinja_env.get_template("platform/module.html").render(**_module_ctx())
    assert "Knowledge" in html and "What every agent reads first." in html
    form = html.split('action="/api/m/knowledge/items"')[1].split("</form>")[0]
    assert 'name="title" required' in form and 'name="body"' in form
    assert 'name="kind" value="policy"' in form and "Policy page (rules every agent reads first)" in form
    # filter row: All, each status, Needs you, AI done; All is active with no filter set
    for s in STATUSES:
        assert f'href="/m/knowledge?status={s}"' in html
    assert 'href="/m/knowledge?needs=you"' in html and 'href="/m/knowledge?needs=ai"' in html
    assert '<a href="/m/knowledge" class="nav-link active">All</a>' in html
    # the item row
    row = html.split('href="/m/knowledge/items/it1"')[1].split("</a>")[0]
    assert "Refund policy" in row and "chip-warn" in row and "Needs you" in row and "AI done" not in row
    assert "Draft with the writer · done" in row and "2026-10-31 09:00" in row
    assert '<span class="chip">policy</span>' not in row
    # nav: both modules and Approvals, the current module active
    assert '<a href="/m/knowledge" class="nav-link active">Knowledge</a>' in html
    assert '<a href="/m/marketing" class="nav-link ">Marketing</a>' in html
    assert 'href="/approvals"' in html


def test_module_page_policy_checkbox_only_for_knowledge(jinja_env):
    tpl = jinja_env.get_template("platform/module.html")
    html = tpl.render(**_module_ctx("marketing", mod=_mod(label="Marketing")))
    assert 'name="kind"' not in html and "Policy page" not in html
    assert 'action="/api/m/marketing/items"' in html


def test_module_page_policy_badge_filters_and_empty_state(jinja_env):
    tpl = jinja_env.get_template("platform/module.html")
    item = _item(meta={"kind": "policy"}, attention="ai_done", latest_run=None)
    html = tpl.render(**_module_ctx(items=[item], status="review"))
    row = html.split('href="/m/knowledge/items/it1"')[1].split("</a>")[0]
    assert '<span class="chip">policy</span>' in row and "AI done" in row and "Needs you" not in row
    assert '<a href="/m/knowledge?status=review" class="nav-link active">review</a>' in html
    assert '<a href="/m/knowledge" class="nav-link ">All</a>' in html
    html = tpl.render(**_module_ctx(items=[], needs="you"))
    assert "Nothing matches this filter." in html
    assert '<a href="/m/knowledge?needs=you" class="nav-link active">Needs you</a>' in html
    html = tpl.render(**_module_ctx(items=[]))
    assert "No items yet." in html


# ---- item page ------------------------------------------------------------------------------------------

def test_item_page_edit_status_and_agents(jinja_env):
    html = jinja_env.get_template("platform/item.html").render(**_item_ctx())
    assert "Refund policy" in html and 'href="/m/knowledge"' in html
    edit = html.split('action="/api/m/knowledge/items/it1/edit"')[1].split("</form>")[0]
    assert 'name="title" required value="Refund policy"' in edit and "Refunds within 30 days." in edit and ">Save<" in edit
    # next_status approved: the two-step confirm, no plain primary button, no modal
    appr = _confirm(html, "/api/m/knowledge/items/it1/status")
    assert appr and "Approve this item? Only a member can do this; agents never approve." in appr
    assert 'name="status" value="approved"' in appr and ">Approve</button>" in appr and ">Cancel</button>" in appr
    assert "hx-confirm" not in html and "window.confirm" not in html
    # the any-status select
    assert '<option value="review" selected>review</option>' in html
    for s in STATUSES:
        assert f'<option value="{s}"' in html
    # agents panel: one htmx form per agent, swapping the runs wrapper
    for name, label in (("writer", "Draft with the writer"), ("reviewer", "Review")):
        form = html.split(f'hx-post="/api/m/knowledge/items/it1/agents/{name}"')[1].split("</form>")[0]
        assert 'hx-target="#platform-runs"' in html.split(f"/agents/{name}")[1].split(">")[0]
        assert 'name="prompt"' in form and "Extra instructions" in form and f">{label}</button>" in form
    # chips and the included runs partial
    assert "Needs you" in html and '<span class="chip">policy</span>' not in html
    assert 'id="platform-runs"' in html and "No runs yet." in html and 'hx-trigger="every 3s"' not in html


@pytest.mark.parametrize("next_status, label", [
    ("review", "Submit for review"), ("done", "Mark done"), ("draft", "Start drafting"),
])
def test_item_page_main_button_for_other_next_statuses(jinja_env, next_status, label):
    html = jinja_env.get_template("platform/item.html").render(**_item_ctx(next_status=next_status))
    assert f'name="status" value="{next_status}"' in html and f">{label}</button>" in html
    assert '<details class="confirm">' not in html and "Approve this item?" not in html


def test_item_page_approved_and_policy(jinja_env):
    item = _item(status="approved", attention="", meta={"kind": "policy", "approved_by": "david", "approved_at": "2026-10-31 10:00"})
    html = jinja_env.get_template("platform/item.html").render(**_item_ctx(item=item, next_status="done", is_policy=True))
    assert "Approved by david at 2026-10-31 10:00" in html
    assert '<span class="chip">policy</span>' in html and "Needs you" not in html and "AI done" not in html
    assert ">Mark done</button>" in html


def test_item_page_without_next_status_keeps_only_the_select(jinja_env):
    html = jinja_env.get_template("platform/item.html").render(**_item_ctx(next_status=None, agents=[]))
    assert html.count('action="/api/m/knowledge/items/it1/status"') == 1 and "<select" in html
    assert "No agents for this module." in html


# ---- runs partial ---------------------------------------------------------------------------------------

@pytest.fixture
def render_runs(jinja_env):
    tpl = jinja_env.get_template("partials/platform_runs.html")
    return lambda runs, polling: tpl.render(module="knowledge", item=_item(), runs=runs, polling=polling)


def test_runs_partial_polls_only_while_polling(render_runs):
    html = render_runs([_run("queued", position=2)], True)
    assert 'id="platform-runs"' in html
    assert 'hx-get="/partials/m/knowledge/items/it1/runs"' in html and 'hx-trigger="every 3s"' in html and 'hx-swap="outerHTML"' in html
    assert "queued, 2 ahead" in html and "Use this draft" not in html
    html = render_runs([_run("running")], False)
    assert "hx-get" not in html and 'hx-trigger="every 3s"' not in html and ">running<" in html.replace("</span>running", ">running<")


def test_runs_partial_use_this_draft_only_for_a_done_run_with_output(render_runs):
    done = _run("done", output={"text": "Refunds within 30 days, no questions asked."})
    html = render_runs([done], False)
    assert 'action="/api/m/knowledge/runs/run1/apply"' in html and "Use this draft" in html
    assert '<pre class="whitespace-pre-wrap' in html and "Refunds within 30 days, no questions asked." in html
    assert "sends the item to review" in html
    assert "gemma-4-e4b" in html and "460 tokens" in html and "4.2 s" in html and "2026-10-31 09:00" in html
    # a done run without text, and a failed run, offer nothing to apply
    html = render_runs([_run("done", output=None), _run("failed", id="run2", error="model timed out")], False)
    assert "Use this draft" not in html and "/apply" not in html
    assert "model timed out" in html and "chip-err" in html


def test_runs_partial_empty_state(render_runs):
    html = render_runs([], False)
    assert "No runs yet." in html and "<pre" not in html


# ---- approvals ------------------------------------------------------------------------------------------

def test_approvals_empty_state_and_filters(jinja_env):
    tpl = jinja_env.get_template("platform/approvals.html")
    html = tpl.render(request=_Req("/approvals"), items=[], show="needs_you", is_owner=True, modules_nav=MODULES_NAV)
    assert "Approvals" in html and "Nothing waits on you." in html
    assert '<a href="/approvals?show=needs_you" class="nav-link active">Needs you</a>' in html
    assert '<a href="/approvals?show=ai_done" class="nav-link ">AI done</a>' in html
    assert '<a href="/approvals?show=all" class="nav-link ">All</a>' in html
    # nav: Approvals active, no module active
    assert '<a href="/approvals" class="nav-link active">Approvals</a>' in html
    assert '<a href="/m/knowledge" class="nav-link ">Knowledge</a>' in html


def test_approvals_rows_link_to_items(jinja_env):
    tpl = jinja_env.get_template("platform/approvals.html")
    items = [
        {"id": "it1", "module": "knowledge", "module_label": "Knowledge", "title": "Refund policy", "status": "review",
         "attention": "needs_you", "latest_run": {"status": "done", "agent": "writer"}, "updated_at": "2026-10-31 09:00"},
        {"id": "it2", "module": "marketing", "module_label": "Marketing", "title": "Launch post", "status": "draft",
         "attention": "ai_done", "latest_run": None, "updated_at": "2026-10-31 08:00"},
    ]
    html = tpl.render(request=_Req("/approvals"), items=items, show="all", is_owner=True, modules_nav=MODULES_NAV)
    assert "Nothing waits on you." not in html
    first = html.split('href="/m/knowledge/items/it1"')[1].split("</a>")[0]
    assert "Knowledge" in first and "Refund policy" in first and "Needs you" in first and "writer · done" in first
    second = html.split('href="/m/marketing/items/it2"')[1].split("</a>")[0]
    assert "Marketing" in second and "Launch post" in second and "AI done" in second and "Needs you" not in second


# ---- base nav -------------------------------------------------------------------------------------------

def test_nav_renders_without_modules_nav(jinja_env):
    """`modules_nav` is a backend Jinja global; every page must still render when it is undefined."""
    html = jinja_env.get_template("projects.html").render(projects=[], fmt=str, request=_Req("/projects"), is_owner=True)
    assert 'href="/approvals"' in html and "/m/" not in html
