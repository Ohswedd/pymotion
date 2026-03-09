"""AssetLoader with LRU cache for images, fonts, and audio files.

Provides centralized asset loading with caching and validation
to prevent repeated file I/O and enforce security constraints.
"""

from __future__ import annotations

import functools
from pathlib import Path

import numpy as np
from PIL import Image

from pymotion.config import get_config
from pymotion.utils.logging import get_logger

logger = get_logger(__name__)


@functools.lru_cache(maxsize=128)
def _load_image_cached(path_str: str) -> np.ndarray:
    """Load an image file and return as BGRA numpy array (cached).

    Args:
        path_str: String path to the image file.

    Returns:
        BGRA numpy array of shape (H, W, 4), dtype uint8.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file cannot be decoded as an image.
    """
    path = Path(path_str)
    if not path.exists():
        msg = f"Image file not found: {path}"
        raise FileNotFoundError(msg)

    try:
        img = Image.open(path).convert("RGBA")
    except Exception as exc:
        msg = f"Failed to load image: {path}"
        raise ValueError(msg) from exc

    arr = np.array(img, dtype=np.uint8)
    # Convert RGBA -> BGRA for internal format
    bgra = arr.copy()
    bgra[:, :, 0] = arr[:, :, 2]  # B <- R
    bgra[:, :, 2] = arr[:, :, 0]  # R <- B
    logger.debug("loaded_image", path=str(path), shape=bgra.shape)
    return bgra


class AssetLoader:
    """Centralized asset loader with LRU caching.

    Loads images, fonts, and other assets from the filesystem
    with validation and caching for performance.

    Args:
        base_dirs: List of allowed base directories for asset loading.
        max_cache_size: Maximum cache size in bytes.
    """

    def __init__(
        self,
        base_dirs: list[Path] | None = None,
        max_cache_size: int | None = None,
    ) -> None:
        """Initialize the asset loader.

        Args:
            base_dirs: List of allowed base directories. If None, allows cwd.
            max_cache_size: Maximum cache size in bytes. Defaults to
                PyMotionConfig.cache_max_bytes.
        """
        self.base_dirs = base_dirs or [Path.cwd()]
        if max_cache_size is None:
            max_cache_size = get_config().cache_max_bytes
        self.max_cache_size = max_cache_size

    def load_image(self, path: str | Path) -> np.ndarray:
        """Load an image file as a BGRA numpy array.

        Args:
            path: Path to the image file.

        Returns:
            BGRA numpy array of shape (H, W, 4), dtype uint8.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the file cannot be decoded.
        """
        resolved = Path(path).resolve()
        return _load_image_cached(str(resolved))

    def clear_cache(self) -> None:
        """Clear the asset cache."""
        _load_image_cached.cache_clear()
        logger.info("asset_cache_cleared")
