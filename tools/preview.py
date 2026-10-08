"""Preview the editor's pages with sample data, without the backend, database or GPU.

The real pages are rendered by synaps-optic-backend with live data. This script renders the main
templates (projects, editor, recast, references, take, invites, sign-in) with a small sample context,
rewrites the app links so you can click between the pages, and stops HTMX requests (there is no
server to answer them). Use it to work on the look of the templates.

    python tools/preview.py --serve            # writes ./preview and serves http://127.0.0.1:8765
    python tools/preview.py --out dist/preview # only write the files
"""
from __future__ import annotations

import argparse
import functools
import http.server
import json
import shutil
import socketserver
import sys
from pathlib import Path
from types import SimpleNamespace

from jinja2 import ChainableUndefined, Environment, FileSystemLoader, select_autoescape

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # run from a plain checkout too
from optic_frontend import STATIC_DIR, TEMPLATES_DIR  # noqa: E402


class SampleUndefined(ChainableUndefined):
    """A value the sample context does not provide renders empty and counts as 0 in arithmetic,
    so a page renders even when a template reads a field the sample data leaves out."""

    def __round__(self, *a): return 0
    def __float__(self): return 0.0
    def __int__(self): return 0
    def __add__(self, o): return o
    __radd__ = __add__
    def __sub__(self, o): return -o if o else 0
    def __rsub__(self, o): return o
    def __mul__(self, o): return 0
    __rmul__ = __mul__
    def __truediv__(self, o): return 0
    def __rtruediv__(self, o): return 0
    def __lt__(self, o): return True
    def __gt__(self, o): return False
    def __le__(self, o): return True
    def __ge__(self, o): return False


def _request(path: str):
    """The slice of Starlette's Request the templates read."""
    return SimpleNamespace(url=SimpleNamespace(path=path), headers={})


def _fmt(_ts) -> str:
    return "Oct 8, 2026 · 01:30"


def _fmt_dur(_s) -> str:
    return "00:04.0"


PROJECT = {"id": "p1", "name": "Launch teaser", "width": 1080, "height": 1920, "fps": 30, "updated_at": "x",
           "overlay_path": None, "background_music_key": None, "duration": 12.0}
CLIPS = [
    {"id": "c1", "name": "Scene 1", "opacity": 1.0, "asset": {"filename": "Scene 1.mp4"}, "effects": [],
     "source_start": 0.0, "source_end": 4.0, "timeline_start": 0.0, "track_index": 0, "asset_id": "a1"},
    {"id": "c2", "name": "Scene 2", "opacity": 1.0, "asset": {"filename": "Scene 2.mp4"}, "effects": [],
     "source_start": 0.0, "source_end": 4.0, "timeline_start": 4.0, "track_index": 0, "asset_id": "a2"},
    {"id": "c3", "name": "Voiceover", "opacity": 0, "asset": {"filename": "voiceover.mp3"}, "effects": [],
     "source_start": 0.0, "source_end": 8.0, "timeline_start": 0.0, "track_index": 1, "asset_id": "a3"},
]
ASSETS = [{"id": "a1", "filename": "Scene 1.mp4", "width": 1080, "height": 1920, "duration": 4.0},
          {"id": "a2", "filename": "Scene 2.mp4", "width": 1080, "height": 1920, "duration": 4.0},
          {"id": "a3", "filename": "voiceover.mp3", "width": 0, "height": 0, "duration": 8.0}]
TAKES = [
    {"id": "t1", "name": "take_ab12cd34_cat", "side": "cat", "mode": "full", "status": "done", "progress": 100,
     "frames": 181, "error": None, "finished_at": "x", "created_at": "x"},
    {"id": "t2", "name": "take_ef56ab78_cat_probe", "side": "cat", "mode": "probe", "status": "running",
     "progress": 40, "frames": 12, "error": None, "finished_at": None, "created_at": "x"},
    {"id": "t3", "name": "take_0011aabb_user", "side": "user", "mode": "full", "status": "failed", "progress": 10,
     "frames": 0, "error": "Out of GPU memory in window 3.", "finished_at": "x", "created_at": "x"},
]
# a finished full take with two compare lanes and five camera shots (the take page's compare view)
SHOT_TABLE = [{"start": 0, "end": 52}, {"start": 52, "end": 92}, {"start": 92, "end": 138}, {"start": 138, "end": 173},
              {"start": 173, "end": 181}]
FULL_TAKE = dict(TAKES[0], frames_total=181, frames_done=181, spf=17.4, lanes=2, preview_key="k", final_key="k",
                 log_tail=["[01:02] window 5: 33 frames in 571 s = 17.3 s/frame", "[01:12] total 181 frames in 54.6 min"])
LANES = [{"key": "source", "take": "t1", "label": "Source clip"}, {"key": "final", "take": "t1", "label": "Cat take"}]
SHOTS = [{"id": f"s{i}", "shot_index": i, "start_frame": r["start"], "end_frame": r["end"], "note": "",
          "status": "done", "decision": ("approve" if i < 3 else ("reroll" if i == 3 else None)), "fix_count": int(i == 2)}
         for i, r in enumerate(SHOT_TABLE, start=1)]
COMMON = {"is_owner": True, "fmt": _fmt, "fmt_dur": _fmt_dur, "gpu_online": True}

# (output file, template, request path, context)
PAGES = [
    ("projects.html", "projects.html", "/projects",
     {"projects": [PROJECT, dict(PROJECT, id="p2", name="Product walkthrough", width=1920, height=1080)]}),
    ("editor.html", "editor.html", "/projects/p1",
     {"project": PROJECT, "clips": CLIPS, "selected_clip": CLIPS[0], "tracks": [0, 1], "jobs": [],
      "assets": ASSETS, "renders": [], "ai_generation": None, "scenes": [], "queue_position": None, "oob_timeline": False,
      "music_tracks": ["calm.mp3"], "project_id": "p1"}),
    ("recast.html", "recast/index.html", "/recast",
     {"takes": TAKES, "cat_takes": TAKES[:1], "active": False, "gpu": {"online": True, "busy": False},
      "reference": {"id": "r1", "name": "Close-up set", "ref_key": None, "ranking": [{"face_h": 212, "score": 0.91}]},
      "phase_labels": {"render": "Rendering", "setup": "Setting up"}}),
    ("take.html", "recast/take.html", "/recast/takes/t1",
     {"take": FULL_TAKE, "lanes": LANES, "shots": SHOTS, "shot_table": SHOT_TABLE, "fps": 24, "stride": 2}),
    ("references.html", "recast/references.html", "/recast/references", {"references": [], "candidates": []}),
    ("invites.html", "admin/invites.html", "/admin/invites",
     {"invites": [{"code": "STUDIO-ALPHA-01", "email": "a@example.com", "redeemed_by": None, "revoked": False,
                   "expires_at": "x", "created_at": "x"}]}),
    ("login.html", "auth/login.html", "/auth/login", {"is_owner": False}),
]

# app routes -> preview files, so the nav and cards link between the rendered pages
LINKS = {'href="/projects/p1"': 'href="editor.html"', 'href="/projects/p2"': 'href="editor.html"', 'href="/projects"': 'href="projects.html"',
         'href="/recast/references"': 'href="references.html"', 'href="/recast/takes/t1"': 'href="take.html"',
         'href="/recast"': 'href="recast.html"', 'href="/admin/invites"': 'href="invites.html"',
         'href="/auth/login"': 'href="login.html"', 'href="/static/': 'href="static/', 'src="/static/': 'src="static/'}
# no server answers HTMX here: cancel every request instead of filling the console with 404s
NO_HTMX = '<script>document.addEventListener("htmx:beforeRequest", function (e) { e.preventDefault(); });</script>'


def _env() -> Environment:
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=select_autoescape(["html"]),
                      undefined=SampleUndefined)
    env.filters["fromjson"] = json.loads
    return env


def render_all(out: Path) -> list[str]:
    """Write every preview page plus the static assets into `out`; return the page file names."""
    env = _env()
    (out / "static").mkdir(parents=True, exist_ok=True)
    shutil.copy2(STATIC_DIR / "htmx.min.js", out / "static" / "htmx.min.js")
    shutil.copytree(STATIC_DIR / "ds", out / "static" / "ds", dirs_exist_ok=True)
    written = []
    for name, template, path, ctx in PAGES:
        html = env.get_template(template).render(request=_request(path), **{**COMMON, **ctx})
        for old, new in LINKS.items():
            html = html.replace(old, new)
        html = html.replace("</head>", NO_HTMX + "\n</head>", 1)
        (out / name).write_text(html, encoding="utf-8")
        written.append(name)
    return written


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="preview", help="output folder (default ./preview)")
    ap.add_argument("--serve", action="store_true", help="serve the folder after writing it")
    ap.add_argument("--port", type=int, default=8765)
    a = ap.parse_args()
    out = Path(a.out)
    pages = render_all(out)
    print(f"wrote {len(pages)} pages to {out}: {', '.join(pages)}")
    if a.serve:
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(out))
        with socketserver.TCPServer(("127.0.0.1", a.port), handler) as httpd:
            print(f"open http://127.0.0.1:{a.port}/projects.html  (Ctrl+C to stop)")
            httpd.serve_forever()


if __name__ == "__main__":
    main()
