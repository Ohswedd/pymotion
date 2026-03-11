"""GPU-accelerated frame compositor using WGPU compute shaders.

Provides the same alpha compositing and blend mode operations as the
CPU compositor but executes on the GPU via WebGPU compute shaders.
Falls back to CPU compositing if ``wgpu`` is not installed or no GPU
adapter is available.

Requires the ``gpu-compute`` optional extra::

    pip install pymotion-studio[gpu-compute]
"""

from __future__ import annotations

from typing import Any

import numpy as np

from pymotion.clip.base import BlendMode
from pymotion.utils.logging import get_logger

logger = get_logger(__name__)

# Blend mode constants matching the WGSL shader
_BLEND_NORMAL = 0
_BLEND_MULTIPLY = 1
_BLEND_SCREEN = 2
_BLEND_OVERLAY = 3
_BLEND_ADD = 4
_BLEND_SOFT_LIGHT = 5
_BLEND_HARD_LIGHT = 6
_BLEND_DIFFERENCE = 7

_BLEND_MODE_MAP: dict[BlendMode, int] = {
    BlendMode.NORMAL: _BLEND_NORMAL,
    BlendMode.MULTIPLY: _BLEND_MULTIPLY,
    BlendMode.SCREEN: _BLEND_SCREEN,
    BlendMode.OVERLAY: _BLEND_OVERLAY,
    BlendMode.ADD: _BLEND_ADD,
    BlendMode.SOFT_LIGHT: _BLEND_SOFT_LIGHT,
    BlendMode.HARD_LIGHT: _BLEND_HARD_LIGHT,
    BlendMode.DIFFERENCE: _BLEND_DIFFERENCE,
}

# WGSL compute shader source — processes one pixel per invocation.
# The shader reads dst and src pixel data from storage buffers,
# performs Porter-Duff alpha compositing with the selected blend mode,
# and writes the result back to the dst buffer.
_COMPOSITE_SHADER = """
struct Params {
    width: u32,
    height: u32,
    blend_mode: u32,
    opacity_fixed: u32,
    region_x0: u32,
    region_y0: u32,
    region_w: u32,
    region_h: u32,
}

@group(0) @binding(0) var<storage, read_write> dst: array<u32>;
@group(0) @binding(1) var<storage, read> src: array<u32>;
@group(0) @binding(2) var<uniform> params: Params;

fn unpack_bgra(packed: u32) -> vec4<f32> {
    let b = f32(packed & 0xFFu);
    let g = f32((packed >> 8u) & 0xFFu);
    let r = f32((packed >> 16u) & 0xFFu);
    let a = f32((packed >> 24u) & 0xFFu);
    return vec4<f32>(b, g, r, a);
}

fn pack_bgra(v: vec4<f32>) -> u32 {
    let b = u32(clamp(v.x, 0.0, 255.0));
    let g = u32(clamp(v.y, 0.0, 255.0));
    let r = u32(clamp(v.z, 0.0, 255.0));
    let a = u32(clamp(v.w, 0.0, 255.0));
    return b | (g << 8u) | (r << 16u) | (a << 24u);
}

fn apply_blend(bg: vec3<f32>, fg: vec3<f32>, mode: u32) -> vec3<f32> {
    switch mode {
        case 1u: {  // MULTIPLY
            return (bg * fg) / 255.0;
        }
        case 2u: {  // SCREEN
            return 255.0 - ((255.0 - bg) * (255.0 - fg)) / 255.0;
        }
        case 3u: {  // OVERLAY
            let low = 2.0 * bg * fg / 255.0;
            let high = 255.0 - 2.0 * (255.0 - bg) * (255.0 - fg) / 255.0;
            return select(high, low, bg < vec3<f32>(128.0));
        }
        case 4u: {  // ADD
            return min(bg + fg, vec3<f32>(255.0));
        }
        case 5u: {  // SOFT_LIGHT
            return (255.0 - 2.0 * fg) * bg * bg / 65025.0 + 2.0 * fg * bg / 255.0;
        }
        case 6u: {  // HARD_LIGHT
            let low = 2.0 * bg * fg / 255.0;
            let high = 255.0 - 2.0 * (255.0 - bg) * (255.0 - fg) / 255.0;
            return select(high, low, fg < vec3<f32>(128.0));
        }
        case 7u: {  // DIFFERENCE
            return abs(bg - fg);
        }
        default: {  // NORMAL
            return fg;
        }
    }
}

@compute @workgroup_size(256)
fn main(@builtin(global_invocation_id) gid: vec3<u32>) {
    let idx = gid.x;
    let region_pixels = params.region_w * params.region_h;
    if idx >= region_pixels {
        return;
    }

    // Map linear index to region coordinates
    let local_y = idx / params.region_w;
    let local_x = idx % params.region_w;
    let global_y = params.region_y0 + local_y;
    let global_x = params.region_x0 + local_x;
    let pixel_idx = global_y * params.width + global_x;

    let dst_px = unpack_bgra(dst[pixel_idx]);
    let src_px = unpack_bgra(src[pixel_idx]);

    // ADD blend uses simple clamped addition (no Porter-Duff)
    if params.blend_mode == 4u {
        let opa = f32(params.opacity_fixed) / 256.0;
        let scaled = src_px * opa;
        let added = min(dst_px + scaled, vec4<f32>(255.0));
        dst[pixel_idx] = pack_bgra(added);
        return;
    }

    // Apply opacity to source alpha
    let src_a = src_px.w * f32(params.opacity_fixed) / 256.0;

    if src_a < 0.5 {
        return;  // Fully transparent source — skip
    }

    let src_alpha = src_a / 255.0;
    let dst_alpha = dst_px.w / 255.0;

    let src_rgb = src_px.xyz;
    let dst_rgb = dst_px.xyz;

    // Apply blend mode to get blended RGB
    let blended_rgb = apply_blend(dst_rgb, src_rgb, params.blend_mode);

    // Porter-Duff alpha compositing
    let out_alpha = src_alpha + dst_alpha * (1.0 - src_alpha);
    let safe_alpha = select(out_alpha, 1.0, out_alpha <= 0.0);

    let out_rgb = (blended_rgb * src_alpha + dst_rgb * dst_alpha * (1.0 - src_alpha)) / safe_alpha;

    let result = vec4<f32>(
        clamp(out_rgb.x, 0.0, 255.0),
        clamp(out_rgb.y, 0.0, 255.0),
        clamp(out_rgb.z, 0.0, 255.0),
        clamp(out_alpha * 255.0, 0.0, 255.0),
    );

    dst[pixel_idx] = pack_bgra(result);
}
"""


class GPUCompositor:
    """WGPU compute shader compositor for frame blending.

    Manages a GPU device and reusable buffers for compositing BGRA uint8
    frames. Buffers are lazily allocated and resized as needed.

    Example::

        gpu = GPUCompositor()
        if gpu.available:
            result = gpu.composite_layers(background, layers)

    """

    def __init__(self) -> None:
        self._device: Any = None
        self._pipeline: Any = None
        self._dst_buffer: Any = None
        self._src_buffer: Any = None
        self._params_buffer: Any = None
        self._readback_buffer: Any = None
        self._bind_group: Any = None
        self._buffer_size: int = 0
        self._available: bool | None = None

    @property
    def available(self) -> bool:
        """Check whether GPU compositing is available.

        Returns:
            True if wgpu is importable and a GPU adapter is found.
        """
        if self._available is not None:
            return self._available
        try:
            self._init_device()
            self._available = True
        except Exception:
            self._available = False
            logger.info("gpu_compositor_unavailable", reason="no wgpu or no adapter")
        return self._available

    def _init_device(self) -> None:
        """Initialize WGPU device and compute pipeline."""
        if self._device is not None:
            return
        try:
            import wgpu  # noqa: F811
        except ImportError as exc:
            raise ImportError(
                "wgpu is required for GPU compositing. "
                "Install with: pip install pymotion-studio[gpu-compute]"
            ) from exc

        adapter = wgpu.gpu.request_adapter_sync(power_preference="high-performance")
        if adapter is None:
            raise RuntimeError("No GPU adapter available for WGPU")

        self._device = adapter.request_device_sync(
            required_limits={
                "max-storage-buffer-binding-size": 1024 * 1024 * 1024,
            }
        )

        self._pipeline = self._device.create_compute_pipeline(
            layout="auto",
            compute={"module": self._device.create_shader_module(code=_COMPOSITE_SHADER)},
        )
        logger.info("gpu_compositor_initialized")

    def _ensure_buffers(self, frame_bytes: int) -> None:
        """Allocate or resize GPU buffers to fit the frame data.

        Args:
            frame_bytes: Total bytes needed for one frame (H * W * 4).
        """
        if self._buffer_size >= frame_bytes:
            return

        # Buffers store pixels as u32 (4 bytes each = same as BGRA uint8)
        self._dst_buffer = self._device.create_buffer(
            size=frame_bytes,
            usage="STORAGE | COPY_SRC | COPY_DST",
        )
        self._src_buffer = self._device.create_buffer(
            size=frame_bytes,
            usage="STORAGE | COPY_DST",
        )
        self._params_buffer = self._device.create_buffer(
            size=32,  # 8 x u32 = 32 bytes
            usage="UNIFORM | COPY_DST",
        )
        self._readback_buffer = self._device.create_buffer(
            size=frame_bytes,
            usage="COPY_DST | MAP_READ",
        )
        self._bind_group = self._device.create_bind_group(
            layout=self._pipeline.get_bind_group_layout(0),
            entries=[
                {"binding": 0, "resource": {"buffer": self._dst_buffer}},
                {"binding": 1, "resource": {"buffer": self._src_buffer}},
                {"binding": 2, "resource": {"buffer": self._params_buffer}},
            ],
        )
        self._buffer_size = frame_bytes
        logger.debug("gpu_buffers_allocated", size=frame_bytes)

    def composite_layers(
        self,
        background: np.ndarray[Any, Any],
        layers: list[tuple[np.ndarray[Any, Any], BlendMode, float]],
    ) -> np.ndarray[Any, Any]:
        """Composite multiple layers onto a background using GPU shaders.

        Drop-in replacement for the CPU ``composite_layers()`` function.
        Each layer is a tuple of ``(frame, blend_mode, opacity)``.

        Args:
            background: BGRA background frame, shape (H, W, 4), dtype uint8.
            layers: List of (frame, blend_mode, opacity) tuples.

        Returns:
            Composited BGRA frame, shape (H, W, 4), dtype uint8.
        """
        if not layers:
            return background

        self._init_device()

        h, w = background.shape[:2]
        frame_bytes = h * w * 4
        self._ensure_buffers(frame_bytes)

        # Find topmost fully-opaque NORMAL layer — skip everything below
        start_idx = 0
        for i in range(len(layers) - 1, -1, -1):
            lf, bm, op = layers[i]
            if bm == BlendMode.NORMAL and op >= 1.0 and lf[:, :, 3].min() == 255:
                start_idx = i
                break

        if start_idx > 0:
            result_frame = layers[start_idx][0].copy()
            active_layers = layers[start_idx + 1 :]
        else:
            result_frame = background.copy()
            active_layers = layers

        # Upload initial result (dst) to GPU
        self._device.queue.write_buffer(self._dst_buffer, 0, result_frame.tobytes())

        for layer_frame, blend_mode, opacity in active_layers:
            if opacity <= 0.0:
                continue

            alpha = layer_frame[:, :, 3]
            max_a = int(alpha.max())
            if max_a == 0:
                continue

            # Determine region
            y0, y1, x0, x1 = 0, h, 0, w
            if max_a < 255 or int(alpha.min()) < 255:
                rows = np.any(alpha > 0, axis=1)
                if not np.any(rows):
                    continue
                cols = np.any(alpha > 0, axis=0)
                y0 = int(np.argmax(rows))
                y1 = int(len(rows) - np.argmax(rows[::-1]))
                x0 = int(np.argmax(cols))
                x1 = int(len(cols) - np.argmax(cols[::-1]))

            region_w = x1 - x0
            region_h = y1 - y0
            if region_w <= 0 or region_h <= 0:
                continue

            # Upload source layer
            self._device.queue.write_buffer(self._src_buffer, 0, layer_frame.tobytes())

            # Write params
            opacity_fixed = int(opacity * 256)
            blend_id = _BLEND_MODE_MAP.get(blend_mode, _BLEND_NORMAL)
            params = np.array(
                [w, h, blend_id, opacity_fixed, x0, y0, region_w, region_h],
                dtype=np.uint32,
            )
            self._device.queue.write_buffer(self._params_buffer, 0, params.tobytes())

            # Dispatch compute shader
            total_pixels = region_w * region_h
            workgroups = (total_pixels + 255) // 256

            encoder = self._device.create_command_encoder()
            compute_pass = encoder.begin_compute_pass()
            compute_pass.set_pipeline(self._pipeline)
            compute_pass.set_bind_group(0, self._bind_group)
            compute_pass.dispatch_workgroups(workgroups)
            compute_pass.end()
            self._device.queue.submit([encoder.finish()])

        # Read back result
        encoder = self._device.create_command_encoder()
        encoder.copy_buffer_to_buffer(self._dst_buffer, 0, self._readback_buffer, 0, frame_bytes)
        self._device.queue.submit([encoder.finish()])

        self._readback_buffer.map_sync("READ")
        data = self._readback_buffer.read_mapped()
        self._readback_buffer.unmap()

        result = np.frombuffer(bytes(data), dtype=np.uint8).reshape(h, w, 4).copy()
        return result

    def release(self) -> None:
        """Release GPU resources.

        Call this when the compositor is no longer needed.
        """
        self._dst_buffer = None
        self._src_buffer = None
        self._params_buffer = None
        self._readback_buffer = None
        self._bind_group = None
        self._buffer_size = 0
        self._device = None
        self._pipeline = None
        self._available = None
        logger.info("gpu_compositor_released")


# Module-level singleton — lazily initialized
_gpu_compositor: GPUCompositor | None = None


def get_gpu_compositor() -> GPUCompositor:
    """Get or create the module-level GPU compositor singleton.

    Returns:
        The shared GPUCompositor instance.
    """
    global _gpu_compositor  # noqa: PLW0603
    if _gpu_compositor is None:
        _gpu_compositor = GPUCompositor()
    return _gpu_compositor


def gpu_composite_layers(
    background: np.ndarray[Any, Any],
    layers: list[tuple[np.ndarray[Any, Any], BlendMode, float]],
) -> np.ndarray[Any, Any]:
    """Composite layers using the GPU, falling back to CPU on failure.

    This is the primary entry point for GPU-accelerated compositing.
    If GPU compositing fails for any reason, it transparently falls
    back to the CPU path.

    Args:
        background: BGRA background frame, shape (H, W, 4), dtype uint8.
        layers: List of (frame, blend_mode, opacity) tuples.

    Returns:
        Composited BGRA frame, shape (H, W, 4), dtype uint8.
    """
    from pymotion.render.compositor import composite_layers as cpu_composite

    gpu = get_gpu_compositor()
    if not gpu.available:
        return cpu_composite(background, layers)

    try:
        return gpu.composite_layers(background, layers)
    except Exception:
        logger.warning("gpu_composite_fallback", reason="gpu compositing failed, using CPU")
        return cpu_composite(background, layers)
