"""Make one MP4 of the Playwright browser tests: run the suite with recording on, caption each test,
and join the clips in run order between a title card and a result card.

    python tools/e2e_video.py                      # -> e2e-artifacts/e2e-run.mp4
    python tools/e2e_video.py --slowmo 500 -k theme  # slower, only the dark-mode tests
Needs the e2e extra, Chromium for Playwright and ffmpeg on PATH.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIDEO_DIR = ROOT / "e2e-artifacts" / "videos"
FONTS = ["C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf"]
W, H, FPS = 1280, 800, 25


def caption(stem: str) -> str:
    """'007_test_page_loads_with_the_design_system_take.html_' -> 'Page loads with the design system · take'."""
    name = re.sub(r"^\d+_test_", "", stem)
    param = ""
    m = re.search(r"\[(.+?)\]$", name)
    if m:
        param = m.group(1).replace(".html", "")
        name = name[:m.start()]
    text = name.replace("_", " ").strip()
    text = text[:1].upper() + text[1:]
    return f"{text} · {param}" if param else text


def ffmpeg(*args: str, cwd: Path) -> None:
    subprocess.run(["ffmpeg", "-y", "-v", "error", *args], check=True, cwd=cwd)


def card(work: Path, out: str, lines: list[str], seconds: float, font: str | None) -> None:
    """A plain white title card in the design system's ink."""
    vf = []
    for i, line in enumerate(lines):
        (work / f"{out}.{i}.txt").write_text(line, encoding="utf-8")
        size = 46 if i == 0 else 26
        y = f"(h/2)-{70 - i * 70}" if len(lines) > 1 else "(h-text_h)/2"
        if font:
            vf.append(f"drawtext=fontfile={font}:textfile={out}.{i}.txt:fontcolor=0x0d0d0d:fontsize={size}:x=(w-text_w)/2:y={y}")
    ffmpeg("-f", "lavfi", "-i", f"color=c=white:s={W}x{H}:r={FPS}:d={seconds}", *(["-vf", ",".join(vf)] if vf else []),
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS), f"{out}.mp4", cwd=work)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(ROOT / "e2e-artifacts" / "e2e-run.mp4"))
    ap.add_argument("--slowmo", type=int, default=250, help="ms between browser actions (readable on video)")
    ap.add_argument("-k", default=None, help="only tests matching this pytest -k expression")
    ap.add_argument("--headed", action="store_true", help="also show the browser while recording")
    a = ap.parse_args()
    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg is not on PATH")

    if VIDEO_DIR.exists():
        shutil.rmtree(VIDEO_DIR)
    env = dict(os.environ, E2E_VIDEO="1", E2E_SLOWMO=str(a.slowmo), PYTHONUTF8="1")
    if a.headed:
        env["E2E_HEADED"] = "1"
    cmd = [sys.executable, "-m", "pytest", "-m", "e2e", "-p", "no:cacheprovider", *(["-k", a.k] if a.k else [])]
    print("+", " ".join(cmd[2:]), flush=True)
    run = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    summary = next((ln.strip("= ").strip() for ln in reversed(run.stdout.splitlines()) if " passed" in ln or " failed" in ln),
                   "tests did not run")
    summary = re.sub(r",? \d+ deselected", "", summary)
    summary = re.sub(r" in [\d.]+s.*$", "", summary)
    print(summary)
    clips = sorted(VIDEO_DIR.glob("[0-9][0-9][0-9]_*.webm"))
    if not clips:
        print(run.stdout[-3000:], run.stderr[-2000:])
        sys.exit("no videos were recorded")

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        font = None
        for f in FONTS:
            if Path(f).exists():
                shutil.copy(f, work / "font.ttf")
                font = "font.ttf"
                break
        card(work, "00_title", ["Synaps Optic", f"Browser tests · {len(clips)} recorded"], 2.5, font)
        parts = ["00_title.mp4"]
        for i, clip in enumerate(clips, start=1):
            text = f"{i}/{len(clips)}  {caption(clip.stem)}"
            (work / f"c{i:03d}.txt").write_text(text, encoding="utf-8")
            vf = f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:white,fps={FPS}"
            if font:
                vf += (f",drawbox=x=0:y=ih-56:w=iw:h=56:color=0x0d0d0d@0.82:t=fill,drawtext=fontfile={font}"
                       f":textfile=c{i:03d}.txt:fontcolor=white:fontsize=24:x=24:y=h-40")
            ffmpeg("-i", str(clip), "-vf", vf, "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS),
                   f"c{i:03d}.mp4", cwd=work)
            parts.append(f"c{i:03d}.mp4")
        card(work, "99_end", [summary[:1].upper() + summary[1:], "pytest -m e2e"], 3, font)
        parts.append("99_end.mp4")
        (work / "list.txt").write_text("".join(f"file '{p}'\n" for p in parts), encoding="utf-8")
        out = Path(a.out).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        ffmpeg("-f", "concat", "-safe", "0", "-i", "list.txt", "-c", "copy", "-movflags", "+faststart", str(out), cwd=work)
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(out)],
                           capture_output=True, text=True)
    print(f"wrote {out} ({len(clips)} clips, {float(probe.stdout or 0):.0f} s, {out.stat().st_size / 1e6:.1f} MB)")
    return run.returncode


if __name__ == "__main__":
    sys.exit(main())
