"""Download and generate all assets for PyMotion v3.2 examples.

Single source of truth for every asset used by every example.
Uses only stdlib (urllib.request, hashlib, zlib, struct, subprocess).

Run once before running examples:
    python examples/download_assets.py
"""

from __future__ import annotations

import math
import struct
import subprocess
import sys
import zlib
from pathlib import Path
from urllib.request import Request, urlopen

ASSETS_DIR = Path(__file__).parent / "assets"

# ---------------------------------------------------------------------------
# Asset manifest: (filename, type, source/params)
# ---------------------------------------------------------------------------

FONT_URLS: dict[str, str] = {
    "Inter-Regular.ttf": (
        "https://fonts.gstatic.com/s/inter/v20/"
        "UcCO3FwrK3iLTeHuS_nVMrMxCp50SjIw2boKoduKmMEVuLyfMZg.ttf"
    ),
    "Inter-Bold.ttf": (
        "https://fonts.gstatic.com/s/inter/v20/"
        "UcCO3FwrK3iLTeHuS_nVMrMxCp50SjIw2boKoduKmMEVuFuYMZg.ttf"
    ),
    "Inter-Light.ttf": (
        "https://fonts.gstatic.com/s/inter/v20/"
        "UcCO3FwrK3iLTeHuS_nVMrMxCp50SjIw2boKoduKmMEVuOKfMZg.ttf"
    ),
    "Montserrat-Bold.ttf": (
        "https://fonts.gstatic.com/s/montserrat/v31/JTUHjIg1_i6t8kCHKm4532VJOt5-QNFgpCuM70w-.ttf"
    ),
}

IMAGE_URLS: dict[str, str] = {
    # picsum.photos with specific IDs for stability (JPEG)
    "product_hero.jpg": "https://picsum.photos/id/0/1200/1200",
    "product_a.jpg": "https://picsum.photos/id/26/1000/1000",
    "product_b.jpg": "https://picsum.photos/id/175/1000/1000",
    "product_c.jpg": "https://picsum.photos/id/225/1000/1000",
}

# Expected minimum sizes for downloaded files (bytes)
MIN_SIZES: dict[str, int] = {
    ".ttf": 10000,
    ".jpg": 5000,
    ".mp4": 10000,
    ".mp3": 10000,
    ".glb": 100,
}

# Magic bytes for file type verification
MAGIC_BYTES: dict[str, bytes] = {
    ".ttf": b"\x00\x01\x00\x00",  # TrueType
    ".jpg": b"\xff\xd8\xff",  # JPEG
    ".png": b"\x89PNG",  # PNG
    ".wav": b"RIFF",  # WAV
    ".mp4": b"\x00\x00\x00",  # MP4 (ftyp box, first byte varies)
    ".glb": b"glTF",  # GLB
    ".mp3": b"\xff\xfb",  # MP3 frame sync (no ID3)
}

_downloaded_count = 0
_total_bytes = 0


# ---------------------------------------------------------------------------
# Download helper
# ---------------------------------------------------------------------------


def _download(url: str, dest: Path, expected_min_size: int = 0) -> bool:
    """Download a URL to a local file. Skip if exists and size OK."""
    global _downloaded_count, _total_bytes

    if dest.exists() and dest.stat().st_size > max(expected_min_size, 100):
        size_mb = dest.stat().st_size / (1024 * 1024)
        print(f"  \u2713 {dest.name} ({size_mb:.1f} MB) [cached]")
        _total_bytes += dest.stat().st_size
        _downloaded_count += 1
        return True

    try:
        req = Request(url, headers={"User-Agent": "PyMotion-AssetDownloader/3.2"})  # noqa: S310
        import ssl

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE  # noqa: S501
        with urlopen(req, context=ctx, timeout=60) as resp:  # noqa: S310
            data = resp.read()

        if len(data) < max(expected_min_size, 100):
            print(f"  \u2717 {dest.name} — too small ({len(data)} bytes)")
            return False

        dest.write_bytes(data)
        size_mb = len(data) / (1024 * 1024)
        print(f"  \u2713 {dest.name} ({size_mb:.2f} MB)")
        _total_bytes += len(data)
        _downloaded_count += 1
        return True

    except Exception as e:
        print(f"  \u2717 {dest.name} — download failed: {e}")
        return False


def _verify_file(path: Path) -> bool:
    """Verify file: non-zero size, correct magic bytes for type."""
    if not path.exists():
        return False
    if path.stat().st_size == 0:
        return False

    ext = path.suffix.lower()
    expected_magic = MAGIC_BYTES.get(ext)
    if expected_magic:
        with open(path, "rb") as f:
            header = f.read(max(len(expected_magic), 8))
        if ext == ".mp4":
            # MP4 ftyp box: bytes 4-8 should be 'ftyp'
            if len(header) >= 8 and header[4:8] == b"ftyp":
                return True
            return False
        if not header.startswith(expected_magic):
            # MP3 can also start with ID3 tag
            if ext == ".mp3" and header[:3] == b"ID3":
                return True
            return False
    return True


# ---------------------------------------------------------------------------
# PNG generation (pure Python via zlib)
# ---------------------------------------------------------------------------


def _make_png(
    width: int,
    height: int,
    pixel_fn: object,
) -> bytes:
    """Generate a PNG image from a pixel function.

    pixel_fn(x, y, w, h) -> (r, g, b, a) each 0-255.
    """
    rows = []
    for y in range(height):
        row = bytearray()
        row.append(0)  # filter: None
        for x in range(width):
            r, g, b, a = pixel_fn(x, y, width, height)  # type: ignore[operator]
            row.extend([r, g, b, a])
        rows.append(bytes(row))

    raw = b"".join(rows)
    compressed = zlib.compress(raw, 6)

    def _chunk(chunk_type: bytes, data: bytes) -> bytes:
        c = chunk_type + data
        crc = zlib.crc32(c) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + c + struct.pack(">I", crc)

    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", ihdr_data)
    png += _chunk(b"IDAT", compressed)
    png += _chunk(b"IEND", b"")
    return png


def _generate_product_png(dest: Path, seed: int, label: str) -> None:
    """Generate a product-style image with colored shape on neutral bg."""
    global _downloaded_count, _total_bytes

    if dest.exists() and dest.stat().st_size > 1000:
        size_mb = dest.stat().st_size / (1024 * 1024)
        print(f"  \u2713 {dest.name} ({size_mb:.1f} MB) [cached]")
        _total_bytes += dest.stat().st_size
        _downloaded_count += 1
        return

    # Deterministic colors from seed
    hue = (seed * 137) % 360
    r0 = int(128 + 80 * math.cos(math.radians(hue)))
    g0 = int(128 + 80 * math.cos(math.radians(hue - 120)))
    b0 = int(128 + 80 * math.cos(math.radians(hue - 240)))

    def pixel_fn(x: int, y: int, w: int, h: int) -> tuple[int, int, int, int]:
        # Neutral light gray background
        bg_r, bg_g, bg_b = 240, 240, 242
        # Centered rounded rectangle product shape
        cx, cy = w / 2, h / 2
        rx, ry = w * 0.35, h * 0.35
        dx = max(0, abs(x - cx) - rx + 20) / 20
        dy = max(0, abs(y - cy) - ry + 20) / 20
        d = math.sqrt(dx * dx + dy * dy)
        if d < 1.0:
            # Inside product shape — gradient
            t = (y - (cy - ry)) / (2 * ry) if ry > 0 else 0.5
            t = max(0.0, min(1.0, t))
            r = int(r0 * (1 - t * 0.3))
            g = int(g0 * (1 - t * 0.3))
            b = int(b0 * (1 - t * 0.3))
            return (min(255, r), min(255, g), min(255, b), 255)
        return (bg_r, bg_g, bg_b, 255)

    size = 512 if "logo" in str(dest).lower() or "icon" in str(dest).lower() else 600
    data = _make_png(size, size, pixel_fn)
    dest.write_bytes(data)
    size_mb = len(data) / (1024 * 1024)
    print(f"  \u2713 {dest.name} ({size_mb:.2f} MB) [generated]")
    _total_bytes += len(data)
    _downloaded_count += 1


def _generate_logo_png(dest: Path, size: int = 512) -> None:
    """Generate a logo with transparency (circle + inner shape)."""
    global _downloaded_count, _total_bytes

    if dest.exists() and dest.stat().st_size > 500:
        size_mb = dest.stat().st_size / (1024 * 1024)
        print(f"  \u2713 {dest.name} ({size_mb:.1f} MB) [cached]")
        _total_bytes += dest.stat().st_size
        _downloaded_count += 1
        return

    def pixel_fn(x: int, y: int, w: int, h: int) -> tuple[int, int, int, int]:
        cx, cy = w / 2, h / 2
        r = w * 0.42
        dx, dy = x - cx, y - cy
        dist = math.sqrt(dx * dx + dy * dy)
        if dist > r:
            return (0, 0, 0, 0)  # transparent outside
        # Blue-to-purple gradient circle
        t = dist / r
        rr = int(40 + 80 * t)
        gg = int(100 - 40 * t)
        bb = int(220 - 20 * t)
        # Inner triangle cutout
        tri_h = r * 0.6
        if dy > -r * 0.3 and dy < r * 0.3:
            tri_w = tri_h * 0.5 * (1 - (dy + r * 0.3) / tri_h)
            if abs(dx) < tri_w:
                return (255, 255, 255, 240)  # white inner mark
        return (rr, gg, bb, 255)

    data = _make_png(size, size, pixel_fn)
    dest.write_bytes(data)
    size_mb = len(data) / (1024 * 1024)
    print(f"  \u2713 {dest.name} ({size_mb:.2f} MB) [generated]")
    _total_bytes += len(data)
    _downloaded_count += 1


# ---------------------------------------------------------------------------
# WAV generation
# ---------------------------------------------------------------------------


def _write_wav(dest: Path, samples: list[int], sample_rate: int = 44100) -> None:
    """Write 16-bit mono WAV file."""
    n = len(samples)
    clamped = [max(-32767, min(32767, s)) for s in samples]
    raw = struct.pack(f"<{n}h", *clamped)
    data_size = n * 2
    with open(dest, "wb") as f:
        f.write(b"RIFF")
        f.write(struct.pack("<I", 36 + data_size))
        f.write(b"WAVE")
        f.write(b"fmt ")
        f.write(struct.pack("<I", 16))
        f.write(struct.pack("<HHIIHH", 1, 1, sample_rate, sample_rate * 2, 2, 16))
        f.write(b"data")
        f.write(struct.pack("<I", data_size))
        f.write(raw)


def _generate_music(dest: Path, duration: float, bpm: float, style: str) -> None:
    """Generate multi-layer background music WAV."""
    global _downloaded_count, _total_bytes

    if dest.exists() and dest.stat().st_size > 1000:
        size_mb = dest.stat().st_size / (1024 * 1024)
        print(f"  \u2713 {dest.name} ({size_mb:.1f} MB) [cached]")
        _total_bytes += dest.stat().st_size
        _downloaded_count += 1
        return

    sr = 44100
    n = int(sr * duration)
    beat_dur = 60.0 / bpm
    samples = [0.0] * n

    if style == "upbeat":
        notes = [130.81, 164.81, 196.0, 164.81]
        for i in range(n):
            t = i / sr
            ni = int(t / beat_dur) % len(notes)
            val = 0.0
            bass_t = (t % beat_dur) / beat_dur
            if bass_t < 0.4:
                val += 0.1 * math.sin(2 * math.pi * notes[ni] * t) * (1 - bass_t / 0.4)
            beat_num = int(t / beat_dur) % 4
            if beat_num in (1, 3):
                stab_t = (t % beat_dur) / beat_dur
                if stab_t < 0.15:
                    for f in [523.25, 659.26, 783.99]:
                        val += 0.04 * math.sin(2 * math.pi * f * t) * (1 - stab_t / 0.15)
            samples[i] = val

    elif style == "cinematic":
        drone = 65.41
        for i in range(n):
            t = i / sr
            progress = t / duration
            val = 0.06 * math.sin(2 * math.pi * drone * t)
            val += 0.04 * math.sin(2 * math.pi * drone * 1.5 * t)
            swell_dur = beat_dur * 8
            swell_pos = (t % swell_dur) / swell_dur
            swell_env = swell_pos * swell_pos * (1 - swell_pos)
            val += swell_env * 0.1 * math.sin(2 * math.pi * 130.81 * t)
            val *= 0.5 + 0.5 * progress
            timp_t = t % (beat_dur * 4)
            if timp_t < 0.15:
                val += 0.1 * math.sin(2 * math.pi * 80 * timp_t) * (1 - timp_t / 0.15)
            samples[i] = val

    else:  # ambient
        chords = [
            [261.63, 329.63, 392.0],
            [220.0, 277.18, 329.63],
            [174.61, 220.0, 261.63],
            [196.0, 246.94, 293.66],
        ]
        chord_dur = beat_dur * 4
        for i in range(n):
            t = i / sr
            ci = int(t / chord_dur) % len(chords)
            val = 0.0
            for f in chords[ci]:
                val += 0.07 * math.sin(2 * math.pi * f * t)
            val += 0.05 * math.sin(2 * math.pi * chords[ci][0] * 0.5 * t)
            samples[i] = val

    # Normalize and envelope
    peak = max((abs(s) for s in samples), default=1.0) or 1.0
    int_samples = []
    for i, s in enumerate(samples):
        t = i / sr
        env = min(1.0, t / 0.5) * min(1.0, (duration - t) / 0.5)
        int_samples.append(int(s / peak * env * 28000))

    _write_wav(dest, int_samples, sr)
    size_mb = dest.stat().st_size / (1024 * 1024)
    print(f"  \u2713 {dest.name} ({size_mb:.2f} MB) [generated]")
    _total_bytes += dest.stat().st_size
    _downloaded_count += 1


def _generate_sfx(dest: Path, duration: float, freq: float, style: str = "tone") -> None:
    """Generate a sound effect WAV."""
    global _downloaded_count, _total_bytes

    if dest.exists() and dest.stat().st_size > 500:
        size_mb = dest.stat().st_size / (1024 * 1024)
        print(f"  \u2713 {dest.name} ({size_mb:.1f} MB) [cached]")
        _total_bytes += dest.stat().st_size
        _downloaded_count += 1
        return

    sr = 44100
    n_samples = int(sr * duration)
    samples = []

    for i in range(n_samples):
        t = i / sr
        env = min(1.0, t / 0.01) * max(0.0, 1.0 - t / duration)

        if style == "impact":
            # Descending frequency impact
            f = freq * math.exp(-t * 8)
            val = env * 0.5 * math.sin(2 * math.pi * f * t)
            # Add noise burst
            noise = math.sin(t * 12345.6789) * math.sin(t * 98765.4321)
            val += env * env * 0.3 * noise
        elif style == "whoosh":
            # Rising then falling frequency
            peak_t = duration * 0.4
            if t < peak_t:
                f = freq * 0.5 + freq * (t / peak_t)
            else:
                f = freq * 1.5 - freq * ((t - peak_t) / (duration - peak_t))
            val = env * 0.4 * math.sin(2 * math.pi * f * t)
        elif style == "ir":
            # Impulse response: sharp attack + exponential decay with reflections
            decay = math.exp(-t * 3)
            val = (
                decay
                * 0.3
                * (
                    math.sin(2 * math.pi * 200 * t)
                    + 0.5 * math.sin(2 * math.pi * 350 * t + 1.2)
                    + 0.3 * math.sin(2 * math.pi * 500 * t + 2.4)
                )
            )
            # Sparse reflections
            for delay in [0.02, 0.05, 0.08, 0.13, 0.21]:
                if t > delay:
                    rt = t - delay
                    val += math.exp(-rt * 5) * 0.1 * math.sin(2 * math.pi * 250 * rt)
        else:  # tone
            val = env * 0.4 * math.sin(2 * math.pi * freq * t)

        samples.append(int(val * 32767))

    _write_wav(dest, samples, sr)
    size_mb = dest.stat().st_size / (1024 * 1024)
    print(f"  \u2713 {dest.name} ({size_mb:.2f} MB) [generated]")
    _total_bytes += dest.stat().st_size
    _downloaded_count += 1


def _generate_voiceover(dest: Path, duration: float = 20.0) -> None:
    """Generate a synthetic voiceover-like WAV (formant synthesis)."""
    global _downloaded_count, _total_bytes

    if dest.exists() and dest.stat().st_size > 1000:
        size_mb = dest.stat().st_size / (1024 * 1024)
        print(f"  \u2713 {dest.name} ({size_mb:.1f} MB) [cached]")
        _total_bytes += dest.stat().st_size
        _downloaded_count += 1
        return

    sr = 44100
    n = int(sr * duration)
    # Simple formant-like synthesis: buzz + resonant filtering approximation
    f0 = 120.0  # fundamental
    samples = []
    for i in range(n):
        t = i / sr
        # Pitch variation
        pitch = f0 * (1 + 0.05 * math.sin(2 * math.pi * 3 * t))
        # Buzz source (sum of harmonics)
        val = 0.0
        for h in range(1, 8):
            val += (0.3 / h) * math.sin(2 * math.pi * pitch * h * t)
        # Speech-like amplitude envelope (words)
        word_dur = 0.4
        word_phase = (t % word_dur) / word_dur
        word_env = math.sin(math.pi * word_phase) ** 0.5
        # Pause between "sentences"
        sentence_t = t % 4.0
        if sentence_t > 3.5:
            word_env *= max(0, (4.0 - sentence_t) / 0.5)
        # Master envelope
        master = min(1.0, t / 0.3) * min(1.0, (duration - t) / 0.3)
        samples.append(int(val * word_env * master * 20000))

    _write_wav(dest, samples, sr)
    size_mb = dest.stat().st_size / (1024 * 1024)
    print(f"  \u2713 {dest.name} ({size_mb:.2f} MB) [generated]")
    _total_bytes += dest.stat().st_size
    _downloaded_count += 1


# ---------------------------------------------------------------------------
# Video generation (via ffmpeg)
# ---------------------------------------------------------------------------


def _generate_video(
    dest: Path,
    duration: int,
    width: int = 1920,
    height: int = 1080,
    pattern: str = "testsrc2",
) -> None:
    """Generate a test video using ffmpeg."""
    global _downloaded_count, _total_bytes

    if dest.exists() and dest.stat().st_size > 10000:
        size_mb = dest.stat().st_size / (1024 * 1024)
        print(f"  \u2713 {dest.name} ({size_mb:.1f} MB) [cached]")
        _total_bytes += dest.stat().st_size
        _downloaded_count += 1
        return

    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"{pattern}=size={width}x{height}:duration={duration}:rate=30",
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-crf",
        "28",
        "-pix_fmt",
        "yuv420p",
        str(dest),
    ]

    try:
        result = subprocess.run(  # noqa: S603
            cmd, capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0:
            print(f"  \u2717 {dest.name} — ffmpeg error: {result.stderr[:200]}")
            return
        size_mb = dest.stat().st_size / (1024 * 1024)
        print(f"  \u2713 {dest.name} ({size_mb:.2f} MB) [generated via ffmpeg]")
        _total_bytes += dest.stat().st_size
        _downloaded_count += 1
    except FileNotFoundError:
        print(f"  \u2717 {dest.name} — ffmpeg not found (install ffmpeg)")
    except subprocess.TimeoutExpired:
        print(f"  \u2717 {dest.name} — ffmpeg timed out")


def _generate_greenscreen_video(dest: Path, duration: int = 8) -> None:
    """Generate a green screen video with a moving colored circle."""
    global _downloaded_count, _total_bytes

    if dest.exists() and dest.stat().st_size > 10000:
        size_mb = dest.stat().st_size / (1024 * 1024)
        print(f"  \u2713 {dest.name} ({size_mb:.1f} MB) [cached]")
        _total_bytes += dest.stat().st_size
        _downloaded_count += 1
        return

    # Green background with a moving white circle (simulates subject)
    filtergraph = (
        f"color=c=0x00B140:size=1920x1080:duration={duration}:rate=30[bg];"
        f"color=c=white:size=300x300:duration={duration}:rate=30,"
        f"format=yuva420p,geq="
        f"lum='if(lt(hypot(X-150\\,Y-150)\\,140)\\,255\\,0)':"
        f"a='if(lt(hypot(X-150\\,Y-150)\\,140)\\,255\\,0)'[circle];"
        f"[bg][circle]overlay="
        f"x='960-150+200*sin(2*PI*t/{duration})':"
        f"y='540-150+100*cos(2*PI*t/{duration})'"
    )
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        filtergraph,
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-crf",
        "28",
        "-pix_fmt",
        "yuv420p",
        "-t",
        str(duration),
        str(dest),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)  # noqa: S603
        if result.returncode != 0:
            print(f"  \u2717 {dest.name} — ffmpeg error: {result.stderr[:200]}")
            return
        size_mb = dest.stat().st_size / (1024 * 1024)
        print(f"  \u2713 {dest.name} ({size_mb:.2f} MB) [generated via ffmpeg]")
        _total_bytes += dest.stat().st_size
        _downloaded_count += 1
    except FileNotFoundError:
        print(f"  \u2717 {dest.name} — ffmpeg not found")
    except subprocess.TimeoutExpired:
        print(f"  \u2717 {dest.name} — ffmpeg timed out")


# ---------------------------------------------------------------------------
# GLB generation (minimal valid glTF binary)
# ---------------------------------------------------------------------------


def _generate_glb(dest: Path) -> None:
    """Generate a minimal valid GLB file (simple triangle mesh)."""
    global _downloaded_count, _total_bytes

    if dest.exists() and dest.stat().st_size > 100:
        size_mb = dest.stat().st_size / (1024 * 1024)
        print(f"  \u2713 {dest.name} ({size_mb:.1f} MB) [cached]")
        _total_bytes += dest.stat().st_size
        _downloaded_count += 1
        return

    import json

    # Simple box-like mesh: 8 vertices, 12 triangles
    vertices = [
        -0.5,
        -0.5,
        -0.5,
        0.5,
        -0.5,
        -0.5,
        0.5,
        0.5,
        -0.5,
        -0.5,
        0.5,
        -0.5,
        -0.5,
        -0.5,
        0.5,
        0.5,
        -0.5,
        0.5,
        0.5,
        0.5,
        0.5,
        -0.5,
        0.5,
        0.5,
    ]
    indices = [
        0,
        1,
        2,
        0,
        2,
        3,  # front
        4,
        6,
        5,
        4,
        7,
        6,  # back
        0,
        4,
        5,
        0,
        5,
        1,  # bottom
        2,
        6,
        7,
        2,
        7,
        3,  # top
        0,
        3,
        7,
        0,
        7,
        4,  # left
        1,
        5,
        6,
        1,
        6,
        2,  # right
    ]

    vtx_data = struct.pack(f"<{len(vertices)}f", *vertices)
    idx_data = struct.pack(f"<{len(indices)}H", *indices)

    # Pad to 4-byte alignment
    while len(vtx_data) % 4:
        vtx_data += b"\x00"
    while len(idx_data) % 4:
        idx_data += b"\x00"

    bin_data = idx_data + vtx_data
    idx_offset = 0
    vtx_offset = len(idx_data)

    gltf = {
        "asset": {"version": "2.0", "generator": "pymotion-asset-gen"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": "Product"}],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 1}, "indices": 0}]}],
        "accessors": [
            {
                "bufferView": 0,
                "componentType": 5123,
                "count": len(indices),
                "type": "SCALAR",
                "max": [max(indices)],
                "min": [min(indices)],
            },
            {
                "bufferView": 1,
                "componentType": 5126,
                "count": len(vertices) // 3,
                "type": "VEC3",
                "max": [0.5, 0.5, 0.5],
                "min": [-0.5, -0.5, -0.5],
            },
        ],
        "bufferViews": [
            {"buffer": 0, "byteOffset": idx_offset, "byteLength": len(idx_data), "target": 34963},
            {"buffer": 0, "byteOffset": vtx_offset, "byteLength": len(vtx_data), "target": 34962},
        ],
        "buffers": [{"byteLength": len(bin_data)}],
        "materials": [
            {
                "pbrMetallicRoughness": {
                    "baseColorFactor": [0.8, 0.8, 0.9, 1.0],
                    "metallicFactor": 0.5,
                    "roughnessFactor": 0.3,
                }
            }
        ],
    }

    json_str = json.dumps(gltf, separators=(",", ":"))
    json_bytes = json_str.encode("utf-8")
    # Pad JSON to 4-byte alignment
    while len(json_bytes) % 4:
        json_bytes += b" "

    # GLB structure
    glb = bytearray()
    total_length = 12 + 8 + len(json_bytes) + 8 + len(bin_data)
    # Header
    glb.extend(b"glTF")
    glb.extend(struct.pack("<II", 2, total_length))
    # JSON chunk
    glb.extend(struct.pack("<I", len(json_bytes)))
    glb.extend(b"JSON")
    glb.extend(json_bytes)
    # BIN chunk
    glb.extend(struct.pack("<I", len(bin_data)))
    glb.extend(b"BIN\x00")
    glb.extend(bin_data)

    dest.write_bytes(bytes(glb))
    size_mb = len(glb) / (1024 * 1024)
    print(f"  \u2713 {dest.name} ({size_mb:.4f} MB) [generated]")
    _total_bytes += len(glb)
    _downloaded_count += 1


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    """Download/generate all assets. Returns 0 on success, 1 on failure."""
    global _downloaded_count, _total_bytes
    _downloaded_count = 0
    _total_bytes = 0
    failed: list[str] = []

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Asset directory: {ASSETS_DIR}\n")

    # ── Fonts (Google Fonts — OFL) ────────────────────────────────────────
    print("Fonts:")
    for name, url in FONT_URLS.items():
        dest = ASSETS_DIR / name
        if not _download(url, dest, expected_min_size=10000):
            failed.append(name)
        elif not _verify_file(dest):
            print(f"  \u2717 {name} — verification failed (bad header)")
            failed.append(name)

    # ── Images ────────────────────────────────────────────────────────────
    print("\nImages (downloaded):")
    for name, url in IMAGE_URLS.items():
        dest = ASSETS_DIR / name
        if not _download(url, dest, expected_min_size=5000):
            failed.append(name)

    print("\nImages (generated PNG with transparency):")
    _generate_logo_png(ASSETS_DIR / "logo.png", size=512)
    _generate_logo_png(ASSETS_DIR / "brand_icon.png", size=256)
    _generate_product_png(ASSETS_DIR / "product_hero.png", seed=42, label="HERO")
    _generate_product_png(ASSETS_DIR / "product_a.png", seed=10, label="A")
    _generate_product_png(ASSETS_DIR / "product_b.png", seed=20, label="B")
    _generate_product_png(ASSETS_DIR / "product_c.png", seed=30, label="C")

    # ── Videos (generated via ffmpeg) ─────────────────────────────────────
    print("\nVideos:")
    _generate_video(ASSETS_DIR / "sample_footage.mp4", duration=10)
    _generate_greenscreen_video(ASSETS_DIR / "greenscreen_subject.mp4", duration=8)
    _generate_video(
        ASSETS_DIR / "screen_recording.mp4",
        duration=12,
        width=1920,
        height=1080,
        pattern="testsrc",
    )

    # ── 3D Model ──────────────────────────────────────────────────────────
    print("\n3D Models:")
    _generate_glb(ASSETS_DIR / "product_3d.glb")

    # ── Audio (generated WAV) ─────────────────────────────────────────────
    print("\nAudio — Music:")
    _generate_music(ASSETS_DIR / "music_upbeat.wav", 90.0, bpm=140, style="upbeat")
    _generate_music(ASSETS_DIR / "music_cinematic.wav", 90.0, bpm=70, style="cinematic")
    _generate_music(ASSETS_DIR / "music_ambient.wav", 90.0, bpm=100, style="ambient")

    print("\nAudio — Voiceover:")
    _generate_voiceover(ASSETS_DIR / "voiceover.wav", duration=20.0)

    print("\nAudio — SFX:")
    _generate_sfx(ASSETS_DIR / "sfx_impact.wav", 1.5, 200, style="impact")
    _generate_sfx(ASSETS_DIR / "sfx_whoosh.wav", 0.6, 600, style="whoosh")
    _generate_sfx(ASSETS_DIR / "ir_hall.wav", 2.0, 250, style="ir")

    # ── Verification ──────────────────────────────────────────────────────
    print("\nVerification:")
    all_expected = (
        list(FONT_URLS.keys())
        + list(IMAGE_URLS.keys())
        + [
            "logo.png",
            "brand_icon.png",
            "product_hero.png",
            "product_a.png",
            "product_b.png",
            "product_c.png",
            "sample_footage.mp4",
            "greenscreen_subject.mp4",
            "screen_recording.mp4",
            "product_3d.glb",
            "music_upbeat.wav",
            "music_cinematic.wav",
            "music_ambient.wav",
            "voiceover.wav",
            "sfx_impact.wav",
            "sfx_whoosh.wav",
            "ir_hall.wav",
        ]
    )

    for name in all_expected:
        path = ASSETS_DIR / name
        if not path.exists():
            print(f"  MISSING: {name}")
            if name not in failed:
                failed.append(name)
        elif path.stat().st_size == 0:
            print(f"  EMPTY: {name}")
            if name not in failed:
                failed.append(name)
        elif not _verify_file(path):
            print(f"  BAD FORMAT: {name}")
            if name not in failed:
                failed.append(name)
        else:
            print(f"  OK: {name}")

    # ── Summary ───────────────────────────────────────────────────────────
    total_mb = _total_bytes / (1024 * 1024)
    print(f"\nAll {_downloaded_count} assets ready. Total: {total_mb:.1f} MB")

    if failed:
        print(f"\nFAILED ({len(failed)}): {', '.join(failed)}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
