# PyMotion Development State

## Current Phase
Phase: Alpha 0.2 — Text, Video, Audio Base
Started: 2026-03-09

## Phase 0.2 Checklist

### Text & Typography
- [x] text/renderer.py — FontLoader (local + system), GlyphRenderer (FreeType)
- [x] text/renderer.py — HarfBuzz integration for complex layout (RTL, ligatures)
- [x] clip/text.py — TextClip full implementation (all params from PRD §7.10)

### Video & Gradient
- [x] clip/video.py — VideoClip (file source, trim, loop, speed, reverse)
- [x] clip/color.py — GradientClip (linear, radial, conic)

### Animation
- [x] animation/easing.py — complete all 30 easings + spring() + cubic_bezier() + steps()
- [x] animation/spring.py — analytical damped harmonic oscillator
- [x] animation/interpolator.py — Color interpolation via OKLCH

### Transitions
- [x] transition/library.py — 20 transitions (Fade, FadeToBlack, FadeToWhite, DipToColor, CrossDissolve, Cut, Slide×4, Push×4, Cover×2, Reveal×2, ZoomIn, ZoomOut)

### Audio
- [x] audio/mixer.py — AudioMixer: add(), set_volume(), render()
- [x] clip/audio.py — AudioClip: trim, fade_in, fade_out, volume, loop, at()
- [x] audio/effects.py — EQ, Compressor, Limiter (via pedalboard)

### Export & CLI
- [x] export/presets.py — add: h264_4k, h265_1080p, h265_4k, webm_1080p, instagram_reel, youtube_1080p, youtube_4k, tiktok
- [x] cli/commands.py — add preview command (basic, no hot-reload yet)
- [x] __init__.py — extend public exports for Phase 0.2 symbols

### Tests (Phase 0.2)
- [x] tests/unit/test_text_renderer.py
- [x] tests/unit/test_audio_mixer.py
- [x] tests/unit/test_transitions.py (all 20)
- [x] tests/integration/test_render_2d.py — extend with TextClip + VideoClip cases

## Completed Phases

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
