# Migration guide

## Versioning policy

PyMotion follows semantic versioning. Major versions (e.g., 2.0, 3.0) may contain breaking changes to the public API. Minor versions (e.g., 1.2, 1.3, 1.4, 1.5) add new features while preserving backward compatibility with existing code. Patch versions (e.g., 1.0.1) contain bug fixes and quality improvements only. Pre-1.0 releases (0.1 through 0.9 RC) were alpha/beta phases where the API was still stabilizing and breaking changes occurred between every minor version.

---

## v0.1 -> v0.2

### Breaking changes

v0.2 introduces the text, video, audio, and transition subsystems. Code written against v0.1 continues to work, but several core concepts are expanded.

**New required concepts:**

- `TextClip` replaces any workaround for text rendering. Text is now rendered via FreeType and HarfBuzz with full multiline word-wrap, alignment, stroke, and shadow support.
- `AudioMixer` and `AudioClip` are new. There was no audio API in v0.1.
- The easing library expands from basic interpolation to 30+ easing functions, spring physics, cubic bezier, and step functions. Existing `Keyframe` usage remains compatible.

**New dependencies:**

- FreeType and HarfBuzz (for text rendering)
- FFmpeg (for `VideoClip` decoding)

No symbols from v0.1 are removed or renamed.

---

## v0.2 -> v0.3

### Breaking changes

No breaking changes to existing v0.2 APIs.

**New subsystems added (additive only):**

- 3D rendering backend via ModernGL (headless)
- Particle system with vectorized NumPy updates and 5 presets (`sparkles`, `confetti`, `fire`, `smoke`, `rain`)
- Audio DSP effects via pedalboard (EQ, Compressor, Limiter)
- Beat detection and waveform extraction via librosa
- Color pipeline with `.cube` LUT support
- Hot-reload preview server

**New optional dependencies:**

- `moderngl` (3D rendering)
- `pedalboard` (audio DSP)
- `librosa` (beat detection)
- `aiohttp` (preview server)

---

## v0.3 -> v0.4

### Breaking changes

No breaking changes to existing v0.3 APIs.

**New features (additive only):**

- 19 new transitions (39 total), completing the transition library
- Complete visual effects suite: MotionBlur, FilmGrain, Sharpen, ChromaticAberration, Glow, Bloom, LensFlare, and more
- Color effects: Brightness, Contrast, Saturation, HSL, ColorBalance, Curves, LUT, SplitToning, BleachBypass
- Distortion effects: WaveWarp, Ripple, Twirl, PerspectiveWarp, Fisheye
- Light effects: LensFlare, GodRays, NeonGlow, LightLeak
- 4 additional particle presets (Stars, Dust, Explosion, Bubbles — 9 total)
- 9 animated text presets (Typewriter, WordByWord, LetterByLetter, Scramble, KineticText, SplitReveal, CountUp, CountDown, GlitchText)
- Variable font support (weight, width, slant axes)
- Google Fonts download with httpx
- Volume and pan keyframe automation
- Template ABC with field validation
- Frame sequence export (PNG/EXR)
- All 15 export presets
- All 8 blend modes (Multiply, Screen, Overlay, etc.)

**New optional dependencies:**

- `httpx` (Google Fonts download)

---

## v0.4 -> v0.9 RC

### Breaking changes

No breaking changes to existing v0.4 APIs.

**New features (additive only):**

- `PyMotionConfig` global configuration object with `get_config()`, `set_config()`, `reset_config()`
- ACES, Reinhard, and Filmic tone mapping operators
- `pymotion doctor` CLI command
- Variable font full axis support (ital, opsz, custom axes)
- Jupyter integration: `export_frame_inline()` and `preview_widget()`
- MkDocs documentation site
- Dockerfile for containerized usage

**Changed defaults:**

- Asset cache size is now configurable via `PyMotionConfig.cache_max_bytes` (previously hardcoded)

---

## v0.9 RC -> v1.0

### Breaking changes

No breaking changes. v1.0 is the stable release of the RC API.

**New exports:**

- `Silence` helper for silent audio placeholders
- `animate()` shorthand for two-keyframe animations
- `Align` enum (13 alignment values)
- Audio effects: `Reverb`, `Delay`, `PitchShift`, `NoiseReduction`, `LowPassFilter`, `HighPassFilter`
- 3D exports: `Scene3DClip`, `Scene3D`, `Camera`, `PointLight`, `DirectionalLight`, `SpotLight`, `AmbientLight`, `HDRIEnvironment`, `PBRMaterial`
- Particle exports: `ParticleSystem`, `Emitter`
- Capitalized particle preset aliases: `Sparkles`, `Confetti`, `Fire`, `Smoke`, `Rain`, `Stars` (the lowercase functions `sparkles`, `confetti`, etc. remain available)
- `ScrambleText` alias for the `Scramble` animated text preset

---

## v1.0 -> v1.0.1

### Breaking changes

**H.264 encoding defaults changed:**

The default H.264 encoding quality settings changed significantly. If you rely on specific file sizes or encoding speed from v1.0, you need to create a custom `OutputPreset`.

| Setting | v1.0 | v1.0.1 |
|---------|------|--------|
| H.264 CRF | 18 | 10 |
| H.264 preset | `faster` | `medium` |
| H.265 CRF | 22 | 16 |
| H.265 preset | `faster` | `medium` |

v1.0.1 also adds `no-dct-decimate` and `no-fast-pskip` x264 params and Lanczos chroma scaling. These changes produce higher quality output but render slower and produce larger files.

**Bug fixes that change visual output:**

- The compositor alpha cache memory aliasing bug is fixed. If your v1.0 renders had flickering or disappearing text layers, they now render correctly. Existing renders that appeared correct are not affected.
- Animated text presets (Typewriter, WordByWord, LetterByLetter) use a new reveal-mask architecture. Already-revealed text pixels are now bit-for-bit identical across frames, eliminating subtle shimmer.
- CountUp and CountDown use quintic ease-out with frame-stepping (`step_frames=3`).

No symbols are removed or renamed.

---

## v1.0.1 -> v1.2

### Breaking changes

No breaking changes. All v1.0.1 code continues to work.

**New clip operations (additive):**

- `clip.split()`, `clip.join()`, `clip.subclip()`, `clip.repeat()`, `clip.freeze_frame()`
- `pm.concatenate()` with optional transitions
- `clip.speed()`, `clip.speed_ramp()`, `clip.reverse()`, `clip.time_remap()`
- Return types: `SubClip`, `JoinedClip`, `ConcatenatedClip`, `RepeatedClip`, `FreezeFrameClip`, `SpeedClip`, `SpeedRampClip`, `ReversedClip`, `TimeRemappedClip`

**New keying effects:**

- `ChromaKey`, `LumaKey`, `ColorKey`, `DifferenceKey`

**New layout helpers:**

- `pm.pip()`, `pm.grid()`, `pm.split_screen()`, `pm.stack()`

**New tracking and proxy features:**

- `MotionTracker`, `clip.stabilize()`, `clip.follow_tracker()`
- `clip.create_proxy()`, `ProxyClip`, `pm.clear_proxy_cache()`, `pm.proxy_cache_size()`
- `clip.add_effect()` and `clip.render_with_effects()`

**New optional dependencies:**

- OpenCV (`cv2`) for optical flow interpolation, motion tracking, and stabilization. Falls back gracefully if unavailable.

---

## v1.2 -> v1.3

### Breaking changes

No breaking changes. All v1.2 code continues to work.

**New compositing features (additive):**

- Nested compositions: `Composition.to_clip()` returns a `CompositionClip`
- `AdjustmentLayer` applies effects to all layers below
- Masking: `BezierMask`, `LinearGradientMask`, `RadialGradientMask`, `TrackMatte`, `TextMask`
- Boolean mask operations: `MaskOp.ADD`, `MaskOp.INTERSECT`, `MaskOp.SUBTRACT`
- Parenting: `clip.parent = other_clip`, `NullObject`
- Expressions: `clip.set_expression()`, `ExpressionContext`, `wiggle()`, `loop_in()`, `loop_out()`
- Path animation: `clip.follow_path()`, `StrokeClip`, `morph_paths()`

---

## v1.3 -> v1.4

### Breaking changes

No breaking changes. All v1.3 code continues to work.

**New motion graphics components (additive):**

- Chart clips: `BarChartClip`, `LineChartClip`, `PieChartClip`, `AreaChartClip`, `RadarChartClip`, `ScatterPlotClip`
- Utility clips: `NumberCounter`, `ProgressBar`
- Motion graphics: `LowerThird`, `LogoReveal`, `CallToAction`, `SocialHandle`, `Countdown`, `QuoteCard`, `Divider`, `TransitionTitle`, `Watermark`
- Device mockups: `BrowserMockup`, `PhoneMockup`, `DesktopMockup`

---

## v1.4 -> v1.5

### Breaking changes

No breaking changes. All v1.4 code continues to work.

**New audio features (additive):**

- 5.1 surround mixing: `SurroundChannel`, `AudioBus`, `ChannelLayout`
- Audio crossfades: `audio_crossfade()` with `linear`, `equal_power`, `s_curve` modes
- `MultibandCompressor`, `ConvolutionReverb`
- LUFS normalization: `mixer.normalize(target_lufs=-14)`
- Audio visualization clips: `WaveformClip`, `SpectrumClip`, `SpectrogramClip`, `AudioReactiveEffect`

**New caption and TTS features:**

- `AutoCaptions` (Whisper-based), `SubtitleClip`, subtitle import/export
- `TTSClip` with system and cloud TTS engines
- Caption styles: `"netflix"`, `"youtube"`, `"tiktok"`, `"karaoke"`

**New color science features:**

- ACES color pipeline: `srgb_to_aces()`, `aces_to_srgb()`
- HDR10 and HLG output presets
- `ColorMatch`, `HSLSecondary`
- Scope clips: `WaveformScopeClip`, `VectorscopeClip`, `HistogramClip`, `ParadeScopeClip`
- EDL/OTIO export: `comp.export_edl()`, `comp.export_otio()`

**New optional dependencies:**

- `whisper` (for `AutoCaptions`)
- `pyttsx3` (for `TTSClip` system engine)
- `opentimelineio` (for OTIO export)

---

## v1.5 -> v2.0

### Breaking changes

No breaking changes. All v1.5 code continues to work. AI features are entirely additive and installed via an optional extra.

**New AI features (all optional, installed via `pip install "pymotion-studio[ai]"`):**

- Background/object: `RemoveBackground`, `ReplaceBackground`, `ObjectSegmentation`, `RemoveObject`, `ExtendFrame`
- Enhancement: `Upscale`, `Denoise`, `Deblur`, `FrameInterpolation`, `ColorizeClip`
- Smart editing: `SceneDetector`, `SilenceRemover`, `HighlightDetector`, `ContentAwareCrop`, `AutoColor`, `AutoEdit`
- Face/body: `FaceDetector`, `FaceTracker`, `FaceBlur`
- AI audio: `VoiceConversion`, `MusicGeneration`, `SoundFXGeneration`

**New optional dependencies (under `[ai]` extra):**

- `rembg>=2.0` (background removal)
- SAM, Real-ESRGAN, RIFE (various AI model backends)

---

## v2.0 -> v2.5

### Breaking changes

No breaking changes. All v2.0 code continues to work.

**New performance features (additive):**

- GPU-accelerated compositing via WGPU compute shaders: `GPUCompositor`, `GPUEffectPipeline`, `GPUBufferPool`
- Hardware encoding presets: `h264_nvenc`, `h265_nvenc`, `h264_qsv`, `h264_amf`
- Automatic hardware encoder detection with software fallback
- Distributed rendering: `Composition.render(..., backend="ray")` and `backend="dask"`
- Frame-level checkpointing: `RenderCheckpoint`
- Profiling: `Composition.render(profile=True)`, `pm.benchmark()`, `pm.memory_report()`, `pm.detect_bottlenecks()`
- `pm.frame_diff()` for pixel-level frame comparison

**New render optimizations (transparent):**

- Smart incremental rendering (skips unchanged frames)
- Memory-mapped frame buffers at 4K
- SIMD-optimized blend operations (optional Cython build)
- Static layer baking
- Parallel audio rendering

**New optional dependencies:**

- `wgpu` (GPU compositing)
- `ray` (distributed rendering)
- `dask` (distributed rendering)
- `cython` (SIMD blend, build-time optional)

---

## v2.5 -> v3.0

### Breaking changes

**`loop_out()` expression behavior changed:**

In v2.5 and earlier, `loop_out()` incorrectly duplicated `loop_in()` behavior (looping the first N frames). In v3.0, `loop_out()` correctly loops the last N frames of the clip.

```python
# v2.5 (buggy): loop_out looped first N frames, same as loop_in
clip.set_expression("position.x", loop_out(30, some_fn))

# v3.0 (fixed): loop_out now loops the LAST N frames
# Same call, but the output is different — it loops the end of the clip
clip.set_expression("position.x", loop_out(30, some_fn))
```

If your code relied on the old (incorrect) `loop_out()` behavior, switch to `loop_in()`.

**Visual output differences:**

Several rendering fixes produce visibly different output compared to v2.5. Existing renders are not pixel-identical:

- Zoom/scale transitions use bilinear interpolation (was nearest-neighbor)
- Iris transitions have smoothstep feathered edges (was hard edges)
- Particle rendering uses circular anti-aliased shapes (was rectangular blocks)
- Vignette uses smoothstep falloff (was linear, which caused banding)
- Bloom uses a downsampling pyramid (was single-pass)
- CrossDissolve uses a smoothstep curve
- Glitch transition now has color channel separation
- Confetti particles rotate per-particle
- Rain particles have motion blur streaks
- Neon chart theme has actual glow effect
- `pip()` shadow parameter renders actual drop shadows (was a no-op stub)
- Karaoke caption style renders spoken/upcoming words in different colors (was unimplemented)

**New exports:**

- `SSAOConfig`, `BloomConfig`, `DepthOfFieldConfig`, `ShadowMapConfig` (3D post-processing configs)
- `__repr__` on `Composition` and `ParticleSystem`

No symbols are removed or renamed.

---

## v3.0 -> v3.1

### Breaking changes

**H.264 encoding defaults changed again:**

v3.1 optimizes for render speed. The default H.264 quality settings are relaxed:

| Setting | v3.0 | v3.1 |
|---------|------|------|
| H.264 CRF | 10 | 18 |
| H.264 preset | `medium` | `fast` |
| x264-params overrides | `no-dct-decimate`, `no-fast-pskip` | none |

If you need the higher-quality v3.0 settings, use a custom `OutputPreset` or specify encoding parameters explicitly.

**New encoding presets:**

- `h264_fast` -- CRF 18, `-preset fast`, no x264-params overrides
- `h264_videotoolbox` -- macOS VideoToolbox hardware encoding on Apple Silicon

**Performance improvements (transparent):**

- Motion graphics frame caching (LowerThird, LogoReveal, CallToAction, SocialHandle, TransitionTitle, Countdown)
- Effect buffer reuse (Vignette, Bloom, GaussianBlur, FilmGrain)
- Compositor buffer reuse and persistent alpha cache for static clips
- Batch contiguous normal-blend layers into single memcpy
- Progress logging every 100 frames

No symbols are removed or renamed.

---

## v3.1 -> v3.2

### Breaking changes

No breaking changes. All v3.1 code continues to work.

**Examples rewritten:**

The example scripts are completely rewritten. If you based your code on an older example, the new examples (EX01 through EX12) replace them entirely. The old examples from v3.0/v3.1 (`01_product_launch.py` through `08_composite_vfx.py`) no longer exist.

All 12 new examples use the `h264_fast` preset with hardware-accelerated encoding.

No symbols are removed or renamed. No API changes.

---

## Deprecations still present

PyMotion has no deprecated symbols at this time. All aliases are permanent conveniences, not deprecation shims:

| Alias | Canonical symbol | Purpose |
|-------|-----------------|---------|
| `ScrambleText` | `Scramble` | PRD naming compatibility |
| `Sparkles` | `sparkles` | Capitalized alias for the particle preset function |
| `Confetti` | `confetti` | Capitalized alias for the particle preset function |
| `Fire` | `fire` | Capitalized alias for the particle preset function |
| `Smoke` | `smoke` | Capitalized alias for the particle preset function |
| `Rain` | `rain` | Capitalized alias for the particle preset function |
| `Stars` | `stars` | Capitalized alias for the particle preset function |

Both forms are supported and neither is scheduled for removal.
