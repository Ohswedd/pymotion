"""GPU-accelerated batch effect processing via WGPU compute shaders.

Applies multiple color-grading effects in a single GPU pass to avoid
repeated CPU ↔ GPU transfers. Effects that cannot be expressed as GPU
operations fall back to their CPU :meth:`apply` method.

Supported GPU-accelerated effects:

- :class:`~pymotion.effects.color.Brightness`
- :class:`~pymotion.effects.color.Contrast`
- :class:`~pymotion.effects.color.Saturation`
- :class:`~pymotion.effects.color.HueSaturationLuminance`

Requires the ``gpu-compute`` optional extra::

    pip install pymotion-studio[gpu-compute]
"""

from __future__ import annotations

from typing import Any

import numpy as np

from pymotion.clip.base import RenderContext
from pymotion.effects.base import Effect
from pymotion.effects.color import Brightness, Contrast, HueSaturationLuminance, Saturation
from pymotion.utils.logging import get_logger

logger = get_logger(__name__)

# Effect type IDs used in the shader's operation array.
_OP_BRIGHTNESS = 0
_OP_CONTRAST = 1
_OP_SATURATION = 2
_OP_HSL = 3

# Which Effect classes can be batched on the GPU.
_GPU_EFFECT_TYPES: tuple[type[Effect], ...] = (
    Brightness,
    Contrast,
    Saturation,
    HueSaturationLuminance,
)

# Maximum number of effects in a single batch pass.
_MAX_OPS = 16

# WGSL compute shader for batched effect processing.
# Each operation is encoded as (type, param0, param1, param2) in a fixed array.
# The shader iterates operations in order, applying them to each pixel.
_BATCH_EFFECT_SHADER = """
struct Params {
    width: u32,
    height: u32,
    num_ops: u32,
    _pad: u32,
}

struct Op {
    op_type: u32,
    _pad0: u32,
    _pad1: u32,
    _pad2: u32,
    param0: f32,
    param1: f32,
    param2: f32,
    _pad3: f32,
}

@group(0) @binding(0) var<storage, read_write> pixels: array<u32>;
@group(0) @binding(1) var<uniform> params: Params;
@group(0) @binding(2) var<storage, read> ops: array<Op>;

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

@compute @workgroup_size(256)
fn main(@builtin(global_invocation_id) gid: vec3<u32>) {
    let idx = gid.x;
    let total = params.width * params.height;
    if idx >= total {
        return;
    }

    var px = unpack_bgra(pixels[idx]);

    for (var i = 0u; i < params.num_ops; i = i + 1u) {
        let op = ops[i];

        switch op.op_type {
            case 0u: {
                // BRIGHTNESS: multiply RGB by param0
                px = vec4<f32>(
                    clamp(px.x * op.param0, 0.0, 255.0),
                    clamp(px.y * op.param0, 0.0, 255.0),
                    clamp(px.z * op.param0, 0.0, 255.0),
                    px.w,
                );
            }
            case 1u: {
                // CONTRAST: (rgb - 128) * param0 + 128
                px = vec4<f32>(
                    clamp((px.x - 128.0) * op.param0 + 128.0, 0.0, 255.0),
                    clamp((px.y - 128.0) * op.param0 + 128.0, 0.0, 255.0),
                    clamp((px.z - 128.0) * op.param0 + 128.0, 0.0, 255.0),
                    px.w,
                );
            }
            case 2u: {
                // SATURATION: lerp toward luminance by param0
                // Luminance weights: B=0.114, G=0.587, R=0.299
                let lum = 0.114 * px.x + 0.587 * px.y + 0.299 * px.z;
                px = vec4<f32>(
                    clamp(lum + (px.x - lum) * op.param0, 0.0, 255.0),
                    clamp(lum + (px.y - lum) * op.param0, 0.0, 255.0),
                    clamp(lum + (px.z - lum) * op.param0, 0.0, 255.0),
                    px.w,
                );
            }
            case 3u: {
                // HSL: param0=hue_shift(deg), param1=sat_mult, param2=lum_mult
                // Approximate: apply saturation, then luminance
                let lum = 0.114 * px.x + 0.587 * px.y + 0.299 * px.z;
                // Saturation
                var rgb = vec3<f32>(
                    lum + (px.x - lum) * op.param1,
                    lum + (px.y - lum) * op.param1,
                    lum + (px.z - lum) * op.param1,
                );
                // Luminance
                rgb = rgb * op.param2;
                // Hue rotation in RGB (Rodrigues' rotation around (1,1,1)/sqrt(3))
                let angle = op.param0 * 3.14159265 / 180.0;
                let cos_a = cos(angle);
                let sin_a = sin(angle);
                let k = 0.57735026;  // 1/sqrt(3)
                let dot_kv = k * (rgb.x + rgb.y + rgb.z);
                let rotated = vec3<f32>(
                    rgb.x * cos_a + (k * rgb.z - k * rgb.y) * sin_a + k * dot_kv * (1.0 - cos_a),
                    rgb.y * cos_a + (k * rgb.x - k * rgb.z) * sin_a + k * dot_kv * (1.0 - cos_a),
                    rgb.z * cos_a + (k * rgb.y - k * rgb.x) * sin_a + k * dot_kv * (1.0 - cos_a),
                );
                px = vec4<f32>(
                    clamp(rotated.x, 0.0, 255.0),
                    clamp(rotated.y, 0.0, 255.0),
                    clamp(rotated.z, 0.0, 255.0),
                    px.w,
                );
            }
            default: {}
        }
    }

    pixels[idx] = pack_bgra(px);
}
"""


def is_gpu_effect(effect: Effect) -> bool:
    """Check whether an effect can be processed on the GPU.

    Args:
        effect: An effect instance.

    Returns:
        True if the effect type is supported by the GPU batch pipeline.
    """
    return isinstance(effect, _GPU_EFFECT_TYPES)


def _effect_to_op(effect: Effect) -> tuple[int, float, float, float]:
    """Convert an effect instance to shader operation params.

    Args:
        effect: A GPU-compatible effect.

    Returns:
        Tuple of (op_type, param0, param1, param2).

    Raises:
        TypeError: If the effect is not GPU-compatible.
    """
    if isinstance(effect, Brightness):
        return (_OP_BRIGHTNESS, effect.value, 0.0, 0.0)
    if isinstance(effect, Contrast):
        return (_OP_CONTRAST, effect.value, 0.0, 0.0)
    if isinstance(effect, Saturation):
        return (_OP_SATURATION, effect.value, 0.0, 0.0)
    if isinstance(effect, HueSaturationLuminance):
        return (
            _OP_HSL,
            float(effect.hue),
            float(effect.saturation),
            float(effect.luminance),
        )
    msg = f"Effect {type(effect).__name__} is not GPU-compatible"
    raise TypeError(msg)


class GPUEffectPipeline:
    """Applies a batch of effects in a single GPU compute pass.

    Minimizes CPU ↔ GPU transfers by uploading the frame once,
    running all compatible effects on the GPU, and downloading
    the result once.

    Example::

        pipeline = GPUEffectPipeline()
        if pipeline.available:
            frame = pipeline.apply_batch(frame, effects, ctx)
    """

    def __init__(self) -> None:
        self._device: Any = None
        self._pipeline: Any = None
        self._available: bool | None = None

    @property
    def available(self) -> bool:
        """Check whether GPU effect processing is available.

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
        return self._available

    def _init_device(self) -> None:
        """Initialize WGPU device and the batch effect pipeline."""
        if self._device is not None:
            return
        try:
            import wgpu
        except ImportError as exc:
            raise ImportError(
                "wgpu is required for GPU effects. "
                "Install with: pip install pymotion-studio[gpu-compute]"
            ) from exc

        adapter = wgpu.gpu.request_adapter_sync(power_preference="high-performance")
        if adapter is None:
            raise RuntimeError("No GPU adapter available")

        self._device = adapter.request_device_sync(
            required_limits={"max-storage-buffer-binding-size": 1024 * 1024 * 1024}
        )
        self._pipeline = self._device.create_compute_pipeline(
            layout="auto",
            compute={"module": self._device.create_shader_module(code=_BATCH_EFFECT_SHADER)},
        )
        logger.info("gpu_effect_pipeline_initialized")

    def apply_batch(
        self,
        frame: np.ndarray[Any, Any],
        effects: list[Effect],
        ctx: RenderContext,
    ) -> np.ndarray[Any, Any]:
        """Apply a list of effects to a frame using the GPU.

        Effects that are GPU-compatible are batched into a single compute
        dispatch. Non-GPU effects are applied on the CPU in their original
        order. Consecutive GPU effects are merged into one GPU pass.

        Args:
            frame: BGRA frame, shape (H, W, 4), dtype uint8.
            effects: Ordered list of effects to apply.
            ctx: Render context for this frame.

        Returns:
            BGRA frame with all effects applied.
        """
        if not effects:
            return frame

        self._init_device()

        result = frame
        gpu_batch: list[Effect] = []

        for effect in effects:
            if is_gpu_effect(effect) and len(gpu_batch) < _MAX_OPS:
                gpu_batch.append(effect)
            else:
                # Flush pending GPU batch before CPU effect
                if gpu_batch:
                    result = self._dispatch_batch(result, gpu_batch)
                    gpu_batch = []
                # Apply non-GPU effect on CPU
                result = effect.apply(result, ctx)

        # Flush remaining GPU batch
        if gpu_batch:
            result = self._dispatch_batch(result, gpu_batch)

        return result

    def _dispatch_batch(
        self,
        frame: np.ndarray[Any, Any],
        effects: list[Effect],
    ) -> np.ndarray[Any, Any]:
        """Run a batch of GPU effects in a single compute pass.

        Args:
            frame: BGRA frame (H, W, 4), dtype uint8.
            effects: List of GPU-compatible effects.

        Returns:
            BGRA frame with effects applied.
        """
        h, w = frame.shape[:2]
        frame_bytes = h * w * 4

        # Pixel buffer (read-write storage)
        pixel_buf = self._device.create_buffer(
            size=frame_bytes,
            usage="STORAGE | COPY_SRC | COPY_DST",
        )
        self._device.queue.write_buffer(pixel_buf, 0, frame.tobytes())

        # Params buffer: width, height, num_ops, padding
        params = np.array([w, h, len(effects), 0], dtype=np.uint32)
        params_buf = self._device.create_buffer(
            size=16,
            usage="UNIFORM | COPY_DST",
        )
        self._device.queue.write_buffer(params_buf, 0, params.tobytes())

        # Ops buffer: array of (type, pad, pad, pad, param0, param1, param2, pad)
        # Each Op struct is 32 bytes (8 x f32/u32)
        ops_data = np.zeros((_MAX_OPS, 8), dtype=np.float32)
        for i, effect in enumerate(effects):
            op_type, p0, p1, p2 = _effect_to_op(effect)
            # op_type goes in first 4 bytes as uint32
            ops_data[i, 0] = np.float32(np.array(op_type, dtype=np.uint32).view(np.float32))
            ops_data[i, 4] = p0
            ops_data[i, 5] = p1
            ops_data[i, 6] = p2

        ops_buf = self._device.create_buffer(
            size=ops_data.nbytes,
            usage="STORAGE | COPY_DST",
        )
        self._device.queue.write_buffer(ops_buf, 0, ops_data.tobytes())

        # Create bind group
        bind_group = self._device.create_bind_group(
            layout=self._pipeline.get_bind_group_layout(0),
            entries=[
                {"binding": 0, "resource": {"buffer": pixel_buf}},
                {"binding": 1, "resource": {"buffer": params_buf}},
                {"binding": 2, "resource": {"buffer": ops_buf}},
            ],
        )

        # Dispatch
        total_pixels = h * w
        workgroups = (total_pixels + 255) // 256

        encoder = self._device.create_command_encoder()
        compute_pass = encoder.begin_compute_pass()
        compute_pass.set_pipeline(self._pipeline)
        compute_pass.set_bind_group(0, bind_group)
        compute_pass.dispatch_workgroups(workgroups)
        compute_pass.end()
        self._device.queue.submit([encoder.finish()])

        # Read back
        readback = self._device.create_buffer(
            size=frame_bytes,
            usage="COPY_DST | MAP_READ",
        )
        encoder = self._device.create_command_encoder()
        encoder.copy_buffer_to_buffer(pixel_buf, 0, readback, 0, frame_bytes)
        self._device.queue.submit([encoder.finish()])

        readback.map_sync("READ")
        data = readback.read_mapped()
        readback.unmap()

        return np.frombuffer(bytes(data)[:frame_bytes], dtype=np.uint8).reshape(h, w, 4).copy()

    def release(self) -> None:
        """Release GPU resources."""
        self._device = None
        self._pipeline = None
        self._available = None


# Module-level singleton
_gpu_effect_pipeline: GPUEffectPipeline | None = None


def get_gpu_effect_pipeline() -> GPUEffectPipeline:
    """Get or create the module-level GPU effect pipeline singleton.

    Returns:
        The shared GPUEffectPipeline instance.
    """
    global _gpu_effect_pipeline  # noqa: PLW0603
    if _gpu_effect_pipeline is None:
        _gpu_effect_pipeline = GPUEffectPipeline()
    return _gpu_effect_pipeline
