"""The platform module pages (platform/module.html, platform/item.html, platform/ask.html,
platform/approvals.html, platform/brief.html) and the partials (partials/platform_runs.html,
partials/platform_ask_runs.html) pin the contract the backend's platform_routes.py relies on: the forms and
their actions, the chips, the polling attributes, the inline approve confirm, the cited-sources list, the
read-only shape of synced items and the brief read view.
Rendered with minimal fake contexts through the same Jinja2 setup the backend uses (tests/conftest.py).

Context keys the templates read:
    module page:   request, module, mod, items, status, needs, statuses, has_ask, is_owner, modules_nav
    item page:     request, module, mod, item, runs, polling, latest, statuses, next_status, attention,
                   is_policy, read_only, agents, is_owner, modules_nav
    runs partial:  module, item, runs, polling, read_only (missing = false)
    ask page:      request, module, mod, runs, polling, is_owner, modules_nav
    ask partial:   module, runs, polling
    approvals:     request, items, show, is_owner, modules_nav
    brief page:    request, briefs, latest, polling, is_owner, modules_nav
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


SOURCES = [{"n": 1, "module": "knowledge", "item_id": "it1", "title": "Refund policy"},
           {"n": 2, "module": "knowledge", "item_id": "it2", "title": "Returns FAQ"}]


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


def test_module_page_ask_link_only_with_has_ask(jinja_env):
    tpl = jinja_env.get_template("platform/module.html")
    html = tpl.render(**_module_ctx())
    assert 'href="/m/knowledge/ask"' not in html and "Ask the wiki" not in html
    html = tpl.render(**_module_ctx(has_ask=True))
    header = html.split("<section")[1].split('action="/api/m/knowledge/items"')[0]
    assert '<a href="/m/knowledge/ask" class="btn btn-secondary btn-sm">Ask the wiki</a>' in header
    assert header.index("</h1>") < header.index("Ask the wiki")


def test_module_page_source_chip_for_synced_items(jinja_env):
    tpl = jinja_env.get_template("platform/module.html")
    html = tpl.render(**_module_ctx(items=[_item(source="repo"), _item(id="it2", source="manual"), _item(id="it3")]))
    repo = html.split('href="/m/knowledge/items/it1"')[1].split("</a>")[0]
    assert '<span class="chip">repo</span>' in repo
    for item_id in ("it2", "it3"):
        row = html.split(f'href="/m/knowledge/items/{item_id}"')[1].split("</a>")[0]
        assert '<span class="chip">manual</span>' not in row and '<span class="chip">repo</span>' not in row


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


def test_item_page_read_only_synced_item(jinja_env):
    tpl = jinja_env.get_template("platform/item.html")
    item = _item(source="repo", external_url="https://github.com/example/wiki/blob/main/refunds.md")
    done = _run("done", output={"text": "A summary of the refund page."})
    html = tpl.render(**_item_ctx(item=item, read_only=True, runs=[done]))
    # the body is shown, not edited; the note names the source and links out to it
    assert "/items/it1/edit" not in html and 'name="title"' not in html and ">Save<" not in html
    assert '<pre class="whitespace-pre-wrap' in html and "Refunds within 30 days." in html
    assert "Synced from repo; read-only on this site." in html
    assert ('<a href="https://github.com/example/wiki/blob/main/refunds.md" target="_blank" rel="noopener" '
            'class="hover:underline">Open the source</a>') in html
    # no Status card at all: no approve confirm, no main button, no select; Agents stay
    assert ">Status<" not in html and "/items/it1/status" not in html and "<select" not in html
    assert '<details class="confirm">' not in html
    assert ">Agents<" in html and 'hx-post="/api/m/knowledge/items/it1/agents/writer"' in html
    # read_only reaches the included runs partial
    assert 'id="platform-runs"' in html and "A summary of the refund page." in html
    assert "Use this draft" not in html and "/apply" not in html
    # without external_url there is no link, and the editable page is unchanged
    html = tpl.render(**_item_ctx(item=_item(source="repo"), read_only=True))
    assert "Synced from repo; read-only on this site." in html and "Open the source" not in html
    html = tpl.render(**_item_ctx(read_only=False))
    assert "/items/it1/edit" in html and ">Status<" in html and "Synced from" not in html


def test_item_page_brief_shows_chip_and_read_view_above_the_edit_form(jinja_env):
    tpl = jinja_env.get_template("platform/item.html")
    item = _item(title="Brief 2026-10-31", body="Finished: 3 renders.\nWaits on you: 1 approval.",
                 status="draft", attention="ai_done", meta={"kind": "brief", "date": "2026-10-31"})
    html = tpl.render(**_item_ctx(item=item, next_status="review"))
    header = html.split("</h1>")[1].split("md:grid-cols")[0]
    assert '<span class="chip">brief</span>' in header and '<span class="chip">policy</span>' not in header
    # the read view comes first, then the edit form still follows with the same body
    body = html.split("md:grid-cols")[1]
    heading = '<div class="ss-body-strong">Brief</div>'
    assert heading in body
    read = body.split(heading)[1].split("</div>")[0]
    assert '<pre class="whitespace-pre-wrap' in read and "Finished: 3 renders." in read
    assert body.index(heading) < body.index('action="/api/m/knowledge/items/it1/edit"')
    edit = html.split('action="/api/m/knowledge/items/it1/edit"')[1].split("</form>")[0]
    assert 'name="title" required value="Brief 2026-10-31"' in edit and "Waits on you: 1 approval." in edit
    assert ">Status<" in html and ">Agents<" in html
    # an ordinary item, and a policy item, have neither the chip nor the read view
    for ctx in (_item_ctx(), _item_ctx(item=_item(meta={"kind": "policy"}), is_policy=True)):
        html = tpl.render(**ctx)
        assert '<span class="chip">brief</span>' not in html and heading not in html


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


def test_runs_partial_lists_sources_of_a_done_run(render_runs):
    done = _run("done", output={"text": "Refunds within 30 days [1], returns in 14 [2].", "sources": SOURCES})
    html = render_runs([done], False)
    block = html.split("</pre>")[1].split("</form>")[0]
    assert ">Sources<" in block
    assert '<a href="/m/knowledge/items/it1" class="ss-body-sm hover:underline">[1] Refund policy</a>' in block
    assert '<a href="/m/knowledge/items/it2" class="ss-body-sm hover:underline">[2] Returns FAQ</a>' in block
    assert "Use this draft" in html
    # no sources, or an empty list: no Sources heading
    for output in ({"text": "Plain draft."}, {"text": "Plain draft.", "sources": []}):
        html = render_runs([_run("done", output=output)], False)
        assert ">Sources<" not in html and "Use this draft" in html


def test_runs_partial_hides_use_this_draft_when_read_only(jinja_env):
    tpl = jinja_env.get_template("partials/platform_runs.html")
    done = _run("done", output={"text": "A summary.", "sources": SOURCES})
    html = tpl.render(module="knowledge", item=_item(source="repo"), runs=[done], polling=False, read_only=True)
    assert "A summary." in html and "[1] Refund policy" in html
    assert "Use this draft" not in html and "/apply" not in html
    # a missing key behaves as false
    html = tpl.render(module="knowledge", item=_item(), runs=[done], polling=False)
    assert "Use this draft" in html and 'action="/api/m/knowledge/runs/run1/apply"' in html


# ---- ask page and partial -------------------------------------------------------------------------------

def _ask_run(status, question="How do refunds work?", **over):
    base = _run(status, label="Ask", agent="ask", input={"question": question})
    base.update(over)
    return base


def _ask_ctx(**over):
    ctx = dict(request=_Req("/m/knowledge/ask"), module="knowledge", mod=_mod(), runs=[], polling=False,
               is_owner=True, modules_nav=MODULES_NAV)
    ctx.update(over)
    return ctx


def test_ask_page_form_and_included_partial(jinja_env):
    html = jinja_env.get_template("platform/ask.html").render(**_ask_ctx())
    assert "Platform · knowledge" in html and "Ask Knowledge" in html
    assert "Answers come from the approved pages, with the pages they used." in html
    assert '<a href="/m/knowledge" class="ss-meta hover:underline">' in html
    form = html.split('hx-post="/api/m/knowledge/ask"')[1].split("</form>")[0]
    assert 'hx-target="#platform-ask-runs"' in form.split(">")[0] and 'hx-swap="outerHTML"' in form.split(">")[0]
    assert '<textarea name="question" rows="3" required' in form
    assert 'placeholder="Ask a question about how the team works"' in form
    assert '<button type="submit" class="btn btn-primary btn-sm">Ask</button>' in form
    assert "window.confirm" not in html and "hx-confirm" not in html
    # the partial is included, idle and empty
    assert 'id="platform-ask-runs"' in html and "No questions yet." in html and 'hx-trigger="every 3s"' not in html
    # nav: the module stays highlighted
    assert '<a href="/m/knowledge" class="nav-link active">Knowledge</a>' in html


def test_ask_page_lists_answers(jinja_env):
    done = _ask_run("done", output={"text": "Within 30 days [1].", "sources": SOURCES[:1]})
    html = jinja_env.get_template("platform/ask.html").render(**_ask_ctx(runs=[done]))
    assert "How do refunds work?" in html and "Within 30 days [1]." in html and "[1] Refund policy" in html


@pytest.fixture
def render_ask_runs(jinja_env):
    tpl = jinja_env.get_template("partials/platform_ask_runs.html")
    return lambda runs, polling: tpl.render(module="knowledge", runs=runs, polling=polling)


def test_ask_partial_polls_only_while_polling(render_ask_runs):
    html = render_ask_runs([_ask_run("queued", position=1)], True)
    assert 'id="platform-ask-runs"' in html and ">Answers<" in html and ">working<" in html.replace("</span>working", ">working<")
    assert 'hx-get="/partials/m/knowledge/ask/runs"' in html and 'hx-trigger="every 3s"' in html and 'hx-swap="outerHTML"' in html
    assert "How do refunds work?" in html and "queued, 1 ahead" in html
    html = render_ask_runs([_ask_run("running")], False)
    assert "hx-get" not in html and 'hx-trigger="every 3s"' not in html and "working" not in html
    assert ">running<" in html.replace("</span>running", ">running<")


def test_ask_partial_shows_question_answer_and_sources(render_ask_runs):
    done = _ask_run("done", model="answerer-v1",
                    output={"text": "Refunds within 30 days [1]; returns in 14 [2].", "sources": SOURCES})
    html = render_ask_runs([done], False)
    assert '<div class="ss-body-strong">How do refunds work?</div>' in html
    assert '<pre class="whitespace-pre-wrap' in html and "Refunds within 30 days [1]; returns in 14 [2]." in html
    assert "answerer-v1" in html and "460 tokens" in html and "4.2 s" in html and "2026-10-31 09:00" in html
    sources = html.split(">Sources<")[1]
    assert '<a href="/m/knowledge/items/it1" class="ss-body-sm hover:underline">[1] Refund policy</a>' in sources
    assert '<a href="/m/knowledge/items/it2" class="ss-body-sm hover:underline">[2] Returns FAQ</a>' in sources
    # answers are never applied to anything
    assert "Use this draft" not in html and "/apply" not in html
    # a failed question shows its error; a done one without sources has no Sources heading
    html = render_ask_runs([_ask_run("failed", id="run2", error="no approved pages"),
                            _ask_run("done", id="run3", output={"text": "Nothing cited.", "sources": []})], False)
    assert "no approved pages" in html and "chip-err" in html
    assert "Nothing cited." in html and ">Sources<" not in html


def test_ask_partial_empty_state(render_ask_runs):
    html = render_ask_runs([], False)
    assert "No questions yet." in html and "<pre" not in html and ">Sources<" not in html


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


# ---- owner brief ----------------------------------------------------------------------------------------

def _brief(n=1, **over):
    date = f"2026-10-{31 - n + 1:02d}"
    base = {"id": f"br{n}", "title": f"Brief {date}", "status": "draft",
            "body": f"Finished: {n} renders.\nWaits on you: 1 approval.\nNext: a cat short.",
            "meta": {"kind": "brief", "date": date}, "updated_at": f"{date} 07:00"}
    base.update(over)
    return base


def _brief_ctx(briefs, polling=False, **over):
    ctx = dict(request=_Req("/brief"), briefs=briefs, latest=briefs[0] if briefs else None, polling=polling,
               is_owner=True, modules_nav=MODULES_NAV)
    ctx.update(over)
    return ctx


def test_brief_page_empty_state(jinja_env):
    html = jinja_env.get_template("platform/brief.html").render(**_brief_ctx([]))
    assert "Platform · brief" in html and "Owner brief" in html
    assert "Every day the brief agent reads what finished, what waits on you and the money records, then suggests what to make next." in html
    form = html.split('action="/api/brief"')[1].split("</form>")[0]
    assert '<button type="submit" class="btn btn-primary btn-sm">Make today\'s brief now</button>' in form
    assert "No brief yet. The first one arrives at the scheduled hour, or press the button." in html
    assert "<pre" not in html and "Earlier briefs" not in html and "/m/knowledge/items/" not in html
    assert "hx-get" not in html and "window.confirm" not in html and "hx-confirm" not in html


def test_brief_page_shows_the_latest_brief(jinja_env):
    html = jinja_env.get_template("platform/brief.html").render(**_brief_ctx([_brief()]))
    assert "No brief yet." not in html
    card = html.split('action="/api/brief"')[1].split("</form>")[1].split("</pre>")[0]
    assert '<span class="ss-body-strong truncate">Brief 2026-10-31</span>' in card
    assert '<span class="chip ">draft</span>' in card
    assert '<a href="/m/knowledge/items/br1" class="ss-meta ml-auto hover:underline">Open</a>' in card
    assert '<pre class="whitespace-pre-wrap rounded-widget bg-surface-field p-3 font-mono text-xs text-fg-1">' in card
    assert "Finished: 1 renders.\nWaits on you: 1 approval.\nNext: a cat short." in card
    assert "being written" not in html and 'class="dot dot-info pulse-dot"' not in html
    # not polling: the section carries no htmx attributes; one brief means no earlier list
    section = html.split("<section")[1].split(">")[0]
    assert "hx-get" not in section and "hx-trigger" not in section
    assert "Earlier briefs" not in html
    # status tone follows the shared map
    html = jinja_env.get_template("platform/brief.html").render(**_brief_ctx([_brief(status="review")]))
    assert '<span class="chip chip-warn">review</span>' in html


def test_brief_page_polls_while_the_brief_is_being_written(jinja_env):
    tpl = jinja_env.get_template("platform/brief.html")
    html = tpl.render(**_brief_ctx([_brief(body="")], polling=True))
    section = html.split("<section")[1].split(">")[0]
    assert 'hx-get="/brief"' in section and 'hx-trigger="every 5s"' in section
    assert 'hx-select="section"' in section and 'hx-swap="outerHTML"' in section
    assert '<span class="chip chip-info"><span class="dot dot-info pulse-dot"></span>being written</span>' in html
    assert "<pre" not in html and 'href="/m/knowledge/items/br1"' in html
    # the body arrived but the backend still says polling: the text shows and the section keeps refreshing
    html = tpl.render(**_brief_ctx([_brief()], polling=True))
    assert 'hx-get="/brief"' in html and "being written" not in html and "Finished: 1 renders." in html


def test_brief_page_lists_earlier_briefs(jinja_env):
    briefs = [_brief(1), _brief(2), _brief(3)]
    html = jinja_env.get_template("platform/brief.html").render(**_brief_ctx(briefs))
    assert "Earlier briefs" in html
    earlier = html.split("Earlier briefs")[1]
    assert 'href="/m/knowledge/items/br1"' not in earlier
    for n, date in ((2, "2026-10-30"), (3, "2026-10-29")):
        row = earlier.split(f'href="/m/knowledge/items/br{n}"')[1].split("</a>")[0]
        assert f"Brief {date}" in row and f'<span class="ss-meta ml-auto">{date} 07:00</span>' in row
    # only the latest body is on the page
    assert html.count("<pre") == 1 and "Finished: 1 renders." in html and "Finished: 2 renders." not in html


# ---- base nav -------------------------------------------------------------------------------------------

def test_nav_renders_without_modules_nav(jinja_env):
    """`modules_nav` is a backend Jinja global; every page must still render when it is undefined."""
    html = jinja_env.get_template("projects.html").render(projects=[], fmt=str, request=_Req("/projects"), is_owner=True)
    assert 'href="/approvals"' in html and 'href="/brief"' in html and "/m/" not in html


def test_nav_has_the_brief_link_after_approvals(jinja_env):
    html = jinja_env.get_template("platform/brief.html").render(**_brief_ctx([]))
    assert '<a href="/brief" class="nav-link active">Brief</a>' in html
    assert '<a href="/approvals" class="nav-link ">Approvals</a>' in html
    assert '<a href="/m/knowledge" class="nav-link ">Knowledge</a>' in html
    assert html.index('href="/approvals"') < html.index('href="/brief"') < html.index('href="/recast"')
    # module pages still render, with Brief present but idle and the module active
    html = jinja_env.get_template("platform/module.html").render(**_module_ctx())
    assert '<a href="/brief" class="nav-link ">Brief</a>' in html
    assert '<a href="/m/knowledge" class="nav-link active">Knowledge</a>' in html
    html = jinja_env.get_template("platform/approvals.html").render(
        request=_Req("/approvals"), items=[], show="needs_you", is_owner=True, modules_nav=MODULES_NAV)
    assert '<a href="/brief" class="nav-link ">Brief</a>' in html and '<a href="/approvals" class="nav-link active">Approvals</a>' in html
