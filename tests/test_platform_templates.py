"""The platform module pages (platform/module.html, platform/item.html, platform/board.html,
platform/people.html, platform/ledger.html, platform/integrations.html, platform/ask.html, platform/approvals.html,
platform/brief.html) and the partials (partials/platform_runs.html, partials/platform_ask_runs.html) pin the contract the backend's
platform_routes.py relies on: the forms and their actions, the chips, the polling attributes, the inline
confirms (approve, replace the checklist), the cited-sources list, the read-only shape of synced items, the
brief read view, the rendered markdown page, the brief mentions, the board columns, the people rows, the
ledger tables, the integrations page (GitHub and Linear), the pull-request / repository / Linear issue cards,
the Work card (start work on a branch), the Linear card (create an issue from an item) and posting a review
run as a pull request comment.
Rendered with minimal fake contexts through the same Jinja2 setup the backend uses (tests/conftest.py).

Context keys the templates read:
    module page:   request, module, mod, items, status, needs, statuses, has_ask, pages (missing = none),
                   is_owner, modules_nav; each item: attention, latest_run, read_only, meta.kind, due_at
                   (meta.kind pr: number, author, draft, checks; meta.kind repo: open_prs; meta.kind issue:
                   state, assignee; meta.work = branch chip)
    item page:     request, module, mod, item (due_at, assignee_user_id, meta), runs, polling, latest, statuses,
                   next_status, attention, is_policy, is_person, checklist, members, owner_name, assignee_name,
                   today, read_only, agents, body_html (missing or "" = no Page card), work_repos (missing or
                   [] = no Start work form), work (None or item.meta.work: repo, branch, base, brief_path,
                   branch_url, compare_url, started_at), comment_agent (passed through to the runs partial),
                   is_issue (missing = false: the "Linear issue" card and chip), linear_teams (missing or None =
                   no "Create in Linear" form; a list of team keys, possibly empty, offers it on a manual
                   editable item), is_owner, modules_nav; item.meta.kind pr (repo, number, author, head, base,
                   state, checks, draft) or repo (default_branch, open_prs, private) or issue (identifier, team,
                   state, state_type, assignee, priority, linear_error) with item.external_url
    board page:    request, module, mod, pages, columns ([{status, items}]; each item: attention, assignee_name,
                   owner_name, overdue, next_status, read_only, due_at, source), today, is_owner, modules_nav
    people page:   request, module, mod, pages, people (role, start_date, done, total), is_owner, modules_nav
    ledger page:   request, module, mod, pages, months, month, entries, categories, imports, modes, imported,
                   skipped, is_owner, modules_nav
    integrations:  request, module ("dev"), mod, pages, configured, github (None or {external_account, scopes,
                   repos, updated_at, last_sync_at, last_error}), open_prs, linear (None or {external_account,
                   scopes, teams, updated_at, last_sync_at, last_error}), issues, poll_minutes, is_owner,
                   modules_nav
    runs partial:  module, item, runs, polling, read_only (missing = false), comment_agent (missing or None =
                   never offer to post; a done run of that agent with text offers "Post as a comment", and
                   run.output.comment_url / commented_by show it as posted)
    ask page:      request, module, mod, runs, polling, is_owner, modules_nav
    ask partial:   module, runs, polling
    approvals:     request, items, show, is_owner, modules_nav
    brief page:    request, briefs, latest, polling, mentions (missing or [] = no "Mentioned" block;
                   each {module, module_label, id, title, why}), is_owner, modules_nav
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


def test_module_page_source_chip_only_for_read_only_items(jinja_env):
    tpl = jinja_env.get_template("platform/module.html")
    items = [_item(source="repo", read_only=True), _item(id="it2", source="manual", read_only=False),
             _item(id="it3"), _item(id="it4", source="members", read_only=False)]
    html = tpl.render(**_module_ctx(items=items))
    repo = html.split('href="/m/knowledge/items/it1"')[1].split("</a>")[0]
    assert '<span class="chip">repo</span>' in repo
    # a synced but editable item (a person from the members table) carries no source chip
    for item_id, source in (("it2", "manual"), ("it3", "repo"), ("it4", "members")):
        row = html.split(f'href="/m/knowledge/items/{item_id}"')[1].split("</a>")[0]
        assert f'<span class="chip">{source}</span>' not in row


def test_module_page_board_and_pages_links(jinja_env):
    tpl = jinja_env.get_template("platform/module.html")
    html = tpl.render(**_module_ctx())
    header = html.split("<section")[1].split('action="/api/m/knowledge/items"')[0]
    assert '<a href="/m/knowledge/board" class="btn btn-secondary btn-sm">Board</a>' in header
    assert header.index("</h1>") < header.index(">Board<")
    assert "People directory" not in header and "Ledger" not in header
    # a module with its own pages links each after Board; `pages` may be missing from older contexts
    html = tpl.render(**_module_ctx("hr", mod=_mod(label="People"), pages=[("people", "People directory")], has_ask=True))
    header = html.split("<section")[1].split('action="/api/m/hr/items"')[0]
    assert '<a href="/m/hr/people" class="btn btn-secondary btn-sm">People directory</a>' in header
    assert header.index("Ask the wiki") < header.index(">Board<") < header.index("People directory")
    html = tpl.render(**_module_ctx("accounting", mod=_mod(label="Accounting"), pages=[("ledger", "Ledger")]))
    assert '<a href="/m/accounting/ledger" class="btn btn-secondary btn-sm">Ledger</a>' in html
    html = tpl.render(**_module_ctx(pages=[]))
    assert 'href="/m/knowledge/board"' in html and 'href="/m/knowledge/people"' not in html


def test_module_page_kind_chips_and_due_date(jinja_env):
    tpl = jinja_env.get_template("platform/module.html")
    items = [_item(meta={"kind": "person", "user_id": "u1"}, source="members", read_only=False),
             _item(id="it2", meta={"kind": "ledger_import", "rows": 3}, due_at="2026-11-15"),
             _item(id="it3", due_at=None)]
    html = tpl.render(**_module_ctx("hr", mod=_mod(label="People"), items=items))
    person = html.split('href="/m/hr/items/it1"')[1].split("</a>")[0]
    assert '<span class="chip">person</span>' in person and '<span class="chip">members</span>' not in person
    assert "due " not in person
    imp = html.split('href="/m/hr/items/it2"')[1].split("</a>")[0]
    assert '<span class="chip">import</span>' in imp and '<span class="ss-meta">due 2026-11-15</span>' in imp
    assert '<span class="chip">person</span>' not in imp
    plain = html.split('href="/m/hr/items/it3"')[1].split("</a>")[0]
    assert "due " not in plain and '<span class="chip">import</span>' not in plain


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


def test_item_page_due_date_owner_and_assignee(jinja_env):
    tpl = jinja_env.get_template("platform/item.html")
    members = [("u1", "ana@example.com"), ("u2", "ben@example.com")]
    item = _item(due_at="2026-11-15", assignee_user_id="u2", owner_user_id="u1")
    html = tpl.render(**_item_ctx(item=item, members=members, owner_name="ana@example.com",
                                  assignee_name="ben@example.com", today="2026-10-31"))
    header = html.split("</h1>")[1].split("md:grid-cols")[0]
    assert '<span class="ss-meta">due 2026-11-15</span>' in header and "chip-err" not in header
    assert '<span class="ss-meta">owner ana@example.com</span>' in header
    assert '<span class="ss-meta">assignee ben@example.com</span>' in header
    # the edit form: the date input and the assignee select with the members, the assignee selected
    edit = html.split('action="/api/m/knowledge/items/it1/edit"')[1].split("</form>")[0]
    assert '<input type="date" name="due_at" value="2026-11-15" class="input input-sm">' in edit
    assert ">Due<" in edit and ">Assignee<" in edit
    select = edit.split('<select name="assignee_user_id" class="select select-sm">')[1].split("</select>")[0]
    assert '<option value="">Unassigned</option>' in select
    assert '<option value="u1">ana@example.com</option>' in select
    assert '<option value="u2" selected>ben@example.com</option>' in select
    # overdue: past due date on an item in review is a chip-err; approved or done never is
    html = tpl.render(**_item_ctx(item=_item(due_at="2026-10-01"), today="2026-10-31"))
    assert '<span class="chip chip-err">due 2026-10-01</span>' in html and '<span class="ss-meta">due 2026-10-01</span>' not in html
    for status in ("approved", "done"):
        html = tpl.render(**_item_ctx(item=_item(due_at="2026-10-01", status=status), today="2026-10-31", next_status=None))
        header = html.split("</h1>")[1].split("md:grid-cols")[0]
        assert '<span class="ss-meta">due 2026-10-01</span>' in header and "chip-err" not in header
    # no due date, no names: nothing of this in the chip row; the empty date input and the select stay
    html = tpl.render(**_item_ctx(members=members, owner_name=None, assignee_name=None, today="2026-10-31"))
    header = html.split("</h1>")[1].split("md:grid-cols")[0]
    assert "due " not in header and "owner " not in header and "assignee " not in header
    assert '<input type="date" name="due_at" value="" class="input input-sm">' in html
    assert '<option value="">Unassigned</option>' in html and '<option value="u1">ana@example.com</option>' in html
    # a read-only item has no edit form, so no due input and no assignee select
    html = tpl.render(**_item_ctx(item=_item(source="repo", due_at="2026-11-15"), read_only=True, today="2026-10-31"))
    assert 'name="due_at"' not in html and 'name="assignee_user_id"' not in html
    assert '<span class="ss-meta">due 2026-11-15</span>' in html


def _person(**over):
    base = _item(id="p1", title="ana@example.com", body="", status="draft", attention="", latest_run=None,
                 source="members", meta={"kind": "person", "user_id": "u1", "role": "member",
                                         "start_date": "2026-10-20", "checklist": []})
    base.update(over)
    return base


def test_item_page_person_card_and_checklist(jinja_env):
    tpl = jinja_env.get_template("platform/item.html")
    checklist = [{"text": "Sign the NDA", "done": True}, {"text": "Read the policy pages", "done": False}]
    person = _person(body="1. Sign the NDA\n2. Read the policy pages\n3. Meet the team",
                     meta={"kind": "person", "user_id": "u1", "role": "member", "start_date": "2026-10-20",
                           "checklist": checklist})
    html = tpl.render(**_item_ctx(item=person, module="hr", mod=_mod(label="People"), is_person=True,
                                  checklist=checklist, members=[("u1", "ana@example.com")], today="2026-10-31",
                                  next_status="review"))
    header = html.split("</h1>")[1].split("md:grid-cols")[0]
    assert '<span class="chip">person</span>' in header and '<span class="chip">members</span>' not in header
    body = html.split("md:grid-cols")[1]
    # the Person card: role, start date, user id and the onboarding note, above the edit form
    card = body.split('<div class="ss-body-strong">Person</div>')[1].split("</p>")[0]
    assert '<span class="chip">member</span>' in card and "since 2026-10-20" in card and "user u1" in card
    assert "Draft an onboarding checklist with the agent, use the draft, then turn the body into the checklist." in card
    assert body.index(">Person<") < body.index(">Checklist<") < body.index('action="/api/m/hr/items/p1/edit"')
    # the Checklist card: progress, one toggle + remove form per item, the add form, the from_body confirm
    check = body.split('<div class="ss-body-strong">Checklist</div>')[1].split('action="/api/m/hr/items/p1/edit"')[0]
    assert '<span class="ss-meta ml-auto">1/2 done</span>' in check
    url = "/api/m/hr/items/p1/checklist"
    forms = [f.split("</form>")[0] for f in check.split(f'action="{url}"')[1:]]
    toggles = [f for f in forms if 'name="action" value="toggle"' in f]
    removes = [f for f in forms if 'name="action" value="remove"' in f]
    assert len(toggles) == 2 and len(removes) == 2
    assert 'name="index" value="0"' in toggles[0] and "☑" in toggles[0] and "Sign the NDA" in toggles[0]
    assert "line-through text-fg-3" in toggles[0]
    assert 'name="index" value="1"' in toggles[1] and "☐" in toggles[1] and "Read the policy pages" in toggles[1]
    assert "line-through" not in toggles[1]
    assert 'name="index" value="1"' in removes[1] and ">×</button>" in removes[1]
    add = [f for f in forms if 'name="action" value="add"' in f][0]
    assert '<input name="text" required placeholder="Add an item" class="input input-sm"' in add
    assert '<button type="submit" class="btn btn-secondary btn-sm">Add</button>' in add
    # from_body sits inside the two-step confirm, with the question and Cancel / Replace; never window.confirm
    confirm = _confirm(html, url)
    assert confirm and 'name="action" value="from_body"' in confirm
    assert "Replace the checklist with the body's lines? Ticked items that keep their text stay ticked." in confirm
    assert ">Cancel</button>" in confirm and ">Replace</button>" in confirm
    assert "Use the body as the checklist" in check.split('<details class="confirm">')[1].split("<form")[0]
    assert "window.confirm" not in html and "hx-confirm" not in html
    # the approve confirm is a separate details block
    assert html.count('<details class="confirm">') == 1 and "Submit for review" in html
    # the edit form and the agents card stay
    assert 'name="title" required value="ana@example.com"' in html and ">Agents<" in html


def test_item_page_checklist_card_only_for_a_person_or_a_list(jinja_env):
    tpl = jinja_env.get_template("platform/item.html")
    # an ordinary item without a checklist: no Person card, no Checklist card
    html = tpl.render(**_item_ctx(is_person=False, checklist=[], members=[], today="2026-10-31"))
    assert ">Person<" not in html and ">Checklist<" not in html and "/checklist" not in html
    # an older context without the new keys renders the same
    html = tpl.render(**_item_ctx())
    assert ">Checklist<" not in html and "/checklist" not in html and 'name="due_at"' in html
    # a person with an empty checklist: the card with its empty state, 0/0, the add form and the confirm
    html = tpl.render(**_item_ctx(item=_person(), module="hr", mod=_mod(label="People"), is_person=True,
                                  checklist=[], members=[("u1", "ana@example.com")], today="2026-10-31", next_status="review"))
    assert ">Person<" in html and ">Checklist<" in html and "No items yet." in html
    assert '<span class="ss-meta ml-auto">0/0 done</span>' in html
    assert 'name="action" value="add"' in html and 'name="action" value="from_body"' in html
    assert 'name="action" value="toggle"' not in html
    # a non-person item with a checklist: the Checklist card without the Person card
    html = tpl.render(**_item_ctx(item=_item(meta={"checklist": [{"text": "Ship it", "done": False}]}),
                                  checklist=[{"text": "Ship it", "done": False}], members=[], today="2026-10-31"))
    assert ">Person<" not in html and ">Checklist<" in html and "Ship it" in html
    assert '<span class="ss-meta ml-auto">0/1 done</span>' in html
    # a read-only item never shows the Checklist card
    html = tpl.render(**_item_ctx(item=_item(source="repo", meta={"checklist": [{"text": "Ship it", "done": False}]}),
                                  read_only=True, checklist=[{"text": "Ship it", "done": False}], today="2026-10-31"))
    assert ">Checklist<" not in html and "/checklist" not in html


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


PAGE_HTML = ('<h2>Refunds</h2>\n<p>Within <strong>30 days</strong> &amp; with a receipt.</p>\n'
             '<ul>\n<li>Cash</li>\n<li>Store credit</li>\n</ul>\n<pre><code>POST /refunds</code></pre>')
PAGE_MD = "## Refunds\n\nWithin **30 days** & with a receipt.\n\n- Cash\n- Store credit\n\n```\nPOST /refunds\n```"
PAGE_HEADING = '<div class="ss-body-strong">Page</div>'


def test_item_page_body_html_shows_the_page_card_above_the_edit_form(jinja_env):
    tpl = jinja_env.get_template("platform/item.html")
    html = tpl.render(**_item_ctx(item=_item(body=PAGE_MD), body_html=PAGE_HTML))
    # the backend's HTML is printed as is (not escaped), once, inside the .md block of the Page card
    assert html.count(PAGE_HEADING) == 1 and html.count('<div class="md">') == 1
    assert f'<div class="md">{PAGE_HTML}</div>' in html and "&lt;h2&gt;" not in html
    card = html.split(PAGE_HEADING)[1].split("</form>")[0]
    assert '<div class="md">' in card.split('action="/api/m/knowledge/items/it1/edit"')[0]
    # the edit form still follows, with the markdown source in the textarea, and the right column is unchanged
    assert html.index(PAGE_HEADING) < html.index('action="/api/m/knowledge/items/it1/edit"')
    edit = html.split('action="/api/m/knowledge/items/it1/edit"')[1].split("</form>")[0]
    assert 'name="title" required value="Refund policy"' in edit and "## Refunds" in edit and "&amp; with a receipt" in edit
    assert ">Status<" in html and ">Agents<" in html and 'id="platform-runs"' in html
    assert "Synced from" not in html and '<pre class="whitespace-pre-wrap' not in html
    # order on the left: Brief / Checklist, then Page, then Edit, then the runs
    brief = _item(body=PAGE_MD, status="draft", meta={"kind": "brief", "date": "2026-10-31", "checklist": [{"text": "Ship", "done": False}]})
    html = tpl.render(**_item_ctx(item=brief, next_status="review", body_html=PAGE_HTML,
                                  checklist=[{"text": "Ship", "done": False}]))
    marks = ['<div class="ss-body-strong">Brief</div>', '<div class="ss-body-strong">Checklist</div>', PAGE_HEADING,
             'action="/api/m/knowledge/items/it1/edit"', 'id="platform-runs"']
    positions = [html.index(m) for m in marks]
    assert positions == sorted(positions), marks


def test_item_page_read_only_item_with_body_html_shows_the_page_instead_of_the_pre(jinja_env):
    tpl = jinja_env.get_template("platform/item.html")
    item = _item(source="repo", body=PAGE_MD, external_url="https://github.com/example/wiki/blob/main/refunds.md")
    html = tpl.render(**_item_ctx(item=item, read_only=True, body_html=PAGE_HTML))
    assert f'<div class="md">{PAGE_HTML}</div>' in html and html.count(PAGE_HEADING) == 1
    assert '<pre class="whitespace-pre-wrap' not in html and ">Body<" not in html and "## Refunds" not in html
    # the synced note and the source link stay, under the rendered page, in the same card
    card = html.split(PAGE_HEADING)[1].split('id="platform-runs"')[0]
    assert "Synced from repo; read-only on this site." in card
    assert ('<a href="https://github.com/example/wiki/blob/main/refunds.md" target="_blank" rel="noopener" '
            'class="hover:underline">Open the source</a>') in card
    assert card.index('<div class="md">') < card.index("Synced from repo")
    # still read-only: no edit form, no Status card; Agents stay
    assert "/items/it1/edit" not in html and 'name="title"' not in html and ">Status<" not in html
    assert ">Agents<" in html and "Use this draft" not in html


def test_item_page_without_body_html_has_no_page_card(jinja_env):
    tpl = jinja_env.get_template("platform/item.html")
    for ctx in (_item_ctx(), _item_ctx(body_html=""), _item_ctx(body_html=None),
                _item_ctx(item=_item(meta={"kind": "brief"}), next_status="review", body_html="")):
        html = tpl.render(**ctx)
        assert PAGE_HEADING not in html and 'class="md"' not in html and "/items/it1/edit" in html
    for ctx in (_item_ctx(item=_item(source="repo"), read_only=True),
                _item_ctx(item=_item(source="repo"), read_only=True, body_html="")):
        html = tpl.render(**ctx)
        assert PAGE_HEADING not in html and 'class="md"' not in html
        assert ">Body<" in html and '<pre class="whitespace-pre-wrap' in html and "Refunds within 30 days." in html
        assert "Synced from repo; read-only on this site." in html


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


MENTIONS = [{"module": "marketing", "module_label": "Marketing", "id": "mk1", "title": "Launch post", "why": "approved"},
            {"module": "knowledge", "module_label": "Knowledge", "id": "it1", "title": "Refund policy", "why": "waiting"},
            {"module": "accounting", "module_label": "Accounting", "id": "ac1", "title": "October ledger", "why": "money"},
            {"module": "hr", "module_label": "HR", "id": "hr1", "title": "Onboard Sam", "why": "done"}]
MENTIONS_HEADING = '<div class="ss-meta">Mentioned in this brief</div>'


def test_brief_page_lists_the_mentions_under_the_latest_brief(jinja_env):
    tpl = jinja_env.get_template("platform/brief.html")
    html = tpl.render(**_brief_ctx([_brief(1), _brief(2)], mentions=MENTIONS))
    assert html.count(MENTIONS_HEADING) == 1
    # inside the latest-brief card: after its pre, before the earlier briefs
    card = html.split('action="/api/brief"')[1].split("</form>")[1].split("Earlier briefs")[0]
    assert card.index("</pre>") < card.index(MENTIONS_HEADING)
    block = card.split(MENTIONS_HEADING)[1]
    for m, cls in zip(MENTIONS, ("chip chip-ok", "chip chip-warn", "chip ", "chip chip-ok")):
        link = f'<a href="/m/{m["module"]}/items/{m["id"]}" class="ss-body-sm hover:underline">{m["title"]}</a>'
        assert link in block
        row = block.split(link)[1].split("</span>")[0] + "</span>"
        assert f'<span class="{cls}">{m["why"]}</span>' in row
    # the mention links are in order and the earlier-briefs list follows them
    assert [block.index(f'/m/{m["module"]}/items/{m["id"]}"') for m in MENTIONS] == sorted(
        block.index(f'/m/{m["module"]}/items/{m["id"]}"') for m in MENTIONS)
    assert html.index(MENTIONS_HEADING) < html.index("Earlier briefs")
    # while the brief is still being written nothing is mentioned yet
    html = tpl.render(**_brief_ctx([_brief(body="")], polling=True, mentions=MENTIONS))
    assert MENTIONS_HEADING not in html and "/m/marketing/items/mk1" not in html and "being written" in html


def test_brief_page_without_mentions_has_no_mentioned_block(jinja_env):
    tpl = jinja_env.get_template("platform/brief.html")
    for ctx in (_brief_ctx([_brief()]), _brief_ctx([_brief()], mentions=[]), _brief_ctx([_brief()], mentions=None),
                _brief_ctx([], mentions=MENTIONS)):
        html = tpl.render(**ctx)
        assert "Mentioned in this brief" not in html and 'class="ss-body-sm hover:underline"' not in html
        assert "/m/marketing/items/mk1" not in html


# ---- board ----------------------------------------------------------------------------------------------

def _card(id="it1", status="review", **over):
    base = _item(id=id, status=status, attention="", due_at=None, owner_user_id="u1", assignee_user_id=None, source="manual",
                 assignee_name=None, owner_name="ana@example.com", overdue=False, read_only=False,
                 next_status={"draft": "review", "review": "approved", "approved": "done", "done": None}[status])
    base.pop("latest_run", None)
    base.update(over)
    return base


def _board_ctx(cards=(), module="knowledge", **over):
    columns = [{"status": s, "items": [c for c in cards if c["status"] == s]} for s in STATUSES]
    ctx = dict(request=_Req(f"/m/{module}/board"), module=module, mod=_mod(), pages=[], columns=columns,
               today="2026-10-31", is_owner=True, modules_nav=MODULES_NAV)
    ctx.update(over)
    return ctx


def _column(html, status):
    return html.split(f'data-status="{status}"')[1].split("data-status=")[0]


def test_board_page_columns_in_status_order_with_counts(jinja_env):
    cards = [_card("it1", "draft"), _card("it2", "draft", attention="ai_done"), _card("it3", "review", attention="needs_you")]
    html = jinja_env.get_template("platform/board.html").render(**_board_ctx(cards))
    assert "Platform · knowledge" in html and "Knowledge board" in html
    assert '<a href="/m/knowledge" class="ss-meta hover:underline">' in html
    assert [html.index(f'data-status="{s}"') for s in STATUSES] == sorted(html.index(f'data-status="{s}"') for s in STATUSES)
    row = html.split("<section")[1].split('data-status=')[0]
    assert "overflow-x-auto" in row
    draft = _column(html, "draft")
    assert '<span class="chip ">draft</span>' in draft and '<span class="ss-numeral">2</span>' in draft
    assert 'href="/m/knowledge/items/it1"' in draft and 'href="/m/knowledge/items/it2"' in draft and "AI done" in draft
    review = _column(html, "review")
    assert '<span class="chip chip-warn">review</span>' in review and '<span class="ss-numeral">1</span>' in review
    assert 'href="/m/knowledge/items/it3"' in review and "Needs you" in review
    for s in ("approved", "done"):
        assert "Nothing here." in _column(html, s) and "/items/" not in _column(html, s)
    assert "Nothing here." not in draft
    # nav: the module stays highlighted; nothing confirms through the browser
    assert '<a href="/m/knowledge" class="nav-link active">Knowledge</a>' in html
    assert "window.confirm" not in html and "hx-confirm" not in html and "hx-post" not in html


def test_board_card_due_assignee_source_and_next_status(jinja_env):
    tpl = jinja_env.get_template("platform/board.html")
    cards = [_card("it1", "draft", due_at="2026-11-15", assignee_name="ben@example.com"),
             _card("it2", "draft", due_at="2026-10-01", overdue=True),
             _card("it3", "review"),
             _card("it4", "approved", due_at="2026-10-01"),
             _card("it5", "done"),
             _card("it6", "draft", source="repo", read_only=True)]
    html = tpl.render(**_board_ctx(cards))

    def card(item_id):  # one card: from its title link to the next card or column
        after = html.split(f'href="/m/knowledge/items/{item_id}"')[1]
        return after.split('<div class="card p-4 grid gap-2">')[0].split("data-status=")[0]

    one = card("it1")
    assert '<span class="ss-meta">due 2026-11-15</span>' in one and "chip-err" not in one
    assert '<span class="ss-meta">ben@example.com</span>' in one and "unassigned" not in one
    assert 'action="/api/m/knowledge/items/it1/status"' in one
    assert 'name="status" value="review"' in one and 'name="back" value="board"' in one
    assert '<button type="submit" class="btn btn-ghost btn-sm">→ review</button>' in one
    two = card("it2")
    assert '<span class="chip chip-err">due 2026-10-01</span>' in two and '<span class="ss-meta">unassigned</span>' in two
    assert "→ review" in two
    # towards approved there is no board button: approving stays on the item page behind its confirm
    three = card("it3")
    assert "/items/it3/status" not in three and "→" not in three and '<details class="confirm">' not in html
    four = card("it4")
    assert 'name="status" value="done"' in four and "→ done" in four and '<span class="ss-meta">due 2026-10-01</span>' in four
    assert "chip-err" not in four
    five = card("it5")
    assert "/items/it5/status" not in five and "→" not in five
    # a read-only card shows its source and has no status button
    six = card("it6")
    assert '<span class="chip">repo</span>' in six and "/items/it6/status" not in six and "→" not in six
    for item_id in ("it1", "it2", "it3", "it4", "it5"):
        assert '<span class="chip">manual</span>' not in card(item_id)
    # the columns hold their own cards: it6 is a draft and sits before the review column
    assert html.index('items/it6"') < html.index('data-status="review"') < html.index('items/it3"')


def test_board_page_empty(jinja_env):
    html = jinja_env.get_template("platform/board.html").render(**_board_ctx([]))
    assert html.count("Nothing here.") == len(STATUSES) and "/items/" not in html
    assert '<span class="ss-numeral">0</span>' in html


# ---- people directory -----------------------------------------------------------------------------------

def _people_ctx(people, **over):
    ctx = dict(request=_Req("/m/hr/people"), module="hr", mod=_mod(label="People", blurb="Who is on the team."),
               pages=[("people", "People directory")], people=people, is_owner=True,
               modules_nav=MODULES_NAV + [("hr", "People")])
    ctx.update(over)
    return ctx


def _person_row(n=1, **over):
    base = {"id": f"p{n}", "title": f"person{n}@example.com", "status": "draft", "updated_at": "2026-10-31 09:00",
            "meta": {"kind": "person", "user_id": f"u{n}", "role": "member", "start_date": "2026-10-20", "checklist": []},
            "role": "member", "start_date": "2026-10-20", "done": 0, "total": 0}
    base.update(over)
    return base


def test_people_page_empty_state(jinja_env):
    html = jinja_env.get_template("platform/people.html").render(**_people_ctx([]))
    assert "Platform · hr" in html and "People directory" in html
    assert "One person per member of this workspace; members appear here as they join. Open a person to draft their onboarding checklist." in html
    assert '<a href="/m/hr" class="ss-meta hover:underline">' in html
    assert "No people yet. Members appear here as they join." in html and "/m/hr/items/" not in html
    assert '<a href="/m/hr" class="nav-link active">People</a>' in html
    assert "window.confirm" not in html and "hx-" not in html.split("</nav>")[-1]


def test_people_page_rows(jinja_env):
    people = [_person_row(1, role="owner", done=2, total=5), _person_row(2, start_date="2026-10-28"), _person_row(3, role="", start_date="")]
    html = jinja_env.get_template("platform/people.html").render(**_people_ctx(people))
    assert "No people yet." not in html
    one = html.split('href="/m/hr/items/p1"')[1].split("</a>")[0]
    assert '<span class="ss-body-strong truncate">person1@example.com</span>' in one
    assert '<span class="chip">owner</span>' in one and "since 2026-10-20" in one and "2/5 onboarding items" in one
    assert "no checklist yet" not in one
    two = html.split('href="/m/hr/items/p2"')[1].split("</a>")[0]
    assert '<span class="chip">member</span>' in two and "since 2026-10-28" in two and "no checklist yet" in two
    three = html.split('href="/m/hr/items/p3"')[1].split("</a>")[0]
    assert "<span class=\"chip\">" not in three and "since " not in three and "no checklist yet" in three


# ---- ledger ---------------------------------------------------------------------------------------------

MONTHS = [{"month": "2026-10", "in": "1200.00", "out": "340.50", "net": "859.50", "count": 12},
          {"month": "2026-09", "in": "0.00", "out": "99.00", "net": "-99.00", "count": 3}]
ENTRIES = [{"id": "e1", "entry_date": "2026-10-03", "direction": "out", "kind": "expense", "description": "Render credits",
            "counterparty": "Kaggle", "category": "compute", "amount": "12.50", "currency": "USD"},
           {"id": "e2", "entry_date": "2026-10-20", "direction": "in", "kind": "invoice", "description": "Cat short",
            "counterparty": "Acme", "category": "sales", "amount": "1200.00", "currency": "USD"}]
CATEGORIES = [{"category": "sales", "direction": "in", "total": "1200.00", "count": 1},
              {"category": "compute", "direction": "out", "total": "340.50", "count": 11}]
IMPORTS = [{"id": "imp1", "title": "Import 2026-10-31 (12 rows)", "created_at": "2026-10-31 09:00",
            "meta": {"kind": "ledger_import", "rows": 12, "inserted": 10, "skipped": 2,
                     "problems": ["line 4: no amount"], "months": ["2026-10"]}}]


def _ledger_ctx(**over):
    ctx = dict(request=_Req("/m/accounting/ledger"), module="accounting", mod=_mod(label="Accounting", blurb="Money records."),
               pages=[("ledger", "Ledger")], months=MONTHS, month="2026-10", entries=ENTRIES, categories=CATEGORIES,
               imports=IMPORTS, modes=["statement", "out", "in"], imported=None, skipped=None, is_owner=True,
               modules_nav=MODULES_NAV + [("accounting", "Accounting")])
    ctx.update(over)
    return ctx


def _table(html, heading):
    return html.split(f'<div class="ss-body-strong">{heading}</div>')[1].split("</table>")[0]


def test_ledger_page_import_form_and_empty_state(jinja_env):
    html = jinja_env.get_template("platform/ledger.html").render(
        **_ledger_ctx(months=[], month="", entries=[], categories=[], imports=[]))
    assert "Platform · accounting" in html and ">Ledger</h1>" in html
    assert "Records only: expenses, invoices and revenue imported from CSV. Nothing here is advice." in html
    assert '<a href="/m/accounting" class="ss-meta hover:underline">' in html
    form = html.split('action="/api/m/accounting/ledger/import"')[1].split("</form>")[0]
    assert 'method="post"' in html.split('action="/api/m/accounting/ledger/import"')[0].rsplit("<form", 1)[1]
    assert 'enctype="multipart/form-data"' in html.split('action="/api/m/accounting/ledger/import"')[1].split(">")[0]
    assert '<textarea name="text" rows="6" placeholder="date, description, amount, category — or paste any export with a header row"' in form
    assert '<input type="file" name="file" accept=".csv,text/csv,text/plain"' in form
    assert '<input type="radio" name="mode" value="statement" checked> A statement: negative amounts are money out' in form
    assert '<input type="radio" name="mode" value="out"> All expenses (money out)' in form
    assert '<input type="radio" name="mode" value="in"> All income (money in)' in form
    assert '<button type="submit" class="btn btn-primary btn-sm">Import</button>' in form
    assert "No entries yet. Paste or upload a CSV above." in html
    assert ">Months<" not in html and "Categories in" not in html and "Entries in" not in html and "Recent imports" not in html
    assert "Imported " not in html and "window.confirm" not in html and "hx-confirm" not in html


def test_ledger_page_months_categories_entries_and_imports(jinja_env):
    html = jinja_env.get_template("platform/ledger.html").render(**_ledger_ctx())
    assert "No entries yet." not in html
    months = _table(html, "Months")
    assert '<a href="/m/accounting/ledger?month=2026-10" class="ss-body-strong hover:underline">2026-10</a>' in months
    assert '<a href="/m/accounting/ledger?month=2026-09" class="ss-body-strong hover:underline">2026-09</a>' in months
    assert months.index("2026-10</a>") < months.index("2026-09</a>")
    selected = months.split('data-month="2026-10"')[0].rsplit("<tr", 1)[1] + months.split('data-month="2026-10"')[1].split("</tr>")[0]
    assert "bg-gray-100" in selected and 'aria-current="true"' in selected
    assert '<td class="py-2 pr-3 text-right ss-numeral">1200.00</td>' in selected
    assert '<td class="py-2 pr-3 text-right ss-numeral">340.50</td>' in selected
    assert '<td class="py-2 pr-3 text-right ss-numeral">859.50</td>' in selected
    assert '<td class="py-2 text-right ss-numeral">12</td>' in selected
    other = months.split('data-month="2026-09"')[0].rsplit("<tr", 1)[1]
    assert "bg-gray-100" not in other and 'aria-current' not in other
    assert ">-99.00</td>" in months
    cats = _table(html, "Categories in 2026-10")
    sales = cats.split("<td class=\"py-2 pr-3\">sales</td>")[1].split("</tr>")[0]
    assert '<span class="chip chip-ok">in</span>' in sales and ">1200.00</td>" in sales and ">1</td>" in sales
    compute = cats.split("<td class=\"py-2 pr-3\">compute</td>")[1].split("</tr>")[0]
    assert '<span class="chip ">out</span>' in compute and ">340.50</td>" in compute and ">11</td>" in compute
    entries = _table(html, "Entries in 2026-10")
    e1 = entries.split('data-entry="e1"')[1].split("</tr>")[0]
    assert "2026-10-03" in e1 and '<span class="chip ">out</span>' in e1 and ">12.50 USD</td>" in e1
    assert ">compute</td>" in e1 and ">Render credits</td>" in e1 and ">Kaggle</td>" in e1 and ">expense</td>" in e1
    e2 = entries.split('data-entry="e2"')[1].split("</tr>")[0]
    assert '<span class="chip chip-ok">in</span>' in e2 and ">1200.00 USD</td>" in e2 and ">Cat short</td>" in e2
    imports = html.split("Recent imports")[1]
    row = imports.split('href="/m/accounting/items/imp1"')[1].split("</a>")[0]
    assert "Import 2026-10-31 (12 rows)" in row and "2026-10-31 09:00" in row
    assert '<div class="ss-meta">12 rows · 10 inserted · 2 skipped</div>' in row and "line 4: no amount" in row
    # the nav keeps the module active
    assert '<a href="/m/accounting" class="nav-link active">Accounting</a>' in html


def test_ledger_page_import_echo_and_month_without_rows(jinja_env):
    tpl = jinja_env.get_template("platform/ledger.html")
    html = tpl.render(**_ledger_ctx(imported=10, skipped=2))
    assert "Imported 10 entries, skipped 2 already in the ledger." in html
    html = tpl.render(**_ledger_ctx(imported=0, skipped=0))
    assert "Imported 0 entries, skipped 0 already in the ledger." in html
    # a selected month with nothing in it: both tables show their empty line; no month: neither heading
    html = tpl.render(**_ledger_ctx(month="2026-09", entries=[], categories=[]))
    assert "Categories in 2026-09" in html and "Entries in 2026-09" in html and html.count("No entries in this month.") == 2
    assert "Imported " not in html
    html = tpl.render(**_ledger_ctx(month=""))
    assert ">Months<" in html and "Categories in" not in html and "Entries in" not in html
    # an import without problems lists none
    html = tpl.render(**_ledger_ctx(imports=[{**IMPORTS[0], "meta": {**IMPORTS[0]["meta"], "problems": []}}]))
    assert "line 4: no amount" not in html and "12 rows · 10 inserted · 2 skipped" in html


# ---- integrations ---------------------------------------------------------------------------------------

GITHUB = {"external_account": "wolfwdavid", "scopes": "repo, read:org",
          "repos": ["wolfwdavid/synaps-optic-backend", "wolfwdavid/synaps-optic-frontend"],
          "updated_at": "2026-10-31 09:00", "last_sync_at": "2026-10-31 09:30", "last_error": None}


def _integrations_ctx(**over):
    ctx = dict(request=_Req("/m/dev/integrations"), module="dev", mod=_mod(label="Dev", blurb="Code and pull requests."),
               pages=[("integrations", "Integrations")], configured=True, github=None, open_prs=0, poll_minutes=10,
               is_owner=True, modules_nav=MODULES_NAV + [("dev", "Dev")])
    ctx.update(over)
    return ctx


def _github_card(html):
    return html.split('<div class="ss-body-strong">GitHub</div>')[1].split('action="/api/m/dev/integrations/github"')[0]


def _connect_form(html):
    return html.split('action="/api/m/dev/integrations/github"')[1].split("</form>")[0]


def test_integrations_page_not_configured(jinja_env):
    html = jinja_env.get_template("platform/integrations.html").render(**_integrations_ctx(configured=False))
    assert "Integrations are not configured on this server: the owner must set INTEGRATION_TOKEN_KEY." in html
    box = html.split("Integrations are not configured on this server")[0].rsplit("<div", 1)[1]
    assert "status-err" in box
    # the connect form still renders, its button disabled
    form = _connect_form(html)
    assert 'name="token"' in form and 'name="repos"' in form
    assert '<button type="submit" class="ml-auto btn btn-primary btn-sm" disabled>Connect</button>' in form
    assert '<span class="chip">Not connected</span>' in html


def test_integrations_page_not_connected(jinja_env):
    html = jinja_env.get_template("platform/integrations.html").render(**_integrations_ctx())
    assert "Platform · dev" in html and ">Integrations</h1>" in html
    assert ("Bring your own account: a personal access token this workspace uses to read its repositories. "
            "Nothing is ever written to GitHub.") in html
    assert '<a href="/m/dev" class="ss-meta hover:underline">' in html
    body = html.split("</style>")[-1]
    assert "INTEGRATION_TOKEN_KEY" not in body and "status-err" not in body
    card = _github_card(html)
    assert '<span class="chip">Not connected</span>' in card and "connected as" not in card
    assert "Sync now" not in html and "/github/sync" not in html and "/github/delete" not in html
    assert '<details class="confirm">' not in html and "Disconnect" not in html
    # the connect form: a plain post, autocomplete off, the password input and the repos textarea
    open_tag = html.split('action="/api/m/dev/integrations/github"')[0].rsplit("<form", 1)[1]
    assert 'method="post"' in open_tag
    assert 'autocomplete="off"' in html.split('action="/api/m/dev/integrations/github"')[1].split(">")[0]
    form = _connect_form(html)
    assert ">Connect GitHub<" in form and ">Personal access token<" in form and ">Repositories<" in form
    assert ('<input type="password" name="token" class="input" autocomplete="off" '
            'placeholder="github_pat_… (fine-grained: Contents and Pull requests, read)" required>') in form
    assert ('<textarea name="repos" rows="3" class="textarea" placeholder="owner/name, one per line or comma-separated" '
            'required></textarea>') in form
    assert '<button type="submit" class="ml-auto btn btn-primary btn-sm">Connect</button>' in form
    assert ("The token is stored encrypted and only used to read the repositories; "
            "the lane polls them every 10 minutes.") in form
    assert "How to make the token: GitHub → Settings → Developer settings → Fine-grained tokens." in form
    assert "Contents and Pull requests, read-only; metadata read is added automatically." in form
    assert "window.confirm" not in html and "hx-confirm" not in html
    assert '<a href="/m/dev" class="nav-link active">Dev</a>' in html


def test_integrations_page_connected(jinja_env):
    html = jinja_env.get_template("platform/integrations.html").render(**_integrations_ctx(github=GITHUB, open_prs=3))
    card = _github_card(html)
    assert '<span class="chip chip-ok">connected as wolfwdavid</span>' in card and "Not connected" not in card
    assert '<div class="ss-meta">scopes repo, read:org</div>' in card
    assert '<span class="chip">wolfwdavid/synaps-optic-backend</span>' in card
    assert '<span class="chip">wolfwdavid/synaps-optic-frontend</span>' in card
    assert '<div class="ss-meta">3 open pull requests · polled every 10 min · last poll 2026-10-31 09:30</div>' in card
    assert "status-err" not in card
    sync = card.split('action="/api/m/dev/integrations/github/sync"')[1].split("</form>")[0]
    assert 'method="post"' in card.split('action="/api/m/dev/integrations/github/sync"')[0].rsplit("<form", 1)[1]
    assert '<button type="submit" class="btn btn-secondary btn-sm">Sync now</button>' in sync
    # disconnect is the inline two-step, never a modal
    dis = _confirm(html, "/api/m/dev/integrations/github/delete")
    assert dis and "Forget the token? The items already synced stay but stop updating." in dis
    assert ">Disconnect</button>" in dis and ">Cancel</button>" in dis
    assert '<summary class="btn btn-ghost btn-sm" role="button">Disconnect</summary>' in card
    assert "window.confirm" not in html and "hx-confirm" not in html
    # the form updates: repos prefilled one per line, the button reads Update, the token never echoed
    form = _connect_form(html)
    assert ">Update the connection<" in form
    assert ('<textarea name="repos" rows="3" class="textarea" placeholder="owner/name, one per line or comma-separated" '
            'required>wolfwdavid/synaps-optic-backend\nwolfwdavid/synaps-optic-frontend</textarea>') in form
    assert '<button type="submit" class="ml-auto btn btn-primary btn-sm">Update</button>' in form and ">Connect<" not in form
    token = form.split('name="token"')[1].split(">")[0]
    assert 'type="password"' in form.split('name="token"')[0].rsplit("<input", 1)[1] and "value=" not in token


def test_integrations_page_error_box_and_never_polled(jinja_env):
    github = {**GITHUB, "scopes": "", "repos": [], "last_sync_at": None,
              "last_error": "HTTPStatusError: 401 Bad credentials"}
    html = jinja_env.get_template("platform/integrations.html").render(**_integrations_ctx(github=github))
    card = _github_card(html)
    assert "HTTPStatusError: 401 Bad credentials" in card
    box = card.split("HTTPStatusError")[0].rsplit("<div", 1)[1]
    assert "status-err" in box
    assert '<div class="ss-meta">0 open pull requests · polled every 10 min · last poll never</div>' in card
    assert "scopes " not in card and '<span class="chip">wolfwdavid' not in card
    assert '<span class="chip chip-ok">connected as wolfwdavid</span>' in card and "Sync now" in card
    assert ('<textarea name="repos" rows="3" class="textarea" placeholder="owner/name, one per line or comma-separated" '
            'required></textarea>') in html
    assert ">Update</button>" in html


# ---- pull requests and repositories as items ------------------------------------------------------------

def _pr(n=1, **meta):
    base_meta = {"kind": "pr", "repo": "wolfwdavid/synaps-optic-backend", "number": n, "author": "wolfwdavid",
                 "head": "feature/x", "sha": "abc123", "base": "main", "draft": False, "checks": "success",
                 "state": "open", "pr_updated_at": "2026-10-31T09:00:00Z"}
    base_meta.update(meta)
    return _item(id=f"pr{n}", title=f"wolfwdavid/synaps-optic-backend#{n}: Add the thing", status="review",
                 attention="", latest_run=None, source="github", read_only=True, meta=base_meta,
                 external_url=f"https://github.com/wolfwdavid/synaps-optic-backend/pull/{n}")


def _repo(id="r1", **meta):
    base_meta = {"kind": "repo", "repo": "wolfwdavid/synaps-optic-backend", "default_branch": "main",
                 "open_prs": 2, "private": True}
    base_meta.update(meta)
    return _item(id=id, title="wolfwdavid/synaps-optic-backend", status="approved", attention="", latest_run=None,
                 source="github", read_only=True, meta=base_meta,
                 external_url="https://github.com/wolfwdavid/synaps-optic-backend")


def _dev_module_ctx(items):
    return _module_ctx("dev", mod=_mod(label="Dev"), pages=[("integrations", "Integrations")], items=items)


@pytest.mark.parametrize("checks, chip", [
    ("success", '<span class="chip chip-ok">checks pass</span>'),
    ("failure", '<span class="chip chip-err">checks fail</span>'),
    ("pending", '<span class="chip chip-warn">checks running</span>'),
    ("none", None),
    (None, None),
])
def test_module_page_pull_request_chips(jinja_env, checks, chip):
    html = jinja_env.get_template("platform/module.html").render(**_dev_module_ctx([_pr(7, checks=checks)]))
    row = html.split('href="/m/dev/items/pr7"')[1].split("</a>")[0]
    assert '<span class="chip">pr</span>' in row and '<span class="chip">github</span>' in row
    assert '<span class="ss-meta">#7 by wolfwdavid</span>' in row and "draft pr" not in row
    if chip:
        assert chip in row and row.count("checks") == 1
    else:
        assert "checks" not in row
    assert '<a href="/m/dev/integrations" class="btn btn-secondary btn-sm">Integrations</a>' in html


def test_module_page_draft_pr_and_repo_chips(jinja_env):
    draft = _pr(8, draft=True)
    del draft["meta"]["checks"]
    bare = _repo("r2")
    del bare["meta"]["open_prs"]
    html = jinja_env.get_template("platform/module.html").render(
        **_dev_module_ctx([draft, _repo(), bare, _repo("r3", open_prs=0)]))
    row = html.split('href="/m/dev/items/pr8"')[1].split("</a>")[0]
    assert '<span class="chip">pr</span>' in row and '<span class="chip">draft pr</span>' in row and "checks" not in row
    assert row.index(">pr<") < row.index(">draft pr<") < row.index("#8 by wolfwdavid")
    assert '<span class="chip">repo</span>' not in row
    r1 = html.split('href="/m/dev/items/r1"')[1].split("</a>")[0]
    assert '<span class="chip">repo</span>' in r1 and '<span class="ss-meta">2 open</span>' in r1
    assert '<span class="chip">pr</span>' not in r1 and '<span class="chip">github</span>' in r1 and " by " not in r1
    r2 = html.split('href="/m/dev/items/r2"')[1].split("</a>")[0]
    assert '<span class="chip">repo</span>' in r2 and " open</span>" not in r2
    r3 = html.split('href="/m/dev/items/r3"')[1].split("</a>")[0]
    assert '<span class="ss-meta">0 open</span>' in r3


def _dev_item_ctx(item, **over):
    ctx = dict(read_only=True, module="dev", mod=_mod(label="Dev"), next_status=None, request=_Req(f"/m/dev/items/{item['id']}"))
    ctx.update(over)
    return _item_ctx(item=item, **ctx)


def _left_card(html, heading):
    """The first card on the left, from its heading to the read-only Body card that follows it."""
    return html.split(f'<div class="ss-body-strong">{heading}</div>')[1].split('<div class="ss-body-strong">Body</div>')[0]


def test_item_page_pull_request_card(jinja_env):
    tpl = jinja_env.get_template("platform/item.html")
    html = tpl.render(**_dev_item_ctx(_pr(7, checks="failure", draft=True)))
    header = html.split("</h1>")[1].split("md:grid-cols")[0]
    assert '<span class="chip">pr</span>' in header and '<span class="chip">repo</span>' not in header
    card = _left_card(html, "Pull request")
    assert ">Repo<" in card and ">wolfwdavid/synaps-optic-backend#7</span>" in card
    assert ">Author<" in card and ">wolfwdavid</span>" in card
    assert ">Branch<" in card and ">feature/x → main</span>" in card
    assert '<span class="chip chip-warn">open</span>' in card
    assert '<span class="chip chip-err">checks fail</span>' in card
    assert '<span class="chip">draft</span>' in card
    assert ('<a href="https://github.com/wolfwdavid/synaps-optic-backend/pull/7" target="_blank" rel="noopener" '
            'class="ml-auto btn btn-secondary btn-sm">Open on GitHub</a>') in card
    # first on the left, above the read-only body and its synced note; still no edit form or Status card
    assert html.index(">Pull request</div>") < html.index(">Body</div>") < html.index("Synced from github; read-only on this site.")
    assert ">Status<" not in html and "/items/pr7/edit" not in html and ">Repository</div>" not in html
    assert "window.confirm" not in html and "hx-confirm" not in html
    # merged: chip-ok, no checks chip for "none", no draft chip, no button without a url
    merged = _pr(9, state="merged", checks="none")
    merged["status"] = "done"
    del merged["external_url"]
    html = tpl.render(**_dev_item_ctx(merged))
    card = _left_card(html, "Pull request")
    assert '<span class="chip chip-ok">merged</span>' in card and "checks" not in card
    assert '<span class="chip">draft</span>' not in card and "Open on GitHub" not in html
    # closed: a plain chip; pending checks
    closed = _pr(10, state="closed", checks="pending")
    closed["status"] = "draft"
    html = tpl.render(**_dev_item_ctx(closed))
    card = _left_card(html, "Pull request")
    assert '<span class="chip ">closed</span>' in card and '<span class="chip chip-warn">checks running</span>' in card
    # the card does not depend on read_only: an editable pr still shows it, above the edit form
    html = tpl.render(**_dev_item_ctx(_pr(11), read_only=False))
    assert ">Pull request</div>" in html and html.index(">Pull request</div>") < html.index("/items/pr11/edit")


def test_item_page_repository_card(jinja_env):
    tpl = jinja_env.get_template("platform/item.html")
    html = tpl.render(**_dev_item_ctx(_repo()))
    header = html.split("</h1>")[1].split("md:grid-cols")[0]
    assert '<span class="chip">repo</span>' in header and '<span class="chip">pr</span>' not in header
    card = _left_card(html, "Repository")
    assert ">Branch<" in card and ">main</span>" in card
    assert ">Open<" in card and ">2 open pull requests</span>" in card
    assert '<span class="chip">private</span>' in card and "public" not in card
    assert ('<a href="https://github.com/wolfwdavid/synaps-optic-backend" target="_blank" rel="noopener" '
            'class="ml-auto btn btn-secondary btn-sm">Open on GitHub</a>') in card
    assert html.index(">Repository</div>") < html.index(">Body</div>")
    assert ">Pull request</div>" not in html and ">Status<" not in html
    html = tpl.render(**_dev_item_ctx(_repo(open_prs=1, private=False, default_branch="develop")))
    card = _left_card(html, "Repository")
    assert ">1 open pull request</span>" in card and '<span class="chip">public</span>' in card and ">develop</span>" in card
    html = tpl.render(**_dev_item_ctx(_repo(open_prs=0)))
    assert ">0 open pull requests</span>" in _left_card(html, "Repository")
    # an ordinary item has neither card
    html = tpl.render(**_item_ctx())
    assert ">Pull request</div>" not in html and ">Repository</div>" not in html and "Open on GitHub" not in html


# ---- start work (the Work card) and posting a review as a comment ---------------------------------------

WORK_REPOS = ["wolfwdavid/synaps-optic-backend", "wolfwdavid/synaps-optic-frontend"]
WORK = {"repo": "wolfwdavid/synaps-optic-backend", "branch": "work/refund-policy-it1", "base": "main",
        "brief_path": "briefs/refund-policy-it1.md",
        "branch_url": "https://github.com/wolfwdavid/synaps-optic-backend/tree/work/refund-policy-it1",
        "compare_url": "https://github.com/wolfwdavid/synaps-optic-backend/compare/main...work/refund-policy-it1?expand=1",
        "started_at": "2026-10-31 10:00"}
WORK_HEADING = '<div class="ss-meta">Work</div>'
START_WORK_URL = "/api/m/knowledge/items/it1/start-work"


def _right_column(html):
    return html.split("md:grid-cols")[1].split('<div class="grid gap-4 content-start">')[1]


def _work_card(html):
    return _right_column(html).split(WORK_HEADING)[1].split('<div class="ss-meta">Agents</div>')[0]


def test_item_page_work_card_offers_start_work(jinja_env):
    html = jinja_env.get_template("platform/item.html").render(**_item_ctx(work_repos=WORK_REPOS, work=None))
    right = _right_column(html)
    assert right.count(WORK_HEADING) == 1
    card = _work_card(html)
    assert 'method="post"' in card.split(f'action="{START_WORK_URL}"')[0].rsplit("<form", 1)[1]
    form = card.split(f'action="{START_WORK_URL}"')[1].split("</form>")[0]
    select = form.split('<select name="repo" class="select select-sm"')[1].split("</select>")[0]
    assert '<option value="wolfwdavid/synaps-optic-backend">wolfwdavid/synaps-optic-backend</option>' in select
    assert '<option value="wolfwdavid/synaps-optic-frontend">wolfwdavid/synaps-optic-frontend</option>' in select
    assert select.index("optic-backend") < select.index("optic-frontend") and select.count("<option") == 2
    assert '<button type="submit" class="btn btn-primary btn-sm">Start work</button>' in form
    assert "Creates a branch and a brief file in the repo; nothing else changes." in card
    # in the right column between Status and Agents; nothing of the started state; no branch chip yet
    assert right.index(">Status<") < right.index(WORK_HEADING) < right.index(">Agents<")
    assert ">Branch<" not in card and "Open a pull request" not in html and "hx-post" not in card
    header = html.split("</h1>")[1].split("md:grid-cols")[0]
    assert '<span class="chip">branch</span>' not in header
    assert "window.confirm" not in html and "hx-confirm" not in html
    # the left column is unchanged
    assert "/items/it1/edit" in html and 'id="platform-runs"' in html


def test_item_page_work_card_shows_the_branch_once_started(jinja_env):
    tpl = jinja_env.get_template("platform/item.html")
    item = _item(meta={"work": WORK})
    html = tpl.render(**_item_ctx(item=item, work_repos=WORK_REPOS, work=WORK))
    header = html.split("</h1>")[1].split("md:grid-cols")[0]
    assert '<span class="chip">branch</span>' in header
    right = _right_column(html)
    assert right.count(WORK_HEADING) == 1
    card = _work_card(html)
    assert ">Branch<" in card
    assert ('<a href="https://github.com/wolfwdavid/synaps-optic-backend/tree/work/refund-policy-it1" target="_blank" '
            'rel="noopener" class="ss-body-sm break-words hover:underline">work/refund-policy-it1</a>') in card
    assert "briefs/refund-policy-it1.md in wolfwdavid/synaps-optic-backend, from main" in card
    assert ('<a href="https://github.com/wolfwdavid/synaps-optic-backend/compare/main...work/refund-policy-it1?expand=1" '
            'target="_blank" rel="noopener" class="btn btn-secondary btn-sm">Open a pull request</a>') in card
    assert card.index(">Branch<") < card.index("work/refund-policy-it1</a>") < card.index("briefs/") < card.index("Open a pull request")
    # no second start: no form, no select, no button
    assert "/start-work" not in html and 'name="repo"' not in html and "Start work" not in html
    assert right.index(">Status<") < right.index(WORK_HEADING) < right.index(">Agents<")
    # the started state shows with the repos missing from the context too, and on a read-only item (no Status card)
    html = tpl.render(**_item_ctx(item=item, work=WORK))
    assert ">Branch<" in html and "Open a pull request" in html and "/start-work" not in html
    html = tpl.render(**_item_ctx(item=_item(source="repo", meta={"work": WORK}), read_only=True, work=WORK, work_repos=[]))
    assert ">Status<" not in html and WORK_HEADING in html and "Open a pull request" in html and "/start-work" not in html
    assert html.index(WORK_HEADING) < html.index(">Agents<") and '<span class="chip">branch</span>' in html


def test_item_page_without_work_has_no_work_card(jinja_env):
    tpl = jinja_env.get_template("platform/item.html")
    for ctx in (_item_ctx(), _item_ctx(work_repos=[], work=None), _item_ctx(work_repos=None, work=None),
                # a read-only item never offers to start work, even if repos reach its context
                _item_ctx(item=_item(source="repo"), read_only=True, work_repos=WORK_REPOS, work=None),
                _dev_item_ctx(_pr(7), work_repos=WORK_REPOS, work=None)):
        html = tpl.render(**ctx)
        assert WORK_HEADING not in html and "/start-work" not in html and "Start work" not in html
        assert "Open a pull request" not in html and '<span class="chip">branch</span>' not in html
        assert ">Agents<" in html


def test_module_page_branch_chip_when_work_started(jinja_env):
    items = [_item(meta={"work": WORK}), _item(id="it2"), _item(id="it3", meta={"kind": "policy", "work": WORK}),
             _item(id="it4", meta={"work": None})]
    html = jinja_env.get_template("platform/module.html").render(**_module_ctx(items=items))
    one = html.split('href="/m/knowledge/items/it1"')[1].split("</a>")[0]
    assert '<span class="chip">branch</span>' in one
    for item_id in ("it2", "it4"):
        row = html.split(f'href="/m/knowledge/items/{item_id}"')[1].split("</a>")[0]
        assert '<span class="chip">branch</span>' not in row
    three = html.split('href="/m/knowledge/items/it3"')[1].split("</a>")[0]
    assert '<span class="chip">policy</span>' in three and '<span class="chip">branch</span>' in three
    assert three.index(">policy<") < three.index(">branch<")


def _review(**over):
    base = _run("done", id="rv1", label="Review", agent="review", output={"text": "Looks fine; one nit in the tests."})
    base.update(over)
    return base


def _render_pr_runs(jinja_env, runs, **over):
    ctx = dict(module="dev", item=_pr(7), runs=runs, polling=False, read_only=True, comment_agent="review")
    ctx.update(over)
    return jinja_env.get_template("partials/platform_runs.html").render(**ctx)


COMMENT_URL = "/api/m/dev/runs/rv1/comment"
COMMENT_QUESTION = ("Post this review as a comment on the pull request? It goes to GitHub under your token, "
                    "and the agent never approves or merges.")


def test_runs_partial_offers_to_post_a_done_review_as_a_comment(jinja_env):
    html = _render_pr_runs(jinja_env, [_review()])
    assert "Looks fine; one nit in the tests." in html and ">Review</span>" in html
    block = _confirm(html, COMMENT_URL)
    assert block and COMMENT_QUESTION in block
    assert 'method="post"' in block.split(f'action="{COMMENT_URL}"')[0].rsplit("<form", 1)[1]
    assert "hx-post" not in block
    assert '<button type="submit" class="btn btn-primary btn-sm">Post</button>' in block and ">Cancel</button>" in block
    assert '<summary class="btn btn-secondary btn-sm" role="button">Post as a comment</summary>' in html
    assert html.count('<details class="confirm">') == 1
    assert "window.confirm" not in html and "hx-confirm" not in html
    # it stands in for "Use this draft": the pr item is read-only, and a writable context keeps the comment form too
    assert "Use this draft" not in html and "/apply" not in html
    assert "Posted as a comment" not in html and "View on GitHub" not in html
    html = _render_pr_runs(jinja_env, [_review()], read_only=False)
    assert _confirm(html, COMMENT_URL) and "Use this draft" not in html and "/apply" not in html
    # through the item page of a read-only pull request the included partial renders the same confirm
    html = jinja_env.get_template("platform/item.html").render(**_dev_item_ctx(_pr(7), runs=[_review()], comment_agent="review"))
    block = _confirm(html, COMMENT_URL)
    assert block and COMMENT_QUESTION in block and ">Post</button>" in block
    assert "Use this draft" not in html and ">Status<" not in html and "/items/pr7/edit" not in html


def test_runs_partial_comment_only_for_the_comment_agent_when_done(jinja_env):
    tpl = jinja_env.get_template("partials/platform_runs.html")
    # another agent's done run on the same item: nothing to post (and nothing to apply, the item is read-only)
    html = _render_pr_runs(jinja_env, [_run("done", output={"text": "A summary."})])
    assert "Post as a comment" not in html and "/comment" not in html and "A summary." in html
    assert "Use this draft" not in html and '<details class="confirm">' not in html
    # comment_agent None or missing: a review run posts nothing
    for ctx in (dict(comment_agent=None), {}):
        base = dict(module="dev", item=_pr(7), runs=[_review()], polling=False, read_only=True)
        base.update(ctx)
        html = tpl.render(**base)
        assert "Post as a comment" not in html and "/comment" not in html and "Looks fine; one nit in the tests." in html
    # on an ordinary writable item without comment_agent the review run still offers "Use this draft"
    html = tpl.render(module="knowledge", item=_item(), runs=[_review()], polling=False)
    assert "Post as a comment" not in html and "Use this draft" in html and 'action="/api/m/knowledge/runs/rv1/apply"' in html
    # a review that is not done, or done without text, posts nothing
    for run in (_review(status="queued", position=0, output=None), _review(status="running", output=None),
                _review(status="failed", error="model timed out", output=None),
                _review(output={"text": ""}), _review(output=None)):
        html = _render_pr_runs(jinja_env, [run])
        assert "Post as a comment" not in html and "/comment" not in html and '<details class="confirm">' not in html


def test_runs_partial_shows_a_posted_review(jinja_env):
    posted = _review(output={"text": "Looks fine; one nit in the tests.",
                             "comment_url": "https://github.com/wolfwdavid/synaps-optic-backend/pull/7#issuecomment-42",
                             "commented_by": "david", "commented_at": "2026-10-31 10:05"})
    html = _render_pr_runs(jinja_env, [posted])
    assert '<span class="ss-meta">Posted as a comment by david</span>' in html
    assert ('<a href="https://github.com/wolfwdavid/synaps-optic-backend/pull/7#issuecomment-42" target="_blank" '
            'rel="noopener" class="ss-body-sm hover:underline">View on GitHub</a>') in html
    assert html.index("Posted as a comment") < html.index("View on GitHub")
    assert "Post as a comment" not in html and COMMENT_URL not in html and '<details class="confirm">' not in html
    assert "Use this draft" not in html and "/apply" not in html
    # without the poster's name the line is just "Posted as a comment"
    posted["output"].pop("commented_by")
    html = _render_pr_runs(jinja_env, [posted])
    assert '<span class="ss-meta">Posted as a comment</span>' in html and " by " not in html.split("Posted as a comment")[1].split("</a>")[0]
    # one posted and one still to post: the link for the first, the confirm for the second only
    html = _render_pr_runs(jinja_env, [posted, _review(id="rv2")])
    assert "View on GitHub" in html and _confirm(html, "/api/m/dev/runs/rv2/comment") and not _confirm(html, COMMENT_URL)
    assert html.count('<details class="confirm">') == 1


# ---- Linear: the integrations card, issues as items, create in Linear ------------------------------------

LINEAR = {"external_account": "dev@synapspaces.com", "scopes": "", "teams": ["OPT", "ENG"],
          "updated_at": "2026-10-31 11:00", "last_sync_at": "2026-10-31 11:30", "last_error": None}
LINEAR_HEADING = '<div class="ss-body-strong">Linear</div>'
LINEAR_CARD_HEADING = '<div class="ss-meta">Linear</div>'
CREATE_URL = "/api/m/knowledge/items/it1/linear"


def _linear_card(html):
    return html.split(LINEAR_HEADING)[1].split('action="/api/m/dev/integrations/linear"')[0]


def _linear_form(html):
    return html.split('action="/api/m/dev/integrations/linear"')[1].split("</form>")[0]


def test_integrations_page_linear_not_connected(jinja_env):
    html = jinja_env.get_template("platform/integrations.html").render(**_integrations_ctx(linear=None, issues=0))
    assert html.index(LINEAR_HEADING) > html.index('action="/api/m/dev/integrations/github"')
    card = _linear_card(html)
    assert '<span class="chip">Not connected</span>' in card and "connected as" not in card
    assert "issues mirrored" not in card and "every team the key sees" not in card
    assert "/linear/sync" not in html and "/linear/delete" not in html and "Forget the key?" not in html
    open_tag = html.split('action="/api/m/dev/integrations/linear"')[0].rsplit("<form", 1)[1]
    assert 'method="post"' in open_tag
    assert 'autocomplete="off"' in html.split('action="/api/m/dev/integrations/linear"')[1].split(">")[0]
    form = _linear_form(html)
    assert ">Connect Linear<" in form and ">Personal API key<" in form and ">Teams<" in form
    assert ('<input type="password" name="token" class="input" autocomplete="off" '
            'placeholder="lin_api_… (a personal API key)" required>') in form
    assert ('<input name="teams" class="input" autocomplete="off" '
            'placeholder="OPT, ENG (empty = every team the key sees)" value="">') in form
    assert '<button type="submit" class="ml-auto btn btn-primary btn-sm">Connect</button>' in form
    assert ("Issues of these teams become Product items; edits and status moves on the site go back to Linear. "
            "Nothing is deleted on either side.") in form
    assert "Linear → Settings → Security &amp; access → Personal API keys" in form
    assert "window.confirm" not in html and "hx-confirm" not in html
    # the GitHub side is untouched
    assert ">Connect GitHub<" in html and html.count('<span class="chip">Not connected</span>') == 2
    # without the encryption key the button is disabled, like GitHub's
    html = jinja_env.get_template("platform/integrations.html").render(**_integrations_ctx(configured=False))
    assert '<button type="submit" class="ml-auto btn btn-primary btn-sm" disabled>Connect</button>' in _linear_form(html)


def test_integrations_page_linear_connected(jinja_env):
    html = jinja_env.get_template("platform/integrations.html").render(
        **_integrations_ctx(github=GITHUB, open_prs=3, linear=LINEAR, issues=12))
    card = _linear_card(html)
    assert '<span class="chip chip-ok">connected as dev@synapspaces.com</span>' in card and "Not connected" not in card
    assert '<span class="chip">OPT</span>' in card and '<span class="chip">ENG</span>' in card
    assert card.index(">OPT<") < card.index(">ENG<") and "every team the key sees" not in card
    assert '<div class="ss-meta">12 issues mirrored · polled every 10 min · last poll 2026-10-31 11:30</div>' in card
    assert "status-err" not in card and "scopes" not in card
    sync = card.split('action="/api/m/dev/integrations/linear/sync"')[1].split("</form>")[0]
    assert 'method="post"' in card.split('action="/api/m/dev/integrations/linear/sync"')[0].rsplit("<form", 1)[1]
    assert '<button type="submit" class="btn btn-secondary btn-sm">Sync now</button>' in sync
    dis = _confirm(html, "/api/m/dev/integrations/linear/delete")
    assert dis and "Forget the key? The items already mirrored stay but stop updating." in dis
    assert ">Disconnect</button>" in dis and ">Cancel</button>" in dis
    assert '<summary class="btn btn-ghost btn-sm" role="button">Disconnect</summary>' in card
    assert html.count('<details class="confirm">') == 2 and "window.confirm" not in html
    # the form updates: teams prefilled, the button reads Update, the key never echoed
    form = _linear_form(html)
    assert ">Update the connection<" in form and ">Connect Linear<" not in form
    assert ('<input name="teams" class="input" autocomplete="off" '
            'placeholder="OPT, ENG (empty = every team the key sees)" value="OPT, ENG">') in form
    assert '<button type="submit" class="ml-auto btn btn-primary btn-sm">Update</button>' in form and ">Connect<" not in form
    token = form.split('name="token"')[1].split(">")[0]
    assert 'type="password"' in form.split('name="token"')[0].rsplit("<input", 1)[1] and "value=" not in token
    # the GitHub card and form are untouched by the Linear state
    assert '<span class="chip chip-ok">connected as wolfwdavid</span>' in _github_card(html)
    assert "3 open pull requests" in _github_card(html) and "issues mirrored" not in _github_card(html)


def test_integrations_page_linear_empty_teams_and_error(jinja_env):
    linear = {**LINEAR, "teams": [], "last_sync_at": None, "last_error": "ValueError: Linear rejected the key"}
    html = jinja_env.get_template("platform/integrations.html").render(**_integrations_ctx(linear=linear, issues=0))
    card = _linear_card(html)
    assert '<div class="ss-meta">every team the key sees</div>' in card
    assert '<span class="chip">OPT</span>' not in card
    assert '<div class="ss-meta">0 issues mirrored · polled every 10 min · last poll never</div>' in card
    assert "ValueError: Linear rejected the key" in card
    box = card.split("ValueError")[0].rsplit("<div", 1)[1]
    assert "status-err" in box
    assert "Sync now" in card and _confirm(html, "/api/m/dev/integrations/linear/delete")
    form = _linear_form(html)
    assert 'placeholder="OPT, ENG (empty = every team the key sees)" value="">' in form and ">Update</button>" in form


def _issue(id="is1", **meta):
    base_meta = {"kind": "issue", "identifier": "OPT-42", "team": "OPT", "linear_id": "uuid-42", "state": "In Progress",
                 "state_type": "started", "assignee": "Dana", "priority": 2, "linear_updated_at": "2026-10-31T11:00:00Z"}
    base_meta.update(meta)
    return _item(id=id, title="OPT-42: Ship the Linear card", status="review", attention="", latest_run=None,
                 source="linear", meta=base_meta, external_url="https://linear.app/synapspaces/issue/OPT-42")


def _product_item_ctx(item, **over):
    ctx = dict(module="product", mod=_mod(label="Product"), request=_Req(f"/m/product/items/{item['id']}"))
    ctx.update(over)
    return _item_ctx(item=item, **ctx)


def _issue_card(html):
    """The Linear issue card, first on the left, up to the edit form that follows it."""
    return html.split('<div class="ss-body-strong">Linear issue</div>')[1].split('<div class="ss-body-strong">Edit</div>')[0]


def test_item_page_linear_issue_card(jinja_env):
    tpl = jinja_env.get_template("platform/item.html")
    html = tpl.render(**_product_item_ctx(_issue(), is_issue=True))
    header = html.split("</h1>")[1].split("md:grid-cols")[0]
    assert '<span class="chip">issue</span>' in header
    assert '<span class="chip">pr</span>' not in header and '<span class="chip">repo</span>' not in header
    card = _issue_card(html)
    assert ">Issue<" in card and ">OPT-42</span>" in card
    assert ">Team<" in card and ">OPT</span>" in card
    assert ">Assignee<" in card and ">Dana</span>" in card
    assert '<span class="chip chip-warn">In Progress</span>' in card
    assert '<span class="ss-meta">priority 2</span>' in card
    assert ('<a href="https://linear.app/synapspaces/issue/OPT-42" target="_blank" rel="noopener" '
            'class="ml-auto btn btn-secondary btn-sm">Open in Linear</a>') in card
    assert "status-err" not in card and "Linear refused" not in html
    # first on the left; the item stays editable: the edit form and the Status card are there, no synced note
    assert html.index(">Linear issue</div>") < html.index("/items/is1/edit")
    assert ">Status<" in html and "Synced from" not in html and ">Body</div>" not in html
    assert ">Pull request</div>" not in html and ">Repository</div>" not in html
    # never offers to create what already is an issue
    assert LINEAR_CARD_HEADING not in html and "Create in Linear" not in html
    assert "window.confirm" not in html and "hx-confirm" not in html
    # completed and canceled read chip-ok; another type is plain; no assignee, team, priority or url
    done = _issue("is2", state="Done", state_type="completed", assignee="", team="", priority=0)
    del done["external_url"]
    html = tpl.render(**_product_item_ctx(done, is_issue=True))
    card = _issue_card(html)
    assert '<span class="chip chip-ok">Done</span>' in card
    assert ">Assignee<" not in card and ">Team<" not in card and "priority" not in card and "Open in Linear" not in html
    html = tpl.render(**_product_item_ctx(_issue("is3", state="Canceled", state_type="canceled"), is_issue=True))
    assert '<span class="chip chip-ok">Canceled</span>' in _issue_card(html)
    html = tpl.render(**_product_item_ctx(_issue("is4", state="Backlog", state_type="backlog"), is_issue=True))
    assert '<span class="chip ">Backlog</span>' in _issue_card(html)
    # a refused change shows in a status-err box inside the card
    html = tpl.render(**_product_item_ctx(_issue("is5", linear_error="Linear: state not found"), is_issue=True))
    card = _issue_card(html)
    assert "Linear refused the last change: Linear: state not found" in card
    box = card.split("Linear refused")[0].rsplit("<div", 1)[1]
    assert "status-err" in box
    # without the flag an ordinary item has no issue card or chip
    html = tpl.render(**_item_ctx())
    assert ">Linear issue</div>" not in html and '<span class="chip">issue</span>' not in html


def _create_card(html):
    return _right_column(html).split(LINEAR_CARD_HEADING)[1].split('<div class="ss-meta">Agents</div>')[0]


def test_item_page_create_in_linear_with_a_select(jinja_env):
    html = jinja_env.get_template("platform/item.html").render(**_item_ctx(linear_teams=["OPT", "ENG"]))
    right = _right_column(html)
    assert right.count(LINEAR_CARD_HEADING) == 1
    card = _create_card(html)
    assert 'method="post"' in card.split(f'action="{CREATE_URL}"')[0].rsplit("<form", 1)[1]
    form = card.split(f'action="{CREATE_URL}"')[1].split("</form>")[0]
    select = form.split('<select name="team" class="select select-sm"')[1].split("</select>")[0]
    assert '<option value="OPT">OPT</option>' in select and '<option value="ENG">ENG</option>' in select
    assert select.index(">OPT<") < select.index(">ENG<") and select.count("<option") == 2
    assert '<input name="team"' not in form
    assert '<button type="submit" class="btn btn-secondary btn-sm">Create in Linear</button>' in form
    assert "Makes a Linear issue from this item; it then mirrors both ways." in card
    assert "hx-post" not in card and "window.confirm" not in html and "hx-confirm" not in html
    # in the right column between Status and Agents, after the Work card when there is one
    assert right.index(">Status<") < right.index(LINEAR_CARD_HEADING) < right.index(">Agents<")
    html = jinja_env.get_template("platform/item.html").render(**_item_ctx(linear_teams=["OPT"], work_repos=WORK_REPOS, work=None))
    right = _right_column(html)
    assert right.index(">Status<") < right.index(WORK_HEADING) < right.index(LINEAR_CARD_HEADING) < right.index(">Agents<")
    # the left column is unchanged
    assert "/items/it1/edit" in html and 'id="platform-runs"' in html and ">Linear issue</div>" not in html


def test_item_page_create_in_linear_with_a_text_input(jinja_env):
    html = jinja_env.get_template("platform/item.html").render(**_item_ctx(linear_teams=[]))
    card = _create_card(html)
    form = card.split(f'action="{CREATE_URL}"')[1].split("</form>")[0]
    assert '<input name="team" class="input input-sm" placeholder="Team key, like OPT" autocomplete="off" required>' in form
    assert "<select" not in form and "<option" not in form
    assert '<button type="submit" class="btn btn-secondary btn-sm">Create in Linear</button>' in form
    assert "Makes a Linear issue from this item; it then mirrors both ways." in card


def test_item_page_create_in_linear_absent_for_issues_read_only_and_without_linear(jinja_env):
    tpl = jinja_env.get_template("platform/item.html")
    for ctx in (_item_ctx(), _item_ctx(linear_teams=None),
                _product_item_ctx(_issue(), is_issue=True, linear_teams=["OPT"]),
                _item_ctx(item=_item(source="repo"), read_only=True, linear_teams=["OPT"]),
                _dev_item_ctx(_pr(7), linear_teams=["OPT"])):
        html = tpl.render(**ctx)
        assert LINEAR_CARD_HEADING not in html and "Create in Linear" not in html and '/linear"' not in html
        assert ">Agents<" in html


def test_module_page_issue_chip(jinja_env):
    items = [_issue(), _issue("is2", state="", assignee=""), _item(id="it2"), _pr(7)]
    html = jinja_env.get_template("platform/module.html").render(
        **_module_ctx("product", mod=_mod(label="Product"), items=items))
    row = html.split('href="/m/product/items/is1"')[1].split("</a>")[0]
    assert '<span class="chip">issue</span>' in row
    assert '<span class="ss-meta">In Progress</span>' in row and '<span class="ss-meta">Dana</span>' in row
    assert row.index(">issue<") < row.index(">In Progress<") < row.index(">Dana<")
    assert '<span class="chip">pr</span>' not in row and "checks" not in row and " by " not in row
    bare = html.split('href="/m/product/items/is2"')[1].split("</a>")[0]
    assert '<span class="chip">issue</span>' in bare
    assert '<span class="ss-meta">In Progress</span>' not in bare and '<span class="ss-meta">Dana</span>' not in bare
    plain = html.split('href="/m/product/items/it2"')[1].split("</a>")[0]
    assert '<span class="chip">issue</span>' not in plain
    pr = html.split('href="/m/product/items/pr7"')[1].split("</a>")[0]
    assert '<span class="chip">pr</span>' in pr and '<span class="chip">issue</span>' not in pr


# ---- base nav -------------------------------------------------------------------------------------------

def test_nav_renders_without_modules_nav(jinja_env):
    """`modules_nav` is a backend Jinja global; every page must still render when it is undefined."""
    html = jinja_env.get_template("projects.html").render(projects=[], fmt=str, request=_Req("/projects"), is_owner=True)
    assert 'href="/approvals"' in html and 'href="/brief"' in html and "/m/" not in html


def test_base_styles_the_rendered_markdown(jinja_env):
    """The .md rules live in base.html's style block, so every page that prints body_html gets them."""
    html = jinja_env.get_template("platform/item.html").render(**_item_ctx(body_html="<p>x</p>"))
    style = html.split("<style>")[-1].split("</style>")[0]  # a comment names the tag before the real one
    assert ".md {" in style and ".md h2 {" in style and ".md p {" in style and ".md a:hover {" in style
    assert ".md code {" in style and ".md blockquote {" in style and ".md hr {" in style
    pre = style.split(".md pre {")[1].split("}")[0]
    assert "white-space: pre-wrap" in pre and "var(--surface-field)" in pre
    table = style.split(".md table {")[1].split("}")[0]
    assert "overflow-x: auto" in table and "display: block" in table
    assert "max-width: 100%" in style.split(".md img {")[1].split("}")[0]


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
