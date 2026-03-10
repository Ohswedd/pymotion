<p align="center">
  <img src="https://img.shields.io/badge/PyMotion-v1.0.1-blue?style=for-the-badge&labelColor=0D1B2A&color=D4AF37" alt="Version"/>
</p>

<h1 align="center">PyMotion</h1>

<p align="center">
  <strong>Code-first video generation for Python.</strong><br>
  Build professional motion graphics, animated explainers, social ads, and product videos — entirely in Python.
</p>

<p align="center">
  <a href="https://github.com/Ohswedd/pymotion/actions/workflows/ci.yml"><img src="https://github.com/Ohswedd/pymotion/actions/workflows/ci.yml/badge.svg?branch=main" alt="CI"></a>
  <a href="https://pypi.org/project/pymotion/"><img src="https://img.shields.io/pypi/v/pymotion?color=D4AF37&label=PyPI" alt="PyPI"></a>
  <a href="https://pypi.org/project/pymotion/"><img src="https://img.shields.io/pypi/dm/pymotion?color=blue&label=Downloads" alt="Downloads"></a>
  <a href="https://pypi.org/project/pymotion/"><img src="https://img.shields.io/pypi/pyversions/pymotion" alt="Python"></a>
  <a href="https://github.com/Ohswedd/pymotion/blob/main/LICENSE"><img src="https://img.shields.io/github/license/Ohswedd/pymotion?color=green" alt="License"></a>
</p>

<p align="center">
  <a href="https://github.com/Ohswedd/pymotion"><img src="https://img.shields.io/badge/mypy-strict-blue" alt="mypy strict"></a>
  <a href="https://github.com/Ohswedd/pymotion"><img src="https://img.shields.io/badge/coverage-85%25-brightgreen" alt="Coverage"></a>
  <a href="https://github.com/Ohswedd/pymotion"><img src="https://img.shields.io/badge/ruff-clean-purple" alt="Ruff"></a>
  <a href="https://github.com/Ohswedd/pymotion"><img src="https://img.shields.io/badge/pip--audit-passing-green" alt="Security Audit"></a>
  <a href="https://github.com/Ohswedd/pymotion"><img src="https://img.shields.io/badge/tests-1116%20passed-brightgreen" alt="Tests"></a>
</p>

---

## Why PyMotion?

Most video tools force you into a GUI timeline. PyMotion doesn't. You write Python, you get broadcast-quality video. No templates to fight, no drag-and-drop constraints — just code that renders frames.

It ships with a Cairo 2D backend, a ModernGL 3D pipeline, FreeType+HarfBuzz typography, a full audio DSP chain, and 15 FFmpeg export presets out of the box. One `pip install`, one `comp.render()` call, done.

```python
from pymotion import Composition, ColorClip, TextClip, Track

comp = Composition(1920, 1080, fps=30, duration=150)

track = Track(name="main")
bg = ColorClip(color="#1a1a2e")
bg.set_duration(150)
track.add(bg)

title = TextClip("Hello, PyMotion!", font="Arial", size=72.0, color="#FFFFFF")
title.set_duration(150).set_position(480.0, 500.0)
track.add(title)

comp.add_track(track)
comp.render("output.mp4", preset="h264_1080p")
```

That's a full 1080p video in 12 lines.

---

## Features

| | |
|---|---|
| **2D Rendering** | Color, image, shape, gradient, and text clips — Cairo backend |
| **3D Rendering** | PBR materials, point/spot/directional/ambient lights, SSAO, bloom, DOF (ModernGL headless) |
| **Animation** | Keyframe tracks, 30+ easing functions, spring physics, cubic bezier curves |
| **Typography** | FreeType + HarfBuzz shaping, variable fonts, 9 animated text presets (Typewriter, CountUp, Scramble, ...) |
| **Audio** | Mixing, EQ, compressor, limiter, reverb, delay, pitch shift, beat detection, waveform analysis |
| **Effects** | 30+ visual/color/distortion/light effects (blur, grain, glow, LUT, wave warp, god rays, ...) |
| **Transitions** | 39 built-in (fade, slide, wipe, zoom, glitch, film burn, shatter, vortex, ...) |
| **Particles** | 9 presets — fire, sparkles, confetti, rain, smoke, stars, dust, explosion, bubbles |
| **Export** | 15 presets — H.264, H.265, ProRes, AV1, WebM, GIF, PNG/EXR frame sequences |
| **Batch** | Template system with field validation for data-driven video generation |
| **Color** | .cube LUT loading, lift/gamma/gain grading, ACES/Reinhard/Filmic tone mapping |
| **CLI** | `render`, `preview`, `benchmark`, `validate`, `doctor`, `new` |

---

## Installation

**Prerequisites:** Python 3.11+, FFmpeg, Cairo

```bash
# macOS
brew install ffmpeg cairo pkg-config

# Ubuntu / Debian
sudo apt-get install ffmpeg libcairo2-dev pkg-config libfreetype6-dev

# Windows (via chocolatey)
choco install ffmpeg cairo
```

**Install from PyPI:**

```bash
pip install pymotion
```

**With extras:**

```bash
pip install "pymotion[3d-extras]"     # GLTF model loading
pip install "pymotion[gpu-compute]"   # wgpu acceleration
pip install "pymotion[jit]"           # Numba JIT compilation
pip install "pymotion[dev]"           # Development tools
```

---

## Quick Start

### Animated Text with Particles

```python
from pymotion import Composition, ColorClip, Track
from pymotion.text.animated import Typewriter
from pymotion.particle.system import sparkles
from pymotion.utils.color import Color

comp = Composition(1920, 1080, fps=30, duration=150)

# Background
bg_track = Track(name="bg")
bg = ColorClip(color="#0D1B2A")
bg.set_duration(150)
bg_track.add(bg)

# Typewriter text
text_track = Track(name="text")
tw = Typewriter(
    text="Welcome to PyMotion",
    font_size=64.0,
    color=Color(1.0, 1.0, 1.0, 1.0),
    chars_per_frame=1.5,
)
tw.set_duration(150).at(10)
text_track.add(tw)

# Sparkle particles
fx_track = Track(name="fx")
sparks = sparkles(1920, 1080).to_clip(150)
sparks.set_duration(150)
fx_track.add(sparks)

comp.add_track(bg_track)
comp.add_track(text_track)
comp.add_track(fx_track)
comp.render("intro.mp4", preset="h264_1080p")
```

### Batch Rendering with Templates

```python
from pymotion import Template, Composition, ColorClip, TextClip, Track

class ProductVideo(Template):
    product_name: str
    brand_color: str = "#FF5500"

    def build(self) -> Composition:
        comp = Composition(1920, 1080, fps=30, duration=90)
        track = Track(name="main")
        bg = ColorClip(color=self.brand_color)
        bg.set_duration(90)
        track.add(bg)
        label = TextClip(self.product_name, font="Arial", size=80.0, color="#FFFFFF")
        label.set_duration(90).set_position(600.0, 480.0)
        track.add(label)
        comp.add_track(track)
        return comp

for name in ["Widget Pro", "Gadget X", "Tool Kit"]:
    ProductVideo(product_name=name).render(f"{name.lower().replace(' ', '_')}.mp4")
```

---

## Examples

Five production-ready scripts ship with the repo, each targeting a real-world use case:

| # | Script | Niche | What It Demonstrates |
|---|--------|-------|----------------------|
| 01 | `real_estate_tour.py` | Property listings | ImageClip slideshow, Typewriter text, sparkle particles, 7-track composition |
| 02 | `tech_review_intro.py` | YouTube intros | CountUp stats, radial/conic gradients, fire particles |
| 03 | `fitness_social_ad.py` | Instagram/TikTok | Vertical 1080×1920, CountDown timer, confetti, LetterByLetter |
| 04 | `restaurant_menu_promo.py` | Menu promotions | WordByWord reveals, stars particles, ShapeClip polygons |
| 05 | `educational_explainer.py` | E-learning | LetterByLetter titles, CountUp counters, diagram shapes |

```bash
python examples/download_assets.py     # grab stock images (~5 MB)
python examples/01_real_estate_tour.py  # render
```

---

## CLI

```bash
pymotion render scene.py -o out.mp4 -p h264_1080p   # render a composition
pymotion export-frame scene.py -f 30 -o thumb.png    # export single frame
pymotion benchmark scene.py -n 100                    # measure frame throughput
pymotion doctor                                       # verify system dependencies
pymotion validate scene.py                            # check composition integrity
pymotion new my-project                               # scaffold a new project
```

---

## Architecture

```
pymotion/
├── animation/     Keyframe tracks, 30+ easings, spring, bezier, interpolation
├── audio/         Mixer, DSP effects (EQ, compressor, reverb, ...), beat detection
├── clip/          ColorClip, ImageClip, ShapeClip, TextClip, VideoClip, Scene3DClip
├── effects/       Visual, color, distortion, light effect processors
├── export/        FFmpeg encoder, 15 output presets
├── particle/      Vectorized particle system, 9 preset generators
├── render/        Cairo 2D, ModernGL 3D, compositor, color pipeline
├── security/      Path traversal, color, asset magic-byte, text sanitization validators
├── template/      Template ABC with field validation for batch rendering
├── text/          FreeType/HarfBuzz renderer, 9 animated text presets
├── transition/    39 transition implementations
├── utils/         Color (OKLCH), Vec2/Vec3, logging (structlog)
└── cli/           Click-based CLI (render, preview, benchmark, doctor, ...)
```

**Internal frame format:** BGRA `uint8` NumPy arrays `(H, W, 4)` — matches Cairo ARGB32 on little-endian. The compositor uses bounding-box sparse blending with `uint16` fixed-point fast paths for opaque layers and alpha-info caching for transparency detection.

---

## Performance

Benchmarked on a typical 7-layer 1080p composition:

| Metric | Value |
|--------|-------|
| Frame render throughput | ~75 fps (13 ms/frame) |
| 12s video end-to-end | ~7s wall time (2.5× realtime) |
| Static layer caching | Single render, reused across frames |
| Particle simulation | Vectorized NumPy — no per-particle Python loops |
| FFmpeg encoding | Multi-threaded, contiguous frame pipe, zero-copy |

---

## Development

```bash
git clone https://github.com/Ohswedd/pymotion.git
cd pymotion
pip install -e ".[dev]"

make lint      # ruff format + ruff check + mypy --strict
make test      # pytest with coverage (85% minimum)
make clean     # remove caches and build artifacts
```

### Running Tests

```bash
pytest -v                              # full suite (1116 tests)
pytest tests/unit/ -v                  # unit tests only
pytest tests/integration/ -v           # integration tests
pytest --cov=pymotion --cov-report=html  # coverage report
```

---

## Docker

```bash
docker build -t pymotion .
docker run --rm -v $(pwd)/output:/app/output pymotion render scene.py -o output/video.mp4
```

---

## System Dependencies

| Dependency | Purpose | Bundled? |
|-----------|---------|----------|
| FFmpeg | Video/audio encoding | No — install separately |
| Cairo | 2D vector rendering | No — install separately |
| FreeType | Font rasterization | Yes (via `freetype-py`) |
| HarfBuzz | Text shaping | Yes (via `uharfbuzz`) |
| ModernGL | 3D PBR rendering | Yes (via pip) |

Run `pymotion doctor` to verify your environment.

---

## License

[MIT](LICENSE)
