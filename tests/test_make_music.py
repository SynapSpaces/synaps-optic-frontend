"""tools/make_music.py: the procedural background-music generator (GEN-06 library).

Pure-numpy checks on short renders; the mp3 path needs ffmpeg and is covered
by the repo's --check run, not here.
"""
import importlib.util
import sys
import wave
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
make_music = importlib.import_module("make_music")

SECONDS = 6.0


@pytest.fixture(scope="module", params=sorted(make_music.STYLES))
def track(request):
    return make_music.compose(request.param, SECONDS, seed=7)


def test_every_style_renders_a_stereo_bed(track):
    n = int(SECONDS * make_music.SR)
    assert track.audio.shape == (n, 2)
    assert track.audio.dtype == np.float32
    assert np.all(np.isfinite(track.audio))
    peak = float(np.max(np.abs(track.audio)))
    assert 0.3 < peak <= 0.8, f"{track.style}: peak {peak} outside the mastering ceiling"
    rms = float(np.sqrt(np.mean(track.audio ** 2)))
    assert 0.03 < rms < 0.2, f"{track.style}: rms {rms} -- silent or far off the -22 dBFS target"


def test_fades_start_and_end_near_silence(track):
    sr = make_music.SR
    assert float(np.max(np.abs(track.audio[: sr // 100]))) < 0.02
    assert float(np.max(np.abs(track.audio[-sr // 100:]))) < 0.02


def test_same_seed_is_bit_identical():
    a = make_music.compose("lofi", SECONDS, seed=3)
    b = make_music.compose("lofi", SECONDS, seed=3)
    assert a.title == b.title and a.bpm == b.bpm and a.mode == b.mode
    assert np.array_equal(a.audio, b.audio)


def test_different_seeds_differ():
    a = make_music.compose("ambient", SECONDS, seed=1)
    b = make_music.compose("ambient", SECONDS, seed=2)
    assert not np.array_equal(a.audio, b.audio)


def test_wav_round_trip(tmp_path):
    t = make_music.compose("minimal", SECONDS, seed=5)
    out = tmp_path / "x.wav"
    make_music.write_wav(out, t.audio)
    with wave.open(str(out)) as w:
        assert (w.getnchannels(), w.getsampwidth(), w.getframerate()) == (2, 2, make_music.SR)
        assert w.getnframes() == len(t.audio)


def test_cli_writes_tracks_with_provenance_and_check_gates_on_license(tmp_path, capsys):
    rc = make_music.main(["--out", str(tmp_path), "--format", "wav", "--count", "3",
                          "--seconds", "4", "--seed", "11"])
    assert rc == 0
    wavs = sorted(tmp_path.glob("*.wav"))
    lics = sorted(tmp_path.glob("*.LICENSE.txt"))
    assert len(wavs) == 3 and len(lics) == 3
    assert {w.stem for w in wavs} == {lic.name.removesuffix(".LICENSE.txt") for lic in lics}
    for lic in lics:
        text = lic.read_text(encoding="utf-8")
        assert make_music.GENERATOR_URL in text
        assert "seed=" in text and "License: " + make_music.PENDING_LICENSE in text

    # Owner has not stamped the terms yet: the acceptance check must refuse.
    assert make_music.main(["--out", str(tmp_path), "--format", "wav", "--check"]) == 1
    assert "PENDING OWNER REVIEW" in capsys.readouterr().out

    # Stamped: passes (ffprobe may be absent on CI, which is reported as the only problem).
    rc = make_music.main(["--out", str(tmp_path), "--format", "wav", "--count", "3",
                          "--seconds", "4", "--seed", "11", "--license", "CC0 1.0 Universal"])
    assert rc == 0
    problems = make_music.check(tmp_path, "wav")
    assert [p for p in problems if "ffprobe" not in p] == []


def test_check_rejects_wrong_track_count(tmp_path):
    make_music.main(["--out", str(tmp_path), "--format", "wav", "--count", "2", "--seconds", "2",
                     "--license", "CC0 1.0 Universal"])
    problems = make_music.check(tmp_path, "wav")
    assert any("expected 3-5" in p for p in problems)
