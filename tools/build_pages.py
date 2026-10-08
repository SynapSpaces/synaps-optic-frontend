"""Render a static preview of the templates for GitHub Pages.

The real templates are served by synaps-optic-backend with live data. This script
renders the pages that need no database (the sign-in flow) with sample context, plus
an index that lists every template in the package, into ``site/``. Links that only
the backend can answer are left in place; they are a style preview, not an app.

    python tools/build_pages.py            # writes ./site
    python tools/build_pages.py --out dist/pages
"""
import argparse
import json
import shutil
from pathlib import Path
from types import SimpleNamespace

from jinja2 import Environment, FileSystemLoader, select_autoescape

from optic_frontend import STATIC_DIR, TEMPLATES_DIR

# (output name, template, context) for the pages that render without the backend.
PAGES = [
    ("login.html", "auth/login.html", {}),
    ("login-expired.html", "auth/login.html", {"error": "expired"}),
    ("login-rate-limited.html", "auth/login.html", {"error": "rate_limited"}),
    ("login-invited.html", "auth/login.html", {"invite_code": "STUDIO-ALPHA-01"}),
    ("check-email.html", "auth/check_email.html", {"email": "you@example.com"}),
    ("waitlist.html", "auth/waitlist.html", {}),
    ("waitlist-saved.html", "auth/waitlist.html", {"email": "you@example.com"}),
]


def _request(path: str = "/auth/login"):
    """The slice of Starlette's Request that base.html reads (request.url.path)."""
    return SimpleNamespace(url=SimpleNamespace(path=path))


def _env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    env.filters["fromjson"] = json.loads
    return env


def _index(rendered: list[tuple[str, str]]) -> str:
    all_templates = sorted(p.relative_to(TEMPLATES_DIR).as_posix() for p in TEMPLATES_DIR.rglob("*.html"))
    previews = "\n".join(
        f'<li><a class="text-blue-400 hover:text-blue-300" href="{out}">{out}</a>'
        f' <span class="text-slate-500">&larr; {tpl}</span></li>'
        for out, tpl in rendered
    )
    listing = "\n".join(f"<li class=\"mono text-xs text-slate-400\">{t}</li>" for t in all_templates)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Synaps Optic Frontend</title>
<script src="https://cdn.tailwindcss.com"></script>
<style>body{{font-family:Inter,system-ui,sans-serif;background:#0c0c0e;color:#e2e8f0}}.mono{{font-family:ui-monospace,monospace}}</style>
</head><body class="min-h-screen"><main class="mx-auto max-w-3xl px-6 py-16 space-y-10">
<header><p class="mono text-xs uppercase tracking-[0.2em] text-slate-400">SynapSpaces</p>
<h1 class="text-2xl font-semibold text-white mt-2">Synaps Optic Frontend</h1>
<p class="text-slate-400 mt-2">The HTMX/Jinja2 templates of the Synaps Optic video editor, rendered here with sample data.
The editor itself runs on the backend; these pages are a visual preview only.</p></header>
<section><h2 class="text-lg font-medium text-white mb-3">Rendered previews</h2><ul class="space-y-1">{previews}</ul></section>
<section><h2 class="text-lg font-medium text-white mb-3">All templates in the package ({len(all_templates)})</h2>
<ul class="space-y-0.5">{listing}</ul></section>
<footer class="text-xs text-slate-500">Source: <a class="text-blue-400" href="https://github.com/SynapSpaces/synaps-optic-frontend">github.com/SynapSpaces/synaps-optic-frontend</a></footer>
</main></body></html>
"""


def build(out: Path) -> list[Path]:
    env = _env()
    if out.exists():
        shutil.rmtree(out)
    (out / "static").mkdir(parents=True)
    shutil.copy2(STATIC_DIR / "htmx.min.js", out / "static" / "htmx.min.js")
    written: list[Path] = []
    rendered: list[tuple[str, str]] = []
    for name, template, ctx in PAGES:
        html = env.get_template(template).render(request=_request(), **ctx)
        # The package serves static files at the site root; Pages hosts under a
        # project path, so make the one static reference relative.
        html = html.replace('src="/static/', 'src="static/')
        (out / name).write_text(html, encoding="utf-8")
        written.append(out / name)
        rendered.append((name, template))
    (out / "index.html").write_text(_index(rendered), encoding="utf-8")
    (out / ".nojekyll").write_text("", encoding="utf-8")
    written.append(out / "index.html")
    return written


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="site", type=Path)
    args = ap.parse_args()
    files = build(args.out)
    print(f"wrote {len(files)} pages to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
