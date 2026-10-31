"""The package must ship every template and static asset the backend serves,
and every template must at least compile under the backend's Jinja2 setup."""
from optic_frontend import MUSIC_DIR, STATIC_DIR, TEMPLATES_DIR

EXPECTED_TEMPLATE_COUNT = 41  # +partials/brand.html (logo), +gen/plan.html and partials/gen_plan.html (generated-video plan review),
                              # +platform/module.html, platform/item.html, platform/approvals.html and partials/platform_runs.html (platform modules),
                              # +platform/ask.html and partials/platform_ask_runs.html (ask the wiki),
                              # +platform/brief.html (the daily owner brief),
                              # +platform/board.html, platform/people.html and platform/ledger.html (board view, people directory, ledger),
                              # +platform/integrations.html (the GitHub integration of the dev module)


def test_core_files_present():
    assert (TEMPLATES_DIR / "base.html").is_file()
    assert (STATIC_DIR / "htmx.min.js").is_file()
    assert MUSIC_DIR.is_dir()


def test_every_template_compiles(jinja_env):
    names = sorted(p.relative_to(TEMPLATES_DIR).as_posix() for p in TEMPLATES_DIR.rglob("*.html"))
    assert len(names) == EXPECTED_TEMPLATE_COUNT, names
    for name in names:
        jinja_env.get_template(name)  # raises TemplateSyntaxError on a broken template
