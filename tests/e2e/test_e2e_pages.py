"""Every page loads with the design system applied, links to the others, and fits the viewport."""
import pytest

PAGES = ["projects.html", "editor.html", "recast.html", "take.html", "references.html", "invites.html", "login.html"]


@pytest.mark.parametrize("name", PAGES)
def test_page_loads_with_the_design_system(session, name):
    page = session.open(name)
    assert page.title().startswith("Synaps Optic")
    assert "Geist" in session.css("body", "font-family")
    assert page.evaluate("document.fonts.check('16px Geist')"), "Geist did not load"
    assert session.css("body", "background-color") == "rgb(255, 255, 255)"
    # no horizontal scrolling at a laptop width
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), "page overflows sideways"


@pytest.mark.parametrize("name", [p for p in PAGES if p != "editor.html"])
def test_top_bar_has_the_logo_and_the_theme_toggle(session, name):
    page = session.open(name)
    logo = page.locator("header .wordmark")
    assert logo.is_visible() and "synapspaces" in logo.inner_text() and "Optic" in logo.inner_text()
    assert page.locator("header .theme-toggle").is_visible()


def test_nav_moves_between_sections(session):
    page = session.open("projects.html")
    assert page.locator("header .nav-link.active").inner_text() == "Projects"
    page.click("header >> text=Recast")
    session.ready()
    assert page.url.endswith("/recast.html")
    assert page.locator("header .nav-link.active").inner_text() == "Recast"
    page.click("header .wordmark")
    session.ready()
    assert page.url.endswith("/projects.html")


def test_project_card_opens_the_editor(session):
    page = session.open("projects.html")
    page.click("text=Launch teaser")
    session.ready()
    assert page.url.endswith("/editor.html")
    assert page.locator("header >> text=Launch teaser").is_visible()


def test_buttons_and_inputs_follow_the_system(session):
    page = session.open("login.html")
    btn = page.locator("button[type=submit]")
    assert btn.evaluate("el => getComputedStyle(el).borderRadius") == "999px"   # pills for actions
    assert btn.evaluate("el => getComputedStyle(el).backgroundColor") == "rgb(13, 13, 13)"
    field = page.locator("input[type=email]")
    assert field.evaluate("el => getComputedStyle(el).height") == "44px"
    # the placeholder is the design system's grey, not Tailwind's blue-grey
    assert field.evaluate("el => getComputedStyle(el, '::placeholder').color") in ("rgb(138, 138, 138)",)


def test_ai_prompt_accepts_text(session):
    page = session.open("projects.html")
    box = page.locator("textarea[name=prompt]")
    box.fill("A 20-second launch teaser for a coffee brand")
    assert box.input_value().startswith("A 20-second")
    page.select_option("select[name=aspect]", "16:9")
    assert page.locator("select[name=aspect]").input_value() == "16:9"
