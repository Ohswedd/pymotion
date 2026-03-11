"""Example 11 — Performance & Scale Showcase.

Demonstrates v2.5 features:

- **GPU compositing** — WGPU compute shader compositor with CPU fallback
- **GPU batch effects** — single-pass multi-effect processing
- **Hardware encoding** — NVENC/QSV/AMF auto-detection and fallback
- **Distributed rendering** — Ray/Dask backends with checkpointing
- **Render optimizations** — incremental rendering, static layer cache,
  memory-mapped buffers, SIMD blend, parallel audio
- **Profiling & diagnostics** — benchmark, bottleneck detection,
  memory report, frame diff

Niche: Render pipeline optimization and large-scale production workflows
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from pymotion import (
    Composition,
    GradientClip,
    IncrementalRenderer,
    LowerThird,
    MappedFrameBuffer,
    RenderCheckpoint,
    StaticLayerCache,
    TextClip,
    Track,
    benchmark,
    detect_bottlenecks,
    detect_hardware_encoders,
    frame_diff,
    memory_report,
    render_audio_parallel,
    resolve_preset_with_fallback,
    try_simd_blend,
)

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

FPS = 30
WIDTH, HEIGHT = 1920, 1080


# ─────────────────────────────────────────────────────────────────────
# 1. Render a showcase composition
# ─────────────────────────────────────────────────────────────────────


def build_showcase_comp() -> Composition:
    """Build a multi-layer composition for profiling demos."""
    comp = Composition(WIDTH, HEIGHT, fps=FPS, duration=150)

    bg_track = Track(name="bg")
    bg = GradientClip(color_start="#0D1B2A", color_end="#1B2838")
    bg.set_duration(150)
    bg_track.add(bg)

    title_track = Track(name="title")
    title = TextClip("Performance & Scale", font="Arial", size=64.0, color="#D4AF37")
    title.set_duration(150).set_position(520.0, 40.0)
    title_track.add(title)

    features_track = Track(name="features")
    features = [
        "GPU Compositing (WGPU)",
        "Hardware Encoding (NVENC/QSV/AMF)",
        "Distributed Rendering (Ray/Dask)",
        "Incremental Rendering & Caching",
        "Profiling & Bottleneck Detection",
    ]
    for i, feat in enumerate(features):
        label = TextClip(f"* {feat}", font="Arial", size=32.0, color="#58A6FF")
        label.set_duration(120).at(15).set_position(200.0, 180.0 + i * 60.0)
        features_track.add(label)

    lt_track = Track(name="lower_third")
    lt = LowerThird(
        name="PyMotion v2.5",
        title="Performance & Scale",
        style="modern",
        animate_in=15,
        animate_out=15,
    )
    lt.set_duration(90).at(30)
    lt_track.add(lt)

    comp.add_track(bg_track)
    comp.add_track(title_track)
    comp.add_track(features_track)
    comp.add_track(lt_track)
    return comp


def demo_render_composition() -> None:
    """Render the showcase video."""
    comp = build_showcase_comp()
    comp.render(str(OUTPUT_DIR / "11a_performance_showcase.mp4"), preset="h264_1080p")
    print("  Rendered 11a_performance_showcase.mp4")


# ─────────────────────────────────────────────────────────────────────
# 2. GPU compositing (with CPU fallback)
# ─────────────────────────────────────────────────────────────────────


def demo_gpu_compositing() -> None:
    """Demonstrate GPU compositor with transparent fallback."""
    try:
        from pymotion import get_gpu_compositor

        gpu = get_gpu_compositor()
        bg = np.zeros((64, 64, 4), dtype=np.uint8)
        layer = np.full((64, 64, 4), 128, dtype=np.uint8)
        layer[:, :, 3] = 200
        result = gpu.composite_layers(bg, [(layer, "normal", 0.8)])
        print(f"  GPU composite: output shape={result.shape}")
    except (RuntimeError, ImportError):
        print("  GPU not available — CPU fallback active (transparent to user)")


# ─────────────────────────────────────────────────────────────────────
# 3. GPU batch effects
# ─────────────────────────────────────────────────────────────────────


def demo_gpu_effects() -> None:
    """Demonstrate GPU batch effect processing."""
    try:
        from pymotion import Brightness, Contrast, GPUEffectPipeline, Saturation, is_gpu_effect

        effects = [Brightness(value=1.2), Contrast(value=1.1), Saturation(value=0.9)]
        gpu_ok = [e for e in effects if is_gpu_effect(e)]
        print(f"  {len(gpu_ok)} of {len(effects)} effects are GPU-compatible")

        _pipeline = GPUEffectPipeline()  # noqa: F841
        print("  GPU effect pipeline initialized")
    except (RuntimeError, ImportError):
        print("  GPU effects not available — effects run on CPU (transparent to user)")


# ─────────────────────────────────────────────────────────────────────
# 4. Hardware encoding detection
# ─────────────────────────────────────────────────────────────────────


def demo_hardware_encoding() -> None:
    """Detect hardware encoders and show fallback logic."""
    available = detect_hardware_encoders()
    if available:
        print(f"  Hardware encoders: {available}")
        preset = resolve_preset_with_fallback(available[0])
        print(f"  Using preset: {preset.name}")
    else:
        print("  No hardware encoders found — using software encoding")
        preset = resolve_preset_with_fallback("h264_nvenc")
        print(f"  Fallback preset: {preset.name}")


# ─────────────────────────────────────────────────────────────────────
# 5. Distributed rendering checkpoint
# ─────────────────────────────────────────────────────────────────────


def demo_checkpointing() -> None:
    """Demonstrate render checkpoint save/resume."""
    cp_path = OUTPUT_DIR / "demo_checkpoint.json"
    cp = RenderCheckpoint(cp_path)

    # Simulate rendering 10 frames
    for i in range(10):
        cp.mark_completed(i)
    cp.save()

    print(f"  Checkpoint saved: {cp.last_completed + 1} frames completed")
    print(f"  Pending frames 0-20: {cp.pending_frames(0, 20)[:5]}...")

    # Clean up
    cp.clear()
    print("  Checkpoint cleared")


# ─────────────────────────────────────────────────────────────────────
# 6. Render optimizations
# ─────────────────────────────────────────────────────────────────────


def demo_incremental_renderer() -> None:
    """Demonstrate incremental rendering with state hashing."""
    comp = build_showcase_comp()
    renderer = IncrementalRenderer(cache_dir=OUTPUT_DIR / "incr_cache")

    # First render — computed
    renderer.render_frame(comp, 0)
    # Second render — served from cache
    renderer.render_frame(comp, 0)

    print(f"  IncrementalRenderer: {renderer.cached_frames} frames cached")
    renderer.invalidate()


def demo_static_layer_cache() -> None:
    """Demonstrate static layer baking."""
    comp = build_showcase_comp()
    cache = StaticLayerCache(comp)
    baked = cache.bake()
    print(f"  StaticLayerCache: baked {baked} static layers out of {cache.baked_count}")


def demo_mmap_buffer() -> None:
    """Demonstrate memory-mapped frame buffer for 4K frames."""
    buf = MappedFrameBuffer(3840, 2160)
    frame = np.random.default_rng(42).integers(0, 256, (2160, 3840, 4), dtype=np.uint8)
    buf.write_frame(frame)

    # Read just a 540p region — no need to load full 32 MB frame
    region = buf.read_region(0, 540, 0, 960)
    mb = buf.size_bytes / 1024 / 1024
    print(f"  MappedFrameBuffer: {mb:.1f} MB buffer, region={region.shape}")
    buf.close()


def demo_simd_blend() -> None:
    """Demonstrate SIMD-optimized alpha blend."""
    dst = np.zeros((1080, 1920, 4), dtype=np.uint8)
    src = np.full((1080, 1920, 4), 180, dtype=np.uint8)
    src[:, :, 3] = 200

    result = try_simd_blend(dst, src, opacity=0.7)
    print(f"  SIMD blend: output mean={result[:, :, :3].mean():.1f}")


def demo_parallel_audio() -> None:
    """Demonstrate parallel audio mixing."""
    seg1 = np.ones(44100, dtype=np.float32) * 0.3
    seg2 = np.ones(44100, dtype=np.float32) * 0.2

    mixed = render_audio_parallel(
        [(seg1, 0, 44100), (seg2, 22050, 66150)],
        output_length=88200,
        num_threads=4,
    )
    print(f"  Parallel audio: mixed {len(mixed)} samples, peak={mixed.max():.2f}")


# ─────────────────────────────────────────────────────────────────────
# 7. Profiling & diagnostics
# ─────────────────────────────────────────────────────────────────────


def demo_benchmark() -> None:
    """Benchmark composition render throughput."""
    comp = build_showcase_comp()
    result = benchmark(comp, n_frames=30)
    print(f"  Benchmark: {result.fps_achieved} fps ({result.avg_frame_ms:.1f} ms/frame)")


def demo_bottleneck_detection() -> None:
    """Detect slowest clips in the composition."""
    comp = build_showcase_comp()
    bottlenecks = detect_bottlenecks(comp, n_frames=10, top_n=3)
    for b in bottlenecks:
        print(f"  Bottleneck: {b.description} — {b.time_ms:.1f} ms ({b.percentage:.1f}%)")


def demo_memory_report() -> None:
    """Measure memory usage during rendering."""
    comp = build_showcase_comp()
    report = memory_report(comp, n_frames=5)
    print(f"  Memory: peak={report.peak_ram_mb:.1f} MB, stages={list(report.per_stage.keys())}")


def demo_frame_diff() -> None:
    """Compare two frames pixel-by-pixel."""
    rng = np.random.default_rng(42)
    frame_a = rng.integers(0, 256, (64, 64, 4), dtype=np.uint8)
    frame_b = frame_a.copy()
    frame_b[10:30, 10:30, :] = 0  # Introduce a difference

    diff = frame_diff(frame_a, frame_b)
    changed = f"{diff.changed_pixels}/{diff.total_pixels}"
    psnr = f"{diff.psnr:.1f}"
    print(f"  Frame diff: identical={diff.identical}, PSNR={psnr} dB, changed={changed} px")


# ─────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    # 1. Render showcase
    demo_render_composition()

    # 2. GPU features
    print("\n=== GPU Compositing ===")
    demo_gpu_compositing()

    print("\n=== GPU Batch Effects ===")
    demo_gpu_effects()

    # 3. Hardware encoding
    print("\n=== Hardware Encoding ===")
    demo_hardware_encoding()

    # 4. Distributed rendering
    print("\n=== Distributed Rendering (Checkpoint) ===")
    demo_checkpointing()

    # 5. Render optimizations
    print("\n=== Render Optimizations ===")
    demo_incremental_renderer()
    demo_static_layer_cache()
    demo_mmap_buffer()
    demo_simd_blend()
    demo_parallel_audio()

    # 6. Profiling & diagnostics
    print("\n=== Profiling & Diagnostics ===")
    demo_benchmark()
    demo_bottleneck_detection()
    demo_memory_report()
    demo_frame_diff()

    print("\nDone! All v2.5 features demonstrated.")
