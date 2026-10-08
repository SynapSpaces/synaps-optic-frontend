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
        f'<li class="ss-body"><a class="text-fg-1 underline underline-offset-2 hover:text-fg-2" href="{out}">{out}</a>'
        f' <span class="text-fg-3">&larr; {tpl}</span></li>'
        for out, tpl in rendered
    )
    listing = "\n".join(f"<li class=\"mono text-xs text-fg-2\">{t}</li>" for t in all_templates)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#ffffff"><title>Synaps Optic Frontend</title>
<link rel="stylesheet" href="static/ds/synapspaces.css">
<style>
body{{margin:0;background:var(--surface-page);color:var(--fg-1);font-family:var(--font-sans)}}
main{{max-width:var(--container);margin:0 auto;padding:64px 40px}}
section{{border-top:1px solid var(--border-subtle);padding-top:40px;margin-top:40px}}
ul{{list-style:none;margin:0;padding:0}} li{{margin:4px 0}}
.mono{{font-family:var(--font-mono)}}
.text-xs{{font-size:12px}} .text-fg-1{{color:var(--fg-1)}} .text-fg-2{{color:var(--fg-2)}} .text-fg-3{{color:var(--fg-3)}}
a{{color:var(--fg-1);text-decoration:underline;text-underline-offset:2px}} a:hover{{color:var(--fg-2)}}
.wordmark{{font:var(--type-body-strong);letter-spacing:var(--tracking-tight);color:var(--fg-1)}}
footer{{margin-top:40px;font:var(--type-caption);color:var(--fg-3)}}
</style>
</head><body><main>
<header><p class="wordmark">Synapspaces</p>
<h1 class="ss-h2" style="margin:12px 0 0">Synaps Optic Frontend</h1>
<p class="ss-body" style="margin:12px 0 0">The HTMX/Jinja2 templates of the Synaps Optic video editor, rendered here with sample data.
The editor itself runs on the backend; these pages are a visual preview only.</p></header>
<section><h2 class="ss-title" style="margin:0 0 12px">Rendered previews</h2><ul>{previews}</ul></section>
<section><h2 class="ss-title" style="margin:0 0 12px">All templates in the package ({len(all_templates)})</h2>
<ul>{listing}</ul></section>
<footer>Source: <a href="https://github.com/SynapSpaces/synaps-optic-frontend">github.com/SynapSpaces/synaps-optic-frontend</a></footer>
</main></body></html>
"""


def build(out: Path) -> list[Path]:
    env = _env()
    if out.exists():
        shutil.rmtree(out)
    (out / "static").mkdir(parents=True)
    shutil.copy2(STATIC_DIR / "htmx.min.js", out / "static" / "htmx.min.js")
    # The design system stylesheet and its Geist fonts, so the preview renders as the app does.
    shutil.copytree(STATIC_DIR / "ds", out / "static" / "ds")
    written: list[Path] = []
    rendered: list[tuple[str, str]] = []
    for name, template, ctx in PAGES:
        html = env.get_template(template).render(request=_request(), **ctx)
        # The package serves static files at the site root; Pages hosts under a
        # project path, so make the static references (script and stylesheet) relative.
        html = html.replace('src="/static/', 'src="static/').replace('href="/static/', 'href="static/')
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
