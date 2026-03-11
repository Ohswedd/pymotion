"""Download free stock assets for PyMotion examples.

Uses picsum.photos for stock photography (CC0/Unsplash license),
and generates simple WAV audio files programmatically for sound effects.

Run this script once before running the examples:
    python examples/download_assets.py
"""

from __future__ import annotations

import math
import ssl
import struct
import urllib.request
from pathlib import Path

ASSETS_DIR = Path(__file__).parent / "assets"


def _download(url: str, dest: Path) -> None:
    """Download a URL to a local file (with SSL workaround for macOS)."""
    if dest.exists():
        print(f"  [skip] {dest.name} already exists")
        return

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})  # noqa: S310
    with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:  # noqa: S310
        data = resp.read()
    dest.write_bytes(data)
    print(f"  [ok]   {dest.name} ({len(data):,} bytes)")


def _generate_wav(dest: Path, duration: float, freq: float, sample_rate: int = 44100) -> None:
    """Generate a simple sine-wave WAV file."""
    if dest.exists():
        print(f"  [skip] {dest.name} already exists")
        return

    n_samples = int(sample_rate * duration)
    samples = []
    for i in range(n_samples):
        t = i / sample_rate
        # Fade envelope: fade in 0.05s, fade out 0.1s
        env = min(1.0, t / 0.05) * min(1.0, (duration - t) / 0.1)
        val = env * 0.4 * math.sin(2 * math.pi * freq * t)
        samples.append(int(val * 32767))

    raw = struct.pack(f"<{n_samples}h", *samples)

    # Write WAV header
    with open(dest, "wb") as f:
        data_size = n_samples * 2
        f.write(b"RIFF")
        f.write(struct.pack("<I", 36 + data_size))
        f.write(b"WAVE")
        f.write(b"fmt ")
        f.write(struct.pack("<I", 16))  # chunk size
        f.write(struct.pack("<H", 1))  # PCM
        f.write(struct.pack("<H", 1))  # mono
        f.write(struct.pack("<I", sample_rate))
        f.write(struct.pack("<I", sample_rate * 2))  # byte rate
        f.write(struct.pack("<H", 2))  # block align
        f.write(struct.pack("<H", 16))  # bits per sample
        f.write(b"data")
        f.write(struct.pack("<I", data_size))
        f.write(raw)

    print(f"  [ok]   {dest.name} ({duration}s, {freq}Hz)")


def _generate_music_wav(dest: Path, duration: float, sample_rate: int = 44100) -> None:
    """Generate a simple ambient background music WAV (chord progression)."""
    if dest.exists():
        print(f"  [skip] {dest.name} already exists")
        return

    n_samples = int(sample_rate * duration)
    # Simple chord progression: Am - F - C - G
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

        # Global envelope
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

    print(f"  [ok]   {dest.name} ({duration}s, ambient music)")


def main() -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    print("Downloading stock assets for PyMotion examples...\n")

    # ── Real Estate photos (specific picsum IDs for consistent architecture images) ──
    print("[Real Estate]")
    re_images = {
        "house_exterior.jpg": "https://picsum.photos/id/49/1920/1080",  # house/building
        "house_interior.jpg": "https://picsum.photos/id/164/1920/1080",  # interior design
        "house_kitchen.jpg": "https://picsum.photos/id/225/1920/1080",  # kitchen/modern
        "house_garden.jpg": "https://picsum.photos/id/28/1920/1080",  # garden/outdoor
    }
    for name, url in re_images.items():
        _download(url, ASSETS_DIR / name)

    # ── Tech Review assets ──
    print("\n[Tech Review]")
    tech_images = {
        "tech_device.jpg": "https://picsum.photos/id/0/1920/1080",  # laptop
        "tech_workspace.jpg": "https://picsum.photos/id/180/1920/1080",  # desk setup
        "tech_circuit.jpg": "https://picsum.photos/id/201/1920/1080",  # abstract/tech
    }
    for name, url in tech_images.items():
        _download(url, ASSETS_DIR / name)

    # ── Fitness/Gym assets ──
    print("\n[Fitness]")
    fitness_images = {
        "fitness_gym.jpg": "https://picsum.photos/id/116/1920/1080",  # nature/energy
        "fitness_running.jpg": "https://picsum.photos/id/136/1920/1080",  # motion/energy
        "fitness_weights.jpg": "https://picsum.photos/id/160/1920/1080",  # strong/bold
    }
    for name, url in fitness_images.items():
        _download(url, ASSETS_DIR / name)

    # ── Restaurant/Food assets ──
    print("\n[Restaurant]")
    food_images = {
        "food_plate.jpg": "https://picsum.photos/id/292/1920/1080",  # food/table
        "food_table.jpg": "https://picsum.photos/id/312/1920/1080",  # dining
        "food_dessert.jpg": "https://picsum.photos/id/326/1920/1080",  # food
        "food_ambiance.jpg": "https://picsum.photos/id/431/1920/1080",  # restaurant
    }
    for name, url in food_images.items():
        _download(url, ASSETS_DIR / name)

    # ── Educational assets ──
    print("\n[Educational]")
    edu_images = {
        "edu_books.jpg": "https://picsum.photos/id/24/1920/1080",  # books
        "edu_classroom.jpg": "https://picsum.photos/id/180/1920/1080",  # workspace
        "edu_abstract.jpg": "https://picsum.photos/id/305/1920/1080",  # abstract pattern
    }
    for name, url in edu_images.items():
        _download(url, ASSETS_DIR / name)

    # ── Audio assets (generated programmatically) ──
    print("\n[Audio]")
    _generate_wav(ASSETS_DIR / "whoosh.wav", 0.5, 800)
    _generate_wav(ASSETS_DIR / "ding.wav", 1.0, 1200)
    _generate_wav(ASSETS_DIR / "click.wav", 0.15, 2000)
    _generate_wav(ASSETS_DIR / "deep_bass.wav", 2.0, 80)
    _generate_music_wav(ASSETS_DIR / "ambient_music.wav", 15.0)
    _generate_music_wav(ASSETS_DIR / "background_loop.wav", 10.0)

    print(f"\nAll assets downloaded to {ASSETS_DIR}/")
    print(f"Total files: {len(list(ASSETS_DIR.iterdir()))}")


if __name__ == "__main__":
    main()
