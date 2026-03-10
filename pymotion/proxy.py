"""Proxy workflow — generate, manage, and clean low-resolution proxies.

Proxies are low-resolution copies of source clips stored on disk
for faster preview rendering. The proxy cache lives in
``~/.pymotion/proxies/`` by default.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from pymotion.clip.base import Clip, RenderContext, Resolution, TimeRange
from pymotion.utils.logging import get_logger

logger = get_logger(__name__)

_DEFAULT_PROXY_DIR = Path.home() / ".pymotion" / "proxies"


@dataclass
class ProxyClip(Clip):
    """A low-resolution proxy clip backed by a cached file.

    Renders frames from a pre-rendered low-resolution source. The proxy
    is stored as raw BGRA frame data on disk.

    Args:
        source: Path to the proxy file on disk.
        _width: Proxy frame width.
        _height: Proxy frame height.
        _frame_count: Number of frames in the proxy.
    """

    source: Path = field(default_factory=lambda: Path(""))
    _width: int = 0
    _height: int = 0
    _frame_count: int = 0

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render a frame from the proxy file.

        Args:
            ctx: The render context for this frame.

        Returns:
            BGRA numpy array of shape (H, W, 4), dtype uint8.
        """
        if not self.source.exists():
            return np.zeros((ctx.resolution.height, ctx.resolution.width, 4), dtype=np.uint8)

        frame_size = self._width * self._height * 4
        frame_idx = min(ctx.local_frame, self._frame_count - 1)
        offset = frame_idx * frame_size

        try:
            with open(self.source, "rb") as f:
                f.seek(offset)
                data = f.read(frame_size)
            if len(data) == frame_size:
                frame = np.frombuffer(data, dtype=np.uint8).reshape(self._height, self._width, 4)
                # Scale up to requested resolution if different
                if self._width != ctx.resolution.width or self._height != ctx.resolution.height:
                    return _resize_nearest(frame, ctx.resolution.width, ctx.resolution.height)
                return frame.copy()
        except OSError:
            logger.warning("proxy_read_failed", source=str(self.source))

        return np.zeros((ctx.resolution.height, ctx.resolution.width, 4), dtype=np.uint8)


def _resize_nearest(frame: np.ndarray, target_w: int, target_h: int) -> np.ndarray:
    """Resize a frame using nearest-neighbor interpolation.

    Args:
        frame: Source BGRA frame.
        target_w: Target width.
        target_h: Target height.

    Returns:
        Resized BGRA frame.
    """
    h, w = frame.shape[:2]
    y_idx = (np.arange(target_h) * h // target_h).clip(0, h - 1)
    x_idx = (np.arange(target_w) * w // target_w).clip(0, w - 1)
    result: np.ndarray = frame[np.ix_(y_idx, x_idx)]
    return result


def create_proxy(
    clip: Clip,
    scale: float = 0.25,
    cache_dir: Path | None = None,
) -> ProxyClip:
    """Generate a low-resolution proxy for a clip.

    The proxy is rendered at the given scale factor and stored as raw
    BGRA frames on disk. If a proxy already exists and the clip hasn't
    changed, the existing proxy is reused.

    Args:
        clip: Source clip to proxy.
        scale: Scale factor for the proxy (0.0-1.0).
        cache_dir: Directory to store proxies. Defaults to
            ``~/.pymotion/proxies/``.

    Returns:
        A ProxyClip backed by the cached file.

    Raises:
        ValueError: If scale is invalid or clip has zero duration.
    """
    if scale <= 0.0 or scale > 1.0:
        msg = f"Proxy scale must be between 0.0 (exclusive) and 1.0, got {scale}"
        raise ValueError(msg)
    if clip.duration <= 0:
        msg = "Cannot create proxy for a clip with zero duration"
        raise ValueError(msg)

    proxy_dir = cache_dir or _DEFAULT_PROXY_DIR
    proxy_dir.mkdir(parents=True, exist_ok=True)

    # Generate unique filename based on clip identity and scale
    clip_id = f"{id(clip)}_{scale}_{clip.duration}"
    proxy_hash = hashlib.sha256(clip_id.encode()).hexdigest()[:12]
    proxy_path = proxy_dir / f"{proxy_hash}.proxy"

    # Use existing proxy if available
    if proxy_path.exists():
        logger.debug("proxy_cache_hit", path=str(proxy_path))
    else:
        # Render proxy frames
        base_w = 1920
        base_h = 1080
        proxy_w = max(2, int(base_w * scale) + (int(base_w * scale) % 2))
        proxy_h = max(2, int(base_h * scale) + (int(base_h * scale) % 2))
        res = Resolution(width=proxy_w, height=proxy_h)

        logger.debug(
            "proxy_render_start",
            frames=clip.duration,
            size=f"{proxy_w}x{proxy_h}",
        )

        with open(proxy_path, "wb") as f:
            for i in range(clip.duration):
                ctx = RenderContext(
                    frame=i,
                    fps=30,
                    resolution=res,
                    time_range=TimeRange(start=0, end=clip.duration),
                    local_frame=i,
                    progress=i / max(clip.duration - 1, 1),
                )
                frame = clip.render_frame(ctx)
                f.write(frame.tobytes())

        logger.debug("proxy_render_complete", path=str(proxy_path))

    # Read proxy metadata
    base_w = 1920
    base_h = 1080
    proxy_w = max(2, int(base_w * scale) + (int(base_w * scale) % 2))
    proxy_h = max(2, int(base_h * scale) + (int(base_h * scale) % 2))

    result = ProxyClip()
    result.source = proxy_path
    result._width = proxy_w
    result._height = proxy_h
    result._frame_count = clip.duration
    result.start = 0
    result.end = clip.duration

    return result


def clear_proxy_cache(
    older_than_days: int = 30,
    cache_dir: Path | None = None,
) -> int:
    """Remove stale proxy files from the cache.

    Args:
        older_than_days: Remove proxies older than this many days.
        cache_dir: Proxy cache directory. Defaults to
            ``~/.pymotion/proxies/``.

    Returns:
        Number of proxy files removed.
    """
    proxy_dir = cache_dir or _DEFAULT_PROXY_DIR
    if not proxy_dir.exists():
        return 0

    cutoff = time.time() - (older_than_days * 86400)
    removed = 0

    for proxy_file in proxy_dir.glob("*.proxy"):
        if proxy_file.stat().st_mtime < cutoff:
            proxy_file.unlink()
            removed += 1
            logger.debug("proxy_removed", path=str(proxy_file))

    return removed


def proxy_cache_size(cache_dir: Path | None = None) -> int:
    """Return the total size of the proxy cache in bytes.

    Args:
        cache_dir: Proxy cache directory. Defaults to
            ``~/.pymotion/proxies/``.

    Returns:
        Total bytes used by proxy files.
    """
    proxy_dir = cache_dir or _DEFAULT_PROXY_DIR
    if not proxy_dir.exists():
        return 0

    total = 0
    for proxy_file in proxy_dir.glob("*.proxy"):
        total += proxy_file.stat().st_size

    return total
