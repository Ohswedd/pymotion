"""Download stock assets for PyMotion examples.

Uses picsum.photos for royalty-free stock photography and generates
audio assets programmatically (sine-wave music, SFX).

Run this script once before running the examples:
    python examples/download_assets.py
"""

from __future__ import annotations

import math
import ssl
import struct
import urllib.request
from pathlib import Path

import structlog

logger = structlog.get_logger()

ASSETS_DIR = Path(__file__).parent / "assets"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _download(url: str, dest: Path) -> None:
    """Download a URL to a local file (with SSL workaround for macOS)."""
    if dest.exists():
        logger.info("asset_skip", file=dest.name, reason="already exists")
        return

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE  # noqa: S501

    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})  # noqa: S310
    with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:  # noqa: S310
        data = resp.read()
    dest.write_bytes(data)
    logger.info("asset_downloaded", file=dest.name, bytes=len(data))


def _generate_wav(
    dest: Path,
    duration: float,
    freq: float,
    sample_rate: int = 44100,
) -> None:
    """Generate a simple sine-wave WAV file."""
    if dest.exists():
        logger.info("asset_skip", file=dest.name, reason="already exists")
        return

    n_samples = int(sample_rate * duration)
    samples = []
    for i in range(n_samples):
        t = i / sample_rate
        env = min(1.0, t / 0.05) * min(1.0, (duration - t) / 0.1)
        val = env * 0.4 * math.sin(2 * math.pi * freq * t)
        samples.append(int(val * 32767))

    _write_wav_mono(dest, samples, sample_rate)
    logger.info("asset_generated", file=dest.name, duration=duration, freq=freq)


def _generate_music(
    dest: Path,
    duration: float,
    bpm: float = 120.0,
    style: str = "corporate",
    sample_rate: int = 44100,
) -> None:
    """Generate a multi-layer background music track.

    Styles: corporate, electronic, cinematic, lofi, upbeat.
    """
    if dest.exists():
        logger.info("asset_skip", file=dest.name, reason="already exists")
        return

    n_samples = int(sample_rate * duration)
    beat_dur = 60.0 / bpm
    samples = [0.0] * n_samples

    if style == "corporate":
        # Warm pad + light bass + gentle rhythm
        chords = [
            [261.63, 329.63, 392.0],  # C major
            [220.0, 277.18, 329.63],  # Am
            [174.61, 220.0, 261.63],  # F
            [196.0, 246.94, 293.66],  # G
        ]
        chord_dur = beat_dur * 4
        for i in range(n_samples):
            t = i / sample_rate
            ci = int(t / chord_dur) % len(chords)
            val = 0.0
            for f in chords[ci]:
                val += 0.08 * math.sin(2 * math.pi * f * t)
            # Sub bass
            val += 0.06 * math.sin(2 * math.pi * chords[ci][0] * 0.5 * t)
            # Light hi-hat
            beat_pos = (t % beat_dur) / beat_dur
            if beat_pos < 0.05:
                val += 0.03 * math.sin(2 * math.pi * 8000 * t) * (1.0 - beat_pos / 0.05)
            samples[i] = val

    elif style == "electronic":
        # Synth arpeggios + bass pulse + kick
        notes = [261.63, 329.63, 392.0, 523.25, 392.0, 329.63]
        for i in range(n_samples):
            t = i / sample_rate
            note_dur = beat_dur / 2
            ni = int(t / note_dur) % len(notes)
            note_t = (t % note_dur) / note_dur
            env = max(0, 1.0 - note_t * 2)
            val = env * 0.1 * math.sin(2 * math.pi * notes[ni] * t)
            # Sub bass pulse
            bass_env = 1.0 if (t % beat_dur) < beat_dur * 0.3 else 0.3
            val += 0.08 * math.sin(2 * math.pi * 55 * t) * bass_env
            # Kick
            kick_t = t % beat_dur
            if kick_t < 0.08:
                kick_freq = 150 * (1 - kick_t / 0.08) + 40
                val += 0.12 * math.sin(2 * math.pi * kick_freq * kick_t) * (1 - kick_t / 0.08)
            samples[i] = val

    elif style == "cinematic":
        # Low strings + brass swells + timpani hits
        drone_freq = 65.41  # C2
        for i in range(n_samples):
            t = i / sample_rate
            progress = t / duration
            # Drone
            val = 0.06 * math.sin(2 * math.pi * drone_freq * t)
            val += 0.04 * math.sin(2 * math.pi * drone_freq * 1.5 * t)
            # Slow brass swell every 8 beats
            swell_dur = beat_dur * 8
            swell_pos = (t % swell_dur) / swell_dur
            swell_env = swell_pos * swell_pos * (1 - swell_pos)
            val += swell_env * 0.1 * math.sin(2 * math.pi * 130.81 * t)
            # Building intensity
            val *= 0.5 + 0.5 * progress
            # Timpani every 4 beats
            timp_t = t % (beat_dur * 4)
            if timp_t < 0.15:
                val += 0.1 * math.sin(2 * math.pi * 80 * timp_t) * (1 - timp_t / 0.15)
            samples[i] = val

    elif style == "lofi":
        # Mellow piano + vinyl crackle + soft bass
        chords = [
            [261.63, 311.13, 392.0],  # Cm
            [233.08, 293.66, 349.23],  # Bb
            [207.65, 261.63, 311.13],  # Ab
            [220.0, 261.63, 329.63],  # Am/soft
        ]
        chord_dur = beat_dur * 4
        for i in range(n_samples):
            t = i / sample_rate
            ci = int(t / chord_dur) % len(chords)
            val = 0.0
            for j, f in enumerate(chords[ci]):
                # Soft piano-like decay
                note_t = (t % (beat_dur * 2)) / (beat_dur * 2)
                decay = math.exp(-note_t * 3)
                val += decay * 0.06 * math.sin(2 * math.pi * f * t + j * 0.3)
            # Soft bass
            val += 0.05 * math.sin(2 * math.pi * chords[ci][0] * 0.5 * t)
            samples[i] = val

    else:  # upbeat
        # Funky bass + clap + bright chords
        notes = [130.81, 164.81, 196.0, 164.81]
        for i in range(n_samples):
            t = i / sample_rate
            ni = int(t / beat_dur) % len(notes)
            val = 0.0
            # Funky bass
            bass_t = (t % beat_dur) / beat_dur
            if bass_t < 0.4:
                val += 0.1 * math.sin(2 * math.pi * notes[ni] * t) * (1 - bass_t / 0.4)
            # Bright chord stabs on beats 2 and 4
            beat_num = int(t / beat_dur) % 4
            if beat_num in (1, 3):
                stab_t = (t % beat_dur) / beat_dur
                if stab_t < 0.15:
                    for f in [523.25, 659.26, 783.99]:
                        val += 0.04 * math.sin(2 * math.pi * f * t) * (1 - stab_t / 0.15)
            # Clap on 2 and 4
            if beat_num in (1, 3) and (t % beat_dur) < 0.02:
                val += 0.08 * math.sin(2 * math.pi * 3000 * t)
            samples[i] = val

    # Global envelope and normalization
    peak = max(abs(s) for s in samples) or 1.0
    int_samples = []
    for i, s in enumerate(samples):
        t = i / sample_rate
        env = min(1.0, t / 0.5) * min(1.0, (duration - t) / 0.5)
        int_samples.append(int(s / peak * env * 28000))

    _write_wav_mono(dest, int_samples, sample_rate)
    logger.info("asset_generated", file=dest.name, duration=duration, style=style, bpm=bpm)


def _write_wav_mono(dest: Path, samples: list[int], sample_rate: int) -> None:
    """Write a list of 16-bit mono samples as a WAV file."""
    n_samples = len(samples)
    raw = struct.pack(f"<{n_samples}h", *[max(-32767, min(32767, s)) for s in samples])
    data_size = n_samples * 2
    with open(dest, "wb") as f:
        f.write(b"RIFF")
        f.write(struct.pack("<I", 36 + data_size))
        f.write(b"WAVE")
        f.write(b"fmt ")
        f.write(struct.pack("<I", 16))
        f.write(struct.pack("<H", 1))  # PCM
        f.write(struct.pack("<H", 1))  # mono
        f.write(struct.pack("<I", sample_rate))
        f.write(struct.pack("<I", sample_rate * 2))
        f.write(struct.pack("<H", 2))
        f.write(struct.pack("<H", 16))
        f.write(b"data")
        f.write(struct.pack("<I", data_size))
        f.write(raw)


# ---------------------------------------------------------------------------
# Asset manifest per example
# ---------------------------------------------------------------------------


def main() -> None:
    """Download all stock assets for PyMotion examples."""
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("downloading_assets", dest=str(ASSETS_DIR))

    # ── 01: Product Launch ─────────────────────────────────────────────
    logger.info("section", example="01_product_launch")
    _download("https://picsum.photos/id/0/1920/1080", ASSETS_DIR / "product_hero.jpg")
    _download("https://picsum.photos/id/201/800/600", ASSETS_DIR / "product_feature_1.jpg")
    _download("https://picsum.photos/id/180/800/600", ASSETS_DIR / "product_feature_2.jpg")
    _download("https://picsum.photos/id/160/800/600", ASSETS_DIR / "product_feature_3.jpg")
    _generate_music(ASSETS_DIR / "music_corporate.wav", 95.0, bpm=110, style="corporate")

    # ── 02: Social Reel ────────────────────────────────────────────────
    logger.info("section", example="02_social_reel")
    _download("https://picsum.photos/id/119/1080/1920", ASSETS_DIR / "reel_hero.jpg")
    _download("https://picsum.photos/id/96/1080/1080", ASSETS_DIR / "reel_problem.jpg")
    _download("https://picsum.photos/id/2/1080/1080", ASSETS_DIR / "reel_solution.jpg")
    _generate_music(ASSETS_DIR / "music_upbeat.wav", 65.0, bpm=140, style="upbeat")
    _generate_wav(ASSETS_DIR / "sfx_whoosh.wav", 0.4, 800)
    _generate_wav(ASSETS_DIR / "sfx_ding.wav", 0.8, 1200)

    # ── 03: Data Story ─────────────────────────────────────────────────
    logger.info("section", example="03_data_story")
    _download("https://picsum.photos/id/1073/1920/1080", ASSETS_DIR / "data_bg.jpg")
    _download("https://picsum.photos/id/366/1920/1080", ASSETS_DIR / "data_conclusion.jpg")
    _generate_music(ASSETS_DIR / "music_documentary.wav", 185.0, bpm=100, style="corporate")

    # ── 04: Tutorial Screencast ────────────────────────────────────────
    logger.info("section", example="04_tutorial_screencast")
    _download("https://picsum.photos/id/0/1920/1080", ASSETS_DIR / "tutorial_screen_1.jpg")
    _download("https://picsum.photos/id/180/1920/1080", ASSETS_DIR / "tutorial_screen_2.jpg")
    _generate_music(ASSETS_DIR / "music_lofi.wav", 125.0, bpm=85, style="lofi")
    _generate_wav(ASSETS_DIR / "sfx_click.wav", 0.15, 2000)
    _generate_wav(ASSETS_DIR / "sfx_success.wav", 1.0, 880)

    # ── 05: Music Video ────────────────────────────────────────────────
    logger.info("section", example="05_music_video")
    _download("https://picsum.photos/id/1025/1920/1080", ASSETS_DIR / "mv_bg_1.jpg")
    _download("https://picsum.photos/id/984/1920/1080", ASSETS_DIR / "mv_bg_2.jpg")
    _download("https://picsum.photos/id/110/1920/1080", ASSETS_DIR / "mv_bg_3.jpg")
    _generate_music(ASSETS_DIR / "music_electronic.wav", 125.0, bpm=128, style="electronic")

    # ── 06: Cinematic Trailer ──────────────────────────────────────────
    logger.info("section", example="06_cinematic_trailer")
    _download("https://picsum.photos/id/1015/1920/1080", ASSETS_DIR / "cine_landscape_1.jpg")
    _download("https://picsum.photos/id/1036/1920/1080", ASSETS_DIR / "cine_landscape_2.jpg")
    _download("https://picsum.photos/id/1039/1920/1080", ASSETS_DIR / "cine_landscape_3.jpg")
    _download("https://picsum.photos/id/1044/1920/1080", ASSETS_DIR / "cine_landscape_4.jpg")
    _generate_music(ASSETS_DIR / "music_cinematic.wav", 95.0, bpm=70, style="cinematic")

    # ── 07: E-Commerce Batch ───────────────────────────────────────────
    logger.info("section", example="07_ecommerce_batch")
    _download("https://picsum.photos/id/26/1000/1000", ASSETS_DIR / "product_headphones.jpg")
    _download("https://picsum.photos/id/175/1000/1000", ASSETS_DIR / "product_watch.jpg")
    _download("https://picsum.photos/id/225/1000/1000", ASSETS_DIR / "product_speaker.jpg")
    _download("https://picsum.photos/id/60/1000/1000", ASSETS_DIR / "product_keyboard.jpg")
    _generate_music(ASSETS_DIR / "music_ecommerce.wav", 20.0, bpm=130, style="upbeat")

    # ── 08: Composite VFX ──────────────────────────────────────────────
    logger.info("section", example="08_composite_vfx")
    _download("https://picsum.photos/id/1062/1920/1080", ASSETS_DIR / "vfx_plate.jpg")
    _download("https://picsum.photos/id/1067/1920/1080", ASSETS_DIR / "vfx_texture.jpg")
    _generate_music(ASSETS_DIR / "music_tech.wav", 65.0, bpm=120, style="electronic")

    total = len(list(ASSETS_DIR.iterdir()))
    logger.info("assets_complete", total_files=total)


if __name__ == "__main__":
    main()
