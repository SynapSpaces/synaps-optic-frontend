"""Make a narrated MP4 of the Playwright browser tests.

Runs the suite with recording on, plays every test's clip at half speed (holding the last frame while
the narration finishes), adds a British English voice-over and captions, and writes a transcript.

    python tools/e2e_video.py                        # -> e2e-artifacts/e2e-run.mp4 (+ .srt, .md)
    python tools/e2e_video.py --speed 1 -k theme     # normal speed, only the dark-mode tests
    python tools/e2e_video.py --no-voice             # captions only

Needs the e2e extra, Chromium for Playwright and ffmpeg on PATH; the voice-over needs piper-tts
(`pip install -e .[video]`). The voice is Piper's en_GB "cori" (UK English female, trained on
public-domain LibriVox recordings), downloaded once to the user's cache (about 115 MB).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import urllib.request
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import e2e_narration as narration  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
VIDEO_DIR = ROOT / "e2e-artifacts" / "videos"
FONTS = ["C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf"]
VOICE = "en_GB-cori-high"
VOICE_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/cori/high/"
W, H, FPS, RATE = 1280, 800, 25, 22050
LEAD, TAIL = 0.35, 0.6
STRIP = 112                     # caption strip height in px (two lines of narration)          # seconds of silence before and after each spoken line


# ----------------------------------------------------------------------------- helpers
def ffmpeg(*args: str, cwd: Path) -> None:
    subprocess.run(["ffmpeg", "-y", "-v", "error", *args], check=True, cwd=cwd)


def duration(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True).stdout.strip()
    return float(out or 0)


def split_name(stem: str) -> tuple[str, str | None]:
    """'007_test_page_loads_with_the_design_system_take.html_' -> ('page_loads_with_the_design_system', 'take.html')."""
    name = re.sub(r"^\d+_test_", "", stem)
    m = re.search(r"\[(.+?)\]$", name)
    return (name[:m.start()], m.group(1)) if m else (name, None)


def voice_model() -> Path:
    cache = Path(os.environ.get("LOCALAPPDATA") or Path.home() / ".cache") / "piper-voices"
    cache.mkdir(parents=True, exist_ok=True)
    for f in (f"{VOICE}.onnx", f"{VOICE}.onnx.json"):
        if not (cache / f).exists():
            print(f"downloading the voice {f} ...", flush=True)
            urllib.request.urlretrieve(VOICE_URL + f, cache / f)
    return cache / f"{VOICE}.onnx"


class Voice:
    def __init__(self, enabled: bool):
        self.v = None
        if enabled:
            try:
                from piper import PiperVoice, SynthesisConfig
            except ImportError:
                sys.exit("the voice-over needs piper-tts: pip install -e .[video]  (or run with --no-voice)")
            self.v = PiperVoice.load(str(voice_model()))
            self.cfg = SynthesisConfig(length_scale=1.08)   # a touch slower than the default

    def say(self, text: str, out: Path) -> float:
        """Write `text` as a WAV with lead/tail silence; return its length (0 without a voice)."""
        if self.v is None:
            return 0.0
        raw = out.with_suffix(".raw.wav")
        with wave.open(str(raw), "wb") as w:
            self.v.synthesize_wav(text, w, syn_config=self.cfg)
        ffmpeg("-i", raw.name, "-af", f"adelay={int(LEAD * 1000)}:all=1,apad=pad_dur={TAIL},aresample={RATE}",
               "-ac", "1", out.name, cwd=out.parent)
        return duration(out)


def wrap(text: str, width: int = 78) -> str:
    return "\n".join(textwrap.wrap(text, width))


def srt_time(t: float) -> str:
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


# ----------------------------------------------------------------------------- segments
def segment(work: Path, name: str, video_filter_in: list[str], text: str, label: str, seconds: float,
            voice: Voice, font: str | None, src: Path | None = None, start: float = 0.0) -> float:
    """One segment = video (a clip or a white card) + its narration, captioned. Returns its length."""
    spoken = voice.say(text, work / f"{name}.wav") if text else 0.0
    seconds = max(seconds, spoken)
    # newline: Windows would write CRLF, and ffmpeg's drawtext draws each CR as an extra blank line
    (work / f"{name}.cap.txt").write_text(wrap(text), encoding="utf-8", newline="\n")
    (work / f"{name}.lab.txt").write_text(label, encoding="utf-8", newline="\n")
    vf = list(video_filter_in) + [f"tpad=stop_mode=clone:stop_duration={seconds}", f"trim=duration={seconds}"]
    if font:
        if label:
            vf.append(f"drawtext=fontfile={font}:textfile={name}.lab.txt:fontcolor=0x5d5d5d:fontsize=20"
                      ":box=1:boxcolor=white@0.85:boxborderw=8:x=20:y=18")
        if text:
            vf.append(f"drawbox=x=0:y=ih-{STRIP}:w=iw:h={STRIP}:color=0x0d0d0d@0.86:t=fill,drawtext=fontfile={font}"
                      f":textfile={name}.cap.txt:fontcolor=white:fontsize=26:line_spacing=10:x=(w-text_w)/2"
                      f":y=h-{STRIP}+({STRIP}-text_h)/2")
    inputs = ["-ss", f"{start:.2f}", "-i", str(src)] if src else ["-f", "lavfi", "-i", f"color=c=white:s={W}x{H}:r={FPS}:d=0.04"]
    audio = ["-i", f"{name}.wav"] if spoken else ["-f", "lavfi", "-t", str(seconds), "-i", f"anullsrc=r={RATE}:cl=mono"]
    ffmpeg(*inputs, *audio, "-filter_complex", f"[0:v]{','.join(vf)}[v];[1:a]apad,atrim=duration={seconds}[a]",
           "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS),
           "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2", f"{name}.mp4", cwd=work)
    return seconds


def title_filters(lines: list[str], work: Path, name: str, font: str | None) -> list[str]:
    out = []
    for i, line in enumerate(lines):
        (work / f"{name}.t{i}.txt").write_text(line, encoding="utf-8", newline="\n")
        if font:
            size, y = (54, "(h/2)-90") if i == 0 else (28, "(h/2)-10")
            out.append(f"drawtext=fontfile={font}:textfile={name}.t{i}.txt:fontcolor=0x0d0d0d:fontsize={size}:x=(w-text_w)/2:y={y}")
    return out


# ----------------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(ROOT / "e2e-artifacts" / "e2e-run.mp4"))
    ap.add_argument("--speed", type=float, default=0.5, help="playback speed of the clips (0.5 = half speed)")
    ap.add_argument("--slowmo", type=int, default=250, help="ms between browser actions while recording")
    ap.add_argument("-k", default=None, help="only tests matching this pytest -k expression")
    ap.add_argument("--no-voice", action="store_true", help="captions without the voice-over")
    ap.add_argument("--headed", action="store_true", help="also show the browser while recording")
    a = ap.parse_args()
    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg is not on PATH")
    voice = Voice(not a.no_voice)

    if VIDEO_DIR.exists():
        shutil.rmtree(VIDEO_DIR)
    env = dict(os.environ, E2E_VIDEO="1", E2E_SLOWMO=str(a.slowmo), PYTHONUTF8="1")
    if a.headed:
        env["E2E_HEADED"] = "1"
    cmd = [sys.executable, "-m", "pytest", "-m", "e2e", "-p", "no:cacheprovider", *(["-k", a.k] if a.k else [])]
    print("+", " ".join(cmd[2:]), flush=True)
    run = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    summary = next((ln.strip("= ").strip() for ln in reversed(run.stdout.splitlines()) if " passed" in ln or " failed" in ln),
                   "the tests did not run")
    summary = re.sub(r" in [\d.]+s.*$", "", re.sub(r",? \d+ deselected", "", summary))
    summary_text = summary.replace("passed", "tests passed").replace("failed", "tests failed")
    print(summary)
    clips = sorted(VIDEO_DIR.glob("[0-9][0-9][0-9]_*.webm"))
    if not clips:
        print(run.stdout[-3000:], run.stderr[-2000:])
        sys.exit("no videos were recorded")

    out = Path(a.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    transcript, t = [], 0.0
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        font = None
        for f in FONTS:
            if Path(f).exists():
                shutil.copy(f, work / "font.ttf")
                font = "font.ttf"
                break
        parts = []

        def add(name, filters, text, label, seconds, src=None, start=0.0):
            nonlocal t
            n = segment(work, name, filters, text, label, seconds, voice, font, src, start)
            parts.append(f"{name}.mp4")
            if text:
                transcript.append((t + LEAD, t + n - TAIL * 0.5, label, text))
            t += n

        add("000_title", title_filters(["Synaps Optic", f"Browser tests · {len(clips)} recorded"], work, "000_title", font),
            narration.INTRO, "", 3.0)
        seen: set[str] = set()
        for i, clip in enumerate(clips, start=1):
            test, param = split_name(clip.stem)
            text = narration.line_for(test, param, seen)
            base = (f"setpts={1 / a.speed:g}*PTS,scale={W}:{H}:force_original_aspect_ratio=decrease,"
                    f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:white,fps={FPS}")
            side = clip.with_suffix(".json")
            start = json.loads(side.read_text())["start"] if side.exists() else 0.0   # skip the blank lead-in
            start = min(start, max(0.0, duration(clip) - 0.5))
            add(f"{i:03d}", [base], text, f"{i}/{len(clips)}", (duration(clip) - start) / a.speed, src=clip, start=start)
            print(f"  {i:2d}/{len(clips)} {test} {param or ''}", flush=True)
        end_line = summary_text[:1].upper() + summary_text[1:]
        add("999_end", title_filters([end_line, "pytest -m e2e"], work, "999_end", font),
            narration.OUTRO.format(summary=end_line), "", 3.5)

        (work / "list.txt").write_text("".join(f"file '{p}'\n" for p in parts), encoding="utf-8")
        srt = out.with_suffix(".srt")
        srt.write_text("".join(f"{n}\n{srt_time(s)} --> {srt_time(e)}\n{wrap(txt, 60)}\n\n"
                               for n, (s, e, _, txt) in enumerate(transcript, start=1)), encoding="utf-8")
        ffmpeg("-f", "concat", "-safe", "0", "-i", "list.txt", "-i", str(srt), "-map", "0", "-map", "1",
               "-c", "copy", "-c:s", "mov_text", "-metadata:s:s:0", "language=eng", "-movflags", "+faststart",
               str(out), cwd=work)

    md = out.with_name(out.stem + "-transcript.md")
    md.write_text("# Synaps Optic browser tests: voice-over transcript\n\n"
                  f"Narrated run of the Playwright suite ({summary}). Voice: Piper `{VOICE}` (UK English, female).\n\n"
                  + "".join(f"**{srt_time(s)[:8]}**{(' · test ' + lab) if lab else ''}  \n{txt}\n\n"
                            for s, _, lab, txt in transcript), encoding="utf-8")
    json.dump({"summary": summary, "clips": len(clips), "seconds": round(duration(out), 1), "voice": None if a.no_voice else VOICE},
              open(out.with_suffix(".json"), "w"), indent=1)
    print(f"wrote {out} ({len(clips)} clips, {duration(out):.0f} s, {out.stat().st_size / 1e6:.1f} MB), {srt.name}, {md.name}")
    return run.returncode


if __name__ == "__main__":
    sys.exit(main())
