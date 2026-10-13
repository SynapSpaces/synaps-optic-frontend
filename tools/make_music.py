#!/usr/bin/env python
"""Generate original background-music tracks for the bundled library (GEN-06).

The editor's music picker and the renderer's ducking pass read
``optic_frontend/static/music/*.mp3`` (``optic_frontend.MUSIC_DIR``). This tool
fills that directory with procedurally synthesized instrumental beds: every
sample is computed from oscillators, envelopes and seeded noise -- no
recordings, samples, third-party audio or generative models are involved, so
there is no upstream license to clear. Next to each track it writes a
``<slug>.LICENSE.txt`` provenance record. Its ``License:`` line starts as
``PENDING OWNER REVIEW``: the owner decides the terms the tracks ship under
(pass ``--license`` to stamp them directly).

Usage (repo root; needs numpy, and ffmpeg on PATH for mp3 output)::

    python tools/make_music.py                       # 4 tracks x 90 s into optic_frontend/static/music
    python tools/make_music.py --styles ambient,lofi --seconds 60 --seed 11
    python tools/make_music.py --out /tmp/m --format wav --count 2 --seconds 8
    python tools/make_music.py --check               # verify the library: 3-5 tracks, LICENSE pairs, ffprobe

Styles: see ``STYLES``. Tracks fade in/out so the renderer's ``-stream_loop``
seam stays soft when a video outlasts the bed.
"""
from __future__ import annotations

import argparse
import datetime as dt
import math
import shutil
import subprocess
import sys
import wave
from dataclasses import dataclass
from pathlib import Path

try:
    import numpy as np
except ImportError:  # pragma: no cover - the CLI explains instead of tracing
    np = None  # type: ignore[assignment]

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = REPO_ROOT / "optic_frontend" / "static" / "music"
GENERATOR_URL = "https://github.com/SynapSpaces/synaps-optic-frontend/blob/main/tools/make_music.py"
GENERATOR_VERSION = "1"
PENDING_LICENSE = "PENDING OWNER REVIEW"

SR = 44100
A4 = 440.0
TWO_PI = 2.0 * math.pi

# ---------------------------------------------------------------------------
# Music theory: modes as semitone offsets, progressions as 0-based scale degrees.
# ---------------------------------------------------------------------------
MODES = {
    "ionian": (0, 2, 4, 5, 7, 9, 11),
    "dorian": (0, 2, 3, 5, 7, 9, 10),
    "lydian": (0, 2, 4, 6, 7, 9, 11),
    "mixolydian": (0, 2, 4, 5, 7, 9, 10),
    "aeolian": (0, 2, 3, 5, 7, 8, 10),
}
PROGRESSIONS = (
    (0, 5, 3, 4),
    (0, 3, 5, 4),
    (5, 3, 0, 4),
    (0, 4, 5, 3),
    (0, 2, 3, 4),
    (3, 4, 0, 5),
    (0, 5, 2, 3),
)
ADJECTIVES = ("still", "amber", "quiet", "northern", "paper", "slow", "glass",
              "evening", "open", "soft", "blue", "early", "copper", "hollow")
NOUNS = ("water", "light", "harbor", "fields", "window", "orbit", "meadow",
         "signal", "morning", "tide", "lantern", "valley", "current", "ember")


@dataclass(frozen=True)
class Style:
    name: str
    description: str
    bpm: tuple[int, int]
    modes: tuple[str, ...]
    tonic: tuple[int, int]      # MIDI range the tonic is drawn from
    chord_bars: int             # bars per chord
    sevenths: bool
    pad: float                  # layer gains (0 = layer off)
    bass: float
    pluck: float
    pluck_density: float        # probability a pluck fires on an eighth note
    arp: float
    drums: float
    drum_pattern: str           # none | pulse | beat
    swing: float                # fraction of a beat the off-eighths lag
    harmonic_rolloff: float     # pad brightness: partial k has amplitude k**-rolloff
    reverb_seconds: float
    reverb_wet: float


STYLES: dict[str, Style] = {
    "ambient": Style("ambient", "slow evolving pads, sparse bell plucks, no drums",
                     (56, 68), ("dorian", "aeolian", "lydian"), (45, 52), 2, True,
                     0.55, 0.30, 0.22, 0.18, 0.0, 0.0, "none", 0.0, 1.6, 2.8, 0.45),
    "cinematic": Style("cinematic", "low drone, dark pads, a slow pulse",
                       (60, 72), ("aeolian", "dorian"), (40, 47), 2, True,
                       0.60, 0.45, 0.15, 0.12, 0.0, 0.30, "pulse", 0.0, 1.3, 3.2, 0.50),
    "lofi": Style("lofi", "warm chords, soft kick and hats, swung eighths",
                  (72, 84), ("dorian", "mixolydian", "ionian"), (48, 55), 1, True,
                  0.40, 0.40, 0.35, 0.45, 0.0, 0.55, "beat", 0.12, 1.9, 1.2, 0.25),
    "uplift": Style("uplift", "bright major arpeggios with a light beat",
                    (96, 112), ("ionian", "lydian", "mixolydian"), (50, 57), 1, False,
                    0.40, 0.35, 0.20, 0.30, 0.30, 0.40, "beat", 0.0, 1.2, 1.6, 0.30),
    "minimal": Style("minimal", "sparse piano-like plucks over a faint pad",
                     (66, 78), ("ionian", "dorian"), (48, 55), 1, False,
                     0.15, 0.25, 0.45, 0.55, 0.0, 0.0, "none", 0.0, 2.0, 2.2, 0.35),
}
DEFAULT_STYLES = ("ambient", "cinematic", "lofi", "uplift")


def midi_to_hz(midi: float) -> float:
    return A4 * 2.0 ** ((midi - 69) / 12.0)


def chord_midi(tonic: int, mode: tuple[int, ...], degree: int, sevenths: bool) -> list[int]:
    """Stacked-thirds chord on a scale degree, as MIDI notes above the tonic."""
    idx = [degree, degree + 2, degree + 4] + ([degree + 6] if sevenths else [])
    return [tonic + mode[i % 7] + 12 * (i // 7) for i in idx]


# ---------------------------------------------------------------------------
# Synthesis primitives (vectorized, mono float32 at SR).
# ---------------------------------------------------------------------------
def envelope(n: int, attack: float, release: float) -> np.ndarray:
    env = np.ones(n, dtype=np.float32)
    a = min(int(attack * SR), n)
    r = min(int(release * SR), n - a)
    if a:
        env[:a] = np.linspace(0.0, 1.0, a, endpoint=False, dtype=np.float32)
    if r:
        env[n - r:] *= np.linspace(1.0, 0.0, r, dtype=np.float32)
    return env


def pad_note(freq: float, n: int, rolloff: float, rng: np.random.Generator) -> np.ndarray:
    t = np.arange(n, dtype=np.float32) / SR
    out = np.zeros(n, dtype=np.float32)
    for detune in (-0.004, 0.0, 0.004):          # three detuned voices beat slowly
        f0 = freq * (1.0 + detune)
        phase = rng.uniform(0.0, TWO_PI)
        for k in range(1, 12):
            fk = f0 * k
            if fk > 6000.0:
                break
            out += (k ** -rolloff) * np.sin(TWO_PI * fk * t + phase * k, dtype=np.float32)
    tremolo = 1.0 + 0.08 * np.sin(TWO_PI * rng.uniform(0.08, 0.2) * t + rng.uniform(0.0, TWO_PI))
    out *= tremolo.astype(np.float32)
    seconds = n / SR
    out *= envelope(n, min(1.2, seconds * 0.35), min(1.5, seconds * 0.35))
    return out / 3.0


def pluck_note(freq: float, n: int, rng: np.random.Generator) -> np.ndarray:
    t = np.arange(n, dtype=np.float32) / SR
    out = np.zeros(n, dtype=np.float32)
    for k in range(1, 7):
        fk = freq * k * (1.0 + 0.0004 * k * k)   # slight string-like inharmonicity
        if fk > 9000.0:
            break
        decay = 2.2 + 1.1 * k + freq / 400.0     # upper partials and high notes die faster
        out += (k ** -1.3) * np.sin(TWO_PI * fk * t + rng.uniform(0.0, TWO_PI), dtype=np.float32) \
            * np.exp(-decay * t, dtype=np.float32)
    out *= envelope(n, 0.004, min(0.05, n / SR * 0.2))
    return out


def bass_note(freq: float, n: int) -> np.ndarray:
    t = np.arange(n, dtype=np.float32) / SR
    out = (np.sin(TWO_PI * freq * t) + 0.25 * np.sin(TWO_PI * 2 * freq * t)
           + 0.08 * np.sin(TWO_PI * 3 * freq * t)).astype(np.float32)
    out *= envelope(n, 0.02, min(0.4, n / SR * 0.3)) * np.exp(-0.35 * t, dtype=np.float32)
    return out


def kick() -> np.ndarray:
    n = int(0.35 * SR)
    t = np.arange(n, dtype=np.float32) / SR
    freq = 42.0 + 90.0 * np.exp(-t * 28.0)
    phase = TWO_PI * np.cumsum(freq) / SR
    return (np.sin(phase) * np.exp(-t * 9.0) * envelope(n, 0.001, 0.05)).astype(np.float32)


def band_noise(n: int, low_hz: float, tilt_hz: float, rng: np.random.Generator) -> np.ndarray:
    """White noise shaped in the frequency domain: a 12 dB/oct roll-off below
    `low_hz` and an exponential tilt above `tilt_hz`, so hats and snares sit
    in the 2-10 kHz band instead of hissing across the whole spectrum."""
    spec = np.fft.rfft(rng.standard_normal(n))
    f = np.fft.rfftfreq(n, 1.0 / SR)
    shape = (f / low_hz) ** 2 / (1.0 + (f / low_hz) ** 2) \
        * np.exp(-np.maximum(f - tilt_hz, 0.0) / (0.3 * tilt_hz))   # about -60 dB by 22 kHz
    out = np.fft.irfft(spec * shape, n).astype(np.float32)
    out /= np.max(np.abs(out)) or 1.0
    return out


def hat(rng: np.random.Generator) -> np.ndarray:
    n = int(0.06 * SR)
    t = np.arange(n, dtype=np.float32) / SR
    return (band_noise(n, 3000.0, 7000.0, rng) * np.exp(-t * 55.0) * 0.35).astype(np.float32)


def snare(rng: np.random.Generator) -> np.ndarray:
    n = int(0.2 * SR)
    t = np.arange(n, dtype=np.float32) / SR
    noise = band_noise(n, 800.0, 5000.0, rng)
    body = np.sin(TWO_PI * 185.0 * t) * np.exp(-t * 30.0)
    return ((0.6 * noise * np.exp(-t * 22.0) + 0.4 * body) * envelope(n, 0.001, 0.02)).astype(np.float32)


def reverb(stereo: np.ndarray, seconds: float, wet: float, rng: np.random.Generator) -> np.ndarray:
    """Convolve with a decorrelated exponentially decaying noise impulse response
    (unit energy per channel, so `wet` is relative to the dry level)."""
    if wet <= 0.0 or seconds <= 0.0:
        return stereo
    n_ir = int(seconds * SR)
    t = np.arange(n_ir, dtype=np.float32) / SR
    size = 1 << (len(stereo) + n_ir - 1).bit_length()
    out = stereo.copy()
    for ch in range(2):
        ir = rng.standard_normal(n_ir).astype(np.float32) * np.exp(-6.9 * t / seconds)
        ir /= math.sqrt(float(np.sum(ir * ir))) or 1.0
        y = np.fft.irfft(np.fft.rfft(stereo[:, ch], size) * np.fft.rfft(ir, size), size)[:len(stereo)]
        out[:, ch] += wet * y.astype(np.float32)
    return out


class Mixer:
    def __init__(self, n: int):
        self.buf = np.zeros((n, 2), dtype=np.float32)

    def add(self, sig: np.ndarray, start: int, gain: float, pan: float = 0.0) -> None:
        """Equal-power pan `pan` in [-1, 1]; anything past the buffer end is dropped."""
        end = min(start + len(sig), len(self.buf))
        if start < 0 or start >= end:
            return
        seg = sig[:end - start]
        angle = (pan + 1.0) * math.pi / 4.0
        self.buf[start:end, 0] += seg * (gain * math.cos(angle))
        self.buf[start:end, 1] += seg * (gain * math.sin(angle))


# ---------------------------------------------------------------------------
# Composition
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Track:
    style: str
    seed: int
    seconds: float
    bpm: int
    mode: str
    tonic: int
    title: str
    slug: str
    audio: np.ndarray           # (n, 2) float32 in [-1, 1]


def _name(style: str, rng: np.random.Generator) -> tuple[str, str]:
    adj = ADJECTIVES[int(rng.integers(len(ADJECTIVES)))]
    noun = NOUNS[int(rng.integers(len(NOUNS)))]
    return f"{adj.title()} {noun.title()}", f"{style}-{adj}-{noun}"


def compose(style_name: str, seconds: float, seed: int) -> Track:
    if np is None:
        raise SystemExit("numpy is required: pip install numpy  (or: pip install -e .[music])")
    style = STYLES[style_name]
    rng = np.random.default_rng(seed)
    title, slug = _name(style_name, rng)
    bpm = int(rng.integers(style.bpm[0], style.bpm[1] + 1))
    mode_name = str(rng.choice(style.modes))
    mode = MODES[mode_name]
    tonic = int(rng.integers(style.tonic[0], style.tonic[1] + 1))
    progression = PROGRESSIONS[int(rng.integers(len(PROGRESSIONS)))]

    beat = 60.0 / bpm
    bar = 4.0 * beat
    n_total = int(seconds * SR)
    bars = max(4, math.ceil(seconds / bar) + 1)      # events past the end are clipped by the mixer
    wet = Mixer(n_total)                            # pads / plucks / arps -> reverb
    dry = Mixer(n_total)                            # bass / drums

    chords = [chord_midi(tonic, mode, progression[(b // style.chord_bars) % len(progression)], style.sevenths)
              for b in range(bars)]

    # Pads: one voicing per chord slot, alternating pan, slight overlap into the next chord.
    if style.pad > 0:
        for slot in range(0, bars, style.chord_bars):
            dur = style.chord_bars * bar + 0.3
            n = int(dur * SR)
            pan = 0.25 if (slot // style.chord_bars) % 2 == 0 else -0.25
            for note in chords[slot]:
                wet.add(pad_note(midi_to_hz(note + 12), n, style.harmonic_rolloff, rng),
                        int(slot * bar * SR), style.pad * 0.9 / len(chords[slot]), pan)

    # Bass: root an octave down on beat 1; styles with a beat also hit beat 3 (root or fifth).
    if style.bass > 0:
        for b in range(bars):
            root = chords[b][0] - 12
            dry.add(bass_note(midi_to_hz(root), int(bar * 0.95 * SR)), int(b * bar * SR), style.bass)
            if style.drum_pattern == "beat":
                note = root if rng.random() < 0.5 else chords[b][2] - 12
                dry.add(bass_note(midi_to_hz(note), int(beat * 1.5 * SR)),
                        int((b * bar + 2 * beat) * SR), style.bass * 0.8)

    # Plucks: random chord tones on eighths, two registers, random pan and length.
    eighths = bars * 8
    if style.pluck > 0:
        for step in range(eighths):
            if rng.random() >= style.pluck_density:
                continue
            b = step // 8
            tones = chords[b]
            note = tones[int(rng.integers(len(tones)))] + (12 if rng.random() < 0.6 else 24)
            swing = style.swing * beat if step % 2 else 0.0
            start = int(((step / 2.0) * beat + swing) * SR)
            n = int(rng.uniform(0.8, 2.0) * SR)
            wet.add(pluck_note(midi_to_hz(note), n, rng), start,
                    style.pluck * rng.uniform(0.5, 1.0), rng.uniform(-0.6, 0.6))

    # Arpeggio: an up-down pattern over the chord tones, one note per eighth.
    if style.arp > 0:
        pattern = (0, 1, 2, 3, 2, 1)
        for step in range(eighths):
            b = step // 8
            tones = [chords[b][0] + 12, chords[b][1] + 12, chords[b][2] + 12, chords[b][0] + 24]
            note = tones[pattern[step % len(pattern)]]
            wet.add(pluck_note(midi_to_hz(note), int(beat * 0.9 * SR), rng),
                    int((step / 2.0) * beat * SR), style.arp, 0.3 if step % 2 else -0.3)

    # Drums.
    if style.drums > 0 and style.drum_pattern != "none":
        kick_sig = kick()
        for b in range(bars):
            bar_start = b * bar
            if style.drum_pattern == "pulse":
                if b % 2 == 0:
                    dry.add(kick_sig, int(bar_start * SR), style.drums)
                continue
            for beat_idx in (0, 2):
                dry.add(kick_sig, int((bar_start + beat_idx * beat) * SR), style.drums)
            if rng.random() < 0.3:
                dry.add(kick_sig, int((bar_start + 3.5 * beat) * SR), style.drums * 0.7)
            for beat_idx in (1, 3):
                dry.add(snare(rng), int((bar_start + beat_idx * beat) * SR), style.drums * 0.45)
            for e in range(8):
                swing = style.swing * beat if e % 2 else 0.0
                vel = rng.uniform(0.5, 0.8) if e % 2 == 0 else rng.uniform(0.25, 0.5)
                dry.add(hat(rng), int((bar_start + e * beat / 2.0 + swing) * SR), style.drums * vel)

    mix = reverb(wet.buf, style.reverb_seconds, style.reverb_wet, rng) + dry.buf
    return Track(style_name, seed, seconds, bpm, mode_name, tonic, title, slug, master(mix))


def master(mix: np.ndarray, fade_in: float = 1.5, fade_out: float = 4.0,
           rms_dbfs: float = -22.0, ceiling: float = 0.8) -> np.ndarray:
    """Fade the ends, normalize loudness to an RMS target (about -20 LUFS: a bed
    that sits under speech before ducking), soft-clip peaks under `ceiling`."""
    out = mix.astype(np.float32, copy=True)
    n = len(out)
    fi = min(int(fade_in * SR), n)
    fo = min(int(fade_out * SR), n - fi)
    if fi:
        out[:fi] *= np.linspace(0.0, 1.0, fi, dtype=np.float32)[:, None]
    if fo:
        out[n - fo:] *= np.linspace(1.0, 0.0, fo, dtype=np.float32)[:, None]
    rms = float(np.sqrt(np.mean(out * out))) or 1e-9
    out *= 10.0 ** (rms_dbfs / 20.0) / rms
    over = np.abs(out) > 0.8
    out[over] = np.sign(out[over]) * (0.8 + 0.2 * np.tanh((np.abs(out[over]) - 0.8) / 0.2))
    peak = float(np.max(np.abs(out))) or 1e-9
    if peak > ceiling:
        out *= ceiling / peak
    return out


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
def write_wav(path: Path, audio: np.ndarray) -> None:
    pcm = np.clip(audio * 32767.0, -32768, 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def write_mp3(path: Path, audio: np.ndarray, title: str, bitrate: str) -> None:
    if not shutil.which("ffmpeg"):
        raise SystemExit("ffmpeg not on PATH -- install it or use --format wav")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", "2",
           "-i", "pipe:0", "-codec:a", "libmp3lame", "-b:a", bitrate,
           "-metadata", f"title={title}", "-metadata", "artist=Synaps Optic (generated)",
           str(path)]
    subprocess.run(cmd, input=audio.astype("<f4").tobytes(), check=True)


def license_text(track: Track, filename: str, license_line: str, today: dt.date) -> str:
    style = STYLES[track.style]
    return (
        f"Title: {track.title}\n"
        f"File: {filename}\n"
        f"Generated: {today.isoformat()}\n"
        f"Source: generated locally by tools/make_music.py v{GENERATOR_VERSION} "
        f"(style={track.style}, seed={track.seed}, length={track.seconds:g}s, "
        f"bpm={track.bpm}, mode={track.mode}, tonic=MIDI {track.tonic})\n"
        f"Generator: {GENERATOR_URL}\n"
        f"Method: procedural synthesis -- {style.description}; additive oscillators, "
        f"synthesized drums and a synthetic noise-impulse reverb. No recordings, samples, "
        f"third-party audio or generative models were used.\n"
        f"Rights: original work created for Synaps Optic; the owner confirms the terms before "
        f"commercial distribution.\n"
        f"License: {license_line}\n"
    )


def generate(out: Path, styles: list[str], count: int, seconds: float, seed: int,
             fmt: str, bitrate: str, license_line: str) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    used: set[str] = set()
    today = dt.date.today()
    for i in range(count):
        style = styles[i % len(styles)]
        track = compose(style, seconds, seed + i)
        slug = track.slug if track.slug not in used else f"{track.slug}-{seed + i}"
        used.add(slug)
        path = out / f"{slug}.{fmt}"
        if fmt == "wav":
            write_wav(path, track.audio)
        else:
            write_mp3(path, track.audio, track.title, bitrate)
        (out / f"{slug}.LICENSE.txt").write_text(license_text(track, path.name, license_line, today),
                                                 encoding="utf-8")
        print(f"{path.name}: {track.title} ({style}, {track.bpm} bpm {track.mode}, seed {seed + i})")
        written.append(path)
    return written


def check(out: Path, fmt: str = "mp3") -> list[str]:
    """Mirror plan 08-03's acceptance criteria. Returns a list of problems (empty = pass)."""
    problems: list[str] = []
    tracks = sorted(out.glob(f"*.{fmt}"))
    licenses = sorted(out.glob("*.LICENSE.txt"))
    if not 3 <= len(tracks) <= 5:
        problems.append(f"expected 3-5 .{fmt} tracks in {out}, found {len(tracks)}")
    if len(licenses) != len(tracks):
        problems.append(f"{len(tracks)} tracks but {len(licenses)} LICENSE.txt files")
    for track in tracks:
        lic = out / f"{track.stem}.LICENSE.txt"
        if not lic.exists():
            problems.append(f"{track.name}: missing {lic.name}")
            continue
        text = lic.read_text(encoding="utf-8")
        if not text.strip():
            problems.append(f"{lic.name}: empty")
        if "http" not in text:
            problems.append(f"{lic.name}: no source/generator URL")
        if PENDING_LICENSE in text:
            problems.append(f"{lic.name}: License line still '{PENDING_LICENSE}' (owner must stamp the terms)")
    if shutil.which("ffprobe"):
        for track in tracks:
            res = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type",
                                  "-of", "csv=p=0", str(track)], capture_output=True, text=True)
            if res.returncode != 0 or "audio" not in res.stdout:
                problems.append(f"{track.name}: ffprobe did not find an audio stream")
    else:
        problems.append("ffprobe not on PATH -- cannot validate the audio files")
    return problems


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--out", type=Path, default=DEFAULT_OUT, help=f"output directory (default {DEFAULT_OUT})")
    p.add_argument("--styles", default=",".join(DEFAULT_STYLES),
                   help=f"comma-separated, cycled over --count; from: {', '.join(STYLES)}")
    p.add_argument("--count", type=int, default=4, help="tracks to generate (the library ships 3-5)")
    p.add_argument("--seconds", type=float, default=90.0, help="track length")
    p.add_argument("--seed", type=int, default=20261013, help="base seed; track i uses seed+i")
    p.add_argument("--format", choices=("mp3", "wav"), default="mp3")
    p.add_argument("--bitrate", default="128k", help="mp3 bitrate")
    p.add_argument("--license", default=PENDING_LICENSE,
                   help='License line for the provenance files, e.g. "CC0 1.0 Universal"')
    p.add_argument("--check", action="store_true", help="validate --out instead of generating")
    args = p.parse_args(argv)

    if args.check:
        problems = check(args.out, args.format)
        for problem in problems:
            print(f"FAIL: {problem}")
        if not problems:
            print(f"OK: {args.out} passes the 08-03 acceptance checks")
        return 1 if problems else 0

    styles = [s.strip() for s in args.styles.split(",") if s.strip()]
    unknown = [s for s in styles if s not in STYLES]
    if unknown:
        p.error(f"unknown style(s) {unknown}; choose from {', '.join(STYLES)}")
    if not 3 <= args.count <= 5:
        print(f"note: the bundled library is meant to hold 3-5 tracks (asked for {args.count})", file=sys.stderr)
    generate(args.out, styles, args.count, args.seconds, args.seed, args.format, args.bitrate, args.license)
    if args.license == PENDING_LICENSE:
        print(f"\nLicense line is '{PENDING_LICENSE}': edit each LICENSE.txt (or rerun with --license) "
              f"once you have decided the terms; --check fails until then.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
