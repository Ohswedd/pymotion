"""Download optional assets for PyMotion examples.

All v3.0 examples are fully self-contained and generate their own
visuals programmatically (ColorClip, GradientClip, ShapeClip, TextClip,
synthetic audio via NumPy).  No external downloads are required.

This script is kept for backwards compatibility and to generate optional
audio assets that can be swapped into examples for richer demos.

Run:
    python examples/download_assets.py
"""

from __future__ import annotations

import math
import struct
from pathlib import Path

import structlog

logger = structlog.get_logger()

ASSETS_DIR = Path(__file__).parent / "assets"


def _generate_wav(dest: Path, duration: float, freq: float, sample_rate: int = 44100) -> None:
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

    raw = struct.pack(f"<{n_samples}h", *samples)

    with open(dest, "wb") as f:
        data_size = n_samples * 2
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

    logger.info("asset_generated", file=dest.name, duration=duration, freq=freq)


def _generate_music_wav(dest: Path, duration: float, sample_rate: int = 44100) -> None:
    """Generate a simple ambient background music WAV (chord progression)."""
    if dest.exists():
        logger.info("asset_skip", file=dest.name, reason="already exists")
        return

    n_samples = int(sample_rate * duration)
    chords = [
        [220.0, 261.63, 329.63],  # Am
        [174.61, 220.0, 261.63],  # F
        [261.63, 329.63, 392.0],  # C
        [196.0, 246.94, 293.66],  # G
    ]
    chord_dur = duration / len(chords)

    samples = []
    for i in range(n_samples):
        t = i / sample_rate
        chord_idx = min(int(t / chord_dur), len(chords) - 1)
        freqs = chords[chord_idx]

        val = 0.0
        for freq in freqs:
            val += 0.12 * math.sin(2 * math.pi * freq * t)

        env = min(1.0, t / 0.5) * min(1.0, (duration - t) / 0.5)
        samples.append(int(val * env * 32767))

    raw = struct.pack(f"<{n_samples}h", *samples)

    with open(dest, "wb") as f:
        data_size = n_samples * 2
        f.write(b"RIFF")
        f.write(struct.pack("<I", 36 + data_size))
        f.write(b"WAVE")
        f.write(b"fmt ")
        f.write(struct.pack("<I", 16))
        f.write(struct.pack("<H", 1))
        f.write(struct.pack("<H", 1))
        f.write(struct.pack("<I", sample_rate))
        f.write(struct.pack("<I", sample_rate * 2))
        f.write(struct.pack("<H", 2))
        f.write(struct.pack("<H", 16))
        f.write(b"data")
        f.write(struct.pack("<I", data_size))
        f.write(raw)

    logger.info("asset_generated", file=dest.name, duration=duration, kind="ambient_music")


def main() -> None:
    """Generate optional audio assets for examples."""
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("generating_assets", dest=str(ASSETS_DIR))

    # Audio assets (generated programmatically — no network required)
    _generate_wav(ASSETS_DIR / "whoosh.wav", 0.5, 800)
    _generate_wav(ASSETS_DIR / "ding.wav", 1.0, 1200)
    _generate_wav(ASSETS_DIR / "click.wav", 0.15, 2000)
    _generate_wav(ASSETS_DIR / "deep_bass.wav", 2.0, 80)
    _generate_music_wav(ASSETS_DIR / "ambient_music.wav", 15.0)
    _generate_music_wav(ASSETS_DIR / "background_loop.wav", 10.0)

    total = len(list(ASSETS_DIR.iterdir()))
    logger.info("assets_complete", total_files=total)


if __name__ == "__main__":
    main()
