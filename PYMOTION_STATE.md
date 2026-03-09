# PyMotion Development State

## Current Phase
Phase: RC 0.9 — Polish & Production Readiness
Started: 2026-03-09

## Phase RC 0.9 Checklist

### Rendering & Performance
- [ ] 4K rendering validated end-to-end (all presets at 3840×2160)
- [ ] render/color_pipeline.py — ACES full color pipeline
- [ ] render/pipeline.py — GPU instancing support (ModernGL)

### 3D Backend
- [ ] render/backend_3d.py — HDRI environment maps (actual EXR loading)
- [ ] render/backend_3d.py — shadow mapping (directional + spot)
- [ ] render/backend_3d.py — skeletal animation (GLTF skin/animation)

### Typography
- [ ] clip/text.py — variable fonts full axis support

### Preview & CLI
- [ ] preview/server.py — Jupyter widget (export_frame inline + preview_widget)
- [ ] cli/commands.py — pymotion doctor (checks all system deps)

### Configuration
- [ ] utils/asset.py — configurable LRU cache size via PyMotionConfig
- [ ] pymotion/config.py — PyMotionConfig (allow_network, cache_size, etc.)

### Quality Gates
- [ ] All mypy --strict errors: zero
- [ ] All ruff errors: zero
- [ ] Test coverage: ≥ 85%
- [ ] Performance regression tests in CI (baseline from benchmark command)

### Documentation
- [ ] docs/ — MkDocs + Material setup with mkdocstrings
- [ ] docs/api/ — auto-generated from all public modules
- [ ] docs/guides/ — minimum 5 guides: getting-started, keyframe-animation, audio-mixing, 3d-scenes, batch-generation

### Examples & Packaging
- [ ] examples/ — 10 working example scripts
- [ ] Docker image — Dockerfile + build verified
- [ ] CHANGELOG.md — complete from phase 0.1 to 0.9
- [ ] README.md — complete with install, quickstart, feature matrix

## Completed Phases

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
- 3D post-FX have CPU fallbacks; GPU shader code ready for RC phase
- structlog add_logger_name removed — incompatible with PrintLoggerFactory
- Google Fonts download uses httpx with domain allowlist (fonts.googleapis.com, fonts.gstatic.com)
- Variable font support via FontLoader.load_variable() with weight/width/slant axes
- Effects use .apply(frame, ctx) pattern — not added to clips directly
