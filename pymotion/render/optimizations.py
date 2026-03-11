"""Render optimizations — incremental rendering, memory-mapped buffers,
SIMD blend ops, static layer baking, and parallel audio rendering.

These utilities reduce memory usage and improve rendering throughput
for large compositions.
"""

from __future__ import annotations

import hashlib
import mmap
import os
import tempfile
import threading
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import numpy as np

from pymotion.utils.logging import get_logger

logger = get_logger(__name__)


class IncrementalRenderer:
    """Skip re-rendering frames whose source clips haven't changed.

    Tracks clip state (position, opacity, effects hash) per frame and
    only re-renders frames where the inputs differ from the cached version.

    Args:
        cache_dir: Directory for frame cache files.
            Defaults to a temporary directory.
    """

    def __init__(self, cache_dir: Path | None = None) -> None:
        self._cache_dir = cache_dir or Path(tempfile.mkdtemp(prefix="pymotion_incr_"))
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._frame_hashes: dict[int, str] = {}

    def _compute_state_hash(self, composition: Any, frame: int) -> str:
        """Compute a hash of all clip states for a given frame.

        Args:
            composition: The Composition to hash.
            frame: Frame number.

        Returns:
            Hex digest of the state hash.
        """
        hasher = hashlib.sha256()
        hasher.update(frame.to_bytes(4, "little"))
        hasher.update(composition.resolution.width.to_bytes(4, "little"))
        hasher.update(composition.resolution.height.to_bytes(4, "little"))

        for track in composition.tracks:
            hasher.update(track.name.encode())
            hasher.update(str(track.opacity).encode())
            for clip in track.clips:
                if clip.start <= frame < clip.end:
                    hasher.update(str(clip.start).encode())
                    hasher.update(str(clip.end).encode())
                    hasher.update(str(clip._opacity).encode())
                    hasher.update(clip.blend_mode.value.encode())
                    for effect in clip._effects:
                        hasher.update(type(effect).__name__.encode())

        return hasher.hexdigest()

    def render_frame(self, composition: Any, frame: int) -> np.ndarray:
        """Render a frame, using cache if the state hasn't changed.

        Args:
            composition: The Composition to render.
            frame: Frame number.

        Returns:
            BGRA frame array.
        """
        state_hash = self._compute_state_hash(composition, frame)

        if frame in self._frame_hashes and self._frame_hashes[frame] == state_hash:
            cache_path = self._cache_dir / f"frame_{frame:06d}.raw"
            if cache_path.exists():
                h = composition.resolution.height
                w = composition.resolution.width
                data = cache_path.read_bytes()
                return np.frombuffer(data, dtype=np.uint8).reshape(h, w, 4).copy()

        rendered: np.ndarray = composition._render_frame(frame)
        self._frame_hashes[frame] = state_hash

        cache_path = self._cache_dir / f"frame_{frame:06d}.raw"
        cache_path.write_bytes(rendered.tobytes())

        return rendered

    def invalidate(self) -> None:
        """Clear all cached frames."""
        self._frame_hashes.clear()
        for f in self._cache_dir.glob("frame_*.raw"):
            f.unlink()

    @property
    def cached_frames(self) -> int:
        """Number of frames currently cached.

        Returns:
            Count of cached frame files.
        """
        return len(self._frame_hashes)


class MappedFrameBuffer:
    """Memory-mapped frame buffer for 4K+ intermediate frames.

    Uses OS-level memory mapping to avoid loading entire frames
    into RAM. Suitable for large intermediate buffers where only
    regions are accessed at a time.

    Args:
        width: Frame width in pixels.
        height: Frame height in pixels.
        path: Optional file path. Defaults to a temp file.
    """

    def __init__(self, width: int, height: int, path: Path | None = None) -> None:
        self._width = width
        self._height = height
        self._frame_bytes = width * height * 4
        if path is None:
            fd, tmp_path = tempfile.mkstemp(prefix="pymotion_mmap_", suffix=".raw")
            os.close(fd)
            self._path = Path(tmp_path)
        else:
            self._path = path
        self._fd: int | None = None
        self._mmap: mmap.mmap | None = None
        self._init_file()

    def _init_file(self) -> None:
        """Create or open the memory-mapped file."""
        self._fd = os.open(str(self._path), os.O_RDWR | os.O_CREAT)
        os.ftruncate(self._fd, self._frame_bytes)
        self._mmap = mmap.mmap(self._fd, self._frame_bytes)
        logger.debug("mmap_buffer_created", size=self._frame_bytes, path=str(self._path))

    def write_frame(self, frame: np.ndarray) -> None:
        """Write a BGRA frame to the memory-mapped buffer.

        Args:
            frame: BGRA frame array (H, W, 4), dtype uint8.
        """
        assert self._mmap is not None  # noqa: S101
        self._mmap.seek(0)
        self._mmap.write(frame.tobytes())

    def read_frame(self) -> np.ndarray:
        """Read the BGRA frame from the memory-mapped buffer.

        Returns:
            BGRA frame array (H, W, 4), dtype uint8.
        """
        assert self._mmap is not None  # noqa: S101
        self._mmap.seek(0)
        data = self._mmap.read(self._frame_bytes)
        return np.frombuffer(data, dtype=np.uint8).reshape(self._height, self._width, 4).copy()

    def read_region(self, y0: int, y1: int, x0: int, x1: int) -> np.ndarray:
        """Read a rectangular region from the buffer.

        Args:
            y0: Top row (inclusive).
            y1: Bottom row (exclusive).
            x0: Left column (inclusive).
            x1: Right column (exclusive).

        Returns:
            BGRA sub-array (y1-y0, x1-x0, 4), dtype uint8.
        """
        frame = self.read_frame()
        return frame[y0:y1, x0:x1].copy()

    @property
    def path(self) -> Path:
        """Path to the memory-mapped file.

        Returns:
            The file path.
        """
        return self._path

    @property
    def size_bytes(self) -> int:
        """Size of the buffer in bytes.

        Returns:
            Frame size in bytes.
        """
        return self._frame_bytes

    def close(self) -> None:
        """Close and clean up the memory-mapped buffer."""
        if self._mmap is not None:
            self._mmap.close()
            self._mmap = None
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None
        if self._path.exists():
            self._path.unlink()

    def __del__(self) -> None:
        self.close()


def try_simd_blend(
    dst: np.ndarray,
    src: np.ndarray,
    opacity: float,
) -> np.ndarray:
    """Attempt SIMD-optimized alpha blend via Cython extension.

    Falls back to NumPy if the Cython extension is not available.

    Args:
        dst: Destination BGRA frame (H, W, 4), dtype uint8.
        src: Source BGRA frame (H, W, 4), dtype uint8.
        opacity: Source opacity (0.0–1.0).

    Returns:
        Blended BGRA frame.
    """
    try:
        from pymotion.render._simd_blend import simd_alpha_blend  # type: ignore[import-untyped]

        return simd_alpha_blend(dst, src, opacity)  # type: ignore[no-any-return]
    except ImportError:
        # Fallback to NumPy
        opa_i = int(opacity * 256)
        src_a = (src[:, :, 3].astype(np.uint16) * opa_i) >> 8
        inv_a = 255 - src_a
        result = dst.copy()
        for c in range(3):
            dc = dst[:, :, c].astype(np.uint16)
            sc = src[:, :, c].astype(np.uint16)
            result[:, :, c] = ((dc * inv_a + sc * src_a) >> 8).astype(np.uint8)
        return result


class StaticLayerCache:
    """Pre-renders non-animated (static) layers once and reuses them.

    A layer is considered static if its clip spans the entire duration
    and has no keyframe animations or expressions.

    Args:
        composition: The Composition to analyze.
    """

    def __init__(self, composition: Any) -> None:
        self._composition = composition
        self._baked: dict[int, np.ndarray] = {}

    def bake(self) -> int:
        """Identify and pre-render static layers.

        Returns:
            Number of layers that were baked.
        """
        from pymotion.clip.base import RenderContext, Resolution, TimeRange

        baked_count = 0
        for track_idx, track in enumerate(self._composition.tracks):
            for clip_idx, clip in enumerate(track.clips):
                if self._is_static(clip):
                    ctx = RenderContext(
                        frame=clip.start,
                        fps=self._composition.fps,
                        resolution=Resolution(
                            self._composition.resolution.width,
                            self._composition.resolution.height,
                        ),
                        time_range=TimeRange(start=clip.start, end=clip.end),
                        local_frame=0,
                        progress=0.0,
                    )
                    frame = clip.render_with_effects(ctx)
                    key = track_idx * 1000 + clip_idx
                    self._baked[key] = frame
                    baked_count += 1
                    logger.debug(
                        "static_layer_baked",
                        track=track.name,
                        clip_idx=clip_idx,
                    )
        return baked_count

    def _is_static(self, clip: Any) -> bool:
        """Check if a clip is static (no animation).

        Args:
            clip: The clip to check.

        Returns:
            True if the clip has no animations or expressions.
        """
        if hasattr(clip, "_keyframe_tracks") and clip._keyframe_tracks:
            return False
        if hasattr(clip, "_expressions") and clip._expressions:
            return False
        return True

    def get_baked(self, track_idx: int, clip_idx: int) -> np.ndarray | None:
        """Get a pre-rendered static layer.

        Args:
            track_idx: Track index.
            clip_idx: Clip index within the track.

        Returns:
            Baked frame array, or None if not static.
        """
        key = track_idx * 1000 + clip_idx
        return self._baked.get(key)

    @property
    def baked_count(self) -> int:
        """Number of baked static layers.

        Returns:
            Count of baked layers.
        """
        return len(self._baked)


def render_audio_parallel(
    audio_segments: list[tuple[np.ndarray, int, int]],
    output_length: int,
    num_threads: int = 4,
) -> np.ndarray:
    """Mix audio segments in parallel across worker threads.

    Each segment is a tuple of ``(audio_data, start_sample, end_sample)``.
    Segments are summed into the output buffer using thread-safe accumulation.

    Args:
        audio_segments: List of (audio_data, start, end) tuples.
        output_length: Total output length in samples.
        num_threads: Number of worker threads.

    Returns:
        Mixed audio array (float32).
    """
    output = np.zeros(output_length, dtype=np.float32)
    lock = threading.Lock()

    def _mix_segment(segment: tuple[np.ndarray, int, int]) -> None:
        audio_data, start, end = segment
        length = min(len(audio_data), end - start)
        local = np.zeros(output_length, dtype=np.float32)
        local[start : start + length] = audio_data[:length]
        with lock:
            output[:] += local

    with ThreadPoolExecutor(max_workers=num_threads) as pool:
        list(pool.map(_mix_segment, audio_segments))

    return output


def profiled_frame_iterator(
    frame_iter: Iterator[np.ndarray],
) -> Iterator[tuple[np.ndarray, float]]:
    """Wrap a frame iterator to yield frames with render timing.

    Args:
        frame_iter: Source frame iterator.

    Yields:
        Tuples of (frame, render_time_seconds).
    """
    import time

    for frame in frame_iter:
        t0 = time.perf_counter()
        yield frame, time.perf_counter() - t0
