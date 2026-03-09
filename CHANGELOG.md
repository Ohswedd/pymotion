# Changelog

All notable changes to PyMotion are documented here.

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
