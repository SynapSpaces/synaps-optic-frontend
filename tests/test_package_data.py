"""The package must ship every template and static asset the backend serves,
and every template must at least compile under the backend's Jinja2 setup."""
from optic_frontend import MUSIC_DIR, STATIC_DIR, TEMPLATES_DIR

EXPECTED_TEMPLATE_COUNT = 28  # +partials/brand.html (logo)


def test_core_files_present():
    assert (TEMPLATES_DIR / "base.html").is_file()
    assert (STATIC_DIR / "htmx.min.js").is_file()
    assert MUSIC_DIR.is_dir()


def test_every_template_compiles(jinja_env):
    names = sorted(p.relative_to(TEMPLATES_DIR).as_posix() for p in TEMPLATES_DIR.rglob("*.html"))
    assert len(names) == EXPECTED_TEMPLATE_COUNT, names
    for name in names:
        jinja_env.get_template(name)  # raises TemplateSyntaxError on a broken template
