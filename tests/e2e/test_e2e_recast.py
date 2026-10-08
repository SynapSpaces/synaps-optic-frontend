"""The Recast take page: compare view (frames come from the stubbed backend), shots, modes, keys."""


def _shown(page):
    """Wait for the compare view to finish loading frames."""
    page.wait_for_function("() => document.getElementById('rc-loading').classList.contains('hidden')")


def test_compare_view_loads_frames(session):
    page = session.open("take.html")
    _shown(page)
    assert page.locator("#rc-img-a").get_attribute("src").startswith("data:image/svg+xml")
    assert page.locator("#rc-cap-a").inner_text() == "A · Source clip"
    assert page.locator("#rc-cap-b").inner_text() == "B · Cat take"


def test_every_shot_tab_fits_its_row(session):
    page = session.open("take.html")
    row = page.locator('#recast-shots [role="tablist"]').bounding_box()
    tabs = page.locator(".rc-shot")
    assert tabs.count() == 5
    for i in range(5):
        box = tabs.nth(i).bounding_box()
        assert box["x"] + box["width"] <= row["x"] + row["width"] + 0.5, f"shot {i + 1} overflows the row"
        assert box["width"] >= 44


def test_selecting_a_shot_shows_its_panel(session):
    page = session.open("take.html")
    _shown(page)
    page.click('.rc-shot[data-shot="3"]')
    assert page.locator('[data-shot-panel="3"]').is_visible()
    assert page.locator('[data-shot-panel="1"]').is_hidden()
    assert page.locator('.rc-shot[data-shot="3"]').evaluate("el => el.classList.contains('ring-2')")
    assert page.locator("#rc-frame").get_attribute("min") == "92"   # shot 3 starts at strided frame 92


def test_side_by_side_and_wipe(session):
    page = session.open("take.html")
    _shown(page)
    page.click('.rc-mode[data-mode="wipe"]')
    assert page.locator("#rc-wipe").is_visible() and page.locator("#rc-side").is_hidden()
    page.locator("#rc-wipe-pos").fill("30")
    assert "inset(0px 70% 0px 0px)" in page.locator("#rc-wipe-a").evaluate("el => getComputedStyle(el).clipPath")
    page.locator("#rc-wipe-pos").blur()          # keys are ignored while a slider has focus
    page.keyboard.press("w")
    assert page.locator("#rc-side").is_visible()
    # the mode labels stay on one line
    h = page.locator('.rc-mode[data-mode="side"]').bounding_box()["height"]
    assert h < 32, f"'Side by side' wrapped ({h}px tall)"


def test_arrow_keys_step_frames(session):
    page = session.open("take.html")
    _shown(page)
    page.keyboard.press("ArrowRight")
    _shown(page)
    assert page.locator("#rc-frame").input_value() == "1"
    assert "f1" in page.locator("#rc-tc").inner_text()
    page.keyboard.press("Shift+ArrowRight")
    assert page.locator("#rc-frame").input_value() == "6"


def test_a_failing_backend_does_not_leave_the_veil_up(browser, site):
    """Network errors on lane_urls used to throw and keep 'loading…' on screen."""
    ctx = browser.new_context()
    ctx.route("**/api/**", lambda route: route.abort())
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"{site}/take.html", wait_until="load")
    page.wait_for_function("() => document.getElementById('rc-loading').classList.contains('hidden')", timeout=10000)
    ctx.close()
    assert not errors, errors
