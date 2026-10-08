"""Voice-over script for tools/e2e_video.py: one plain sentence per Playwright test, keyed by the test
function's name. Parametrised tests get a full line the first time and a short one after that."""
from __future__ import annotations

PAGE = {"projects": "the projects page", "editor": "the editor", "recast": "the Recast page", "take": "the take review page",
        "references": "the references page", "invites": "the invites page", "login": "the sign-in page"}

INTRO = ("These are the browser tests for Synaps Optic. Each one opens a page in Chrome and checks it "
         "the way a person would.")
OUTRO = "{summary}. The tests run automatically on every push to the repository."

# test name -> (first time, later times). {page} is the page under test.
LINES: dict[str, tuple[str, str]] = {
    "rail_switches_the_inspector_panel": (
        "In the editor, each button on the left rail opens its own panel, and only one button is highlighted at a time.", ""),
    "videos_sub_tabs": (
        "The Videos panel has three tabs: edit, effects and transitions. Exactly one is selected after each click.", ""),
    "tool_buttons_are_exclusive": (
        "The select and hand tools work like a switch. Choosing one turns the other off.", ""),
    "inspector_collapses": (
        "The inspector on the left can be collapsed to give the preview more room.", ""),
    "timeline_shows_every_clip": (
        "The timeline shows all three clips. The two scenes are video clips, and the voice-over is an audio clip.", ""),
    "page_loads_with_the_design_system": (
        "Next, every page loads with the Synapspaces design system: the Geist font, a white page, and nothing "
        "spilling off the side. This is {page}.",
        "Now {page}."),
    "top_bar_has_the_logo_and_the_theme_toggle": (
        "Each page's top bar shows the Synapspaces logo and the light and dark switch. This is {page}.",
        "And {page}."),
    "nav_moves_between_sections": (
        "The navigation moves between Projects and Recast, and the logo leads back home.", ""),
    "project_card_opens_the_editor": (
        "Clicking a project card opens that project in the editor.", ""),
    "buttons_and_inputs_follow_the_system": (
        "On the sign-in page, buttons are rounded pills, fields are the standard height, and placeholder text "
        "uses the design system's grey.", ""),
    "ai_prompt_accepts_text": (
        "The AI prompt on the home page accepts a description, and the aspect ratio can be changed.", ""),
    "compare_view_loads_frames": (
        "On the take review page, the compare view loads frames from the source clip and the cat take, side by side.", ""),
    "every_shot_tab_fits_its_row": (
        "All five shot tabs fit in their row. This test caught the last tab being cut off.", ""),
    "selecting_a_shot_shows_its_panel": (
        "Selecting a shot opens its review panel and moves the frame slider to that shot.", ""),
    "side_by_side_and_wipe": (
        "The compare view switches between side by side and a wipe. The slider moves the wipe, and the W key switches back.", ""),
    "arrow_keys_step_frames": (
        "The arrow keys step one frame at a time. With shift held, they jump five frames.", ""),
    "a_failing_backend_does_not_leave_the_veil_up": (
        "If the backend cannot be reached, the loading screen still goes away instead of getting stuck.", ""),
    "follows_a_light_system": (
        "Dark mode. With the computer set to light, the editor is light.", ""),
    "follows_a_dark_system": (
        "With the computer set to dark, the editor turns dark, and the main buttons flip to light.", ""),
    "toggle_switches_and_is_remembered": (
        "The switch in the top bar changes the theme. The choice is remembered after a reload and carries into the editor.", ""),
    "choice_survives_without_a_flash": (
        "The saved theme is applied before the page appears, so there is no white flash.", ""),
    "media_stays_dark_in_dark_mode": (
        "Video and images keep their black background in both themes. This is {page}.",
        "And again on {page}."),
    "editor_toggle_works_too": (
        "Finally, the switch in the editor's own top bar works too.", ""),
}


def line_for(test: str, param: str | None, seen: set[str]) -> str:
    """The narration for one clip. `test` is the function name without 'test_'; `param` the page, if any."""
    first, later = LINES.get(test, (test.replace("_", " ").capitalize() + ".", ""))
    page = PAGE.get((param or "").split("-")[0].replace(".html", ""), "this page")
    text = first if test not in seen or not later else later
    seen.add(test)
    return text.format(page=page)
