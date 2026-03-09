# PyMotion Development State

## Current Phase
Phase: Beta 0.3 — 3D, Particles, Advanced Audio
Started: 2026-03-09

## Phase 0.3 Checklist

### 3D Rendering
- [ ] render/backend_3d.py — ModernGLRenderer (headless, EGL + OSMesa)
- [ ] clip/scene3d.py — Scene3D, Camera, all light types, PBR materials
- [ ] GLTF/OBJ import

### 3D Post-FX
- [ ] 3D post-FX: SSAO, Bloom, DOF

### Audio Advanced
- [ ] audio/analysis.py — Beat detection (librosa)

### Particles
- [ ] particle/system.py — ParticleSystem with 5 presets

### Color Pipeline
- [ ] render/color_pipeline.py — LUT support, basic color grade

### Preview
- [ ] preview/server.py — Preview server with hot-reload

### Quality
- [ ] 80% test coverage
- [ ] Snapshot tests added

## Completed Phases

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
- Phase 0.1 coverage at 68% (target was >= 50% for alpha)
- Pillow fromarray() called without mode parameter to avoid deprecation warning
- Color interpolation changed from RGBA to OKLCH (perceptually uniform) in Phase 0.2
- Font loader supports .ttf, .otf, and .ttc (TrueType Collection) files
- freetype-py and uharfbuzz have type stubs, use Any types instead of type: ignore
- pedalboard lazy-imported to avoid startup cost
