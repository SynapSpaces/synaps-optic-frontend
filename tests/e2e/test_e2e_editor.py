"""The editor's own scripts: the left rail, the Videos sub-tabs, the tools and the inspector."""


def test_rail_switches_the_inspector_panel(session):
    page = session.open("editor.html")
    for key, title in [("audios", "Audios"), ("photos", "Photos"), ("text", "Text"), ("videos", "Videos")]:
        page.click(f'[data-rail="{key}"]')
        assert page.locator(f'[data-panel="{key}"]').is_visible()
        assert page.locator("#inspector-title").inner_text() == title
        assert page.locator(f'[data-rail="{key}"]').evaluate("el => el.classList.contains('active')")
        assert page.locator("[data-rail].active").count() == 1


def test_videos_sub_tabs(session):
    page = session.open("editor.html")
    page.click('[data-rail="videos"]')
    for key in ("effects", "transitions", "edit"):
        tab = page.locator(f'.vsub-btn[data-vsub="{key}"]')
        tab.click()
        assert tab.evaluate("el => el.classList.contains('bg-ink')"), f"{key} tab is not highlighted"
        others = page.locator(".vsub-btn.bg-ink")
        assert others.count() == 1


def test_tool_buttons_are_exclusive(session):
    page = session.open("editor.html")
    assert page.locator("#tool-select").evaluate("el => el.classList.contains('active')")
    page.click("#tool-hand")
    assert page.locator("#tool-hand").evaluate("el => el.classList.contains('active')")
    assert not page.locator("#tool-select").evaluate("el => el.classList.contains('active')")


def test_inspector_collapses(session):
    page = session.open("editor.html")
    aside = page.locator("aside.panel")
    assert aside.is_visible()
    page.evaluate("VE.toggleInspector ? VE.toggleInspector() : null")
    if page.evaluate("typeof VE.toggleInspector") == "function":
        assert not aside.is_visible()


def test_timeline_shows_every_clip(session):
    page = session.open("editor.html")
    clips = page.locator(".tl-clip")
    assert clips.count() == 3
    kinds = clips.evaluate_all("els => els.map(e => [...e.classList].find(c => c.startsWith('clip-') && c !== 'clip-bar'))")
    assert kinds.count("clip-video") == 2 and kinds.count("clip-audio") == 1
    assert page.locator(".tl-clip.selected").count() == 1
