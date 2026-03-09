# PyMotion

A Python-native, code-first video generation framework for producing
professional-grade video content entirely through Python code.

## Features

| Category | Highlights |
|----------|-----------|
| **2D Rendering** | Color, image, shape, gradient, and text clips with Cairo backend |
| **3D Rendering** | PBR materials, multiple light types, SSAO/bloom/DOF post-FX (ModernGL) |
| **Animation** | Keyframe tracks, 30+ easings, spring physics, cubic bezier |
| **Typography** | FreeType + HarfBuzz, variable fonts, animated text presets |
| **Audio** | Mixing, EQ/compressor/limiter, beat detection, waveform analysis |
| **Effects** | 30+ visual/color/distortion/light effects |
| **Transitions** | 39 built-in transitions (fade, slide, wipe, zoom, glitch, etc.) |
| **Particles** | 9 presets (fire, sparkles, confetti, rain, smoke, etc.) |
| **Export** | 15 presets (H.264, H.265, ProRes, AV1, WebM, GIF, frame sequences) |
| **Templates** | Reusable templates with validation for batch generation |
| **Color Pipeline** | LUT support, lift/gamma/gain grading, ACES/Reinhard/Filmic tone mapping |
| **CLI** | render, preview, benchmark, validate, doctor, new |

## Installation

### Prerequisites

- Python 3.11+
- FFmpeg
- Cairo (`brew install cairo pkg-config` on macOS)

### Install

```bash
pip install pymotion
```

With optional extras:

```bash
pip install "pymotion[3d-extras]"   # GLTF support
pip install "pymotion[dev]"         # Development tools
```

## Quick Start

```python
from pymotion import Composition, ColorClip, TextClip, Fade

# Create a 1080p, 30fps, 5-second composition
comp = Composition(1920, 1080, fps=30, duration=150)

# Add a background
bg = ColorClip(color="#1a1a2e", duration=150, width=1920, height=1080)
comp.add(bg)

# Add text
title = TextClip("Hello, PyMotion!", font="Arial", size=72.0, color="#FFFFFF")
title.set_position(960, 540).set_duration(150)
comp.add(title)

# Render to file
comp.render("output.mp4", preset="h264_1080p")
```

## Batch Generation with Templates

```python
from pymotion import Template, Composition, ColorClip

class ProductTemplate(Template):
    product_name: str
    brand_color: str = "#FF5500"

    def build(self) -> Composition:
        comp = Composition(1920, 1080, fps=30, duration=150)
        bg = ColorClip(color=self.brand_color, duration=150, width=1920, height=1080)
        comp.add(bg)
        return comp

# Batch render
for product in ["Widget", "Gadget", "Tool"]:
    tpl = ProductTemplate(product_name=product)
    tpl.render(f"{product.lower()}.mp4")
```

## CLI Usage

```bash
# Render a composition
pymotion render comp.py -o output.mp4 -p h264_1080p

# Export a single frame
pymotion export-frame comp.py -f 30 -o frame.png

# Benchmark performance
pymotion benchmark comp.py -n 100

# Check system dependencies
pymotion doctor

# Create a new project
pymotion new my-project
```

## System Dependencies

| Dependency | Purpose | Install |
|-----------|---------|---------|
| FFmpeg | Video encoding | `brew install ffmpeg` |
| Cairo | 2D rendering | `brew install cairo pkg-config` |
| FreeType | Font rendering | Included with freetype-py |
| ModernGL | 3D rendering | Installed via pip |

## Development

```bash
git clone https://github.com/your-org/pymotion.git
cd pymotion
pip install -e ".[dev]"

# Run checks
ruff format pymotion/ tests/
ruff check pymotion/ tests/
mypy --strict pymotion/
pytest tests/ -v
```

## License

MIT
