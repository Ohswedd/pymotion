# PyMotion Development State

## Current Phase
Phase: Alpha 0.1
Started: 2026-03-09

## Phase 0.1 Checklist
### Infrastructure
- [x] pyproject.toml
- [x] Full directory structure
- [x] PYMOTION_STATE.md
- [x] .gitignore
- [x] .github/workflows/ci.yml
- [x] Makefile (lint, test, render shortcuts)

### Core Modules
- [x] utils/color.py — Color class, parsing, conversion
- [x] utils/math.py — Vec2, Vec3, clamp, lerp, bezier
- [x] utils/logging.py — structured logger setup
- [x] utils/asset.py — AssetLoader with LRU cache
- [x] security/validation.py — all 4 validators
- [x] animation/easing.py — first 10 easings
- [x] animation/keyframe.py — Keyframe, KeyframeTrack
- [x] animation/interpolator.py — float + Color + Vec2
- [x] clip/base.py — Clip ABC
- [x] clip/color.py — ColorClip, GradientClip
- [x] clip/shape.py — ShapeClip (rect, circle, polygon, path)
- [x] clip/image.py — ImageClip
- [x] composition.py — Composition, Track
- [x] timeline.py — TimelineResolver, FrameScheduler
- [x] render/interface.py — RendererInterface ABC
- [x] render/backend_2d.py — CairoRenderer
- [x] render/compositor.py — alpha compositing + 4 blend modes
- [x] render/color_pipeline.py — sRGB passthrough + LUT stub
- [x] render/pipeline.py — RenderPipeline (serial first)
- [x] effects/base.py — Effect ABC
- [x] effects/visual.py — GaussianBlur, Vignette
- [x] transition/base.py — Transition ABC
- [x] transition/library.py — Fade, CrossDissolve
- [x] export/presets.py — OutputPreset + h264_1080p preset
- [x] export/encoder.py — FFmpegEncoder (secure)
- [x] cli/commands.py — render + export-frame commands
- [x] __init__.py — public exports (Phase 0.1 subset)

### Tests (Phase 0.1)
- [x] tests/conftest.py — fixtures
- [x] tests/unit/test_color.py
- [x] tests/unit/test_math.py
- [x] tests/unit/test_keyframe.py
- [x] tests/unit/test_easing.py
- [x] tests/unit/test_compositor.py
- [x] tests/unit/test_security.py
- [x] tests/integration/test_render_2d.py
- [x] tests/integration/test_encode.py

## Completed Tasks
- Task 0: Project scaffolding (pyproject.toml, directory structure, CI, Makefile)
- Phase 0.1: All core modules implemented and tested

## In Progress
(none)

## Blocked / Issues
(none)

## Dependency Additions
(none beyond PRD S13)

## Notes
- Cairo ARGB32 on little-endian is BGRA in memory, matching internal frame format
- scipy.ndimage used for GaussianBlur (no stubs available, type: ignore used)
- Phase 0.1 coverage at 68% (target was >= 50% for alpha)
- Pillow fromarray() called without mode parameter to avoid deprecation warning
