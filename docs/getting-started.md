# Getting started

This guide covers the core model you need to understand before writing production code with PyMotion.

## Core concepts

### Composition

A Composition is the root container. It defines the output dimensions, frame rate, and total duration in frames. Every video starts with one.

```python
from pymotion import Composition

comp = Composition(1920, 1080, fps=30, duration=150)
```

The composition holds tracks, manages the render loop, and writes the final output file.

### Clip

A Clip is the atomic visual unit. All clips have a start frame, a duration, a position, scale, rotation, and opacity. PyMotion provides several clip types: ColorClip, GradientClip, ImageClip, VideoClip, TextClip, ShapeClip, Scene3DClip, and many specialized clips for charts, motion graphics, and audio visualization.

```python
from pymotion import ColorClip

bg = ColorClip(color="#1a1a2e")
bg.set_duration(150)
```

Clips use a fluent interface. Methods like `set_duration()`, `set_position()`, `set_scale()`, `set_opacity()`, and `at()` all return the clip, so you can chain them:

```python
card = ColorClip(color="#e94560")
card.set_duration(90).set_position(100.0, 200.0).set_scale(0.5).set_opacity(0.8).at(30)
```

### Track

A Track is a z-ordered layer that holds clips. The first track added to a composition renders at the bottom; the last track renders on top. A track can hold multiple clips that occupy different time ranges.

```python
from pymotion import Track

track = Track(name="background")
track.add(bg)
comp.add_track(track)
```

### Effect

An Effect transforms a clip's rendered frame. Effects are chained: the first effect added runs first, and its output feeds into the next.

```python
from pymotion import GaussianBlur, Vignette

card.add_effect(GaussianBlur(radius=3.0))
card.add_effect(Vignette(strength=0.4))
```

`add_effect()` returns the clip, so you can chain it with other setters.

### Mask

A Mask controls which parts of a clip are visible by modifying its alpha channel. PyMotion supports BezierMask, LinearGradientMask, RadialGradientMask, TrackMatte, and TextMask. Multiple masks combine with boolean operations (add, intersect, subtract).

```python
from pymotion import BezierMask, BezierPoint, MaskOp
from pymotion import Vec2

mask = BezierMask(
    points=[
        BezierPoint(vertex=Vec2(100, 100)),
        BezierPoint(vertex=Vec2(400, 100)),
        BezierPoint(vertex=Vec2(400, 400)),
        BezierPoint(vertex=Vec2(100, 400)),
    ],
    feather=10.0,
)
card.add_mask(mask)
```

### animate()

The `animate()` function creates a two-keyframe animation that changes a value over time. It returns a KeyframeTrack that you can assign to any animatable property.

```python
from pymotion import animate

opacity_track = animate(0.0, 1.0, duration=30, easing="ease_out_cubic")
```

For more complex animations, build a KeyframeTrack with individual Keyframe objects:

```python
from pymotion import Keyframe, KeyframeTrack

track = KeyframeTrack(keyframes=[
    Keyframe(frame=0, value=0.0, easing="ease_in_quad"),
    Keyframe(frame=30, value=1.0, easing="ease_out_quad"),
    Keyframe(frame=90, value=0.0),
])
```

### AudioMixer

Audio is assembled separately from video. Add AudioClip instances to an AudioMixer, configure volume, panning, and effects per track, then pass the mixer to `comp.render()`.

```python
from pymotion import AudioClip, AudioMixer, AudioClipData

mixer = AudioMixer(sample_rate=48000, channels=2)
music = AudioClip("music.wav", volume=0.8)
mixer.add(AudioClipData(music.get_samples(), start_sample=0))
```

### Composition.render()

The render call assembles everything and writes the output file:

```python
comp.render("output.mp4", preset="h264_1080p")
```

You can also export a single frame for inspection:

```python
comp.export_frame(frame=45, output="frame_45.png")
```

## The render pipeline

When you call `comp.render()`, PyMotion resolves the output preset to an FFmpeg encoder configuration, including codec, pixel format, quality settings, and audio codec. It then opens a subprocess pipe to FFmpeg with `shell=False`.

For each frame in the composition's time range, the compositor iterates over tracks in order. For each track, it identifies which clips are active at that frame number (where `clip.start <= frame < clip.start + clip.duration`). Each active clip renders its raw frame as a BGRA uint8 NumPy array, then applies its effect chain in order. If the clip has masks, they are evaluated and composited to produce the final alpha channel. If the clip has expressions, they override the corresponding property values for that frame. If the clip has a parent, the parent's transform is applied before the clip's own transform.

The compositor blends each clip's output onto the background buffer using bounding-box sparse blending. For fully opaque clips with NORMAL blend mode, this is a direct memory copy. For clips with transparency or non-NORMAL blend modes, the compositor uses uint16 fixed-point arithmetic for the alpha blend.

After all tracks are composited, the final BGRA frame is converted to the encoder's pixel format and written to FFmpeg's stdin pipe. Audio, if an AudioMixer is provided, is rendered in parallel and written as a separate stream.

```
Composition.render()
    |
    v
FFmpeg subprocess (stdin pipe)
    |
    v
For each frame:
    |-- Track 1 (bottom)
    |   |-- Clip A: render_frame() -> effects -> masks -> expressions -> transform
    |   |-- Clip B: render_frame() -> effects -> masks -> expressions -> transform
    |-- Track 2
    |   |-- Clip C: ...
    |-- Track N (top)
    |   |-- Clip D: ...
    |
    v
Compositor: sparse bounding-box alpha blend
    |
    v
BGRA -> pixel format conversion -> FFmpeg stdin
    |
    v
output.mp4
```

## Time: frames vs seconds

PyMotion uses integer frame numbers as the primary time unit. All clip start times, durations, keyframe positions, and transition durations are specified in frames.

To convert from seconds to frames: `frame = int(seconds * fps)`.

```python
# A composition at 30 fps lasting 5 seconds
comp = Composition(1920, 1080, fps=30, duration=150)  # 5 * 30 = 150

# A clip that starts at 1 second and lasts 3 seconds
clip.at(30).set_duration(90)  # 1*30=30, 3*30=90
```

AudioClip methods like `trim()`, `fade_in()`, and `fade_out()` accept seconds (float) because audio is sample-based internally. The `at_seconds()` method converts seconds to frames for timeline placement.

```python
audio = AudioClip("voice.wav")
audio.trim(start_sec=1.0, end_sec=5.0)
audio.fade_in(duration_sec=0.5)
audio.at_seconds(2.0, fps=30)  # places at frame 60
```

## Coordinate system

The origin is the top-left corner of the frame. X increases to the right. Y increases downward. Position values are in pixels and refer to the top-left corner of the clip's bounding box.

```
(0,0) ────────────────────── (1920,0)
  |                              |
  |     clip at (100, 200)       |
  |     ┌──────────┐             |
  |     │          │             |
  |     └──────────┘             |
  |                              |
(0,1080) ─────────────────── (1920,1080)
```

The `anchor` property (default `Vec2(0.5, 0.5)`) controls the point around which scale and rotation are applied. An anchor of `(0.5, 0.5)` means the clip rotates and scales around its center.

## Working with color

PyMotion accepts colors in four formats:

```python
from pymotion import Color

# Hex string (RGB or RGBA)
color1 = "#FF5500"
color2 = "#FF550080"  # with alpha

# CSS color name
color3 = "red"

# RGB or RGBA tuple (0-255 integers)
color4 = (255, 85, 0)
color5 = (255, 85, 0, 128)

# Color object (0.0-1.0 floats)
color6 = Color(1.0, 0.33, 0.0, 1.0)
```

Internally, colors are stored as `Color(r, g, b, a)` with float values from 0.0 to 1.0. Frame data uses BGRA uint8 NumPy arrays to match Cairo's ARGB32 format on little-endian systems. Alpha matters whenever you composite clips — a clip with alpha=0 in a region shows the layers below.

## Common patterns

### Fade in, hold, fade out

```python
from pymotion import Composition, ColorClip, Track, Keyframe, KeyframeTrack

comp = Composition(1920, 1080, fps=30, duration=120)
track = Track(name="main")

clip = ColorClip(color="#e94560")
clip.set_duration(120)

# Opacity: 0 -> 1 over 15 frames, hold, 1 -> 0 over 15 frames
opacity = KeyframeTrack(keyframes=[
    Keyframe(frame=0, value=0.0, easing="ease_out_quad"),
    Keyframe(frame=15, value=1.0),
    Keyframe(frame=105, value=1.0, easing="ease_in_quad"),
    Keyframe(frame=120, value=0.0),
])
clip.set_expression("opacity", lambda ctx: opacity.value_at(ctx.frame))

track.add(clip)
comp.add_track(track)
```

### Text that follows a parent clip

```python
from pymotion import Composition, ColorClip, TextClip, NullObject, Track

comp = Composition(1920, 1080, fps=30, duration=90)
track = Track(name="main")

# Null object as a moving anchor
anchor = NullObject()
anchor.set_duration(90).set_position(200.0, 300.0)
anchor.set_expression("position.x", lambda ctx: 200.0 + ctx.frame * 5.0)
track.add(anchor)

# Label follows the anchor
label = TextClip("Moving text", font="Arial", size=32.0, color="#FFFFFF")
label.set_duration(90)
label.parent = anchor
track.add(label)

comp.add_track(track)
```

### Loop a clip for the composition duration

```python
from pymotion import Composition, ColorClip, Track

comp = Composition(1920, 1080, fps=30, duration=300)
track = Track(name="main")

# A 30-frame clip repeated 10 times to fill 300 frames
clip = ColorClip(color="#0f3460")
clip.set_duration(30)
looped = clip.repeat(10)  # 30 frames * 10 = 300 frames
track.add(looped)

comp.add_track(track)
```

### Half-resolution preview render

```python
from pymotion import Composition, ColorClip, TextClip, Track

# Full-resolution composition
comp = Composition(1920, 1080, fps=30, duration=90)
track = Track(name="main")
bg = ColorClip(color="#1a1a2e").set_duration(90)
title = TextClip("Preview", font="Arial", size=48.0, color="#FFFFFF")
title.set_duration(90).set_position(800.0, 500.0)
track.add(bg)
track.add(title)
comp.add_track(track)

# Render at full resolution
comp.render("final.mp4", preset="h264_1080p")

# Render a fast draft at half resolution
draft = Composition(960, 540, fps=30, duration=90)
draft_track = Track(name="main")
draft_bg = ColorClip(color="#1a1a2e").set_duration(90)
draft_track.add(draft_bg)
draft.add_track(draft_track)
draft.render("draft.mp4", preset="h264_fast")
```
