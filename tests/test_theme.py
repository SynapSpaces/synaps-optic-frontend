"""Dark mode: the theme script runs before the stylesheets, the dark tokens exist, every page that
draws a top bar carries the toggle, and media wells keep the light tokens so footage stays on black."""
from optic_frontend import TEMPLATES_DIR

BASE = (TEMPLATES_DIR / "base.html").read_text(encoding="utf-8")


def test_theme_is_chosen_before_the_stylesheets_load():
    assert BASE.index("opticTheme") < BASE.index("/static/ds/synapspaces.css")
    assert 'localStorage.getItem(KEY)' in BASE and "prefers-color-scheme: dark" in BASE


def test_dark_tokens_reverse_the_neutral_scale():
    dark = BASE[BASE.index(':root[data-theme="dark"] {'):]
    dark = dark[:dark.index("}")]
    for token in ("--white:", "--ink:", "--gray-50:", "--gray-600:", "--tint-sage:", "--status-err:"):
        assert token in dark, token
    assert "color-scheme: dark" in dark


def test_tailwind_colours_follow_the_tokens():
    assert "ink: v('--ink')" in BASE and "page: v('--surface-page')" in BASE
    assert "'#0d0d0d'" not in BASE[BASE.index("tailwind.config"):BASE.index("</script>", BASE.index("tailwind.config"))]


def test_toggle_in_both_top_bars():
    assert "brand.theme_toggle()" in BASE
    assert "brand.theme_toggle()" in (TEMPLATES_DIR / "editor.html").read_text(encoding="utf-8")


def test_media_wells_stay_dark():
    editor = (TEMPLATES_DIR / "editor.html").read_text(encoding="utf-8")
    take = (TEMPLATES_DIR / "recast" / "take.html").read_text(encoding="utf-8")
    assert "tone-light flex-1 min-h-0 flex flex-col bg-ink" in editor  # the preview stage
    assert take.count("tone-light") >= 5  # compare images, wipe, loading veil, video
