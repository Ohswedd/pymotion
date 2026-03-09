"""Generate example assets for PyMotion demos.

Run this script once to create sample images and audio files
that the example scripts depend on.

    python3 examples/assets/generate_assets.py
"""

from __future__ import annotations

import struct
import wave
from pathlib import Path

import numpy as np
from PIL import Image

ASSETS_DIR = Path(__file__).parent


def _generate_gradient_image(
    path: Path,
    width: int,
    height: int,
    color_a: tuple[int, int, int],
    color_b: tuple[int, int, int],
) -> None:
    """Generate a horizontal gradient image."""
    arr = np.zeros((height, width, 3), dtype=np.uint8)
    for x in range(width):
        t = x / max(width - 1, 1)
        arr[:, x, 0] = int(color_a[0] * (1 - t) + color_b[0] * t)
        arr[:, x, 1] = int(color_a[1] * (1 - t) + color_b[1] * t)
        arr[:, x, 2] = int(color_a[2] * (1 - t) + color_b[2] * t)
    Image.fromarray(arr).save(path)
    print(f"  Created {path.name}")


def _generate_photo(path: Path, width: int, height: int, base_color: tuple[int, int, int]) -> None:
    """Generate a simple photo-like image with gradients and shapes."""
    arr = np.zeros((height, width, 3), dtype=np.uint8)
    # Sky gradient (top half)
    for y in range(height // 2):
        t = y / (height // 2)
        arr[y, :, 0] = int(100 + 80 * t)
        arr[y, :, 1] = int(150 + 60 * t)
        arr[y, :, 2] = int(220 - 40 * t)
    # Ground with base color (bottom half)
    for y in range(height // 2, height):
        t = (y - height // 2) / (height // 2)
        arr[y, :, 0] = int(base_color[0] * (1 - t * 0.3))
        arr[y, :, 1] = int(base_color[1] * (1 - t * 0.3))
        arr[y, :, 2] = int(base_color[2] * (1 - t * 0.3))
    # Add a circle (sun / object)
    cx, cy, r = width // 4, height // 4, min(width, height) // 8
    yy, xx = np.ogrid[:height, :width]
    mask = (xx - cx) ** 2 + (yy - cy) ** 2 < r**2
    arr[mask] = [255, 220, 100]
    Image.fromarray(arr).save(path)
    print(f"  Created {path.name}")


def _generate_product_image(path: Path, width: int, height: int) -> None:
    """Generate a product-style image with centered object."""
    arr = np.full((height, width, 3), 240, dtype=np.uint8)
    # Center rectangle (product placeholder)
    pw, ph = width // 3, height // 2
    x0, y0 = (width - pw) // 2, (height - ph) // 2
    arr[y0 : y0 + ph, x0 : x0 + pw] = [60, 120, 200]
    # Rounded highlight
    for y in range(y0, y0 + ph // 4):
        arr[y, x0 : x0 + pw, :] = [80, 140, 220]
    Image.fromarray(arr).save(path)
    print(f"  Created {path.name}")


def _generate_logo(path: Path, size: int = 200) -> None:
    """Generate a simple logo image with transparency."""
    arr = np.zeros((size, size, 4), dtype=np.uint8)
    cx, cy = size // 2, size // 2
    yy, xx = np.ogrid[:size, :size]
    # Outer ring
    outer = ((xx - cx) ** 2 + (yy - cy) ** 2 < (size // 2 - 5) ** 2) & (
        (xx - cx) ** 2 + (yy - cy) ** 2 > (size // 3) ** 2
    )
    arr[outer] = [80, 160, 255, 255]
    # Inner dot
    inner = (xx - cx) ** 2 + (yy - cy) ** 2 < (size // 6) ** 2
    arr[inner] = [255, 200, 80, 255]
    Image.fromarray(arr, "RGBA").save(path)
    print(f"  Created {path.name}")


def _generate_wav(path: Path, duration_sec: float, freq: float, sample_rate: int = 44100) -> None:
    """Generate a simple WAV file with a sine wave and harmonics."""
    n_samples = int(duration_sec * sample_rate)
    t = np.linspace(0, duration_sec, n_samples, endpoint=False)
    # Base tone + harmonics for a richer sound
    signal = (
        0.4 * np.sin(2 * np.pi * freq * t)
        + 0.2 * np.sin(2 * np.pi * freq * 2 * t)
        + 0.1 * np.sin(2 * np.pi * freq * 3 * t)
    )
    # Fade in/out
    fade = min(int(0.05 * sample_rate), n_samples // 2)
    signal[:fade] *= np.linspace(0, 1, fade)
    signal[-fade:] *= np.linspace(1, 0, fade)
    # Normalize to 16-bit
    signal = np.clip(signal * 32767, -32768, 32767).astype(np.int16)

    with wave.open(str(path), "w") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        # Stereo: duplicate mono to both channels
        stereo = np.column_stack([signal, signal]).flatten()
        wf.writeframes(struct.pack(f"<{len(stereo)}h", *stereo))
    print(f"  Created {path.name} ({duration_sec}s)")


def _generate_music(path: Path, duration_sec: float = 10.0, sample_rate: int = 44100) -> None:
    """Generate a simple background music track with chord progression."""
    n_samples = int(duration_sec * sample_rate)
    t = np.linspace(0, duration_sec, n_samples, endpoint=False)
    signal = np.zeros(n_samples, dtype=np.float64)

    # Simple chord progression (C - Am - F - G)
    chords = [
        [261.63, 329.63, 392.00],  # C major
        [220.00, 261.63, 329.63],  # A minor
        [174.61, 220.00, 261.63],  # F major
        [196.00, 246.94, 293.66],  # G major
    ]
    beats_per_chord = duration_sec / len(chords)
    for i, chord in enumerate(chords):
        start = int(i * beats_per_chord * sample_rate)
        end = int((i + 1) * beats_per_chord * sample_rate)
        for note_freq in chord:
            signal[start:end] += 0.15 * np.sin(2 * np.pi * note_freq * t[start:end])

    # Add subtle bass
    signal += 0.2 * np.sin(2 * np.pi * 65.41 * t)

    # Fade in/out
    fade = int(0.5 * sample_rate)
    signal[:fade] *= np.linspace(0, 1, fade)
    signal[-fade:] *= np.linspace(1, 0, fade)

    signal = np.clip(signal * 32767, -32768, 32767).astype(np.int16)
    stereo = np.column_stack([signal, signal]).flatten()

    with wave.open(str(path), "w") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f"<{len(stereo)}h", *stereo))
    print(f"  Created {path.name} ({duration_sec}s music)")


def main() -> None:
    """Generate all example assets."""
    print("Generating PyMotion example assets...")
    print()

    # --- Images ---
    print("Images:")
    _generate_gradient_image(ASSETS_DIR / "bg_blue.png", 1920, 1080, (20, 20, 60), (40, 80, 160))
    _generate_gradient_image(
        ASSETS_DIR / "bg_sunset.png", 1920, 1080, (255, 100, 50), (80, 20, 100)
    )
    _generate_gradient_image(ASSETS_DIR / "bg_dark.png", 1920, 1080, (15, 15, 25), (30, 30, 50))

    _generate_photo(ASSETS_DIR / "photo_beach.png", 1920, 1080, (194, 178, 128))
    _generate_photo(ASSETS_DIR / "photo_mountains.png", 1920, 1080, (80, 120, 80))
    _generate_photo(ASSETS_DIR / "photo_city.png", 1920, 1080, (120, 120, 130))
    _generate_photo(ASSETS_DIR / "photo_sunset.png", 1920, 1080, (200, 130, 80))

    _generate_product_image(ASSETS_DIR / "product.png", 800, 800)
    _generate_logo(ASSETS_DIR / "logo.png", 200)

    # --- Audio ---
    print("\nAudio:")
    _generate_wav(ASSETS_DIR / "whoosh.wav", 0.5, 800)
    _generate_wav(ASSETS_DIR / "ding.wav", 1.0, 880)
    _generate_wav(ASSETS_DIR / "click.wav", 0.15, 1200)
    _generate_music(ASSETS_DIR / "background_music.wav", 15.0)
    _generate_music(ASSETS_DIR / "short_music.wav", 5.0)

    print("\nDone! All assets generated in:", ASSETS_DIR)


if __name__ == "__main__":
    main()
