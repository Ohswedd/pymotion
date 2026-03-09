# PyMotion Development State

## Current Phase
Phase: v1.0 — Stable Release
Started: 2026-03-09

## Phase v1.0 Checklist

### API & Imports
- [x] API stability audit — all PRD §8.2 exports verified
- [x] Zero broken imports from `import pymotion`
- [x] __init__.py — added: 3D types, ParticleSystem, Silence, animate, Align, 6 audio effects
- [x] __init__.py — docstring updated to "v1.0"

### Version & Release
- [x] pyproject.toml version → "1.0.0"
- [x] CHANGELOG.md — finalized 1.0.0 section

### Documentation
- [x] docs/guides/ — 10 total guides (5 new: text-animation, effects-pipeline, transitions, particles, template-system)
- [x] examples/ — 20 total examples (5 new: social_media_ad, countdown_timer, photo_slideshow, corporate_intro, music_visualizer)

### Quality Gates
- [x] All mypy --strict errors: zero
- [x] All ruff errors: zero
- [x] Test coverage: ≥ 85% (85%, 1116 tests)
- [x] All examples syntax-check pass

### External (require user action)
- [ ] PyPI test publish (TestPyPI) — install and verify
- [ ] PyPI production publish
- [ ] GitHub Release with generated notes from CHANGELOG
- [ ] Docker Hub publish: pymotion/pymotion:1.0.0 + pymotion/pymotion:latest
- [ ] git tag: v1.0.0

## Completed Phases

### Phase RC 0.9 — Polish & Production Readiness (COMPLETE)
- All 22 checklist items complete
- 1079 tests pass, 85% coverage

### Phase 0.4 — Full Feature Completeness (COMPLETE)
- All 24 checklist items complete
- 976 tests pass, 85% coverage
- Exit criteria: batch-render 5 Templates with transitions, particles, effects, audio DSP

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
- 3D post-FX have CPU fallbacks; GPU shader code ready for v1.0
- structlog add_logger_name removed — incompatible with PrintLoggerFactory
- Google Fonts download uses httpx with domain allowlist (fonts.googleapis.com, fonts.gstatic.com)
- Variable font support extended: ital, opsz axes + custom axes dict
- Effects use .apply(frame, ctx) pattern — not added to clips directly
- Tone mapping: ACES (Narkowicz 2015), Reinhard, Filmic (Hable) operators added
- Jupyter: export_frame_inline() for notebooks, preview_widget() with ipywidgets
- PyMotionConfig: thread-safe global config with get/set/reset
- Pillow Image.LANCZOS needs type: ignore[attr-defined] in Pillow 13+
- ipywidgets and IPython are optional deps (type: ignore[import-not-found])
- OpenEXR is optional dep — _load_exr falls back to gray 64x128 environment
- Shadow mapping is config-only (ShadowMapConfig) — full GPU implementation for v1.0
- Skeletal animation uses linear interpolation, no quaternion SLERP yet
- GPU instancing uses per-instance draw calls (true GPU instancing planned for v1.0)
