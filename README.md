# PyMotion

Code-first video generation for Python. Build motion graphics, animated explainers, data visualizations, and production videos entirely in code.

[![CI](https://github.com/Ohswedd/pymotion/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Ohswedd/pymotion/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/pymotion-studio)](https://pypi.org/project/pymotion-studio/)
[![Python](https://img.shields.io/badge/python-3.12%20%7C%203.13%20%7C%203.14-blue)](https://pypi.org/project/pymotion-studio/)
[![License](https://img.shields.io/badge/license-Source%20Available-blue)](https://github.com/Ohswedd/pymotion/blob/main/LICENSE)

## Install

Requires Python 3.12+ and FFmpeg.

```bash
# Install system dependencies
# macOS
brew install ffmpeg cairo pkg-config

# Ubuntu / Debian
sudo apt-get install ffmpeg libcairo2-dev pkg-config libfreetype6-dev

# Windows (chocolatey)
choco install ffmpeg cairo
```

```bash
# Install PyMotion
pip install pymotion-studio

# Optional extras
pip install "pymotion-studio[ai]"            # AI features (rembg, SAM, Real-ESRGAN, MusicGen)
pip install "pymotion-studio[3d-extras]"     # GLTF model loading
pip install "pymotion-studio[gpu-compute]"   # WGPU GPU compositing
pip install "pymotion-studio[dev]"           # Development tools
```

The Python import name is `pymotion`:

```python
from pymotion import Composition, ColorClip, Track
```

## Quick start

```python
from pymotion import (
    Composition, ColorClip, TextClip, Track,
    GaussianBlur, Fade, animate
)

comp = Composition(1920, 1080, fps=30, duration=90)

# Dark background
bg_track = Track(name="bg")
bg = ColorClip(color="#1a1a2e")
bg.set_duration(90)
bg_track.add(bg)

# Colored card with a blur effect
content_track = Track(name="content")
card = ColorClip(color="#e94560")
card.set_duration(60).set_position(360.0, 240.0).set_scale(0.6)
card.add_effect(GaussianBlur(radius=2.0))
content_track.add(card)

# Title text
text_track = Track(name="text")
title = TextClip("Hello, PyMotion", font="Arial", size=64.0, color="#FFFFFF")
title.set_duration(90).set_position(560.0, 480.0)
text_track.add(title)

# Assemble and render
comp.add_track(bg_track)
comp.add_track(content_track)
comp.add_track(text_track)
comp.render("output.mp4", preset="h264_1080p")
```

## What PyMotion can do

PyMotion started as a 2D rendering pipeline with Cairo, then grew into a full video production framework. The core gives you compositions, tracks, clips, keyframe animation with 30 easing functions, and an effect chain that processes BGRA frames through NumPy. Eight blend modes, a sparse bounding-box compositor, and FreeType+HarfBuzz typography are built in.

Video editing operations cover split, join, subclip, repeat, freeze frame, concatenate with transitions, speed control, speed ramp, reverse, and time remap with optical flow interpolation. Four keying effects (chroma, luma, color, difference) handle green screen and isolation work. Layout helpers arrange clips in picture-in-picture, grid, split screen, and stack configurations. Motion tracking and video stabilization use OpenCV under the hood, and a proxy workflow caches low-res versions for fast iteration.

The compositing layer adds nested compositions (pre-comps), adjustment layers, clip parenting with NullObject, a Bezier/gradient/track-matte/text mask system with boolean operations, Python expressions on any animatable property, and SVG path animation with draw-on strokes and path morphing.

Nine motion graphics components (LowerThird, LogoReveal, CallToAction, SocialHandle, Countdown, QuoteCard, Divider, TransitionTitle, Watermark), eight animated chart types, three device mockups, and a number counter and progress bar cover data visualization and overlay needs.

Professional audio includes 5.1 surround mixing with bus routing, twelve DSP effects, LUFS normalization, beat detection, audio-reactive visual effects, Whisper-powered auto-captions with four subtitle styles, and text-to-speech. The color science module provides an ACES 1.3 pipeline, HDR10 and HLG output, secondary color grading, four video scopes, and EDL/OTIO interchange export.

AI features are optional extras that add background removal, object segmentation, upscaling, denoising, face detection and blur, scene detection, content-aware cropping, and AI music and sound effect generation. GPU-accelerated compositing runs through WGPU compute shaders, and hardware encoding supports NVENC, QSV, AMF, and VideoToolbox with automatic detection and software fallback. Distributed rendering uses Ray or Dask backends with frame-level checkpointing.

## Examples

Twelve production-ready scripts ship with the repo, each self-contained with generated assets:

| # | Script | What it demonstrates |
|---|--------|---------------------|
| 01 | `01_core_composition.py` | Composition, tracks, color/gradient/image/shape clips, keyframes, easings, effects, presets, config, profiling |
| 02 | `02_typography.py` | TextClip, Typewriter, WordByWord, LetterByLetter, Scramble, KineticText, CountUp, CountDown, GlitchText, SplitReveal |
| 03 | `03_video_editing.py` | Split, join, subclip, repeat, freeze frame, speed, reverse, concatenate, transitions, PiP, grid, stack, proxy |
| 04 | `04_keying_compositing.py` | ChromaKey, LumaKey, ColorKey, DifferenceKey, adjustment layers, track mattes, color grading, scopes |
| 05 | `05_3d_rendering.py` | Scene3D, Camera, PBR materials, lights, HDRI, SSAO, bloom, depth of field, ACES, tone mapping |
| 06 | `06_particles_vfx.py` | ParticleSystem, Emitter, 6 presets, 15 transitions, distortion/light effects, film grain, motion blur |
| 07 | `07_audio_mixing.py` | AudioMixer, buses, EQ, compressor, reverb, beat detection, waveform/spectrum/spectrogram clips |
| 08 | `08_captions_tts.py` | AutoCaptions, SubtitleClip, SRT/VTT/ASS parsing, TTSClip, caption styles |
| 09 | `09_motion_graphics.py` | LowerThird, LogoReveal, CallToAction, SocialHandle, Countdown, charts, mockups, transitions |
| 10 | `10_advanced_compositing.py` | NullObject, BezierMask, gradient masks, TextMask, expressions, wiggle, StrokeClip, path morph |
| 11 | `11_ai_features.py` | RemoveBackground, Upscale, Denoise, FaceDetector, SceneDetector, AutoColor, MusicGeneration |
| 12 | `12_batch_template.py` | Template ABC, field validation, batch rendering |

```bash
python examples/download_assets.py
python examples/01_core_composition.py
```

## Presets

| Preset | Codec | Format | Quality | Use case |
|--------|-------|--------|---------|----------|
| `h264_1080p` | libx264 | mp4 | CRF 18 | General purpose 1080p |
| `h264_1080p_hq` | libx264 | mp4 | CRF 10 | Archival quality 1080p |
| `h264_fast` | libx264 | mp4 | CRF 22 | Fast draft rendering |
| `h264_4k` | libx264 | mp4 | CRF 18 | 4K delivery |
| `h265_1080p` | libx265 | mp4 | CRF 16 | Smaller file size 1080p |
| `h265_4k` | libx265 | mp4 | CRF 16 | 4K with HEVC |
| `youtube_1080p` | libx264 | mp4 | CRF 10 | YouTube upload (high bitrate) |
| `youtube_4k` | libx265 | mp4 | CRF 14 | YouTube 4K upload |
| `instagram_reel` | libx264 | mp4 | 8 Mbps | Instagram vertical (1080x1920) |
| `tiktok` | libx264 | mp4 | 8 Mbps | TikTok vertical (1080x1920) |
| `webm_1080p` | VP9 | webm | CRF 31 | Web embedding |
| `av1_1080p` | AV1 | webm | CRF 28 | Next-gen web delivery |
| `prores_4444` | ProRes 4444 | mov | Lossless | Post-production with alpha |
| `prores_hq` | ProRes HQ | mov | Near-lossless | Post-production |
| `dnxhd_1080p` | DNxHD | mov | 185 Mbps | Broadcast editing |
| `gif_1080p` | GIF | gif | Palette | Animated previews |
| `frame_sequence_png` | PNG | image2 | Lossless | Frame-by-frame export |
| `h264_nvenc` | H.264 (NVIDIA) | mp4 | VBR | GPU-accelerated (NVIDIA) |
| `h265_nvenc` | H.265 (NVIDIA) | mp4 | VBR | GPU-accelerated HEVC (NVIDIA) |
| `h264_qsv` | H.264 (Intel) | mp4 | Quality 18 | GPU-accelerated (Intel) |
| `h264_amf` | H.264 (AMD) | mp4 | VBR | GPU-accelerated (AMD) |
| `h264_videotoolbox` | H.264 (Apple) | mp4 | Quality 65 | GPU-accelerated (macOS) |

Hardware presets are auto-detected. If the hardware encoder is unavailable, PyMotion falls back to the equivalent software preset.

## System requirements

| Requirement | Details |
|-------------|---------|
| Python | 3.12, 3.13, or 3.14 |
| FFmpeg | Any recent version (tested with 6.x and 7.x) |
| Cairo | Required for 2D rendering (libcairo2 / cairo) |
| pkg-config | Required to locate Cairo headers |
| OpenCV | Optional, needed for motion tracking, stabilization, and optical flow |
| ModernGL | Optional, needed for 3D rendering (installed via pip) |
| WGPU | Optional, needed for GPU compositing (install `[gpu-compute]` extra) |
| AI models | Optional, needed for AI features (install `[ai]` extra) |

No GPU is required for CPU-path rendering. All GPU features detect hardware availability at runtime and fall back to CPU.

Run `pymotion doctor` to verify your environment.

## License

PyMotion is released under the [PyMotion Source Available License 1.0](LICENSE). You can use it in any project, including commercial products. You cannot redistribute, rebrand, or republish the library itself. Read the full [LICENSE](LICENSE) for details.
