# Changelog

All notable changes to PyMotion are documented here.

## [3.2.0] — 2026-03-11

### Added
- **Examples** — 12 production-quality examples (EX01-EX12) exercising all 312 public API symbols
  - EX01: Core composition & 2D rendering
  - EX02: Text & typography
  - EX03: Video editing & clip operations
  - EX04: Keying & compositing (+ CircularWipe, IrisIn, IrisOut)
  - EX05: 3D rendering (+ ACES pipeline, HDR presets)
  - EX06: Particles & VFX (+ 15 transitions)
  - EX07: Audio mixing & visualization
  - EX08: Captions & TTS
  - EX09: Motion graphics & charts (+ slide/wipe transitions)
  - EX10: Advanced compositing (masks, expressions, paths)
  - EX11: AI features (24 classes)
  - EX12: Batch template (Template ABC)
- **Assets** — Self-contained product-themed assets replacing old stock images

### Changed
- All examples use `h264_fast` preset with hardware-accelerated encoding
- Transitions distributed across examples for full coverage

## [3.0.0] — 2026-03-11

### Fixed
- **Expressions** — `loop_out()` now correctly loops the last N frames instead of duplicating `loop_in()` behavior
- **Transitions** — Bilinear interpolation for zoom/scale transitions (was nearest-neighbor); smoothstep feathered edges on iris transitions; glitch transition now has color channel separation; CrossDissolve uses smoothstep curve
- **Particles** — Circular anti-aliased rendering for multi-pixel particles; fractional spawn rate accumulation; per-particle rotation for confetti; motion blur streaks for rain; `_sizes` array now used in rendering
- **Effects** — Vignette uses smoothstep falloff (eliminates banding); bloom uses downsampling pyramid for natural glow; neon chart theme has actual glow effect
- **Audio** — Sidechain compressor implemented; 5.1 surround export with proper channel count; audio export via temp WAV → FFmpeg AAC encoding
- **Layout** — `pip()` shadow parameter now renders actual drop shadows
- **Text** — Emoji glyphs log debug warning instead of silently dropping
- **Captions** — Karaoke word highlighting renders spoken/upcoming words in different colors

### Changed
- **Examples** — Complete rewrite: 8 production-quality self-contained showcase scripts replacing 11 older examples
- **API** — Export 3D post-processing configs (SSAOConfig, BloomConfig, DepthOfFieldConfig, ShadowMapConfig); `__repr__` on Composition and ParticleSystem; error messages include received values

### Improved
- **Coverage** — 2427 tests (up from 2185), 91% coverage (up from 88%)
- **Quality** — ruff format clean, ruff check clean, mypy --strict clean

## [2.0.0] — 2026-03-11

### Added
- **Background & object manipulation** — `RemoveBackground` (rembg), `ReplaceBackground`, `ObjectSegmentation` (SAM + text prompt), `RemoveObject` (inpainting), `ExtendFrame` (outpainting)
- **Enhancement & restoration** — `Upscale` (Real-ESRGAN 2×/4×), `Denoise` (deep learning denoiser), `Deblur` (blind deconvolution), `FrameInterpolation` (RIFE-based), `ColorizeClip` (grayscale → color)
- **Smart editing helpers** — `SceneDetector`, `SilenceRemover`, `HighlightDetector`, `ContentAwareCrop` (AI reframing), `AutoColor` (one-click correction), `AutoEdit` (AI-powered rough cut)
- **Face & body** — `FaceDetector`, `FaceTracker`, `FaceBlur` (automatic face detection + blur)
- **AI voice & audio** — `VoiceConversion` (voice style transfer), `MusicGeneration` (MusicGen background music), `SoundFXGeneration` (AI sound effects)
- All AI features are optional extras — no AI dependency required for core library (`pip install "pymotion-studio[ai]"`)

## [1.5.0] — 2026-03-11

### Added
- **Advanced audio mixing** — 5.1 surround channel routing (`SurroundChannel`), audio bus routing with volume/pan automation, audio crossfades (linear, equal-power, S-curve), multiband compressor, convolution reverb, LUFS normalization, silence generator
- **Audio visualization** — `WaveformClip` (bars/line), `SpectrumClip` (FFT frequency spectrum with color maps), `SpectrogramClip` (scrolling heatmap), `AudioReactiveEffect` (modulate any effect property from audio amplitude)
- **Captions & subtitles** — SRT/VTT/ASS import (`import_subtitles`, `parse_srt`, `parse_vtt`, `parse_ass`), `SubtitleClip` with 4 built-in styles (netflix, youtube, tiktok, karaoke), `AutoCaptions` via Whisper, `WordTimestamp` for word-level timing, subtitle export
- **Text-to-speech** — `TTSClip` with system (pyttsx3) and OpenAI engines
- **ACES color science** — sRGB ↔ ACES AP0 conversion with filmic tone mapping, HDR10 (PQ/ST 2084) and HLG (ARIB STD-B67) transfer functions
- **Color grading** — `ColorMatch` (Reinhard color transfer), `HSLSecondary` (range-based HSL secondary grading with hue wrapping)
- **Video scopes** — `WaveformScopeClip`, `VectorscopeClip`, `HistogramClip`, `ParadeScopeClip` (Cairo-rendered)
- **EDL/OTIO export** — `Composition.export_edl()` (CMX 3600), `Composition.export_otio()` (OpenTimelineIO)
- Example 09: Audio & Color Science showcase
- 5 new guide docs and 5 API reference docs

## [1.4.0] — 2026-03-10

### Added
- **Animated chart clips** — `BarChartClip`, `LineChartClip`, `PieChartClip`,
  `AreaChartClip`, `RadarChartClip`, and `ScatterPlotClip` with Cairo rendering,
  ease-out grow/draw-on animations, and four built-in themes (corporate, minimal,
  neon, gradient). All charts accept list, dict, or per-frame callable data sources.
- **NumberCounter** — animates a number from start to end value with customizable
  formatting, font, size, and color. Cubic ease-out animation.
- **ProgressBar** — horizontal progress bar with rounded corners, custom fill/bg
  colors, and support for callable animated values.
- **Motion graphics components** — `LowerThird` (8 styles with slide-in/out),
  `LogoReveal` (6 reveal styles: fade, slice, grow, glitch, draw, shatter),
  `CallToAction` (subscribe/buy/visit styles), `SocialHandle` (YouTube, Instagram,
  TikTok, X, LinkedIn), `Countdown` (numbers and clock modes), `QuoteCard` (4 styles
  with word wrapping), `Divider` (5 styles), `TransitionTitle` (5 styles with
  enter/exit animation), `Watermark` (5 positions with configurable opacity).
- **Device mockups** — `BrowserMockup` (light/dark chrome with traffic lights and
  URL bar), `PhoneMockup` (flat/notch/dynamic_island models), `DesktopMockup`
  (macos/windows/minimal themes). All mockups composite a content clip into the
  device frame with animate_in/animate_out support.

## [1.3.0] — 2026-03-10

### Added
- **Nested compositions (pre-comps)** — `Composition.to_clip()` wraps a composition as
  a `CompositionClip` for nesting inside parent compositions. Supports independent resolution
  and fps with automatic scaling, recursive nesting up to 10 levels, and a shared LRU frame
  cache across nesting depths.
- **Adjustment layers** — `AdjustmentLayer` applies its effects to all layers below it in
  the same composition. Supports opacity blending between adjusted and original frames.
- **Advanced masking system** — `BezierMask` (Cairo-rasterized closed paths with keyframe
  animation), `LinearGradientMask`, `RadialGradientMask`, `TrackMatte` (alpha or BT.601 luma),
  `TextMask` (Cairo text-shaped masks). Boolean mask operations: `MaskOp.ADD` (union),
  `MaskOp.INTERSECT` (intersection), `MaskOp.SUBTRACT` (difference). Per-mask feather,
  expansion, invert, and opacity controls.
- **Clip parenting** — `clip.parent = other_clip` for transform inheritance (position, scale,
  rotation). `NullObject` as an invisible transform group anchor. Circular parenting detection
  with `ValueError`.
- **Expression system** — `clip.set_expression(prop, fn)` to drive position, scale, rotation,
  and opacity with Python callables. `ExpressionContext` provides frame, time, fps, progress,
  and composition dimensions. Built-in helpers: `wiggle(freq, amp, seed)` for smooth random
  oscillation, `loop_in(duration, fn)` and `loop_out(duration, fn)` for expression looping.
  Expression linking between clips via `clip_a.opacity_at(frame)`.
- **Path animation** — `clip.follow_path(svg_path, duration, align)` animates a clip along
  SVG paths (M, L, C, Z commands). `StrokeClip` with `trim_start`/`trim_end` for draw-on/off
  stroke effects via Cairo dash patterns. `morph_paths(path_a, path_b, progress)` for bezier
  path interpolation. `ShapeClip.morph()` for applying morphed paths directly.
- **Documentation** — 4 new guides (compositing, masking, expressions, path animation),
  3 new API reference pages, updated existing API docs with NullObject, CompositionClip,
  and AdjustmentLayer.
- **Example** — `07_motion_graphics_toolkit.py` with 7 demos covering all v1.3 features.

### Changed
- Version bumped to 1.3.0
- Test suite expanded to 1444 tests, coverage at 86%
- README updated with v1.3 feature table, architecture diagram, and static badges

## [1.2.1] — 2026-03-10

### Fixed
- CI matrix updated to Python 3.12, 3.13, 3.14 (dropped 3.10/3.11)
- Merged publish workflow into release workflow for reliable PyPI deploys
- Relaxed Pillow dependency to `>=10.0,<14.0`

## [1.2.0] — 2026-03-10

### Added
- **Clip manipulation** — `clip.split()`, `clip.join()`, `clip.subclip()`, `clip.repeat()`,
  `clip.freeze_frame()`, `pm.concatenate()` with optional transitions between clips.
- **Speed & time operations** — `clip.speed()` with uniform speed change (0.1×–10×),
  `clip.speed_ramp()` for variable speed, `clip.reverse()`, `clip.time_remap()` for
  arbitrary time remapping via keyframe curves. Optical flow interpolation via OpenCV
  with automatic fallback to linear blending.
- **Chroma key & keying effects** — `ChromaKey` (YCbCr-based), `LumaKey`, `ColorKey`,
  `DifferenceKey` with shared utilities for feathering, choking, and despill.
- **Picture-in-Picture & layout helpers** — `pm.pip()`, `pm.grid()`, `pm.split_screen()`,
  `pm.stack()` for composing multi-clip layouts with named anchor positioning.
- **Motion tracking & stabilization** — `MotionTracker` for region tracking across frames,
  `clip.stabilize()` for video stabilization, `clip.follow_tracker()` to wire tracking
  data to clip properties.
- **Proxy workflow** — `clip.create_proxy()` for low-res preview proxies cached on disk,
  `pm.clear_proxy_cache()`, `pm.proxy_cache_size()` for cache management.
- **Effect system on clips** — `clip.add_effect()` and `clip.render_with_effects()` for
  storing and applying effects directly on clip instances.

## [1.0.1] — 2026-03-10

### Fixed
- **Critical: compositor alpha cache memory aliasing** — `_alpha_cache` in `compositor.py`
  used numpy memory pointers (`ctypes.data`) as cache keys. When numpy reused memory
  addresses for new frame allocations, the cache returned stale alpha info from previous
  frames, causing the compositor to randomly skip text and clip layers (visible as
  flickering/disappearing text in rendered videos). Fixed by clearing the cache at the
  start of each `composite_layers()` call.
- **Text animation reveal-mask architecture** — Rewrote Typewriter, WordByWord, and
  LetterByLetter presets to use a cached full-text render with a horizontal alpha reveal
  mask. Already-revealed pixels are now bit-for-bit identical across frames. CountUp and
  CountDown use quintic ease-out with frame-stepping (`step_frames=3`) for smooth
  deceleration.

### Changed
- **H.264 encoding quality** — CRF 18 → 10, preset `faster` → `medium` for all H.264
  presets. Added `no-dct-decimate` and `no-fast-pskip` x264 params to eliminate temporal
  text shimmer. Added Lanczos chroma scaling (`-sws_flags lanczos+accurate_rnd+full_chroma_int`)
  for better colored text quality during RGB → YUV420p conversion.
- **H.265 encoding quality** — CRF 22 → 16, preset `faster` → `medium`.
- **Instagram/TikTok presets** — Added `-tune animation` for better text/graphics quality.
- **FreeType text renderer** — Replaced block-character fallback with proper FreeType
  glyph rendering in `_render_text_simple`. Added glyph cache and character position
  measurement for reveal-mask animations.

### Improved
- **Examples rewritten** — All 5 example scripts (`01_real_estate_tour` through
  `05_educational_explainer`) rewritten as complete, production-ready runnable demos
  showcasing real-world niches (real estate, tech review, fitness, restaurant, education).
  Each uses multiple PyMotion features: ImageClip, TextClip, ShapeClip, GradientClip,
  animated text, particles, blend modes, and multi-track composition.
- **Stock assets** — Added `download_assets.py` script and 19 stock image/audio assets
  for the example scripts.

## [1.0.0] — 2026-03-09

### Added
- Complete PRD §8.2 public API: all symbols importable from `import pymotion`
- `Silence` helper for creating silent audio placeholders
- `animate()` shorthand for two-keyframe animations
- `Align` enum for text/element alignment (13 values)
- Audio effects: `Reverb`, `Delay`, `PitchShift`, `NoiseReduction`, `LowPassFilter`, `HighPassFilter`
- 3D exports: `Scene3DClip`, `Scene3D`, `Camera`, `PointLight`, `DirectionalLight`, `SpotLight`, `AmbientLight`, `HDRIEnvironment`, `PBRMaterial`
- Particle exports: `ParticleSystem`, `Emitter`, `Sparkles`, `Confetti`, `Fire`, `Smoke`, `Rain`, `Stars`
- `ScrambleText` alias for `Scramble` animated text
- 37 new unit tests for v1.0 API surface

### Changed
- Version bumped to 1.0.0 (stable release)
- `__init__.py` docstring updated to "v1.0"

## [0.9.0-rc] — 2026-03-09

### Added
- `PyMotionConfig` global configuration (network access, cache size, file limits)
- ACES, Reinhard, and Filmic tone mapping operators
- `pymotion doctor` CLI command for checking system dependencies
- Variable font full axis support (ital, opsz, custom axes)
- Jupyter integration: `export_frame_inline()` and `preview_widget()`
- MkDocs documentation site with API reference and 5 guides
- 10 example scripts
- Dockerfile for containerized usage
- README with install, quickstart, feature matrix
- Performance regression test infrastructure

### Changed
- Asset cache size now configurable via `PyMotionConfig.cache_max_bytes`
- Color pipeline supports tone mapping parameter

## [0.4.0-beta] — 2026-03-09

### Added
- All 39 built-in transitions (19 new: ZoomBlur, Glitch, FilmBurn, etc.)
- Complete visual effects: MotionBlur, FilmGrain, Sharpen, ChromaticAberration, Glow, Bloom, LensFlare
- Color effects: Brightness, Contrast, Saturation, HSL, ColorBalance, Curves, LUT, SplitToning, BleachBypass
- Distortion effects: WaveWarp, Ripple, Twirl, PerspectiveWarp, Fisheye
- Light effects: LensFlare, GodRays, NeonGlow, LightLeak
- Particle presets: Stars, Dust, Explosion, Bubbles (9 total)
- 9 animated text presets (Typewriter, WordByWord, etc.)
- Variable font support (weight, width, slant axes)
- Google Fonts download with httpx and domain allowlist
- Volume keyframe automation and pan automation
- Waveform-to-keyframe converter
- Template ABC with field validation
- Frame sequence export (PNG/EXR)
- All 15 export presets
- Frame cache for static layers
- All 8 blend modes (Multiply, Screen, Overlay, etc.)
- CLI benchmark, validate, new commands
- pip-audit in CI

## [0.3.0-beta] — 2026-03-09

### Added
- 3D rendering backend (ModernGL headless, PBR shaders, OBJ/GLTF loading)
- SSAO, Bloom, Depth of Field post-FX
- ACES/Filmic/Reinhard tone mapping (3D backend)
- Audio DSP effects (EQ, Compressor, Limiter via pedalboard)
- Beat detection, onset detection, waveform extraction (librosa)
- Sidechain compression
- Particle system with vectorized NumPy updates
- 5 particle presets (Sparkles, Confetti, Fire, Smoke, Rain)
- Color pipeline with .cube LUT support and trilinear interpolation
- Color grading (lift/gamma/gain/saturation)
- Hot-reload preview server (asyncio + aiohttp + WebSocket)
- Parallel frame rendering (multiprocessing)

## [0.2.0-alpha] — 2026-03-09

### Added
- FontLoader with system font discovery and LRU cache
- GlyphRenderer with FreeType and HarfBuzz integration
- TextClip with multiline word-wrap, alignment, stroke, shadow
- VideoClip (FFmpeg decode, trim, loop, speed, reverse)
- GradientClip (linear, radial, conic)
- Complete easing library (30+ functions, spring, cubic bezier, steps)
- Color interpolation via OKLCH
- 20 transitions (Fade, CrossDissolve, Slide, Push, Cover, Reveal, Zoom)
- AudioMixer with add, set_volume, render
- AudioClip with trim, fade, volume, loop
- 8 export presets
- CLI preview command (basic)

## [0.1.0-alpha] — 2026-03-09

### Added
- Core architecture: Composition, Track, Clip base class
- ColorClip, ImageClip, ShapeClip
- Keyframe animation system with interpolation
- 2D rendering backend (Cairo)
- Compositor with alpha blending
- FFmpeg encoder with subprocess (shell=False)
- GaussianBlur, Vignette effects
- Security validators (path, color, asset magic, text sanitize)
- CLI render and export-frame commands
- Asset loader with LRU cache
- structlog-based logging
