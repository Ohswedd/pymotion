# PyMotion

**Python-native, code-first video generation framework.**

PyMotion lets you create, animate, and render videos entirely from Python code.
No timeline GUIs, no drag-and-drop -- just composable objects, keyframe
animation, and a render pipeline backed by Cairo, FFmpeg, and ModernGL.

## Features

- **Declarative composition** -- build videos from `Composition`, `Track`, and `Clip` objects with a fluent API.
- **Rich clip library** -- `ColorClip`, `TextClip`, `ImageClip`, `VideoClip`, `ShapeClip`, `GradientClip`, and `Scene3DClip`.
- **Clip operations** -- `split`, `join`, `subclip`, `repeat`, `freeze_frame`, `concatenate` with transitions between clips.
- **Speed and time** -- uniform `speed()`, variable `speed_ramp()`, `reverse()`, `time_remap()` with optical flow interpolation.
- **Keyframe animation** -- `Keyframe` and `KeyframeTrack` with 30 built-in easing functions, cubic bezier curves, and physics-based spring animation.
- **Effects pipeline** -- color grading, visual effects, distortions, light effects, and keying (`ChromaKey`, `LumaKey`, `ColorKey`, `DifferenceKey`).
- **Layout helpers** -- `pip()`, `grid()`, `split_screen()`, `stack()` for multi-clip layouts with named anchor positioning.
- **Motion tracking** -- `MotionTracker` for region tracking, `stabilize()` for video stabilization, `follow_tracker()` for data binding.
- **Proxy workflow** -- `create_proxy()` for low-res previews cached on disk, with cache cleanup utilities.
- **39 transitions** -- `Fade`, `CrossDissolve`, `SlideLeft`, `IrisIn`, `Glitch`, `PageTurn`, and many more.
- **Multi-track audio** -- 5.1 surround mixing, bus routing, crossfades, multiband compressor, convolution reverb, LUFS normalization.
- **3D rendering** -- `Scene3D` with Cook-Torrance PBR materials, lights, OBJ loading, and headless ModernGL.
- **Template system** -- subclass `Template` for reusable, parameterized video generators with typed field validation.
- **Export presets** -- 15 built-in presets for H.264, HEVC, ProRes, WebM, GIF, and frame sequences.
- **Animated text** -- `Typewriter`, `KineticText`, `LetterByLetter`, `GlitchText`, `CountUp`, and more.
- **Charts & data viz** -- `BarChartClip`, `LineChartClip`, `PieChartClip`, `AreaChartClip`, `RadarChartClip`, `ScatterPlotClip`, `NumberCounter`, `ProgressBar` with 4 themes.
- **Motion graphics** -- `LowerThird`, `LogoReveal`, `CallToAction`, `SocialHandle`, `Countdown`, `QuoteCard`, `Divider`, `TransitionTitle`, `Watermark`.
- **Device mockups** -- `BrowserMockup`, `PhoneMockup`, `DesktopMockup` for wrapping content clips inside device frames.
- **Audio visualization** -- `WaveformClip`, `SpectrumClip`, `SpectrogramClip`, `AudioReactiveEffect` for animated audio visualizations.
- **Captions & subtitles** -- `AutoCaptions` (Whisper), `SubtitleClip`, SRT/VTT/ASS import/export, 4 caption styles.
- **Text-to-speech** -- `TTSClip` with system (pyttsx3), OpenAI, and ElevenLabs engines.
- **Color science** -- ACES 1.3 pipeline, HDR10/HLG presets, `ColorMatch`, `HSLSecondary`, 4 video scopes.
- **Interchange export** -- EDL (CMX 3600) and OTIO (OpenTimelineIO) export from compositions.

## Installation

### System dependencies

```bash
# macOS
brew install cairo pkg-config ffmpeg

# Ubuntu / Debian
sudo apt install libcairo2-dev pkg-config ffmpeg libfreetype6-dev
```

### Python package

```bash
pip install pymotion-studio
```

The import name is `pymotion`:

```python
from pymotion import Composition, ColorClip, Track
```

For development:

```bash
git clone https://github.com/Ohswedd/pymotion.git
cd pymotion
pip install -e ".[dev]"
```

Requires Python 3.12 or later.

## Quick start

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
comp.render("hello.mp4", preset="h264_1080p")
```

See the [Getting Started](guides/getting-started.md) guide for a full walkthrough.

## Project status

PyMotion v1.5 is stable and in active development. 1784 tests, 87% coverage.
