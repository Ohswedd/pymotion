"""RenderPipeline — orchestrates the full frame rendering pipeline.

Coordinates backend selection, rendering, compositing, effects,
and color pipeline for each frame. Includes a frame cache for static layers.
"""

from __future__ import annotations

from collections import OrderedDict

import numpy as np

from pymotion.render.backend_2d import CairoRenderer
from pymotion.render.interface import RendererInterface
from pymotion.utils.logging import get_logger

logger = get_logger(__name__)


class FrameCache:
    """LRU frame cache for static layers.

    Caches rendered frames keyed by (clip_id, frame_number) to avoid
    re-rendering static clips that don't change between frames.

    Args:
        max_size: Maximum number of cached frames.
    """

    def __init__(self, max_size: int = 256) -> None:
        """Initialize frame cache.

        Args:
            max_size: Maximum number of frames to cache.
        """
        self._max_size = max(1, max_size)
        self._cache: OrderedDict[tuple[int, int], np.ndarray] = OrderedDict()
        self._hits = 0
        self._misses = 0

    def get(self, clip_id: int, frame: int) -> np.ndarray | None:
        """Get a cached frame if it exists.

        Args:
            clip_id: Unique clip identifier.
            frame: Frame number.

        Returns:
            Cached BGRA frame, or None if not cached.
        """
        key = (clip_id, frame)
        if key in self._cache:
            self._hits += 1
            self._cache.move_to_end(key)
            return self._cache[key]
        self._misses += 1
        return None

    def put(self, clip_id: int, frame: int, data: np.ndarray) -> None:
        """Cache a rendered frame.

        Args:
            clip_id: Unique clip identifier.
            frame: Frame number.
            data: BGRA frame data.
        """
        key = (clip_id, frame)
        if key in self._cache:
            self._cache.move_to_end(key)
        else:
            if len(self._cache) >= self._max_size:
                self._cache.popitem(last=False)
            self._cache[key] = data

    def clear(self) -> None:
        """Clear all cached frames."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    @property
    def size(self) -> int:
        """Current number of cached frames."""
        return len(self._cache)

    @property
    def hit_rate(self) -> float:
        """Cache hit rate (0.0-1.0)."""
        total = self._hits + self._misses
        if total == 0:
            return 0.0
        return self._hits / total


class RenderPipeline:
    """Orchestrates the full rendering pipeline.

    Manages renderer backends, frame cache for static layers, and
    coordinates the render flow from timeline resolution through
    final frame output.
    """

    def __init__(self, cache_size: int = 256) -> None:
        """Initialize the render pipeline with default backends.

        Args:
            cache_size: Maximum frames to cache for static layers.
        """
        self.backends: list[RendererInterface] = [
            CairoRenderer(),
        ]
        self.frame_cache = FrameCache(max_size=cache_size)
        logger.debug("pipeline_initialized", backends=len(self.backends), cache_size=cache_size)
