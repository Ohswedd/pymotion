# Changelog

All notable changes to PyMotion are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [3.4.0] — 2026-03-11

### Fixed
- PieChartClip donut rendering: spike/star artifacts caused by Cairo implicit line from label `show_text()` current point to next slice arc start; fixed with `new_sub_path()` before each arc and `LINE_JOIN_ROUND` on borders
- NumberCounter ignored `set_position()` — always rendered text at frame center; now respects `_position` as content center
- ProgressBar ignored `set_position()` — always rendered bar at frame center; now respects `_position` as content center
- EX05 3D fallback too dark — increased overlay opacity (0.3→0.7), added "3D Preview (GPU required)" label
- EX06 bloom overexposure on section 10 — reduced LensFlare/LensFlareLight/Bloom intensities
- EX07 black frames in audio-only sections — added section label TextClips

## [3.3.0] — 2026-03-11

### Added
- Complete documentation rewrite from source audit: README, getting-started, api-reference, cookbook, migration guide, CHANGELOG
- Visual output audit of all 12 examples (109 frames inspected, 0 critical/major findings)
- `audit/visual/FINDINGS.md` with per-example inspection results

### Changed
- README: fixed version (was v2.5.0, now v3.2.0), test count (was 2185, now 2431), coverage (was 89%, now 91%), preset count (was 19, now 22), particle count (was 9, now 6)
- docs/api-reference.md: comprehensive reference for all 312+ public API symbols
- docs/cookbook.md: 9 recipe categories with tested code examples
- docs/migration.md: complete version-to-version migration guide (v0.1 through v3.2)
- docs/getting-started.md: core concepts, render pipeline, coordinate system, common patterns

## [3.2.0] — 2026-03-11

### Added
- 12 production-quality examples (EX01-EX12) exercising all 312 public API symbols
  - EX01: Core composition and 2D rendering
  - EX02: Text and typography
  - EX03: Video editing and clip operations
  - EX04: Keying and compositing
  - EX05: 3D rendering
  - EX06: Particles and VFX
  - EX07: Audio mixing and visualization
  - EX08: Captions and TTS
  - EX09: Motion graphics and charts
  - EX10: Advanced compositing (masks, expressions, paths)
  - EX11: AI features
  - EX12: Batch template
- Self-contained product-themed assets replacing old stock images

### Changed
- All examples use `h264_fast` preset with hardware-accelerated encoding
- Transitions distributed across examples for full coverage
- CI validates hardware encoders with test encode, fixes version assertion

## [3.1.0] — 2026-03-11

### Changed
- Default h264 encoding changed from CRF 10 / preset medium to CRF 18 / preset fast
- Added `-tune fastdecode` for faster playback on mobile/web targets
- Added `h264_fast` preset (CRF 22, ultrafast) for draft rendering
- Added `h264_videotoolbox` preset for macOS hardware encoding
- Auto-detect and prefer hardware encoders when `preset="h264_1080p"` is used

### Fixed
- LowerThird frame caching for static middle frames between animate_in and animate_out
- LogoReveal caches final revealed state once animation completes
- CallToAction and SocialHandle cache static frames after animate_in
- TransitionTitle caches middle frames between animate_in and animate_out
- Countdown caches per-number frame (each digit renders once)
- Vignette effect caches distance mask per resolution and parameter set
- Bloom pre-allocates downsampling buffers and reuses across frames
- GaussianBlur pre-allocates float32 buffer and reuses across frames
- FilmGrain pre-allocates noise buffer per resolution
- Compositor reuses background frame buffer instead of copying every frame
- Alpha cache persists across frames for static clips
- Batch contiguous NORMAL-blend opaque layers into single memcpy

## [3.0.0] — 2026-03-11

### Fixed
- `loop_out()` now correctly loops the last N frames instead of duplicating `loop_in()` behavior
- Bilinear interpolation for zoom/scale transitions (was nearest-neighbor)
- Smoothstep feathered edges on iris transitions
- Glitch transition now has color channel separation (was scanline-only)
- CrossDissolve uses smoothstep curve
- Circular anti-aliased rendering for multi-pixel particles (was rectangular blocks)
- Fractional particle spawn rate accumulation (was truncated)
- Per-particle rotation for confetti preset
- Motion blur streaks for rain particles
- `_sizes` array now used in particle rendering (was ignored)
- Vignette uses smoothstep falloff (eliminates banding)
- Bloom uses downsampling pyramid for natural glow
- Neon chart theme has actual glow effect (was just different colors)
- Sidechain compressor implemented (was missing)
- 5.1 surround export with proper channel count (mixer produced 6ch but encoder ignored it)
- `pip()` shadow parameter renders actual drop shadows (was a stub)
- Emoji glyphs log debug warning instead of silently dropping
- Karaoke word highlighting renders spoken/upcoming words in different colors (was not implemented)

### Changed
- 8 production-quality showcase scripts replacing 11 older examples
- Export 3D post-processing configs (SSAOConfig, BloomConfig, DepthOfFieldConfig, ShadowMapConfig)
- `__repr__` on Composition and ParticleSystem
- Error messages include received values for AI effects
- 2427 tests (up from 2185), 91% coverage (up from 88%)

## [2.5.0] — 2026-03-11

### Added
- GPU-accelerated compositing via WGPU compute shaders with 8 blend modes
- GPU texture pooling and batch effect processing in single GPU pass
- Configurable VRAM budget with automatic CPU fallback
- NVENC hardware encoding preset (`h264_nvenc`, `h265_nvenc`)
- QSV hardware encoding preset (`h264_qsv`)
- AMF hardware encoding preset (`h264_amf`)
- Automatic hardware encoder detection and software fallback
- Ray backend for distributed rendering (`backend="ray"`)
- Dask backend for distributed rendering (`backend="dask"`)
- Fault-tolerant frame distribution with automatic retry
- Frame-level checkpointing for interrupted render resume
- Smart incremental rendering (skip unchanged frames)
- Memory-mapped frame buffers for 4K intermediates
- SIMD-optimized blend operations via Cython (optional)
- Static layer baking (pre-render non-animated layers once)
- Parallel audio rendering across worker threads
- `benchmark(comp, frames)` for render throughput measurement
- `profile_composition(comp, frames, detailed)` for per-stage timing
- `memory_report(comp)` for peak RAM per render stage
- `detect_bottlenecks(comp)` for identifying slowest clips/effects
- `frame_diff(frame_a, frame_b)` for pixel-level comparison

## [2.0.0] — 2026-03-11

### Added
- `RemoveBackground` effect (rembg) for background removal
- `ReplaceBackground` for compositing over new backgrounds
- `ObjectSegmentation` with SAM and text prompt for object isolation
- `RemoveObject` for inpainting over masked regions
- `ExtendFrame` for outpainting to extend frame edges
- `Upscale` effect (Real-ESRGAN 2x and 4x)
- `Denoise` effect (deep learning denoiser)
- `Deblur` effect (blind deconvolution)
- `FrameInterpolation` effect (RIFE-based)
- `ColorizeClip` for grayscale footage colorization
- `SceneDetector` for scene boundary detection
- `SilenceRemover` for removing silent segments
- `HighlightDetector` for extracting interesting segments
- `ContentAwareCrop` for AI reframing (16:9 to 9:16)
- `AutoColor` for one-click AI color correction
- `AutoEdit` for AI-powered rough cuts
- `FaceDetector`, `FaceTracker`, `FaceBlur` for face detection and anonymization
- `VoiceConversion` for voice style transfer
- `MusicGeneration` (MusicGen) for AI background music
- `SoundFXGeneration` for AI sound effects
- All AI features are optional extras (`pip install "pymotion-studio[ai]"`)

## [1.5.0] — 2026-03-11

### Added
- 5.1 surround channel routing with `SurroundChannel` enum
- Audio bus routing with volume and pan automation per bus
- Audio crossfades (linear, equal-power, S-curve)
- Multiband compressor with 4-band crossover
- Convolution reverb with impulse response WAV files
- LUFS normalization (`mixer.normalize(target_lufs=-14)`)
- `Silence` helper for generating timed silence
- `WaveformClip` for animated audio waveforms
- `SpectrumClip` for animated frequency spectrum bars
- `SpectrogramClip` for scrolling spectrograms
- `AudioReactiveEffect` for driving visual effects from audio amplitude
- `AutoCaptions` via Whisper transcription with word-level timing
- `SubtitleClip` for rendering subtitles from SRT files
- SRT, VTT, and ASS/SSA subtitle import and export
- 4 caption styles: netflix, youtube, tiktok, karaoke
- `TTSClip` with system (pyttsx3) and OpenAI engines
- ACES 1.3 color pipeline with sRGB-to-ACES conversion and filmic tone mapping
- HDR10 output preset (PQ transfer function, Rec.2020, 10-bit)
- HLG output preset (Hybrid Log-Gamma, Rec.2020)
- `ColorMatch` for Reinhard color transfer
- `HSLSecondary` for range-based secondary color grading
- `WaveformScopeClip`, `VectorscopeClip`, `HistogramClip`, `ParadeScopeClip`
- `Composition.export_edl()` for CMX 3600 EDL export
- `Composition.export_otio()` for OpenTimelineIO export

## [1.4.0] — 2026-03-10

### Added
- `BarChartClip`, `LineChartClip`, `PieChartClip`, `AreaChartClip`, `RadarChartClip`, `ScatterPlotClip` with Cairo rendering, ease-out animations, and 4 themes (corporate, minimal, neon, gradient)
- `NumberCounter` for animating numbers with formatting
- `ProgressBar` with rounded corners and animated fill
- `LowerThird` (8 styles), `LogoReveal` (6 styles), `CallToAction`, `SocialHandle` (5 platforms), `Countdown`, `QuoteCard` (4 styles), `Divider` (5 styles), `TransitionTitle` (5 styles), `Watermark`
- `BrowserMockup` (light/dark), `PhoneMockup` (flat/notch/dynamic_island), `DesktopMockup` (macos/windows/minimal)
- All mockups support animate_in/animate_out presets

## [1.3.0] — 2026-03-10

### Added
- `Composition.to_clip()` for nested compositions (pre-comps) up to 10 levels
- `AdjustmentLayer` that applies effects to all layers below it
- `BezierMask` with Cairo-rasterized paths and keyframe animation
- `LinearGradientMask`, `RadialGradientMask`, `TrackMatte`, `TextMask`
- Boolean mask operations: `MaskOp.ADD`, `MaskOp.INTERSECT`, `MaskOp.SUBTRACT`
- Clip parenting (`clip.parent = other`) with transform inheritance
- `NullObject` as invisible transform group anchor
- Expression system (`clip.set_expression(prop, fn)`) with `ExpressionContext`
- `wiggle(freq, amp, seed)`, `loop_in(duration, fn)`, `loop_out(duration, fn)` helpers
- `clip.follow_path(svg_path, duration, align)` for SVG path animation
- `StrokeClip` with trim_start/trim_end for draw-on/off strokes
- `morph_paths(path_a, path_b, progress)` for bezier path interpolation

## [1.2.1] — 2026-03-10

### Fixed
- CI matrix updated to Python 3.12, 3.13, 3.14 (dropped 3.10/3.11)
- Relaxed Pillow dependency to `>=10.0,<14.0`

## [1.2.0] — 2026-03-10

### Added
- `clip.split()`, `clip.join()`, `clip.subclip()`, `clip.repeat()`, `clip.freeze_frame()`
- `concatenate()` with optional transitions between clips
- `clip.speed()` (0.1x-10x), `clip.speed_ramp()`, `clip.reverse()`, `clip.time_remap()`
- Optical flow interpolation via OpenCV with automatic fallback
- `ChromaKey`, `LumaKey`, `ColorKey`, `DifferenceKey` with feathering, choking, despill
- `pip()`, `grid()`, `split_screen()`, `stack()` layout helpers
- `MotionTracker` for region tracking, `clip.stabilize()`, `clip.follow_tracker()`
- `clip.create_proxy()`, `clear_proxy_cache()`, `proxy_cache_size()`
- `clip.add_effect()` and `clip.render_with_effects()` for per-clip effect chains

## [1.0.1] — 2026-03-10

### Fixed
- Compositor `_alpha_cache` memory aliasing causing random layer skipping
- Text animation flicker via reveal-mask architecture for Typewriter/WordByWord/LetterByLetter
- CountUp/CountDown use quintic ease-out with frame-stepping for smooth counters
- FreeType renderer replaced block-character fallback with proper glyph rendering

### Changed
- H.264 presets: CRF 18 to 10, preset faster to medium, added x264 params
- H.265 presets: CRF 22 to 16, preset faster to medium
- Instagram/TikTok presets: added `-tune animation`
- 5 production-ready example scripts rewritten

## [1.0.0] — 2026-03-09

### Added
- Complete PRD public API: all symbols importable from `import pymotion`
- `Silence` helper, `animate()` shorthand, `Align` enum (13 values)
- Audio effects: `Reverb`, `Delay`, `PitchShift`, `NoiseReduction`, `LowPassFilter`, `HighPassFilter`
- 3D exports: `Scene3DClip`, `Scene3D`, `Camera`, lights, `PBRMaterial`
- Particle exports: `ParticleSystem`, `Emitter`, 6 presets
- `ScrambleText` alias for `Scramble`

## [0.9.0-rc] — 2026-03-09

### Added
- `PyMotionConfig` global configuration
- ACES, Reinhard, and Filmic tone mapping
- `pymotion doctor` CLI command
- Variable font full axis support
- MkDocs documentation site
- Dockerfile for containerized usage

## [0.4.0-beta] — 2026-03-09

### Added
- All 39 built-in transitions
- Complete visual, color, distortion, and light effects
- 9 animated text presets
- Variable font support, Google Fonts download
- Volume and pan keyframe automation
- Template ABC with field validation
- Frame sequence export, 15 export presets
- All 8 blend modes
- CLI benchmark, validate, new commands

## [0.3.0-beta] — 2026-03-09

### Added
- 3D rendering backend (ModernGL headless, PBR shaders, OBJ/GLTF loading)
- SSAO, Bloom, Depth of Field post-FX
- Audio DSP effects (EQ, Compressor, Limiter)
- Beat detection, onset detection, waveform extraction
- Particle system with vectorized NumPy updates and 5 presets
- Color pipeline with .cube LUT support
- Hot-reload preview server

## [0.2.0-alpha] — 2026-03-09

### Added
- TextClip with FreeType + HarfBuzz, multiline, stroke, shadow
- VideoClip (FFmpeg decode, trim, loop, speed, reverse)
- GradientClip (linear, radial, conic)
- 30 easing functions, spring physics, cubic bezier, steps
- 20 transitions (Fade, CrossDissolve, Slide, Push, Cover, Reveal, Zoom)
- AudioMixer, AudioClip with trim, fade, volume, loop
- 8 export presets

## [0.1.0-alpha] — 2026-03-09

### Added
- Core architecture: Composition, Track, Clip base class
- ColorClip, ImageClip, ShapeClip
- Keyframe animation system with interpolation
- 2D rendering backend (Cairo)
- Compositor with alpha blending
- FFmpeg encoder (subprocess, shell=False)
- GaussianBlur, Vignette effects
- Security validators
- CLI render and export-frame commands
- structlog-based logging
