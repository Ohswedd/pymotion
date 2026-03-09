# PyMotion Development State

## Current Phase
Phase: Beta 0.4 — Full Feature Completeness
Started: 2026-03-09

## Phase 0.4 Checklist

### Transitions
- [ ] transition/library.py — complete all 40 transitions (add remaining 20)

### Visual Effects
- [ ] effects/visual.py — MotionBlur, FilmGrain, Sharpen, ChromaticAberration, Glow, Bloom, LensFlare
- [ ] effects/color.py — Brightness, Contrast, Saturation, HSL, ColorBalance, Curves, LUT, SplitToning, BleachBypass
- [ ] effects/distortion.py — WaveWarp, Ripple, Twirl, PerspectiveWarp, Fisheye
- [ ] effects/light.py — LensFlare, GodRays, NeonGlow, LightLeak

### Particles
- [ ] particle/system.py — remaining presets: Stars, Dust, Explosion, Bubbles

### Typography
- [ ] text/animated.py — 8 animated text presets
- [ ] text/renderer.py — variable font support, text on bezier path, SDF
- [ ] clip/text.py — Google Fonts download

### Audio
- [ ] audio/mixer.py — volume keyframe automation, pan automation
- [ ] audio/analysis.py — waveform-to-keyframe converter

### Template System
- [ ] template/base.py — Template ABC with validation

### Export
- [ ] export/encoder.py — ProRes4444, ProResHQ, DNxHD, frame sequences
- [ ] export/presets.py — complete all 15 presets

### Security
- [ ] security/validation.py — complete all validators + tests

### Rendering
- [ ] render/pipeline.py — frame cache for static layers
- [ ] render/compositor.py — all 8 blend modes

### CLI
- [ ] cli/commands.py — benchmark + validate + new commands

### Integration
- [ ] __init__.py — final public API surface
- [ ] tests/unit/test_effects.py — all effects tested
- [ ] tests/unit/test_template.py — validation, type errors, path security
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
(none)

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
