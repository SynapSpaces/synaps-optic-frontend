"""Record docs/preview.gif: a short tour of the preview pages (projects, editor, recast).

Needs Playwright with Chromium (`pip install playwright pillow && python -m playwright install chromium`).
Renders the pages with tools/preview.py into a temp folder and drives a headless browser over them
through file:// URLs, so no server is needed.

    python tools/record_gif.py                 # writes docs/preview.gif
"""
from __future__ import annotations

import argparse
import sys
import tempfile
from io import BytesIO
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import preview  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
WIDTH, HEIGHT = 1280, 760


def shoot(page) -> Image.Image:
    return Image.open(BytesIO(page.screenshot(type="png"))).convert("RGB")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(ROOT / "docs" / "preview.gif"))
    ap.add_argument("--scale", type=float, default=0.625, help="GIF size relative to the 1280x760 viewport")
    a = ap.parse_args()
    from playwright.sync_api import sync_playwright

    with tempfile.TemporaryDirectory() as tmp:
        site = Path(tmp)
        preview.render_all(site)
        frames: list[tuple[Image.Image, int]] = []  # (frame, milliseconds on screen)
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": WIDTH, "height": HEIGHT})

            def visit(name: str, hold: int = 1600) -> None:
                page.goto((site / name).as_uri(), wait_until="load")
                # the Tailwind CDN script styles the page after load; the HTMX polls never let the
                # network go idle, so wait for Tailwind's injected stylesheet instead
                page.wait_for_function("() => [...document.querySelectorAll('style')].some(s => s.textContent.includes('--tw-'))",
                                       timeout=60000)
                page.evaluate("document.fonts.ready")
                page.wait_for_timeout(500)
                frames.append((shoot(page), hold))

            def scroll(dy: int, steps: int = 4, hold: int = 1400) -> None:
                for _ in range(steps):
                    page.mouse.wheel(0, dy / steps)
                    page.wait_for_timeout(120)
                    frames.append((shoot(page), 90))
                frames[-1] = (frames[-1][0], hold)

            visit("projects.html", 1800)                      # home: the AI prompt and the tools
            page.fill("textarea[name=prompt]", "A 20-second launch teaser for a coffee brand")
            frames.append((shoot(page), 1400))
            scroll(560)                                       # recent projects
            visit("editor.html", 2400)                        # the editor
            page.click("text=Effects")
            page.wait_for_timeout(250)
            frames.append((shoot(page), 1600))
            visit("recast.html", 1800)                        # recast takes
            scroll(420, hold=1800)
            browser.close()

    size = (int(WIDTH * a.scale), int(HEIGHT * a.scale))
    imgs = [f.resize(size, Image.LANCZOS) for f, _ in frames]
    pal = [im.quantize(colors=128, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE) for im in imgs]
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    pal[0].save(out, save_all=True, append_images=pal[1:], duration=[d for _, d in frames], loop=0, optimize=True)
    print(f"wrote {out} ({len(frames)} frames, {size[0]}x{size[1]}, {out.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
