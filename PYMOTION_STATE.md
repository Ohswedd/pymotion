# PyMotion Development State

## Current Phase
Phase: Beta 0.4 — Full Feature Completeness
Started: 2026-03-09

## Phase 0.4 Checklist

### Transitions
- [x] transition/library.py — complete all 39 transitions (added 19 new)

### Visual Effects
- [x] effects/visual.py — MotionBlur, FilmGrain, Sharpen, ChromaticAberration, Glow, Bloom, LensFlare
- [x] effects/color.py — Brightness, Contrast, Saturation, HSL, ColorBalance, Curves, LUT, SplitToning, BleachBypass
- [x] effects/distortion.py — WaveWarp, Ripple, Twirl, PerspectiveWarp, Fisheye
- [x] effects/light.py — LensFlareLight, GodRays, NeonGlow, LightLeak

### Particles
- [x] particle/system.py — remaining presets: Stars, Dust, Explosion, Bubbles

### Typography
- [x] text/animated.py — 9 animated text presets (Typewriter, WordByWord, LetterByLetter, Scramble, KineticText, SplitReveal, CountUp, CountDown, GlitchText)
- [x] text/renderer.py — variable font support (weight, width, slant axes via load_variable)
- [x] clip/text.py — Google Fonts download (download_google_font with httpx, caching, domain allowlist)

### Audio
- [x] audio/mixer.py — volume keyframe automation, pan automation
- [x] audio/analysis.py — waveform-to-keyframe converter

### Template System
- [x] template/base.py — Template ABC with validation

### Export
- [x] export/encoder.py — frame sequence support (PNG/EXR via encode_frame_sequence)
- [x] export/presets.py — all 15 presets (added AV1, ProRes4444, ProResHQ, DNxHD, GIF, frame_sequence_png)

### Security
- [x] security/validation.py — all 5 validators + tests (added validate_file_size)

### Rendering
- [x] render/pipeline.py — frame cache for static layers
- [x] render/compositor.py — all 8 blend modes

### CLI
- [x] cli/commands.py — benchmark, validate, new commands added

### Integration
- [x] __init__.py — final public API surface (all effects, transitions, audio, templates exported)
- [x] tests/unit/test_effects.py — all effects tested
- [x] tests/unit/test_template.py — validation, type errors, path security
- [ ] tests/integration/test_encode.py — extend with all presets
- [ ] tests/snapshot/ — 20 reference frames total
- [ ] pip-audit added to CI and passing

## Completed Phases

### Phase 0.3 — 3D, Particles, Advanced Audio (COMPLETE)
- All 9 checklist items complete
- 558 tests pass, 82% coverage
- Exit criteria: 3D scene + 3 particle effects + audio analysis + color pipeline

### Phase 0.2 — Text, Video, Audio Base (COMPLETE)
- All 20 checklist items complete
- 275 tests pass, 69% coverage
- Exit criteria: product video with text, shapes, audio, 6 transitions to valid MP4

### Phase 0.1 — Core 2D Rendering Pipeline (COMPLETE)
- All infrastructure, core modules, and tests complete
- 132 tests pass, 68% coverage
- Exit criteria: valid MP4 render

## In Progress
Remaining: test_encode preset coverage, snapshot tests, pip-audit CI

## Blocked / Issues
(none)

## Dependency Additions
(none beyond PRD §13)

## Notes
- Cairo ARGB32 on little-endian is BGRA in memory, matching internal frame format
- scipy.ndimage used for GaussianBlur (no stubs available, type: ignore used)
- Pillow fromarray() called without mode parameter to avoid deprecation warning
- Color interpolation changed from RGBA to OKLCH (perceptually uniform) in Phase 0.2
- Font loader supports .ttf, .otf, and .ttc (TrueType Collection) files
- freetype-py and uharfbuzz have type stubs, use Any types instead of type: ignore
- pedalboard lazy-imported to avoid startup cost
- ModernGL create_standalone_context needs type: ignore[arg-type] for size parameter
- .cube LUT format: R varies fastest → data indexed as [b, g, r]
- librosa has type stubs, no type: ignore needed
- GLTF/GLB loading requires pygltflib optional dep (not in core deps)
- 3D post-FX have CPU fallbacks; GPU shader code ready for RC phase
- structlog add_logger_name removed — incompatible with PrintLoggerFactory
- Google Fonts download uses httpx with domain allowlist (fonts.googleapis.com, fonts.gstatic.com)
- Variable font support via FontLoader.load_variable() with weight/width/slant axes
- 956 tests pass, 85% coverage after Phase 0.4 implementation batch
