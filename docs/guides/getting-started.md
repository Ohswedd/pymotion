# Getting Started

This guide walks you through installing PyMotion, creating your first
composition, adding clips and effects, and rendering to a video file.

## Installation

### System dependencies

PyMotion uses Cairo for 2D rendering and FFmpeg for video encoding. Install
them before the Python package:

```bash
# macOS
brew install cairo pkg-config ffmpeg

# Ubuntu / Debian
sudo apt install libcairo2-dev pkg-config ffmpeg
```

### Install PyMotion

```bash
pip install pymotion-studio
```

The import name is `pymotion` (no hyphen):

```python
from pymotion import Composition, ColorClip, Track
```

For development with linting, type checking, and test tools:

```bash
git clone https://github.com/Ohswedd/pymotion.git
cd pymotion
pip install -e ".[dev]"
```

Python 3.12 or later is required.

## Core concepts

PyMotion uses a small set of composable objects:

- **Composition** -- the root container. Owns the resolution, frame rate,
  duration, background color, and all tracks.
- **Track** -- a named layer of clips composited in z-order. Every composition
  starts with a default track.
- **Clip** -- a visual element (color, text, image, video, shape, gradient, or
  3D scene). Clips have a start frame, duration, position, opacity, blend
  mode, and optional effects.

All durations and times are specified in **frames** (integers). To convert
from seconds, multiply by the fps: `3 * 30 = 90 frames`.

## Your first composition

```python
from pymotion import Composition, ColorClip, TextClip

# 1920x1080, 30 fps, 5 seconds (150 frames)
comp = Composition(1920, 1080, fps=30, duration=150)

# Solid background
bg = ColorClip("#0f0f23")
bg.set_duration(150)
comp.add(bg)

# Centered title
title = TextClip("Welcome to PyMotion", font_size=64, color="#ffffff")
title.set_position(960, 540)
title.set_duration(150)
comp.add(title)

# Render
comp.render("first_video.mp4")
```

The `render()` method encodes every frame through FFmpeg and writes the output
file. The default preset is `h264_1080p`.

## Adding multiple clips

Clips are layered in the order they are added -- later clips draw on top.

```python
from pymotion import Composition, ColorClip, ShapeClip, TextClip

comp = Composition(1920, 1080, fps=30, duration=90)

# Background
bg = ColorClip("#1b1b2f")
bg.set_duration(90)

# A circle shape
circle = ShapeClip.circle(radius=100, color="#e94560")
circle.set_position(960, 540)
circle.set_duration(90)

# Label
label = TextClip("Play", font_size=36, color="#ffffff")
label.set_position(960, 540)
label.set_duration(90)

comp.add(bg, circle, label)
comp.render("layered.mp4")
```

## Using tracks

For complex compositions, organize clips into named tracks:

```python
from pymotion import Composition, Track, ColorClip, TextClip

comp = Composition(1920, 1080, fps=30, duration=120)

bg_track = Track(name="background")
bg = ColorClip("#162447")
bg.set_duration(120)
bg_track.add(bg)

text_track = Track(name="titles")
title = TextClip("Chapter 1", font_size=48, color="#e43f5a")
title.set_position(960, 300)
title.set_duration(120)
text_track.add(title)

comp.add_track(bg_track)
comp.add_track(text_track)
comp.render("tracks.mp4")
```

Tracks have their own `visible`, `opacity`, and `blend_mode` properties.

## Applying effects

Effects are added to clips with the `add_effect()` method:

```python
from pymotion import (
    Composition, ColorClip, TextClip,
    GaussianBlur, Brightness, Vignette,
)

comp = Composition(1920, 1080, fps=30, duration=90)

bg = ColorClip("#2c003e")
bg.set_duration(90)
bg.add_effect(Vignette(strength=0.6))

title = TextClip("Glow", font_size=96, color="#ff6f91")
title.set_position(960, 540)
title.set_duration(90)
title.add_effect(GaussianBlur(radius=2.0))
title.add_effect(Brightness(value=1.2))

comp.add(bg, title)
comp.render("effects.mp4")
```

## Exporting a single frame

Use `export_frame()` to save a PNG snapshot without encoding an entire video:

```python
comp.export_frame(frame=45, output="snapshot.png")
```

## Export presets

PyMotion ships with 15 export presets. Pass the preset name to `render()`:

```python
comp.render("output.mp4", preset="h264_1080p")
comp.render("output.webm", preset="vp9_1080p")
comp.render("output.mov", preset="prores_422")
comp.render("output.gif", preset="gif_480p")
```

## Next steps

- [Clip Operations](clip-operations.md) -- split, join, speed, reverse, and time-remap clips.
- [Keying Effects](keying.md) -- chroma key, luma key, color key, and difference key.
- [Layout, Tracking & Proxy](layout-tracking-proxy.md) -- PiP, grid, split screen, motion tracking, stabilization, and proxy workflow.
- [Keyframe Animation](keyframe-animation.md) -- animate any property over time.
- [Audio Mixing](audio-mixing.md) -- add music, sound effects, and voice-overs.
- [3D Scenes](3d-scenes.md) -- render 3D models with PBR materials.
- [Batch Generation](batch-generation.md) -- use templates for data-driven videos.
