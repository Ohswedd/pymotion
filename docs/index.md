# PyMotion

**Python-native, code-first video generation framework.**

PyMotion lets you create, animate, and render videos entirely from Python code.
No timeline GUIs, no drag-and-drop -- just composable objects, keyframe
animation, and a render pipeline backed by Cairo, FFmpeg, and ModernGL.

## Features

- **Declarative composition** -- build videos from `Composition`, `Track`, and `Clip` objects with a fluent API.
- **Rich clip library** -- `ColorClip`, `TextClip`, `ImageClip`, `VideoClip`, `ShapeClip`, `GradientClip`, and `Scene3DClip`.
- **Keyframe animation** -- `Keyframe` and `KeyframeTrack` with 30 built-in easing functions, cubic bezier curves, and physics-based spring animation.
- **Effects pipeline** -- color grading (`Brightness`, `Contrast`, `Saturation`, `LUTEffect`), visual effects (`GaussianBlur`, `Bloom`, `FilmGrain`), distortions (`Fisheye`, `Twirl`, `Ripple`), and light effects (`NeonGlow`, `GodRays`, `LensFlare`).
- **39 transitions** -- `Fade`, `CrossDissolve`, `SlideLeft`, `IrisIn`, `Glitch`, `PageTurn`, and many more.
- **Multi-track audio** -- `AudioClip` with trim, fade, loop, and pan; `AudioMixer` with per-track volume automation and equal-power panning.
- **3D rendering** -- `Scene3D` with Cook-Torrance PBR materials, point and directional lights, OBJ model loading, and headless ModernGL rendering.
- **Template system** -- subclass `Template` to build reusable, parameterized video generators with typed field validation.
- **Export presets** -- 15 built-in presets for H.264, HEVC, ProRes, WebM, GIF, and frame sequences.
- **Animated text** -- `Typewriter`, `KineticText`, `LetterByLetter`, `GlitchText`, `CountUp`, and more.

## Installation

### System dependencies

```bash
# macOS
brew install cairo pkg-config ffmpeg

# Ubuntu / Debian
sudo apt install libcairo2-dev pkg-config ffmpeg
```

### Python package

```bash
pip install pymotion
```

For development:

```bash
git clone https://github.com/your-org/pymotion.git
cd pymotion
pip install -e ".[dev]"
```

Requires Python 3.11 or later.

## Quick start

```python
from pymotion import Composition, ColorClip, TextClip

# Create a 5-second 1080p composition at 30 fps
comp = Composition(1920, 1080, fps=30, duration=150)

# Add a blue background
bg = ColorClip("#1a1a2e")
bg.set_duration(150)
comp.add(bg)

# Add a title
title = TextClip("Hello, PyMotion!", font_size=72, color="#e94560")
title.set_position(960, 540)
title.set_duration(150)
comp.add(title)

# Render to file
comp.render("hello.mp4")
```

See the [Getting Started](guides/getting-started.md) guide for a full walkthrough.

## Project status

PyMotion is in active development (v0.9.0-rc). The API is stabilizing but may
have minor changes before 1.0.
