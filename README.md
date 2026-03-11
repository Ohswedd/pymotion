<p align="center">
  <img src="https://img.shields.io/badge/PyMotion-v1.5.0-blue?style=for-the-badge&labelColor=0D1B2A&color=D4AF37" alt="Version"/>
</p>

<h1 align="center">PyMotion</h1>

<p align="center">
  <strong>Code-first video generation for Python.</strong><br>
  Build professional motion graphics, animated explainers, social ads, and product videos — entirely in Python.
</p>

<p align="center">
  <a href="https://github.com/Ohswedd/pymotion/actions/workflows/ci.yml"><img src="https://github.com/Ohswedd/pymotion/actions/workflows/ci.yml/badge.svg?branch=main" alt="CI"></a>
  <a href="https://pypi.org/project/pymotion-studio/"><img src="https://img.shields.io/badge/PyPI-v1.5.0-D4AF37" alt="PyPI"></a>
  <a href="https://pypi.org/project/pymotion-studio/"><img src="https://img.shields.io/badge/python-3.12%20%7C%203.13%20%7C%203.14-blue" alt="Python"></a>
  <a href="https://github.com/Ohswedd/pymotion/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-Source%20Available-blue" alt="License"></a>
</p>

<p align="center">
  <a href="https://github.com/Ohswedd/pymotion"><img src="https://img.shields.io/badge/tests-1784%20passed-brightgreen" alt="Tests"></a>
  <a href="https://github.com/Ohswedd/pymotion"><img src="https://img.shields.io/badge/coverage-87%25-brightgreen" alt="Coverage"></a>
  <a href="https://github.com/Ohswedd/pymotion"><img src="https://img.shields.io/badge/mypy-strict-blue" alt="mypy strict"></a>
  <a href="https://github.com/Ohswedd/pymotion"><img src="https://img.shields.io/badge/ruff-clean-purple" alt="Ruff"></a>
  <a href="https://github.com/Ohswedd/pymotion"><img src="https://img.shields.io/badge/pip--audit-passing-green" alt="Security Audit"></a>
</p>

<p align="center">
  <a href="https://pypi.org/project/pymotion-studio/"><img src="https://img.shields.io/pypi/dm/pymotion-studio?label=PyPI%20downloads&color=blue" alt="PyPI Downloads"></a>
  <a href="https://github.com/Ohswedd/pymotion"><img src="https://img.shields.io/github/stars/Ohswedd/pymotion?style=flat&label=stars&color=D4AF37" alt="GitHub Stars"></a>
  <a href="https://github.com/Ohswedd/pymotion"><img src="https://img.shields.io/github/forks/Ohswedd/pymotion?style=flat&label=forks&color=blue" alt="GitHub Forks"></a>
  <a href="https://github.com/Ohswedd/pymotion/issues"><img src="https://img.shields.io/github/issues/Ohswedd/pymotion?label=issues&color=orange" alt="Issues"></a>
  <a href="https://github.com/Ohswedd/pymotion"><img src="https://img.shields.io/github/last-commit/Ohswedd/pymotion?label=last%20commit&color=brightgreen" alt="Last Commit"></a>
  <a href="https://github.com/Ohswedd/pymotion"><img src="https://img.shields.io/github/repo-size/Ohswedd/pymotion?label=repo%20size&color=blue" alt="Repo Size"></a>
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

## At a Glance

| | |
|---|---|
| **Public API** | 255 symbols — clips, effects, transitions, audio, color, layout, animation |
| **Source** | 76 modules, ~25k lines of production code |
| **Tests** | 1784 tests, 87% coverage, ~15k lines of test code |
| **Quality** | `mypy --strict`, `ruff` (format + lint), `pip-audit` — all clean |
| **Docs** | 24 guides, 22 API reference pages, 9 runnable examples |
| **Version** | v1.5.0 — Professional Audio & Color Science |

---

## Features

| | |
|---|---|
| **2D Rendering** | Color, image, shape, gradient, and text clips — Cairo backend |
| **3D Rendering** | PBR materials, point/spot/directional/ambient lights, SSAO, bloom, DOF (ModernGL headless) |
| **Animation** | Keyframe tracks, 30+ easing functions, spring physics, cubic bezier curves |
| **Typography** | FreeType + HarfBuzz shaping, variable fonts, 9 animated text presets (Typewriter, CountUp, Scramble, ...) |
| **Audio** | 5.1 surround, bus routing, crossfades, multiband compressor, convolution reverb, LUFS normalization, EQ, beat detection |
| **Effects** | 30+ visual/color/distortion/light effects (blur, grain, glow, LUT, wave warp, god rays, ...) |
| **Keying** | ChromaKey, LumaKey, ColorKey, DifferenceKey — with feathering, choking, despill |
| **Editing** | Split, join, subclip, repeat, freeze frame, concatenate with transitions |
| **Speed/Time** | Uniform speed, speed ramp, reverse, time remap, optical flow slow-motion |
| **Layout** | Picture-in-picture, grid, split screen, stack — named anchor positioning |
| **Tracking** | Motion tracking, video stabilization, follow-tracker binding |
| **Compositing** | Nested compositions (pre-comps), adjustment layers, clip parenting with NullObject |
| **Masking** | Bezier, linear/radial gradient, track matte, text masks — boolean ops (add, intersect, subtract) |
| **Expressions** | Drive any property with Python callables — wiggle, loop_in, loop_out helpers |
| **Path Animation** | SVG path following, StrokeClip draw-on/off, bezier path morphing |
| **Charts** | Animated bar, line, pie, area, radar, scatter charts + number counter, progress bar — 4 themes |
| **Motion Graphics** | LowerThird, LogoReveal, CallToAction, SocialHandle, Countdown, QuoteCard, Divider, TransitionTitle, Watermark |
| **Device Mockups** | BrowserMockup, PhoneMockup, DesktopMockup — wrap content clips inside device frames |
| **Proxy** | Low-res proxy generation with disk cache for fast preview |
| **Transitions** | 39 built-in (fade, slide, wipe, zoom, glitch, film burn, shatter, vortex, ...) |
| **Particles** | 9 presets — fire, sparkles, confetti, rain, smoke, stars, dust, explosion, bubbles |
| **Export** | 15 presets — H.264, H.265, ProRes, AV1, WebM, GIF, PNG/EXR frame sequences |
| **Batch** | Template system with field validation for data-driven video generation |
| **Audio Viz** | WaveformClip, SpectrumClip, SpectrogramClip, AudioReactiveEffect — animated audio visualizations |
| **Captions** | AutoCaptions (Whisper), SubtitleClip, SRT/VTT/ASS import/export, 4 caption styles (netflix, youtube, tiktok, karaoke) |
| **TTS** | TTSClip with system (pyttsx3), OpenAI, and ElevenLabs engines |
| **Color Science** | ACES 1.3 pipeline, HDR10/HLG presets, ColorMatch, HSLSecondary grading, 4 video scopes |
| **Color** | .cube LUT loading, lift/gamma/gain grading, ACES/Reinhard/Filmic tone mapping |
| **Interchange** | EDL export (CMX 3600), OTIO export (OpenTimelineIO) |
| **CLI** | `render`, `preview`, `benchmark`, `validate`, `doctor`, `new` |

---

## Installation

**Prerequisites:** Python 3.12+, FFmpeg, Cairo

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
pip install pymotion-studio
```

**With extras:**

```bash
pip install "pymotion-studio[3d-extras]"     # GLTF model loading
pip install "pymotion-studio[gpu-compute]"   # wgpu acceleration
pip install "pymotion-studio[jit]"           # Numba JIT compilation
pip install "pymotion-studio[dev]"           # Development tools
```

> **Note:** The Python import name is `pymotion` (no hyphen):
> ```python
> from pymotion import Composition, ColorClip, Track
> ```

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

### Data Visualization

```python
from pymotion import BarChartClip, NumberCounter, Composition, Track

comp = Composition(1920, 1080, fps=30, duration=90)

chart_track = Track(name="chart")
chart = BarChartClip(
    data={"Q1": 120, "Q2": 200, "Q3": 180, "Q4": 250},
    animate_duration=30,
    theme="corporate",
    title="Quarterly Revenue",
    show_values=True,
)
chart.set_duration(90)
chart_track.add(chart)
comp.add_track(chart_track)
comp.render("chart.mp4", preset="h264_1080p")
```

### Video Editing Operations

```python
from pymotion import ColorClip, concatenate, CrossDissolve, pip, grid

# Split, speed, reverse
clip = ColorClip(color="#e94560")
clip.set_duration(120)
first, second = clip.split(60)
slow = first.speed(0.5)
backwards = second.reverse()

# Concatenate with transitions
final = concatenate([slow, backwards], transition=CrossDissolve(), transition_duration=15)

# Picture-in-picture
main = ColorClip(color="#1a1a2e").set_duration(90)
overlay = ColorClip(color="#e94560").set_duration(90)
comp = pip(main, overlay, position="bottom-right", size=(320, 180))

# Grid layout
clips = [ColorClip(color=c).set_duration(90) for c in ["#e94560", "#0f3460", "#533483", "#16213e"]]
comp = grid(clips, rows=2, cols=2, gap=10)
```

---

## Examples

Nine production-ready scripts ship with the repo, each targeting a real-world use case:

| # | Script | Niche | What It Demonstrates |
|---|--------|-------|----------------------|
| 01 | `real_estate_tour.py` | Property listings | ImageClip slideshow, Typewriter text, sparkle particles, 7-track composition |
| 02 | `tech_review_intro.py` | YouTube intros | CountUp stats, radial/conic gradients, fire particles |
| 03 | `fitness_social_ad.py` | Instagram/TikTok | Vertical 1080x1920, CountDown timer, confetti, LetterByLetter |
| 04 | `restaurant_menu_promo.py` | Menu promotions | WordByWord reveals, stars particles, ShapeClip polygons |
| 05 | `educational_explainer.py` | E-learning | LetterByLetter titles, CountUp counters, diagram shapes |
| 06 | `video_editing_showcase.py` | Post-production | split/join/speed/reverse, ChromaKey, grid/pip/split_screen, proxy workflow |
| 07 | `motion_graphics_toolkit.py` | Motion graphics | Nested comps, masks, expressions, wiggle, path animation, adjustment layers |
| 08 | `data_dashboard.py` | Data visualization | Animated charts, number counters, progress bars, device mockups, lower thirds |
| 09 | `audio_color_science.py` | Broadcast post-production | 5.1 surround mixing, audio viz, captions, TTS, ACES grading, video scopes, EDL export |

```bash
python examples/download_assets.py     # grab stock images (~5 MB)
python examples/01_real_estate_tour.py  # render
```

---

## Code Quality & Checks

PyMotion enforces strict quality gates on every change. All checks must pass before any commit is merged.

| Check | Tool | Status | What It Enforces |
|-------|------|--------|------------------|
| **Type Safety** | `mypy --strict` | passing | Full static type coverage — no `Any` leaks, strict return types, generic protocols |
| **Formatting** | `ruff format` | clean | Consistent code style across all 76 modules — zero manual formatting |
| **Linting** | `ruff check` | clean | 800+ rules — import sorting, unused variables, security patterns, complexity limits |
| **Tests** | `pytest` | 1784 passed | Unit, integration, snapshot, and performance tests — 87% line coverage |
| **Security** | `pip-audit` | passing | Zero known vulnerabilities in the dependency tree |
| **Coverage** | `pytest-cov` | 87% | Enforced minimum — PRs that drop coverage below 85% are rejected |

### Running Locally

```bash
make lint      # ruff format + ruff check + mypy --strict (all three must pass)
make test      # pytest with coverage (85% minimum gate)
make clean     # remove caches and build artifacts
```

Or individually:

```bash
ruff format pymotion/ tests/                  # auto-format
ruff check pymotion/ tests/                   # lint
mypy --strict pymotion/                       # type check
pytest -v                                     # full suite (1784 tests)
pytest tests/unit/ -v                         # unit tests only
pytest --cov=pymotion --cov-report=html       # coverage report
```

---

## Project Structure

```
pymotion/                    76 modules, ~25,000 lines
├── animation/               Keyframe tracks, 30+ easings, spring, bezier, interpolation
├── audio/                   5.1 surround mixer, bus routing, DSP effects, convolution reverb, beat detection
├── clip/                    ColorClip, ImageClip, ShapeClip, TextClip, VideoClip, Scene3DClip, charts, mockups, audio viz
├── captions.py              Subtitle import/export, AutoCaptions (Whisper), caption styles
├── color_science.py         ACES pipeline, HDR presets, ColorMatch, HSLSecondary, video scopes
├── composition.py           Composition, Track, CompositionClip, AdjustmentLayer, EDL/OTIO export
├── masking.py               Bezier, gradient, track matte, text masks + boolean ops
├── expressions.py           Expression system — wiggle, loop_in, loop_out
├── path_animation.py        SVG path following, StrokeClip, path morphing
├── tts.py                   Text-to-speech (system, OpenAI, ElevenLabs)
├── effects/                 Visual, color, distortion, light effect processors
├── export/                  FFmpeg encoder, 15 output presets
├── particle/                Vectorized particle system, 9 preset generators
├── render/                  Cairo 2D, ModernGL 3D, compositor, color pipeline
├── security/                Path traversal, color, asset magic-byte, text sanitization validators
├── template/                Template ABC with field validation for batch rendering
├── text/                    FreeType/HarfBuzz renderer, 9 animated text presets
├── transition/              39 transition implementations
├── utils/                   Color (OKLCH), Vec2/Vec3, logging (structlog)
└── cli/                     Click-based CLI (render, preview, benchmark, doctor, ...)

tests/                       1784 tests, ~15,000 lines
├── unit/                    Fast isolated tests (mocked I/O, no rendering)
├── integration/             End-to-end render tests (FFmpeg required)
├── snapshot/                Frame-level regression tests
└── performance/             Throughput benchmarks

docs/                        46 pages
├── guides/                  24 practical tutorials (code-first, copy-paste ready)
└── api/                     22 auto-generated API reference pages (mkdocstrings)

examples/                    9 production-ready scripts targeting real-world niches
```

**Internal frame format:** BGRA `uint8` NumPy arrays `(H, W, 4)` — matches Cairo ARGB32 on little-endian. The compositor uses bounding-box sparse blending with `uint16` fixed-point fast paths for opaque layers and alpha-info caching for transparency detection.

---

## Performance

Benchmarked on a typical 7-layer 1080p composition:

| Metric | Value |
|--------|-------|
| Frame render throughput | ~75 fps (13 ms/frame) |
| 12s video end-to-end | ~7s wall time (2.5x realtime) |
| Static layer caching | Single render, reused across frames |
| Particle simulation | Vectorized NumPy — no per-particle Python loops |
| FFmpeg encoding | Multi-threaded, contiguous frame pipe, zero-copy |

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

## Development

```bash
git clone https://github.com/Ohswedd/pymotion.git
cd pymotion
pip install -e ".[dev]"
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

## Release History

| Version | Date | Highlights |
|---------|------|------------|
| **v1.5.0** | 2026-03-11 | Professional Audio & Color Science — 5.1 surround, ACES, HDR, scopes, captions, TTS, EDL/OTIO |
| **v1.4.0** | 2026-03-10 | Motion Graphics & Data Visualization — charts, mockups, motion graphics overlays |
| **v1.3.0** | 2026-03-10 | Advanced Compositing — pre-comps, adjustment layers, masking, expressions, path animation |
| **v1.2.0** | 2026-03-10 | Video Editing — split/join/speed, chroma key, PiP, stabilization, proxy |
| **v1.0.0** | 2026-03-10 | Initial release — core rendering, animation, effects, transitions, particles, 3D |

---

## License

PyMotion is released under the [PyMotion Source Available License 1.0](LICENSE).

**What you can do:**
- Use PyMotion in any project, including commercial products
- Fork the repo and modify the code for your own use
- Contribute back via pull requests

**What you cannot do:**
- Redistribute, rebrand, or republish PyMotion as a standalone library
- Sell, sublicense, or commercially exploit the library itself
- Publish modified versions to any package registry

Read the full [LICENSE](LICENSE) for details.
