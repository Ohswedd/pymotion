# GPU Acceleration

PyMotion v2.5 adds GPU-accelerated compositing and effect processing
via WebGPU (wgpu-py). GPU mode is optional — the framework transparently
falls back to CPU when no GPU is available.

## Setup

Install the GPU extra:

```bash
pip install "pymotion-studio[gpu-compute]"
```

This pulls in `wgpu`, which discovers your system's Vulkan, Metal, or
DirectX 12 backend automatically.

## Enabling GPU compositing

Toggle GPU compositing globally via config:

```python
from pymotion import set_config

set_config(gpu_compositing=True)
```

When enabled, `Composition._render_frame()` routes layer blending through
a WGSL compute shader instead of the NumPy compositor. All 8 blend modes
are supported: Normal, Multiply, Screen, Overlay, Darken, Lighten,
Color Dodge, and Add.

## GPUCompositor

For direct access to the GPU pipeline:

```python
from pymotion import GPUCompositor, get_gpu_compositor
import numpy as np

# Singleton — reuses device and pipeline across calls
gpu = get_gpu_compositor()

background = np.zeros((1080, 1920, 4), dtype=np.uint8)
layers = [
    (layer_frame, "normal", 0.8),   # (frame, blend_mode, opacity)
    (overlay_frame, "screen", 1.0),
]

result = gpu.composite_layers(background, layers)
```

If the GPU is unavailable, `get_gpu_compositor()` raises `RuntimeError`.
For transparent fallback, use the convenience function:

```python
from pymotion.render.gpu_compositor import gpu_composite_layers

# Falls back to CPU if GPU init fails
result = gpu_composite_layers(background, layers)
```

## GPU buffer pool

The compositor manages a VRAM-budgeted buffer pool to avoid repeated
allocation. Buffers are bucketed by power-of-two sizes and reused:

```python
from pymotion import GPUBufferPool

# Default: 2 GB VRAM budget
pool = GPUBufferPool(device, vram_budget=2 * 1024 * 1024 * 1024)

# Acquire a buffer for a 1080p frame
buf = pool.acquire(1920 * 1080 * 4, usage="storage")
# ... use the buffer ...
pool.release(buf)
```

When the pool exceeds its VRAM budget, `acquire()` raises
`MemoryError`. The calling code can then fall back to CPU.

## GPU batch effects

The GPU effect pipeline batches compatible color effects (Brightness,
Contrast, Saturation, HSL) into a single compute pass:

```python
from pymotion import GPUEffectPipeline, is_gpu_effect, get_gpu_effect_pipeline
from pymotion import Brightness, Contrast, Saturation

effects = [Brightness(value=1.2), Contrast(value=1.1), Saturation(value=0.9)]

# Check which effects can run on GPU
gpu_ok = [e for e in effects if is_gpu_effect(e)]
print(f"{len(gpu_ok)} of {len(effects)} effects are GPU-compatible")

# Apply batch on GPU (falls back to CPU per-effect if needed)
pipeline = get_gpu_effect_pipeline()
result = pipeline.apply_batch(frame, effects, ctx)
```

Effects that are not GPU-compatible (e.g., GaussianBlur, LUT) flush the
GPU batch and run on CPU, then the next GPU-compatible effects start a
new batch.

## VRAM budget

Control the VRAM limit via config:

```python
from pymotion import set_config

# Limit to 1 GB (useful on shared GPU machines)
set_config(gpu_vram_limit_bytes=1 * 1024 * 1024 * 1024)
```

When the budget is exceeded, the compositor automatically falls back to
CPU for that frame.

## When to use GPU

GPU compositing helps most when:

- Compositions have many layers (5+) with alpha blending
- Working at 4K resolution or higher
- Applying multiple color effects per frame
- Batch rendering many frames

For simple 2-3 layer 1080p compositions, the CPU path is often faster
due to GPU setup overhead.
