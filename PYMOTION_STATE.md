# PyMotion Development State

## Current Phase
Phase: v1.2 — Video Editing & Clip Operations (IN PROGRESS)
Started: 2026-03-10

## Publishing & Distribution

| Channel | Value |
|---------|-------|
| **PyPI package** | `pymotion-studio` |
| **Install** | `pip install pymotion-studio` |
| **Import** | `from pymotion import ...` |
| **GitHub** | github.com/Ohswedd/pymotion |
| **License** | PyMotion Source Available License 1.0 |

## How to Release a New Version

1. Bump version in `pyproject.toml`
2. Add release notes to `CHANGELOG.md`
3. Commit and push to `main`
4. Tag and push:
   ```bash
   git tag v1.x.x
   git push origin v1.x.x
   ```
5. Create a GitHub Release from the tag (or let `release.yml` do it automatically)
6. `publish.yml` fires on the release event and uploads to PyPI via trusted publisher
7. `docker.yml` fires on the same event and pushes to Docker Hub (if secrets configured)

## CI/CD Pipelines

| Workflow | Trigger | What It Does |
|----------|---------|--------------|
| `ci.yml` | push/PR to `main` | Lint (ruff + mypy --strict), Test (Python 3.11 + 3.12, 80% coverage gate), Security audit (pip-audit) |
| `release.yml` | tag push `v*` | Extracts CHANGELOG section, creates GitHub Release |
| `publish.yml` | GitHub release published | Builds sdist + wheel, publishes to PyPI via OIDC |
| `docker.yml` | GitHub release published | Builds Docker image, pushes to Docker Hub |

---

## Full Roadmap Overview

| Phase | Name | Status |
|-------|------|--------|
| v0.1 | Core 2D Rendering Pipeline | COMPLETE |
| v0.2 | Text, Video, Audio Base | COMPLETE |
| v0.3 | 3D, Particles, Advanced Audio | COMPLETE |
| v0.4 | Full Feature Completeness | COMPLETE |
| v0.9 RC | Polish & Production Readiness | COMPLETE |
| v1.0 | Stable Release | COMPLETE |
| v1.0.1 | Patch Release | COMPLETE |
| **v1.2** | **Video Editing & Clip Operations** | **IN PROGRESS** |
| v1.3 | Advanced Compositing & Masking | PLANNED |
| v1.4 | Motion Graphics & Data Visualization | PLANNED |
| v1.5 | Professional Audio & Color Science | PLANNED |
| v2.0 | AI-Powered Features | PLANNED |
| v2.5 | Performance & Scale | PLANNED |

---

## Phase v1.2 — Video Editing & Clip Operations (IN PROGRESS)

**Goal:** Make PyMotion a complete, code-first video editing toolkit covering every operation a professional editor needs.

### 1.2.1 Clip Manipulation
- [x] `clip.split(frame)` — split a clip into two at a given frame; preserves all effects, keyframes, and audio
- [x] `clip.join(other)` — concatenate two clips sequentially; returns a new combined clip with merged audio
- [x] `pm.concatenate(clips, transition=None, transition_duration=15)` — merge a list of clips with optional transition between each pair
- [x] `clip.subclip(start, end)` — extract a portion of a clip in local frame coordinates
- [x] `clip.repeat(n)` — repeat a clip N times; n=-1 fills composition duration
- [x] `clip.freeze_frame(frame, duration)` — hold a single frame for a duration, then resume playback

### 1.2.2 Speed & Time
- [x] `clip.speed(factor)` — uniform speed change (0.1×–10×) with audio pitch correction via phase vocoder
- [x] `clip.speed_ramp(keyframes)` — variable speed within one clip; list of (frame, factor) pairs; recalculates total duration
- [x] `clip.reverse()` — play video and audio backwards
- [x] `clip.time_remap(curve)` — arbitrary time remapping via BezierCurve mapping output_frame → source_frame
- [x] Optical flow interpolation for slow-motion: `clip.speed(0.5, interpolation="optical_flow")` uses `cv2.calcOpticalFlowFarneback`; falls back to frame duplication if OpenCV unavailable

### 1.2.3 Chroma Key & Keying
- [x] `ChromaKey` effect — YCbCr-based green/blue screen removal; params: `color`, `tolerance`, `edge_softness`, `spill_suppression`
- [x] `LumaKey` effect — key on luminance threshold; params: `threshold`, `softness`, `invert`
- [x] `ColorKey` effect — key any arbitrary color using Lab color distance; params: `color`, `tolerance`, `softness`
- [x] `DifferenceKey` effect — key based on pixel difference from a reference frame
- [x] Shared keying utilities in `effects/keying.py`: `_feather_mask`, `_choke_mask`, `_despill`

### 1.2.4 Picture-in-Picture & Layout Helpers
- [x] `pm.pip(main, overlay, position, size, border=None, shadow=None)` — composite overlay onto main; position accepts pixel tuple or named anchor
- [x] `pm.grid(clips, rows, cols, gap=0, background="#000000")` — arrange clips in an R×C grid; auto-scale each clip to its cell
- [x] `pm.split_screen(clips, layout)` — layout: `"horizontal"`, `"vertical"`, `"quad"`, or list of normalized `(x, y, w, h)` rects
- [x] `pm.stack(clips, direction, gap=0)` — stack clips side-by-side or top-to-bottom; auto-calculates output resolution
- [x] `_resolve_position(anchor, clip_size, container_size)` in `utils/layout.py` — resolve named anchors to pixel coords

### 1.2.5 Motion Tracking & Stabilization
- [x] `clip.stabilize(smoothing=30, border_mode="crop")` — feature tracking + affine smoothing; `border_mode`: `"crop"` | `"reflect"`; requires OpenCV
- [x] `pm.MotionTracker(clip, region=(x, y, w, h))` — track a region across frames using `cv2.TrackerCSRT_create()`
- [x] `tracker.track()` — returns `dict[int, Vec2]` of frame → center position
- [x] `tracker.to_keyframes(prop)` — converts tracking data to a `KeyframeTrack`
- [x] `clip.follow_tracker(tracker, prop="position", offset=(0, 0))` — wire tracker output to any clip property

### 1.2.6 Proxy Workflow
- [x] `clip.create_proxy(scale=0.25, cache_dir=None)` — generate low-res proxy; filename = `SHA256(source + scale)[:12].proxy`; reuses existing proxy if hash matches
- [x] `ProxyClip` — renders frames from cached raw BGRA proxy file; auto-scales to requested resolution via nearest-neighbor
- [x] `pm.clear_proxy_cache(older_than_days=30)` — remove stale proxies from `~/.pymotion/proxies/`
- [x] `pm.proxy_cache_size()` — returns total bytes used by proxy cache

---

## Phase v1.3 — Advanced Compositing & Masking (PLANNED)

**Goal:** After Effects-level compositing precision — masks, mattes, parenting, and expressions — all in pure Python code.

### 1.3.1 Nested Compositions
- [ ] `Composition.to_clip()` — embed a composition as a clip inside another; recursive up to 10 levels
- [ ] Independent resolution and fps per nested comp with auto-scaling to parent
- [ ] Shared asset LRU cache across all nesting levels

### 1.3.2 Adjustment Layers
- [ ] `AdjustmentLayer(effects)` — applies its effect chain to every layer below it in the track
- [ ] Maskable: accepts the same mask interface as any other clip
- [ ] All effect parameters animatable via keyframes

### 1.3.3 Advanced Masking
- [ ] Bezier path masks: `clip.add_mask(BezierMask(points, feather, expansion, invert))`
- [ ] Mask shape animation: interpolate bezier control points per frame
- [ ] Multiple masks per clip with boolean ops: `union`, `intersect`, `subtract`
- [ ] `TrackMatte` — use another clip's alpha channel or luma as a mask
- [ ] Gradient masks: `LinearGradientMask`, `RadialGradientMask`
- [ ] Text as mask: `TextMask(text, font, size)` — clip visible only through letterforms

### 1.3.4 Parenting & Hierarchy
- [ ] `clip.parent = other_clip` — child inherits position, scale, rotation from parent each frame
- [ ] `NullObject` — invisible clip used as a transform group anchor
- [ ] Independent local offsets on top of inherited parent transform
- [ ] Chains of arbitrary depth (A → B → C); circular parenting raises `ValueError`

### 1.3.5 Expression System
- [ ] Python callable on any animatable property: `clip.set_expression("position.x", lambda ctx: ctx.frame * 2.5)`
- [ ] Expression context object: `ctx.frame`, `ctx.time`, `ctx.fps`, `ctx.comp_width`, `ctx.comp_height`, `ctx.progress`
- [ ] `wiggle(freq, amp, seed=0)` expression helper — smooth random oscillation
- [ ] `loop_in()` / `loop_out()` — loop keyframe animation at clip boundaries
- [ ] Expression linking: `clip_b.set_expression("opacity", lambda ctx: clip_a.opacity_at(ctx.frame))`

### 1.3.6 Path Animation
- [ ] `clip.follow_path(svg_path_str, duration, align=True)` — animate clip center along an SVG path
- [ ] Path trim animation: `StrokeClip(path, trim_start=animate(...), trim_end=animate(...))` — draw-on / draw-off stroke
- [ ] Path morph: `ShapeClip.morph(path_a, path_b, progress=animate(...))` — interpolate between two bezier paths

---

## Phase v1.4 — Motion Graphics & Data Visualization (PLANNED)

**Goal:** Complete library of reusable, animatable motion graphics components and data-driven chart clips — everything needed for YouTube content, corporate video, and explainer videos.

### 1.4.1 Animated Chart Clips
- [ ] `BarChartClip(data, labels, animate_duration, theme)` — animated bar chart; bars grow from baseline
- [ ] `LineChartClip(data, labels, animate_duration, theme)` — animated line chart; line draws on
- [ ] `PieChartClip(data, labels, animate_duration, theme)` — animated pie chart; slices sweep in
- [ ] `AreaChartClip(data, labels, animate_duration, theme)` — filled area variant of line chart
- [ ] `RadarChartClip(data, axes, animate_duration, theme)` — spider/radar chart
- [ ] `ScatterPlotClip(x, y, labels, animate_duration, theme)` — scatter plot with point animation
- [ ] `NumberCounter(start, end, duration, format_fn, font, size, color)` — animates a number from start to end
- [ ] `ProgressBar(value=animate(...), width, height, fill_color, bg_color, radius)` — animated progress bar
- [ ] Chart themes: `"corporate"`, `"minimal"`, `"neon"`, `"gradient"` — each sets colors, fonts, gridlines, label style
- [ ] All charts accept `data` as a Python list, dict, pandas Series, or a callable returning data per frame (live binding)

### 1.4.2 Motion Graphics Components
- [ ] `LowerThird(name, title, style)` — 8+ designs; animated in/out; fully customizable colors and fonts
- [ ] `LogoReveal(image, style, duration)` — 6+ reveal animations: fade, slice, grow, glitch, draw, shatter
- [ ] `CallToAction(text, sub_text, style)` — animated CTA overlay (subscribe, buy, visit)
- [ ] `SocialHandle(platform, handle, style)` — platform-styled overlay (YouTube, Instagram, TikTok, X, LinkedIn)
- [ ] `Countdown(from_n, duration, font, style)` — animated countdown timer (numbers or clock)
- [ ] `QuoteCard(text, attribution, style)` — styled quote overlay with animation
- [ ] `Divider(style, direction, duration)` — animated line/shape divider between sections
- [ ] `TransitionTitle(text, style, duration)` — full-screen title card with enter/exit animation
- [ ] `Watermark(image_or_text, position, opacity)` — persistent branded overlay with optional pulse animation

### 1.4.3 Screen & Device Mockups
- [ ] `BrowserMockup(content_clip, theme)` — browser chrome frame around a clip; theme: `"light"` | `"dark"`
- [ ] `PhoneMockup(content_clip, model)` — phone bezel frame; model: `"flat"` | `"notch"` | `"dynamic_island"`
- [ ] `DesktopMockup(content_clip, os_theme)` — desktop window frame; theme: `"macos"` | `"windows"` | `"minimal"`
- [ ] All mockups: animatable position, scale, rotation; support `animate_in` / `animate_out` presets

---

## Phase v1.5 — Professional Audio & Color Science (PLANNED)

**Goal:** Broadcast-grade audio processing and a complete professional color pipeline. Every tool a colorist or audio engineer expects, expressed as Python API.

### 1.5.1 Advanced Audio
- [ ] Multi-channel audio mixing: 5.1 surround (L, R, C, LFE, Ls, Rs channel routing)
- [ ] Audio bus routing: named submixes (`dialogue`, `music`, `sfx`) → master bus
- [ ] Frame-accurate audio automation curves (keyframe-driven volume and pan per bus)
- [ ] Audio crossfades: `linear`, `equal_power`, `s_curve` — applied at clip boundaries
- [ ] Multiband compressor: 4-band with crossover frequencies and per-band controls
- [ ] Convolution reverb: load impulse response WAV file for acoustic space simulation
- [ ] LUFS normalization: `mixer.normalize(target_lufs=-14)` for streaming; `-23` for broadcast
- [ ] `Silence(duration_sec)` — generates precisely timed silence (already exists — verify and extend)

### 1.5.2 Audio Visualization Clips
- [ ] `WaveformClip(audio, style, color, background)` — animated audio waveform
- [ ] `SpectrumClip(audio, bands, style, color_map)` — animated frequency spectrum bars
- [ ] `SpectrogramClip(audio, style)` — scrolling spectrogram as a video clip
- [ ] `AudioReactiveEffect(effect, audio, property, band, sensitivity)` — drive any visual effect parameter from audio amplitude or a specific frequency band

### 1.5.3 Captions & Subtitles
- [ ] `AutoCaptions(audio_clip, model, style)` — Whisper transcription → animated word-by-word subtitle overlay
- [ ] `SubtitleClip(srt_path, style)` — render subtitles from an SRT file
- [ ] Subtitle import: SRT, VTT, ASS/SSA parser → list of timed `TextClip`s
- [ ] Subtitle export: `comp.export_subtitles(path, format="srt")`
- [ ] Caption styles: `"netflix"`, `"youtube"`, `"tiktok"`, `"karaoke"` (karaoke highlights current word)
- [ ] Word-level timestamp alignment from Whisper output

### 1.5.4 TTS Integration
- [ ] `TTSClip(text, voice, engine, speed, pitch)` — generates an audio clip from text
- [ ] Engine support: `"system"` (pyttsx3, zero deps), `"openai"` (requires API key), `"elevenlabs"` (requires API key)
- [ ] Returns a standard `AudioClip` that works in `AudioMixer` like any other

### 1.5.5 Color Science
- [ ] Full ACES 1.3 color pipeline option: `Composition(color_space="aces")`
- [ ] HDR10 output preset (PQ transfer function, Rec.2020 primaries, 10-bit)
- [ ] HLG output preset (Hybrid Log-Gamma, Rec.2020)
- [ ] `ColorMatch(reference_clip)` effect — match color grade of current clip to a reference
- [ ] `HSLSecondary(hue_range, saturation_range, luminance_range, grade)` — isolate and grade a specific color range
- [ ] Scope clips (for QC and educational use):
  - [ ] `WaveformScopeClip(source)` — luma waveform monitor
  - [ ] `VectorscopeClip(source)` — chrominance vectorscope
  - [ ] `HistogramClip(source, channels)` — per-channel histogram
  - [ ] `ParadeScopeClip(source)` — RGB parade monitor
- [ ] EDL export: `comp.export_edl(path)` — basic CMX 3600 EDL
- [ ] OTIO export: `comp.export_otio(path)` — OpenTimelineIO (requires `opentimelineio` optional dep)

---

## Phase v2.0 — AI-Powered Features (PLANNED)

**Goal:** Integrate best-in-class AI capabilities as first-class PyMotion effects and clip types. All AI features are optional extras — no AI dependency required for core library.

### 2.0.1 Background & Object Manipulation
- [ ] `RemoveBackground` effect — removes background using `rembg`; returns clip with alpha
- [ ] `ReplaceBackground(new_bg)` — combines `RemoveBackground` + compositing over new_bg
- [ ] `ObjectSegmentation(prompt)` — Segment Anything Model (SAM) + text prompt to isolate objects
- [ ] `RemoveObject(mask)` — inpaint over a masked region to remove objects from scene
- [ ] `ExtendFrame(direction, amount)` — outpainting to extend frame edges

### 2.0.2 Enhancement & Restoration
- [ ] `Upscale(factor)` effect — Real-ESRGAN 2× and 4× upscaling; 2× runs on CPU
- [ ] `Denoise` effect — deep learning denoiser for noisy footage
- [ ] `Deblur` effect — blind deconvolution deblurring
- [ ] `FrameInterpolation(factor)` effect — RIFE-based frame interpolation for smooth slow-motion; requires GPU
- [ ] `ColorizeClip` effect — AI colorization of grayscale footage

### 2.0.3 Smart Editing Helpers
- [ ] `pm.SceneDetector(clip)` — detect scene boundaries; returns list of frame indices
- [ ] `pm.SilenceRemover(clip, threshold_db, min_silence_sec)` — removes silent segments and re-joins
- [ ] `pm.HighlightDetector(clip, criteria)` — score and extract the most visually interesting segments
- [ ] `pm.ContentAwareCrop(clip, target_ratio)` — AI reframing (16:9 → 9:16); tracks subject using saliency
- [ ] `pm.AutoColor(clip)` — one-click AI color correction to neutral, well-exposed baseline
- [ ] `pm.AutoEdit(clips, style, music)` — AI selects best moments from raw clips, cuts on beats, returns `Composition`

### 2.0.4 Face & Body
- [ ] `FaceDetector(clip)` — detect and return face bounding boxes per frame
- [ ] `FaceTracker(clip)` — track detected faces across frames; returns `MotionTracker`-compatible data
- [ ] `FaceBlur(clip, strength)` — automatically detect and blur all faces

### 2.0.5 AI Voice & Audio
- [ ] `VoiceConversion(clip, target_voice_sample)` — convert voice style; requires `voice-conversion` optional dep
- [ ] `MusicGeneration(prompt, duration, tempo)` — AI background music via MusicGen; returns `AudioClip`
- [ ] `SoundFXGeneration(description, duration)` — AI sound effect generation; returns `AudioClip`

---

## Phase v2.5 — Performance & Scale (PLANNED)

**Goal:** Make PyMotion fast enough for production pipelines — 4K batch rendering, GPU-accelerated compositing, and distributed execution.

### 2.5.1 GPU-Accelerated Compositing
- [ ] WGPU compute shaders for frame compositing (replace NumPy blending with GPU kernels)
- [ ] GPU texture pooling: reuse GPU memory across frames instead of allocating per frame
- [ ] Batch effect processing on GPU: apply multiple effects in a single GPU pass
- [ ] GPU memory budget management: configurable VRAM limit with fallback to CPU

### 2.5.2 Hardware Encoding
- [ ] NVENC hardware encoding preset (NVIDIA GPUs) — `preset="h264_nvenc"` / `preset="h265_nvenc"`
- [ ] QSV hardware encoding preset (Intel Quick Sync) — `preset="h264_qsv"`
- [ ] AMF hardware encoding preset (AMD) — `preset="h264_amf"`
- [ ] Automatic hardware encoder detection and fallback to software encoder

### 2.5.3 Distributed Rendering
- [ ] Ray integration: `Composition.render(..., backend="ray")` distributes frames across Ray cluster
- [ ] Fault-tolerant frame distribution: failed frames are automatically retried on a different worker
- [ ] `Composition.render(..., backend="dask")` — Dask bag alternative for simpler setups
- [ ] Frame-level checkpointing: resume interrupted renders from last completed frame
- [ ] Cloud execution examples: AWS Lambda, GCP Cloud Run, Azure Container Instances

### 2.5.4 Render Optimizations
- [ ] Smart incremental rendering: skip re-rendering frames whose source clips haven't changed
- [ ] Memory-mapped frame buffers: `mmap` for intermediate frames at 4K to avoid RAM exhaustion
- [ ] SIMD-optimized blend operations via Cython extensions (optional build dep)
- [ ] Static layer baking: pre-render non-animated layers once and reuse across all frames
- [ ] Parallel audio rendering: split audio timeline processing across worker threads

### 2.5.5 Profiling & Diagnostics
- [ ] `Composition.render(profile=True)` — detailed per-stage, per-clip timing report
- [ ] `pm.benchmark(comp, n_frames=100)` — measure and report render throughput
- [ ] Memory usage report: peak RAM and VRAM per render stage
- [ ] Bottleneck detector: automatically identifies the slowest clip or effect in the pipeline
- [ ] Frame diff tool: `pm.frame_diff(frame_a, frame_b)` — pixel-level comparison returning diff image and score

---

## Completed Phases

### Phase v1.0.1 — Patch Release (COMPLETE, 2026-03-10)

#### Critical Bug Fixes
- [x] Compositor `_alpha_cache` memory aliasing — text layers randomly skipped due to numpy pointer reuse
- [x] Animated text flickering — reveal-mask architecture for Typewriter/WordByWord/LetterByLetter
- [x] CountUp/CountDown frame-stepping — quintic ease-out + step_frames=3 for smooth counters
- [x] FreeType renderer — replaced block-char fallback with proper glyph rendering

#### Encoding Quality
- [x] H.264 presets: CRF 18→10, preset faster→medium
- [x] Added x264-params: no-dct-decimate, no-fast-pskip
- [x] Added Lanczos chroma scaling for RGB→YUV420p conversion
- [x] H.265 presets: CRF 22→16, preset faster→medium
- [x] Instagram/TikTok presets: added -tune animation

#### Examples & Infrastructure
- [x] 5 production-ready examples rewritten with stock assets
- [x] 1116 tests pass, 85% coverage, ruff clean, mypy --strict clean
- [x] pip-audit clean (Pillow bumped for CVE-2026-25990)
- [x] GitHub repo public: github.com/Ohswedd/pymotion
- [x] CI/CD: ci.yml, publish.yml, release.yml, docker.yml
- [x] git tags: v1.0.0, v1.0.1 — PyPI: pymotion-studio v1.0.1 published

### Phase v1.0 — Stable Release (COMPLETE, 2026-03-09)
- [x] Complete PRD §8.2 public API surface
- [x] 1116 tests, 85% coverage, all quality gates passed

### Phase RC 0.9 (COMPLETE) · Phase 0.4 (COMPLETE) · Phase 0.3 (COMPLETE)
### Phase 0.2 (COMPLETE) · Phase 0.1 (COMPLETE)

---

## Blocked / Issues
(none)

## Dependency Additions
(none beyond pyproject.toml — document any additions here with justification)

## Notes
(architecture decisions that deviate from spec go here with rationale)