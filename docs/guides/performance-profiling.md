# Performance & Profiling

PyMotion v2.5 includes tools for measuring render performance, tracking
memory usage, detecting bottlenecks, and optimizing compositions with
caching strategies.

## Profiling a composition

Get detailed per-frame and per-clip timing:

```python
from pymotion import profile_composition

comp = build_my_composition()

profile = profile_composition(comp, start=0, end=100, detailed=True)

print(f"Total: {profile.total_ms:.1f} ms")
print(f"Avg frame: {profile.avg_frame_ms:.1f} ms")
print(f"Min/Max: {profile.min_frame_ms:.1f} / {profile.max_frame_ms:.1f} ms")
print(f"Throughput: {profile.fps_achieved:.1f} fps")
```

With `detailed=True`, each frame includes per-clip timing:

```python
for fp in profile.frame_profiles[:3]:
    print(f"Frame {fp.frame}: {fp.total_ms:.1f} ms, composite: {fp.composite_ms:.1f} ms")
    for ct in fp.clip_timings:
        print(f"  {ct.clip_type} on '{ct.track_name}': {ct.render_ms:.1f} ms ({ct.effects_count} effects)")
```

## Benchmarking

Quick throughput measurement:

```python
from pymotion import benchmark

result = benchmark(comp, n_frames=100)
print(f"{result.fps_achieved} fps ({result.avg_frame_ms:.1f} ms/frame)")
```

`benchmark()` caps at the composition duration if `n_frames` exceeds it.

## Memory report

Track peak RAM usage during rendering:

```python
from pymotion import memory_report

report = memory_report(comp, n_frames=10)
print(f"Peak RAM: {report.peak_ram_mb:.1f} MB")
print(f"Per-stage breakdown: {report.per_stage}")
```

The report uses Python's `tracemalloc` to measure allocation peaks at
each render stage (baseline, render).

## Bottleneck detection

Automatically find the slowest clips and effects:

```python
from pymotion import detect_bottlenecks

bottlenecks = detect_bottlenecks(comp, n_frames=30, top_n=5)
for b in bottlenecks:
    print(f"  [{b.category}] {b.description}: {b.time_ms:.1f} ms ({b.percentage:.1f}%)")
```

Output example:

```
  [clip] VideoClip on 'footage' (index 0, 3 effects): 45.2 ms (62.3%)
  [clip] TextClip on 'titles' (index 1, 1 effects): 18.7 ms (25.8%)
  [clip] ColorClip on 'bg' (index 0, 0 effects): 8.6 ms (11.9%)
```

## Frame comparison

Compare two frames pixel-by-pixel:

```python
from pymotion import frame_diff

diff = frame_diff(frame_a, frame_b)
print(f"Identical: {diff.identical}")
print(f"Max diff: {diff.max_diff}")
print(f"PSNR: {diff.psnr} dB")
print(f"Changed pixels: {diff.changed_pixels} / {diff.total_pixels}")

# The diff image can be saved for visual inspection
diff_image = diff.diff_image  # (H, W, 4) uint8
```

Useful for regression testing, comparing GPU vs CPU output, or
validating render optimizations.

## Render optimizations

### Incremental rendering

Skip re-rendering frames whose source clips haven't changed:

```python
from pymotion import IncrementalRenderer

renderer = IncrementalRenderer(cache_dir=Path("./frame_cache"))

# First render — all frames computed
frame = renderer.render_frame(comp, 0)

# Second render — same state, served from cache
frame = renderer.render_frame(comp, 0)

print(f"Cached: {renderer.cached_frames} frames")
renderer.invalidate()  # Clear when composition changes
```

### Static layer baking

Pre-render layers that don't animate:

```python
from pymotion import StaticLayerCache

cache = StaticLayerCache(comp)
baked = cache.bake()
print(f"Baked {baked} static layers")

# Retrieve pre-rendered layer
layer = cache.get_baked(track_idx=0, clip_idx=0)
```

A layer is considered static if it has no keyframe tracks and no
expressions. Baked layers skip the full render pipeline on every frame.

### Memory-mapped frame buffers

For 4K+ workflows, use memory-mapped buffers to avoid loading entire
frames into RAM:

```python
from pymotion import MappedFrameBuffer

buf = MappedFrameBuffer(3840, 2160)
buf.write_frame(frame)

# Read just a region without loading the full 32 MB frame
region = buf.read_region(y0=0, y1=540, x0=0, x1=960)

buf.close()
```

### SIMD blend

For alpha blending hot paths, `try_simd_blend` attempts a Cython SIMD
path and falls back to NumPy:

```python
from pymotion import try_simd_blend

result = try_simd_blend(dst, src, opacity=0.8)
```

### Parallel audio

Mix audio segments across multiple threads:

```python
from pymotion import render_audio_parallel

segments = [
    (audio_data_1, start_sample_1, end_sample_1),
    (audio_data_2, start_sample_2, end_sample_2),
]
mixed = render_audio_parallel(segments, output_length=44100, num_threads=4)
```

## Profiled rendering

Enable per-frame timing during a full render:

```python
comp.render("output.mp4", preset="h264_1080p", profile=True)
```

This logs per-frame timing to structlog at DEBUG level.
