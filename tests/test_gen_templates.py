"""partials/gen_plan.html renders one view per pipeline stage. These tests pin the per-stage contract the
backend relies on (polling attribute, action forms, banners) with minimal fake contexts, rendered through
the same Jinja2 setup the backend uses (tests/conftest.py).

Context variables the partial reads (the backend's _plan_ctx must supply every one):
    request, plan, doc, shots, children, request_params, feedback, planned_s, plan_json_text,
    can_review, polling, fmt, is_owner, can_pick, can_render, can_reroll, can_final,
    blocking, failed_shots, stage_counts, render
"""
import pytest

SHOT_SPECS = [
    {"id": "s01", "kind": "ai_video", "duration_s": 4, "narration": "The sky scatters blue light.",
     "caption": None, "ai_video": {"prompt": "a blue sky over a field", "camera": "slow pan", "motion": "low", "negative": ""}},
    {"id": "s02", "kind": "still", "duration_s": 3, "narration": None, "caption": "Rayleigh scattering",
     "still": {"prompt": "a prism splitting light", "move": "zoom", "negative": ""}},
    {"id": "s03", "kind": "animation", "duration_s": 5, "narration": "Shorter wavelengths scatter more.",
     "caption": None, "animation": {"template": "title_card", "params": {"text": "Why the sky is blue"}}},
]

DOC = {
    "title": "Why the sky is blue", "aspect": "16:9", "target_duration_s": 12, "shots": SHOT_SPECS,
    "look_bible": {"style": "clean explainer", "character": None, "lighting": "soft daylight", "lens": None,
                   "palette": ["#d8e3f1", "#0d0d0d"], "negative": "text, logos"},
}


def _plan(stage, **over):
    base = {"id": "plan1", "project_id": "proj1", "stage": stage, "status": "approved", "quality": "draft",
            "version": 1, "model": "gemma@GPU", "prompt": "why is the sky blue", "error": None, "progress": 0,
            "parent_plan_id": None, "approved_at": "2026-10-13T00:00:00Z"}
    base.update(over)
    return base


def _row(shot_id, status, **over):
    base = {"id": f"row-{shot_id}", "shot_id": shot_id, "status": status, "decision": None, "note": None,
            "error": None, "reroll_count": 0, "timed_duration_s": None, "progress": 0}
    base.update(over)
    return base


def _keyframes(shot_id, selected_index=None, thumbs=True):
    return [
        {"id": f"kf-{shot_id}-{i}", "candidate_index": i, "url": f"/kf/{shot_id}/{i}.png",
         "thumb_url": f"/kf/{shot_id}/{i}.thumb.jpg" if thumbs else None,
         "score": [0.42, 0.91, None][i], "chosen": i == 1, "selected": i == selected_index}
        for i in range(3)
    ]


def _confirm(html, url):
    """The inline confirm block posting to `url` (its question and buttons), or None."""
    for block in html.split('<details class="confirm">')[1:]:
        block = block.split("</details>")[0]
        if f'hx-post="{url}"' in block:
            return block
    return None


def _clip(shot_id, version=1):
    return {"url": f"/clips/{shot_id}/v{version}.mp4", "thumb_url": f"/clips/{shot_id}/v{version}.jpg",
            "version": version, "engine": "ltx", "duration_s": 4.0}


def _ctx(stage, shots, plan=None, **over):
    ctx = dict(
        request=None, plan=plan or _plan(stage), doc=DOC, shots=shots, children=[],
        request_params={"mode": "mixed", "aspect": "16:9", "target_duration_s": 12}, feedback=[],
        planned_s=12.0, plan_json_text="{}", can_review=False, polling=False, fmt=lambda x: str(x),
        is_owner=True, can_pick=False, can_render=False, can_reroll=False, can_final=False,
        blocking=[], failed_shots=[], stage_counts=None, render=None,
    )
    ctx.update(over)
    return ctx


@pytest.fixture
def render(jinja_env):
    tpl = jinja_env.get_template("partials/gen_plan.html")
    return lambda ctx: tpl.render(**ctx)


def test_planning_polls_without_shots(render):
    html = render(_ctx("planning", [], plan=_plan("planning", status="draft"), doc=None, planned_s=None, polling=True))
    assert 'hx-trigger="every 3s"' in html and 'hx-get="/partials/gen/plans/plan1"' in html
    assert "Writing the shot list" in html
    assert "Render shots" not in html and "/pick" not in html


def test_plan_review_keeps_decisions_edit_and_approve(render):
    shots = [{"spec": s, "row": _row(s["id"], "pending", decision="approve" if s["id"] == "s01" else None),
              "keyframes": [], "clip": None, "clip_versions": []} for s in SHOT_SPECS]
    html = render(_ctx("plan_review", shots, plan=_plan("plan_review", status="draft"), can_review=True))
    assert 'hx-trigger="every 3s"' not in html
    assert "Approve plan" in html and "/api/gen/plans/plan1/edit" in html
    appr = _confirm(html, "/api/gen/plans/plan1/approve")
    assert appr and "Approve this shot list?" in appr and ">Approve</button>" in appr and "hx-confirm" not in html
    assert html.count("/api/gen/shots/row-s01/decision") == 2 and "approved" in html
    assert 'id="note-row-s02"' in html
    assert "Render shots" not in html and "/pick" not in html and "/reroll" not in html


def test_failed_plan_shows_error_and_stops_polling(render):
    html = render(_ctx("failed", [], plan=_plan("failed", status="draft", error="planner timed out"), doc=None, planned_s=None))
    assert "Planning failed: planner timed out" in html and 'hx-trigger="every 3s"' not in html


@pytest.mark.parametrize("stage, text", [
    ("voicing", "Voicing the narration… 40%"),
    ("keyframing", "Painting keyframes"),
    ("rendering", "Rendering shots… 1 of 3 clips ready"),
    ("assembling", "Assembling the final cut…"),
])
def test_handler_stages_poll_with_banner(render, stage, text):
    shots = [{"spec": s, "row": _row(s["id"], "pending"), "keyframes": [], "clip": None, "clip_versions": []} for s in SHOT_SPECS]
    html = render(_ctx(stage, shots, plan=_plan(stage, progress=40), polling=True, stage_counts={"ready": 1, "total": 3}))
    assert 'hx-trigger="every 3s"' in html and text in html
    if stage == "keyframing":
        assert "1 of 3 shots ready" in html
    assert "Render shots" not in html and "Render final quality" not in html


def test_keyframe_review_candidate_grid_pick_reroll_and_render(render):
    shots = [
        {"spec": SHOT_SPECS[0], "row": _row("s01", "needs_review"), "keyframes": _keyframes("s01", selected_index=1),
         "clip": None, "clip_versions": []},
        {"spec": SHOT_SPECS[1], "row": _row("s02", "needs_review"), "keyframes": _keyframes("s02"),
         "clip": None, "clip_versions": []},
        {"spec": SHOT_SPECS[2], "row": _row("s03", "pending"), "keyframes": [], "clip": None, "clip_versions": []},
    ]
    html = render(_ctx("keyframe_review", shots, can_pick=True, can_render=False, blocking=["s02"]))
    assert 'hx-trigger="every 3s"' not in html
    # six candidates, one pick form each
    assert html.count("/api/gen/shots/row-s01/pick") == 3 and html.count("/api/gen/shots/row-s02/pick") == 3
    assert 'name="keyframe_id" value="kf-s01-1"' in html
    # the grid loads the 240 px thumbs; the full still only goes to the lightbox trigger
    assert html.count('loading="lazy"') == 6 and 'src="/kf/s02/2.thumb.jpg"' in html and 'src="/kf/s02/2.png"' not in html
    assert html.count('class="lightbox-open') == 6 and 'data-full="/kf/s02/2.png"' in html
    assert "judge's pick" in html and "0.91" in html and "0.42" in html
    assert "ring-2 ring-ink" in html and "Picked" in html and "pick a keyframe" in html
    # re-roll on the two keyframe shots only; the animation shot waits
    assert html.count("/api/gen/shots/row-s01/reroll") == 1 and html.count("/api/gen/shots/row-s02/reroll") == 1
    assert "/api/gen/shots/row-s03/reroll" not in html and "renders after review" in html.lower()
    reroll = _confirm(html, "/api/gen/shots/row-s01/reroll")
    assert reroll and "Re-roll this shot?" in reroll and ">Yes, re-roll</button>" in reroll and ">Cancel</button>" in reroll
    assert "hx-confirm" not in html and "confirm(" not in html   # nothing modal: automation and the owner both get an inline step
    # render button present but blocked, and a blocked render has no confirm step to open
    assert "/api/gen/plans/plan1/render" in html and "Render shots" in html
    assert "disabled" in html.split("Render shots")[0].rsplit("<button", 1)[1]
    assert _confirm(html, "/api/gen/plans/plan1/render") is None
    assert "Waiting on s02" in html
    assert "Approve plan" not in html and "Render final quality" not in html


def test_keyframe_grid_without_thumbs_falls_back_to_the_full_still(render):
    """Plans published before the thumbs existed carry thumb_url=None: the grid shows the full still."""
    shots = [{"spec": SHOT_SPECS[0], "row": _row("s01", "needs_review"), "keyframes": _keyframes("s01", thumbs=False),
              "clip": None, "clip_versions": []}]
    html = render(_ctx("keyframe_review", shots, can_pick=True))
    assert 'src="/kf/s01/0.png"' in html and 'data-full="/kf/s01/0.png"' in html and ".thumb.jpg" not in html


def test_keyframe_review_failed_shot_and_ready_render(render):
    shots = [
        {"spec": SHOT_SPECS[0], "row": _row("s01", "needs_review"), "keyframes": _keyframes("s01", selected_index=0),
         "clip": None, "clip_versions": []},
        {"spec": SHOT_SPECS[1], "row": _row("s02", "failed", error="judge crashed"), "keyframes": [],
         "clip": None, "clip_versions": []},
    ]
    plan = _plan("keyframe_review", error="1 keyframe shot(s) failed: s02")
    html = render(_ctx("keyframe_review", shots, plan=plan, can_pick=True, can_render=True))
    assert "judge crashed" in html and "1 keyframe shot(s) failed: s02" in html and "status-err" in html
    assert "/api/gen/shots/row-s02/reroll" in html
    # a ready render is the two-step button: no disabled button, the question and a confirm
    assert "<button" not in html.split("Render shots")[0].rsplit("<summary", 1)[1]
    assert '<summary class="btn btn-primary w-full" role="button">Render shots</summary>' in html
    rend = _confirm(html, "/api/gen/plans/plan1/render")
    assert rend and "Render every shot now? This starts the Kaggle run." in rend and ">Render</button>" in rend
    assert "hx-confirm" not in html


def test_rendering_shows_status_chips_clips_and_failed_reroll(render):
    shots = [
        {"spec": SHOT_SPECS[0], "row": _row("s01", "done"), "keyframes": [], "clip": _clip("s01"), "clip_versions": [_clip("s01")]},
        {"spec": SHOT_SPECS[1], "row": _row("s02", "needs_review"), "keyframes": [], "clip": None, "clip_versions": []},
        {"spec": SHOT_SPECS[2], "row": _row("s03", "failed", error="manim exited 1"), "keyframes": [], "clip": None, "clip_versions": []},
    ]
    plan = _plan("rendering", error="1 shot(s) failed: s03")
    html = render(_ctx("rendering", shots, plan=plan, polling=True, stage_counts={"ready": 1, "total": 3}, failed_shots=["s03"]))
    assert 'hx-trigger="every 3s"' in html
    assert "waiting for Kaggle" in html and "manim exited 1" in html and "1 shot(s) failed: s03" in html
    assert '<video controls preload="none" poster="/clips/s01/v1.jpg" src="/clips/s01/v1.mp4"' in html
    assert "v1 · ltx" in html
    assert html.count("/reroll") == 1 and "/api/gen/shots/row-s03/reroll" in html
    assert "Render shots" not in html and "/pick" not in html


def test_done_shows_final_video_rerolls_and_final_button(render):
    shots = [{"spec": s, "row": _row(s["id"], "done"), "keyframes": [], "clip": _clip(s["id"], 2),
              "clip_versions": [_clip(s["id"], 1), _clip(s["id"], 2)]} for s in SHOT_SPECS]
    final = {"url": "/renders/r1.mp4", "version": 3, "duration_s": 12.4, "bytes": 2_621_440}
    html = render(_ctx("done", shots, can_reroll=True, can_final=True, render=final))
    assert 'hx-trigger="every 3s"' not in html
    assert '<video controls preload="metadata" src="/renders/r1.mp4"' in html
    assert "final v3" in html and "12.4 s" in html and "2.5 MB" in html
    assert html.count("/reroll") == 3 and "v2 · ltx" in html and "2 takes" in html
    assert "/api/gen/plans/plan1/final" in html and "Render final quality" in html
    fin = _confirm(html, "/api/gen/plans/plan1/final")
    assert fin and "Re-render every shot at final size and re-assemble?" in fin and ">Render final</button>" in fin
    assert "hx-confirm" not in html
    assert "Render shots" not in html and "Approve plan" not in html


def test_plan_page_carries_the_lightbox_outside_the_polled_partial(jinja_env):
    """gen/plan.html owns the <dialog> and its script; #gen-plan is swapped every 3 s and must not contain them."""
    shots = [{"spec": SHOT_SPECS[0], "row": _row("s01", "needs_review"), "keyframes": _keyframes("s01"),
              "clip": None, "clip_versions": []}]
    ctx = _ctx("keyframe_review", shots, can_pick=True)
    ctx["request"] = _Req()
    html = jinja_env.get_template("gen/plan.html").render(**ctx)
    partial = html.split('id="gen-plan"')[1].rsplit("</section>", 1)[0]
    assert '<dialog id="gen-lightbox"' in html and "showModal()" in html
    assert "gen-lightbox" not in partial and 'data-full="/kf/s01/0.png"' in partial


def test_done_at_final_quality_offers_no_rerender(render):
    shots = [{"spec": s, "row": _row(s["id"], "done"), "keyframes": [], "clip": _clip(s["id"]), "clip_versions": []} for s in SHOT_SPECS]
    html = render(_ctx("done", shots, plan=_plan("done", quality="final"), can_reroll=True, can_final=False, render=None))
    assert "Render final quality" not in html and "Rendered at final quality" in html
    assert "<video" not in html.split('id="gen-shots"')[0]  # no final-cut card without a render


def test_rows_may_be_missing(render):
    """A spec without a row (plan edited, rows not yet created) must not blow up in any stage."""
    for stage in ("plan_review", "keyframe_review", "rendering", "done"):
        shots = [{"spec": s, "row": None, "keyframes": [], "clip": None, "clip_versions": []} for s in SHOT_SPECS]
        html = render(_ctx(stage, shots, can_pick=True, can_reroll=True))
        assert "s01" in html and "/reroll" not in html and "/pick" not in html


class _Req:
    """Enough of starlette's Request for base.html's nav highlighting."""
    class url:
        path = "/projects"
    headers: dict = {}


def test_projects_page_has_narrated_video_form(jinja_env):
    html = jinja_env.get_template("projects.html").render(projects=[], fmt=lambda x: str(x), request=_Req(), is_owner=True)
    form = html.split('action="/api/gen/plans"')[1].split("</form>")[0]
    assert "Generate a narrated video" in html and "Plan the video" in form
    for field in ('name="prompt"', 'name="aspect"', 'name="mode"', 'name="target_duration_s"', 'name="captions"', 'name="quality"'):
        assert field in form
    assert '<option value="16:9" selected>' in form and '<option value="mixed" selected>' in form
    assert 'value="on" checked' in form and 'min="5" max="180"' in form and 'value="draft"' in form
    assert "you review it before anything renders" in html
    assert 'action="/api/ai/generate"' in html  # the existing hero form stays
