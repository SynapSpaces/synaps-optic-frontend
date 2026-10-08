"""Dark mode: follows the system, the toggle switches and remembers, and media stays dark."""
import pytest

LIGHT_BG, DARK_BG = "rgb(255, 255, 255)", "rgb(14, 14, 14)"


def test_follows_a_light_system(session):
    session.open("projects.html")
    assert session.theme() == "light" and session.css("body", "background-color") == LIGHT_BG


def test_follows_a_dark_system(dark_session):
    s = dark_session
    s.open("projects.html")
    assert s.theme() == "dark" and s.css("body", "background-color") == DARK_BG
    assert s.page.locator("meta[name=theme-color]").get_attribute("content") == "#0e0e0e"
    # primary buttons invert: light pill, dark label
    assert s.css(".btn-primary", "background-color") == "rgb(242, 242, 242)"


def test_toggle_switches_and_is_remembered(dark_session):
    s = dark_session
    page = s.open("projects.html")
    assert page.locator("header .theme-sun").is_visible() and not page.locator("header .theme-moon").is_visible()
    page.click("header .theme-toggle")
    assert s.theme() == "light" and s.css("body", "background-color") == LIGHT_BG
    assert page.locator("header .theme-moon").is_visible()
    page.reload()
    s.ready()
    assert s.theme() == "light", "a saved choice must beat the dark system setting"
    s.open("editor.html")
    assert s.theme() == "light", "the choice carries to the editor"


def test_choice_survives_without_a_flash(dark_session):
    """The theme attribute is set by the inline script in <head>, before first paint."""
    s = dark_session
    page = s.open("projects.html")
    page.click("header .theme-toggle")          # stores "light"
    page.goto(f"{s.site}/recast.html", wait_until="commit")
    page.wait_for_selector("html[data-theme]", state="attached")
    assert s.theme() == "light"


@pytest.mark.parametrize("name,selector", [
    ("editor.html", ".tone-light.bg-ink"),                 # the preview stage
    ("take.html", "#rc-img-a"),                            # the compare images
    ("take.html", "#rc-video"),                            # the take preview
])
def test_media_stays_dark_in_dark_mode(dark_session, name, selector):
    dark_session.open(name)
    bg = dark_session.css(selector, "background-color")
    assert bg in ("rgb(13, 13, 13)", "color(srgb 0.0509804 0.0509804 0.0509804)"), bg


def test_editor_toggle_works_too(session):
    page = session.open("editor.html")
    page.click(".theme-toggle")
    assert session.theme() == "dark"
    assert session.css("body", "background-color") == DARK_BG
