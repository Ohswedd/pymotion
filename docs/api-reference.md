# PyMotion API Reference

Complete reference for all public classes, functions, and constants in the PyMotion framework.

---

## Composition and Rendering

### Composition

The top-level container that holds tracks, clips, and renders the final output.

```python
Composition(
    width: int = 1920,
    height: int = 1080,
    fps: int = 30,
    duration: int = 90,
    background: ColorInput = "#000000",
)
```

**Methods:**

| Method | Signature | Description |
|--------|-----------|-------------|
| `add` | `(*clips: Clip) -> Composition` | Creates a track and adds clips to it. |
| `add_track` | `(track: Track) -> Composition` | Adds an existing track to the composition. |
| `render` | `(output: str \| Path, preset: str = "h264_1080p", start: int = 0, end: int \| None = None, *, backend: str = "local", checkpoint_path: str \| Path \| None = None, profile: bool = False) -> Path` | Renders the composition to a video file. |
| `export_frame` | `(frame: int, output: str \| Path) -> Path` | Exports a single frame as an image. |
| `export_edl` | `(path: str \| Path) -> None` | Exports the timeline as an EDL file. |
| `export_otio` | `(path: str \| Path) -> None` | Exports the timeline as an OpenTimelineIO file. |
| `to_clip` | `() -> CompositionClip` | Wraps this composition as a clip for nesting. |

### Track

A layer within a composition that holds clips.

```python
Track(
    name: str = "default",
    clips: list[Clip] = [],
    visible: bool = True,
    opacity: float = 1.0,
    blend_mode: BlendMode = BlendMode.NORMAL,
)
```

**Methods:**

| Method | Signature | Description |
|--------|-----------|-------------|
| `add` | `(*clips: Clip) -> Track` | Adds one or more clips to the track. |

### AdjustmentLayer

Extends `Clip`. Applies its effects to all layers below it in the stack.

```python
AdjustmentLayer(effects: list[Effect] | None = None)
```

### CompositionClip

Wraps a `Composition` as a `Clip` for nesting. Supports up to 10 levels of nesting depth.

### OutputPreset

Defines an encoding preset for rendering.

```python
OutputPreset(
    name, codec, pixel_format, crf, bitrate,
    audio_codec, audio_bitrate, container, extra_flags,
)
```

### get_preset

Returns a named output preset.

```python
get_preset(name: str) -> OutputPreset
```

Raises `ValueError` if the preset name is not found.

---

## Configuration

### PyMotionConfig

Thread-safe global configuration. Frozen dataclass.

```python
PyMotionConfig(
    allow_network,
    cache_max_bytes,
    max_image_size,
    max_audio_size,
    max_model_size,
    gpu_compositing,
    gpu_vram_limit_bytes,
    font_allowlist,
)
```

### Config Functions

| Function | Signature | Description |
|----------|-----------|-------------|
| `get_config` | `() -> PyMotionConfig` | Returns the current global configuration. |
| `set_config` | `(config: PyMotionConfig) -> None` | Sets the global configuration. |
| `reset_config` | `() -> None` | Resets to the default configuration. |

---

## Core Types

### BlendMode

Enumeration of compositing blend modes.

| Value | Description |
|-------|-------------|
| `NORMAL` | Standard alpha compositing. |
| `MULTIPLY` | Multiplies source and destination. |
| `SCREEN` | Inverse multiply (lightens). |
| `OVERLAY` | Combines multiply and screen. |
| `ADD` | Additive blending. |
| `SOFT_LIGHT` | Soft light compositing. |
| `HARD_LIGHT` | Hard light compositing. |
| `DIFFERENCE` | Absolute difference of layers. |

### Align

Enumeration of spatial alignment positions.

| Value | Value | Value |
|-------|-------|-------|
| `TOP_LEFT` | `TOP_CENTER` | `TOP_RIGHT` |
| `CENTER_LEFT` | `CENTER` | `CENTER_RIGHT` |
| `BOTTOM_LEFT` | `BOTTOM_CENTER` | `BOTTOM_RIGHT` |
| `LEFT` | `RIGHT` | `TOP` |
| `BOTTOM` | | |

### Resolution

Frozen dataclass representing a frame resolution. Validates that width and height are even and positive.

```python
Resolution(width: int, height: int)
```

### TimeRange

Frozen dataclass representing a range of frames.

```python
TimeRange(start: int, end: int)
```

**Properties:**

- `duration` -- Number of frames in the range.

### RenderContext

Frozen dataclass passed to effects and expressions during rendering.

```python
RenderContext(
    frame: int,
    fps: int,
    resolution: Resolution,
    time_range: TimeRange,
    local_frame: int,
    progress: float,
)
```

### NullObject

An invisible clip used for transform grouping. Other clips can parent to a NullObject to inherit its transforms.

```python
NullObject()
```

### Color

Represents an RGBA color with float components in the 0.0--1.0 range.

```python
Color(r: float, g: float, b: float, a: float = 1.0)
```

**Class Methods:**

| Method | Signature | Description |
|--------|-----------|-------------|
| `parse` | `(value) -> Color` | Parses hex strings, CSS color names, RGB/RGBA tuples, or Color instances. |

### Vec2

A 2D vector.

```python
Vec2(x: float, y: float)
```

### Vec3

A 3D vector.

```python
Vec3(x: float, y: float, z: float)
```

---

## Clips

### Clip (Base Class)

All clips inherit from `Clip`. The base class provides the following fluent methods that return `Self`:

| Method | Signature | Description |
|--------|-----------|-------------|
| `set_duration` | `(frames: int) -> Self` | Sets clip duration in frames. |
| `set_position` | `(x, y) -> Self` | Sets the position. |
| `set_scale` | `(sx, sy=None) -> Self` | Sets scale; if `sy` is None, uniform scale. |
| `set_rotation` | `(deg) -> Self` | Sets rotation in degrees. |
| `set_opacity` | `(v) -> Self` | Sets opacity (0.0--1.0). |
| `at` | `(frame) -> Self` | Offsets the clip start to the given frame. |
| `add_effect` | `(effect) -> Self` | Adds an effect to the clip. |
| `add_mask` | `(mask, op=None) -> Self` | Adds a mask to the clip. |
| `set_expression` | `(prop, fn) -> Self` | Attaches an expression to a property. |

**Properties:**

- `parent` (get/set) -- Parent clip for transform inheritance.

### ColorClip

Generates a solid color frame.

```python
ColorClip(color: ColorInput = "#000000")
```

### GradientClip

Generates a gradient frame (linear or radial).

```python
GradientClip(
    color_start: ColorInput,
    color_end: ColorInput,
    direction: float = 0.0,
    *,
    gradient_type: str = "linear",
    center_x: float = 0.5,
    center_y: float = 0.5,
    radius: float = 0.5,
)
```

### ImageClip

Loads a still image as a clip.

```python
ImageClip(source: str | Path, *, fit_mode: str = "contain")
```

### VideoClip

Loads a video file as a clip.

```python
VideoClip(
    source: str | Path,
    *,
    trim_start: float = 0.0,
    trim_end: float | None = None,
    speed_factor: float = 1.0,
    reverse: bool = False,
    loop: int = 1,
)
```

### TextClip

Renders text using Cairo.

```python
TextClip(
    text: str = "",
    *,
    font: str = "Arial",
    size: float = 24.0,
    color: ColorInput = "#FFFFFF",
    letter_spacing: float = 0.0,
    line_height: float = 1.2,
    align: str = "left",
    max_width: int | None = None,
    stroke_color: ColorInput | None = None,
    stroke_width: float = 0.0,
    shadow: Shadow | None = None,
)
```

### Shadow

Text shadow configuration.

```python
Shadow(
    color: Color,
    offset_x: float = 2.0,
    offset_y: float = 2.0,
    blur: float = 3.0,
)
```

### AudioClip

Loads an audio file.

```python
AudioClip(
    source: str | Path,
    *,
    volume: float = 1.0,
    pan: float = 0.0,
    sample_rate: int = 48000,
)
```

### Silence

Generates silent audio.

```python
Silence(
    duration_sec: float = 1.0,
    sample_rate: int = 48000,
    channels: int = 2,
)
```

### ShapeClip

Creates vector shapes via factory methods. Do not instantiate directly.

| Factory Method | Signature |
|----------------|-----------|
| `.rect` | `(x, y, w, h, fill)` |
| `.circle` | `(cx, cy, r, fill)` |
| `.ellipse` | `(cx, cy, rx, ry, fill)` |
| `.polygon` | `(points, fill)` |
| `.line` | `(x1, y1, x2, y2, color, width)` |

---

## Clip Operations

Methods available on all clip instances, plus the standalone `concatenate` function.

| Operation | Signature | Returns | Description |
|-----------|-----------|---------|-------------|
| `clip.split` | `(frame) -> tuple[SubClip, SubClip]` | Two sub-clips | Splits at the given frame. |
| `clip.join` | `(other) -> JoinedClip` | Joined clip | Joins two clips sequentially. |
| `clip.subclip` | `(start, end) -> SubClip` | Sub-clip | Extracts a frame range. |
| `clip.repeat` | `(n: int) -> RepeatedClip` | Repeated clip | Repeats the clip `n` times (n >= 1). |
| `clip.freeze_frame` | `(frame, duration) -> FreezeFrameClip` | Frozen clip | Holds a single frame for a duration. |
| `clip.speed` | `(factor, interpolation="nearest") -> SpeedClip` | Speed clip | Changes playback speed. |
| `clip.speed_ramp` | `(keyframes: list[tuple[int, float]]) -> SpeedRampClip` | Ramped clip | Variable speed over time. |
| `clip.reverse` | `() -> ReversedClip` | Reversed clip | Reverses playback. |
| `clip.time_remap` | `(curve: KeyframeTrack) -> TimeRemappedClip` | Remapped clip | Arbitrary time remapping via keyframes. |

### concatenate

Joins a sequence of clips with optional transitions.

```python
concatenate(
    clips,
    transition=None,
    transition_duration=15,
) -> ConcatenatedClip
```

---

## Animation

### Keyframe

A single keyframe in an animation track.

```python
Keyframe(
    frame: int,
    value: AnimatableValue,
    easing: str = "linear",
)
```

### KeyframeTrack

An ordered collection of keyframes that defines an animation curve.

```python
KeyframeTrack(keyframes: list[Keyframe])
```

**Methods:**

| Method | Signature | Description |
|--------|-----------|-------------|
| `add` | `(kf: Keyframe) -> None` | Adds a keyframe to the track. |
| `value_at` | `(frame: int) -> AnimatableValue` | Evaluates the interpolated value at a frame. |

### animate

Convenience function to create a KeyframeTrack from start and end values.

```python
animate(
    start,
    end,
    duration,
    *,
    easing: str = "linear",
    delay: int = 0,
) -> KeyframeTrack
```

### AnimatableValue

Type alias: `float | Color | Vec2 | Vec3`

### interpolate

Interpolates between two animatable values.

```python
interpolate(a, b, t) -> AnimatableValue
```

### Easing Functions

All 30 built-in easing functions are available by name via `get_easing()`.

| Family | In | Out | In-Out |
|--------|----|-----|--------|
| Quad | `ease_in_quad` | `ease_out_quad` | `ease_in_out_quad` |
| Cubic | `ease_in_cubic` | `ease_out_cubic` | `ease_in_out_cubic` |
| Quart | `ease_in_quart` | `ease_out_quart` | `ease_in_out_quart` |
| Quint | `ease_in_quint` | `ease_out_quint` | `ease_in_out_quint` |
| Sine | `ease_in_sine` | `ease_out_sine` | `ease_in_out_sine` |
| Expo | `ease_in_expo` | `ease_out_expo` | `ease_in_out_expo` |
| Circ | `ease_in_circ` | `ease_out_circ` | `ease_in_out_circ` |
| Back | `ease_in_back` | `ease_out_back` | `ease_in_out_back` |
| Elastic | `ease_in_elastic` | `ease_out_elastic` | `ease_in_out_elastic` |
| Bounce | `ease_in_bounce` | `ease_out_bounce` | `ease_in_out_bounce` |

Additionally, `linear` is always available.

### Easing Utility Functions

| Function | Signature | Description |
|----------|-----------|-------------|
| `get_easing` | `(name: str) -> EasingFn` | Returns an easing function by name. |
| `cubic_bezier` | `(x1, y1, x2, y2) -> EasingFn` | Creates a cubic bezier easing curve. |
| `spring` | `(stiffness=180.0, damping=12.0, mass=1.0) -> EasingFn` | Creates a spring physics easing. |
| `steps` | `(n: int, direction="end") -> EasingFn` | Creates a stepped easing function. |

---

## Effects

### Blur and Sharpen

| Effect | Signature | Description |
|--------|-----------|-------------|
| `GaussianBlur` | `(radius=5.0)` | Applies a Gaussian blur. |
| `MotionBlur` | `(angle=0.0, distance=10.0)` | Applies directional motion blur. |
| `Sharpen` | `(amount=1.0)` | Sharpens the image. |

### Stylize

| Effect | Signature | Description |
|--------|-----------|-------------|
| `Vignette` | `(strength=0.5, radius=0.8, feather=0.3)` | Darkens frame edges. |
| `FilmGrain` | `(strength=0.3, size=1.0, monochrome=True)` | Adds film grain noise. |
| `ChromaticAberration` | `(offset=3.0, angle=0.0)` | Simulates lens chromatic aberration. |
| `Glow` | `(radius=10.0, strength=0.5, threshold=200.0)` | Adds a soft glow to bright areas. |
| `Bloom` | `(radius=10.0, strength=0.5, threshold=200.0, iterations=3)` | Multi-pass bloom effect. |
| `LensFlare` | `(position=None, intensity=0.8, color="#FFE6B3")` | Renders a lens flare. |
| `BleachBypass` | `(strength=0.5)` | Simulates bleach bypass film processing. |

### Color Correction

| Effect | Signature | Description |
|--------|-----------|-------------|
| `Brightness` | `(value=1.0)` | Adjusts brightness. |
| `Contrast` | `(value=1.0)` | Adjusts contrast. |
| `Saturation` | `(value=1.0)` | Adjusts saturation. |
| `HueSaturationLuminance` | `(hue=0.0, saturation=1.0, luminance=0.0)` | HSL adjustment. |
| `ColorBalance` | `(shadows, midtones, highlights)` | Three-way color balance. |
| `Curves` | `(rgb_curve, r_curve, g_curve, b_curve)` | RGB curves adjustment. |
| `LUTEffect` | `(lut_path, intensity=1.0)` | Applies a .cube LUT file. |
| `SplitToning` | `(highlights_color, shadows_color, balance=0.0)` | Split toning for highlights and shadows. |

### Distortion

| Effect | Signature | Description |
|--------|-----------|-------------|
| `WaveWarp` | `(amplitude=10.0, frequency=0.05, phase=0.0, axis="x")` | Applies a wave distortion. |
| `Ripple` | `(center, amplitude=10.0, frequency=0.1, decay=0.01)` | Concentric ripple distortion. |
| `Twirl` | `(center, angle=1.0, radius=100.0)` | Twirl distortion from a center point. |
| `PerspectiveWarp` | `(corners)` | Four-corner perspective transform. |
| `Fisheye` | `(strength=0.5)` | Barrel distortion (fisheye lens). |

### Keying

| Effect | Signature | Description |
|--------|-----------|-------------|
| `ChromaKey` | `(color="#00FF00", tolerance=0.3, edge_softness=0.0, spill_suppression=0.5)` | Green/blue screen removal. |
| `LumaKey` | `(threshold=0.5, softness=0.1, invert=False)` | Key based on luminance. |
| `ColorKey` | `(color, tolerance=0.3, softness=0.1)` | Key based on a specific color. |
| `DifferenceKey` | `(reference, tolerance=0.2, softness=0.1)` | Key based on difference from a reference frame. |

### Lighting

| Effect | Signature | Description |
|--------|-----------|-------------|
| `GodRays` | `(position, intensity=0.5, decay=0.95, samples=50)` | Volumetric light rays. |
| `NeonGlow` | `(color, radius=8.0, strength=0.7, threshold=50.0)` | Neon-colored glow effect. |
| `LensFlareLight` | `(position, intensity=0.8, color="#FFF2CC")` | Light-source lens flare. |
| `LightLeak` | `(color, position, intensity=0.5, size=0.4)` | Simulates light leak on film. |

---

## Transitions

All transitions accept `duration: int = 30` (frames). Use with `concatenate()` or between clips.

### Basic

| Transition | Parameters | Description |
|------------|------------|-------------|
| `Fade` | | Fades between clips. |
| `FadeToBlack` | | Fades out to black, then fades in. |
| `FadeToWhite` | | Fades out to white, then fades in. |
| `DipToColor` | `color` | Fades through a specified color. |
| `CrossDissolve` | | Cross-dissolve between clips. |
| `Cut` | | Hard cut (no transition effect). |

### Slide

| Transition | Description |
|------------|-------------|
| `SlideLeft` | Slides incoming clip from the right. |
| `SlideRight` | Slides incoming clip from the left. |
| `SlideUp` | Slides incoming clip from below. |
| `SlideDown` | Slides incoming clip from above. |

### Push

| Transition | Description |
|------------|-------------|
| `PushLeft` | Pushes outgoing clip to the left. |
| `PushRight` | Pushes outgoing clip to the right. |
| `PushUp` | Pushes outgoing clip upward. |
| `PushDown` | Pushes outgoing clip downward. |

### Cover

| Transition | Description |
|------------|-------------|
| `CoverLeft` | Incoming clip covers from the right. |
| `CoverRight` | Incoming clip covers from the left. |
| `CoverUp` | Incoming clip covers from below. |
| `CoverDown` | Incoming clip covers from above. |

### Reveal

| Transition | Description |
|------------|-------------|
| `RevealLeft` | Outgoing clip reveals by sliding left. |
| `RevealRight` | Outgoing clip reveals by sliding right. |
| `RevealUp` | Outgoing clip reveals by sliding up. |
| `RevealDown` | Outgoing clip reveals by sliding down. |

### Wipe

| Transition | Description |
|------------|-------------|
| `WipeLeft` | Wipe from right to left. |
| `WipeRight` | Wipe from left to right. |
| `WipeDiagonal` | Diagonal wipe. |
| `CircularWipe` | Circular wipe from center. |

### Zoom

| Transition | Description |
|------------|-------------|
| `ZoomIn` | Zooms into the incoming clip. |
| `ZoomOut` | Zooms out to the incoming clip. |
| `ZoomBlur` | Zoom with motion blur. |
| `ScaleDissolve` | Dissolve with scaling. |

### Iris

| Transition | Description |
|------------|-------------|
| `IrisIn` | Iris opens to reveal incoming clip. |
| `IrisOut` | Iris closes over outgoing clip. |

### Advanced

| Transition | Parameters | Description |
|------------|------------|-------------|
| `PixelDissolve` | `seed=42` | Random pixel-by-pixel dissolve. |
| `Glitch` | `seed=42` | Glitch-style transition. |
| `FilmBurn` | | Simulates film burn. |
| `PageTurn` | | 3D page turn effect. |
| `Vortex` | | Spiral vortex transition. |
| `Shatter` | `seed=42, grid_size=6` | Shatters outgoing clip into pieces. |
| `MorphWarp` | | Morph-warp between clips. |

---

## Masking

### BezierPoint

A point on a bezier path with optional control handles.

```python
BezierPoint(
    vertex: Vec2,
    in_handle=None,
    out_handle=None,
)
```

### BezierMask

A freeform mask defined by bezier points.

```python
BezierMask(
    points,
    feather=0.0,
    expansion=0.0,
    invert=False,
    opacity=1.0,
)
```

### LinearGradientMask

A gradient mask along a line.

```python
LinearGradientMask(
    start, end,
    feather, expansion, invert, opacity,
)
```

### RadialGradientMask

A gradient mask radiating from a center point.

```python
RadialGradientMask(
    center, radius,
    feather, expansion, invert, opacity,
)
```

### TrackMatte

Uses another clip as a mask source.

```python
TrackMatte(
    source,
    mode="alpha",
    feather, expansion, invert, opacity,
)
```

### TextMask

Uses rendered text as a mask.

```python
TextMask(
    text, font,
    size=48.0,
    feather, expansion, invert, opacity,
)
```

### MaskGroup

Groups a mask with an operation for combining with other masks on a clip.

```python
MaskGroup(mask, op=MaskOp.ADD)
```

### MaskOp

Enumeration of mask combination operations.

| Value | Description |
|-------|-------------|
| `ADD` | Union of masks. |
| `INTERSECT` | Intersection of masks. |
| `SUBTRACT` | Subtracts the mask from existing masks. |

---

## Audio

### AudioMixer

Central audio mixing engine.

```python
AudioMixer(
    sample_rate: int = 48000,
    bit_depth: int = 24,
    channels: int = 2,
)
```

**Methods:**

| Method | Description |
|--------|-------------|
| `.add()` | Adds an audio clip to the mixer. |
| `.set_volume()` | Sets volume for a clip or bus. |
| `.set_pan()` | Sets stereo pan for a clip or bus. |
| `.create_bus()` | Creates a named audio bus. |
| `.normalize()` | Normalizes audio levels. |
| `.sidechain()` | Applies sidechain compression. |
| `.render()` | Renders the mixed audio. |

### AudioBus

A named audio bus for routing and grouping.

```python
AudioBus(name, volume=1.0, pan=0.0)
```

### AudioClipData

Raw audio sample data.

```python
AudioClipData(samples, start_sample=0, sample_rate=48000)
```

### Audio Effects

| Effect | Signature | Description |
|--------|-----------|-------------|
| `EQ` | `(bands)` | Parametric equalizer. |
| `EQBand` | `(frequency=1000.0, gain_db=0.0, q=1.0, band_type="peak")` | A single EQ band. |
| `Compressor` | `(threshold_db=-20.0, ratio=4.0, attack_ms=10.0, release_ms=100.0)` | Dynamic range compressor. |
| `Limiter` | `(threshold_db=-1.0, release_ms=100.0)` | Brick-wall limiter. |
| `Reverb` | `(room_size=0.5, damping=0.5, wet_level=0.33, dry_level=0.4)` | Algorithmic reverb. |
| `Delay` | `(delay_seconds=0.25, feedback=0.3, mix=0.5)` | Echo/delay effect. |
| `PitchShift` | `(semitones=0.0)` | Shifts pitch by semitones. |
| `NoiseReduction` | `(threshold_db, ratio, attack_ms, release_ms)` | Reduces background noise. |
| `LowPassFilter` | `(cutoff_hz=5000.0)` | Low-pass frequency filter. |
| `HighPassFilter` | `(cutoff_hz=200.0)` | High-pass frequency filter. |
| `MultibandCompressor` | `(crossover_freqs, thresholds_db, ratios, attack_ms, release_ms, makeup_gain_db)` | Multi-band dynamic compression. |
| `ConvolutionReverb` | `(ir_path, wet=0.3, dry=1.0, pre_delay_ms=0.0)` | Reverb using an impulse response file. |

### audio_crossfade

Crossfades between two audio clips.

```python
audio_crossfade(clip_a, clip_b, crossfade_samples, curve="linear")
```

### Audio Analysis

| Class/Function | Signature | Description |
|----------------|-----------|-------------|
| `BeatDetector` | `.detect(audio, sample_rate, fps) -> list[int]` | Detects beat positions as frame numbers. |
| `OnsetDetector` | `.detect(audio, sample_rate, fps) -> list[int]` | Detects audio onsets as frame numbers. |
| `WaveformExtractor` | `.extract(audio, n_points) -> ndarray` | Extracts waveform amplitude data. |
| `waveform_to_keyframes` | `(audio, sample_rate, fps, min_value, max_value, smoothing) -> list[tuple[int, float]]` | Converts audio amplitude to animation keyframes. |

### Audio Visualization Clips

| Clip | Signature | Description |
|------|-----------|-------------|
| `WaveformClip` | `(audio, style, color, background, sample_rate, line_width)` | Renders an animated waveform. |
| `SpectrumClip` | `(audio, bands=32, style, color_map, background, sample_rate)` | Renders a frequency spectrum. |
| `SpectrogramClip` | `(audio, style, fft_size, sample_rate, color_low, color_high)` | Renders a spectrogram. |
| `AudioReactiveEffect` | `(effect, audio, property_name, band, sensitivity, sample_rate, min_value, max_value)` | Drives any effect property from audio. |

---

## Captions and TTS

### CaptionSegment

A single caption with timing.

```python
CaptionSegment(text, start_sec, end_sec, words=None)
```

### WordTimestamp

Per-word timing within a caption.

```python
WordTimestamp(word, start_sec, end_sec)
```

### AutoCaptions

Generates captions from an audio clip using speech recognition.

```python
AutoCaptions(audio_clip, model, style)
```

### SubtitleClip

Renders subtitles from an SRT file.

```python
SubtitleClip(srt_path, style, fps)
```

### TTSClip

Generates speech audio from text.

```python
TTSClip(
    text,
    voice="default",
    engine="system",
    speed=1.0,
    pitch=1.0,
    sample_rate=48000,
)
```

### Caption Functions

| Function | Signature | Description |
|----------|-----------|-------------|
| `get_caption_style` | `(name) -> CaptionStyle` | Returns a named style: `"netflix"`, `"youtube"`, `"tiktok"`, `"karaoke"`. |
| `parse_srt` | `(text) -> list[CaptionSegment]` | Parses SRT subtitle text. |
| `parse_vtt` | `(text) -> list[CaptionSegment]` | Parses WebVTT subtitle text. |
| `parse_ass` | `(text) -> list[CaptionSegment]` | Parses ASS/SSA subtitle text. |
| `import_subtitles` | `(path) -> list[CaptionSegment]` | Imports subtitles from a file (auto-detects format). |
| `export_subtitles` | `(segments, path, fmt) -> None` | Exports segments to a subtitle file. |
| `render_caption_frame` | `(segments, time_sec, width, height, style) -> ndarray` | Renders caption overlay for a specific time. |

---

## Motion Graphics

### Lower Thirds and Titles

| Class | Signature | Description |
|-------|-----------|-------------|
| `LowerThird` | `(name, title, style, animate_in=15, animate_out=15, margin_bottom=80.0, margin_left=60.0)` | Animated lower third graphic. |
| `LogoReveal` | `(image, style, duration)` | Animated logo reveal. |
| `CallToAction` | `(text, sub_text, style)` | Call-to-action overlay. |
| `SocialHandle` | `(platform, handle, style)` | Social media handle display. |
| `Countdown` | `(from_n, duration, font, style)` | Animated countdown. |
| `QuoteCard` | `(text, attribution, style)` | Styled quote card. |
| `Divider` | `(style, direction, duration)` | Animated divider line. |
| `TransitionTitle` | `(text, style, duration)` | Title with built-in transition. |
| `Watermark` | `(image_or_text, position, opacity)` | Watermark overlay. |

### Charts

All chart clips accept `(data, labels, animate_duration, theme)`.

| Class | Description |
|-------|-------------|
| `BarChartClip` | Animated bar chart. |
| `LineChartClip` | Animated line chart. |
| `PieChartClip` | Animated pie chart. |
| `AreaChartClip` | Animated area chart. |
| `RadarChartClip` | Animated radar/spider chart. |
| `ScatterPlotClip` | Animated scatter plot. |

### Data Visualization

| Class | Signature | Description |
|-------|-----------|-------------|
| `NumberCounter` | `(start, end, duration, format_fn, font, size, color)` | Animated number counter. |
| `ProgressBar` | `(value, width, height, fill_color, bg_color, radius)` | Animated progress bar. |

### Device Mockups

| Class | Signature | Description |
|-------|-----------|-------------|
| `BrowserMockup` | `(content, theme, url)` | Wraps content in a browser window frame. |
| `PhoneMockup` | `(content, device, theme)` | Wraps content in a phone device frame. |
| `DesktopMockup` | `(content, theme, title)` | Wraps content in a desktop window frame. |

---

## Expressions and Path Animation

### ExpressionContext

Frozen dataclass passed to expression functions during evaluation.

```python
ExpressionContext(
    frame, time, fps,
    comp_width, comp_height,
    progress, local_frame,
)
```

### ExpressionFn

Type alias: `Callable[[ExpressionContext], float]`

### Expression Generators

| Function | Signature | Description |
|----------|-----------|-------------|
| `wiggle` | `(freq, amp, seed=0) -> ExpressionFn` | Generates random wiggle motion. |
| `loop_in` | `(duration_frames, base_fn) -> ExpressionFn` | Loops the start of an expression. |
| `loop_out` | `(duration_frames, base_fn) -> ExpressionFn` | Loops the end of an expression. |

### Path Animation

| Symbol | Signature | Description |
|--------|-----------|-------------|
| `StrokeClip` | `(path, trim_start=0.0, trim_end=1.0, stroke_color, stroke_width=2.0)` | Renders and animates an SVG path stroke. |
| `follow_path` | `(clip, svg_path_str, duration, align=True) -> Clip` | Moves a clip along an SVG path. |
| `morph_paths` | `(path_a, path_b, progress) -> str` | Interpolates between two SVG paths. |

---

## 3D Rendering

### Scene3D

The 3D scene container using ModernGL for headless rendering with PBR shading.

```python
Scene3D(width, height)
```

**Attributes and Methods:**

| Member | Description |
|--------|-------------|
| `.camera` | The scene camera (Camera instance). |
| `.load_model()` | Loads a 3D model file. |
| `.add_model()` | Adds a model to the scene. |
| `.add_light()` | Adds a light source. |
| `.set_environment()` | Sets the HDRI environment map. |
| `.add_effect()` | Adds a post-processing effect (SSAO, Bloom, etc.). |
| `.to_clip(duration)` | Converts the scene to a renderable clip. |

### Scene3DClip

Wraps a Scene3D as a clip.

```python
Scene3DClip(scene)
```

### Camera

```python
Camera(position, target, fov, near, far)
```

### PBRMaterial

Physically-based rendering material.

```python
PBRMaterial(
    albedo, metallic, roughness,
    emissive, normal_map,
)
```

### Lights

| Class | Signature | Description |
|-------|-----------|-------------|
| `PointLight` | `(position, color, intensity)` | Omnidirectional point light. |
| `DirectionalLight` | `(direction, color, intensity)` | Infinite directional light. |
| `SpotLight` | `(position, direction, color, intensity, inner_cone, outer_cone)` | Cone-shaped spotlight. |
| `AmbientLight` | `(color, intensity)` | Uniform ambient light. |

### HDRIEnvironment

Set via `scene.set_environment()`. Provides image-based lighting from an HDRI map.

### 3D Post-Processing Configs

| Config | Signature | Description |
|--------|-----------|-------------|
| `SSAOConfig` | `(radius, samples, strength)` | Screen-space ambient occlusion. |
| `BloomConfig` | `(threshold, radius, strength)` | 3D bloom post-processing. |
| `DepthOfFieldConfig` | `(focus_distance, aperture, max_blur)` | Depth of field simulation. |
| `ShadowMapConfig` | `(resolution, bias)` | Shadow mapping configuration. |

### Tone Mapping

| Function | Signature | Description |
|----------|-----------|-------------|
| `tone_map_aces` | `(frame) -> ndarray` | ACES filmic tone mapping. |
| `tone_map_filmic` | `(frame) -> ndarray` | Filmic tone mapping curve. |
| `tone_map_reinhard` | `(frame) -> ndarray` | Reinhard tone mapping. |

---

## Particles

### Emitter

Defines how particles are spawned and behave.

```python
Emitter(
    position, rate, lifetime, speed, angle, size,
    color_over_life, opacity_over_life,
    gravity, drag, turbulence, rotation_speed,
    sprite, blend_mode,
)
```

### ParticleSystem

Container that manages emitters and simulates particles.

```python
ParticleSystem(width, height)
```

**Methods:**

| Method | Description |
|--------|-------------|
| `.add_emitter()` | Adds an emitter to the system. |
| `.to_clip(duration)` | Converts to a renderable clip. |

### Particle Presets

All presets return a configured `ParticleSystem` and accept `(w, h)`.

| Preset | Description |
|--------|-------------|
| `sparkles(w, h)` | Sparkling particle effect. |
| `confetti(w, h)` | Falling confetti. |
| `fire(w, h)` | Fire simulation. |
| `smoke(w, h)` | Smoke simulation. |
| `rain(w, h)` | Rain particle effect. |
| `stars(w, h)` | Twinkling star field. |

---

## Color Science

### Color Space Conversion

| Function | Signature | Description |
|----------|-----------|-------------|
| `srgb_to_aces` | `(frame) -> ndarray` | Converts sRGB frame to ACES color space. |
| `aces_to_srgb` | `(frame) -> ndarray` | Converts ACES frame to sRGB color space. |

### Color Grading

| Class | Signature | Description |
|-------|-----------|-------------|
| `ColorMatch` | `(reference_frame)` | Matches color grading to a reference frame. |
| `HSLSecondary` | `(hue_range, saturation_range, luminance_range, grade)` | Targets a color range for selective grading. |

### Scopes

| Class | Signature | Description |
|-------|-----------|-------------|
| `WaveformScopeClip` | `(source)` | Renders a waveform monitor. |
| `VectorscopeClip` | `(source)` | Renders a vectorscope. |
| `HistogramClip` | `(source)` | Renders an RGB histogram. |
| `ParadeScopeClip` | `(source)` | Renders an RGB parade scope. |

### HDR Presets

| Constant | Description |
|----------|-------------|
| `HDR10_PRESET` | HDR10 output configuration. |
| `HLG_PRESET` | Hybrid Log-Gamma output configuration. |

---

## AI Features

All AI features require the `[ai]` extra: `pip install pymotion[ai]`.

### Background and Object

| Class | Signature | Description |
|-------|-----------|-------------|
| `RemoveBackground` | | Removes the background using rembg. |
| `ReplaceBackground` | `(new_bg)` | Replaces the background with a new image or clip. |
| `ObjectSegmentation` | `(prompt)` | Segments objects using SAM with a text prompt. |
| `RemoveObject` | `(mask)` | Inpaints over a masked region to remove an object. |
| `ExtendFrame` | `(direction, amount)` | Extends the frame canvas using outpainting. |

### Enhancement

| Class | Signature | Description |
|-------|-----------|-------------|
| `Upscale` | `(factor)` | Upscales using Real-ESRGAN. |
| `Denoise` | | AI-based denoising. |
| `Deblur` | | AI-based deblurring. |
| `FrameInterpolation` | `(factor)` | Generates intermediate frames for slow motion. |
| `ColorizeClip` | | Colorizes grayscale footage. |

### Analysis

| Class | Signature | Description |
|-------|-----------|-------------|
| `SceneDetector` | `(clip, threshold)` | Detects scene boundaries. |
| `SilenceRemover` | `(clip, threshold_db, min_silence_sec)` | Removes silent sections. |
| `HighlightDetector` | `(clip, criteria, top_n)` | Finds highlight moments. |
| `ContentAwareCrop` | `(clip, target_ratio)` | Crops to a target aspect ratio keeping subjects in frame. |
| `AutoColor` | `(clip)` | Automatic color correction. |
| `AutoEdit` | `(clips, style, music)` | Automatic editing of multiple clips. |

### Face

| Class | Signature | Description |
|-------|-----------|-------------|
| `FaceDetector` | `(clip)` | Detects faces in frames. |
| `FaceTracker` | `(clip)` | Tracks faces across frames. |
| `FaceBlur` | `(clip, strength)` | Blurs detected faces. |

### Audio AI

| Class | Signature | Description |
|-------|-----------|-------------|
| `VoiceConversion` | `(clip, target_voice_sample)` | Converts voice to match a target sample. |
| `MusicGeneration` | `(prompt, duration, tempo)` | Generates music from a text prompt. |
| `SoundFXGeneration` | `(description, duration)` | Generates sound effects from a description. |

---

## Layout

Convenience functions for common multi-clip arrangements.

| Function | Signature | Description |
|----------|-----------|-------------|
| `pip` | `(main, overlay, position, size, border=None, shadow=None) -> Composition` | Picture-in-picture layout. |
| `grid` | `(clips, rows, cols, gap=0, background="#000000") -> Composition` | Grid layout of clips. |
| `split_screen` | `(clips, layout="horizontal") -> Composition` | Side-by-side or stacked split screen. |
| `stack` | `(clips, direction="horizontal", gap=0) -> Composition` | Stacks clips in a direction. |

---

## Tracking and Proxy

### MotionTracker

Tracks a region across frames using optical flow or template matching.

```python
MotionTracker(clip, region)
```

**Methods:**

| Method | Signature | Description |
|--------|-----------|-------------|
| `.track` | `() -> dict[int, Vec2]` | Runs tracking and returns per-frame positions. |
| `.to_keyframes` | `(prop)` | Converts tracking data to a KeyframeTrack. |

### StabilizedClip

Created via `clip.stabilize()`.

```python
clip.stabilize(smoothing=30, border_mode="crop") -> StabilizedClip
```

### ProxyClip

Created via `clip.create_proxy()`. Renders with a lower-resolution proxy for faster previews.

```python
clip.create_proxy(scale=0.25, cache_dir=None) -> ProxyClip
```

### Proxy Cache Functions

| Function | Signature | Description |
|----------|-----------|-------------|
| `clear_proxy_cache` | `(older_than_days=30) -> int` | Clears old proxy files, returns count deleted. |
| `proxy_cache_size` | `() -> int` | Returns total proxy cache size in bytes. |

---

## Template

### Template (ABC)

Abstract base class for reusable, parameterized compositions.

Define fields as class attributes and implement `build()`.

```python
class MyTemplate(Template):
    title: str = "Default"

    def build(self) -> Composition:
        ...
```

**Methods:**

| Method | Signature | Description |
|--------|-----------|-------------|
| `render` | `(output) -> Path` | Validates fields, calls `build()`, and renders. |

### TemplateValidationError

Raised when template field validation fails. Inherits from `ValueError`.

---

## Profiling

### benchmark

Benchmarks rendering performance over a number of frames.

```python
benchmark(comp, n_frames=100) -> RenderProfile
```

### profile_composition

Profiles rendering with optional per-frame detail.

```python
profile_composition(comp, start, end, detailed=False) -> RenderProfile
```

### memory_report

Reports memory usage during rendering.

```python
memory_report(comp, n_frames) -> MemoryReport
```

### detect_bottlenecks

Identifies performance bottlenecks in a composition.

```python
detect_bottlenecks(comp, n_frames, top_n) -> list[Bottleneck]
```

### frame_diff

Compares two frames pixel by pixel.

```python
frame_diff(frame_a, frame_b) -> FrameDiff
```

### Data Classes

**RenderProfile:**

| Field | Type | Description |
|-------|------|-------------|
| `total_frames` | `int` | Number of frames profiled. |
| `total_ms` | `float` | Total render time in milliseconds. |
| `avg_frame_ms` | `float` | Average time per frame. |
| `min_frame_ms` | `float` | Fastest frame time. |
| `max_frame_ms` | `float` | Slowest frame time. |
| `fps_achieved` | `float` | Effective frames per second. |
| `frame_profiles` | `list[FrameProfile]` | Per-frame breakdown (when detailed). |

**FrameProfile:**

| Field | Type | Description |
|-------|------|-------------|
| `frame` | `int` | Frame number. |
| `total_ms` | `float` | Total time for this frame. |
| `composite_ms` | `float` | Time spent compositing. |
| `clip_timings` | `list[ClipTiming]` | Per-clip timing breakdown. |

**ClipTiming:**

| Field | Type | Description |
|-------|------|-------------|
| `track_name` | `str` | Name of the containing track. |
| `clip_index` | `int` | Index within the track. |
| `clip_type` | `str` | Type name of the clip. |
| `render_ms` | `float` | Render time for this clip. |
| `effects_count` | `int` | Number of effects applied. |

**MemoryReport:**

| Field | Type | Description |
|-------|------|-------------|
| `peak_ram_bytes` | `int` | Peak RAM usage in bytes. |
| `current_ram_bytes` | `int` | Current RAM usage in bytes. |
| `peak_ram_mb` | `float` | Peak RAM in megabytes. |
| `per_stage` | `dict` | Memory usage broken down by stage. |

**Bottleneck:**

| Field | Description |
|-------|-------------|
| `category` | Type of bottleneck. |
| `description` | Human-readable description. |
| `time_ms` | Time consumed. |
| `percentage` | Share of total render time. |

**FrameDiff:**

| Field | Description |
|-------|-------------|
| `psnr` | Peak signal-to-noise ratio. |
| `changed_pixels` | Number of pixels that differ. |
| `total_pixels` | Total pixel count. |
| `identical` | Whether frames are pixel-identical. |
