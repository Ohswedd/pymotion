"""ImageClip — display static images within a composition.

Supports PNG, JPG, WEBP formats. Images are loaded lazily on first render.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

from pymotion.clip.base import Clip, RenderContext
from pymotion.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ImageClip(Clip):
    """A clip that displays a static image.

    Args:
        source: Path to the image file.
    """

    source: str | Path = ""
    _cached_frame: np.ndarray | None = None

    def __init__(self, source: str | Path, **kwargs: object) -> None:
        """Initialize an ImageClip with the given source path.

        Args:
            source: Path to the image file.
            **kwargs: Additional Clip parameters.
        """
        super().__init__()
        self.source = Path(source)
        self._cached_frame = None

    def _load(self, width: int, height: int) -> np.ndarray:
        """Load and convert the image to BGRA format.

        Args:
            width: Target width to resize to.
            height: Target height to resize to.

        Returns:
            BGRA numpy array of shape (height, width, 4).

        Raises:
            FileNotFoundError: If the image file does not exist.
        """
        path = Path(self.source)
        if not path.exists():
            msg = f"Image file not found: {path}"
            raise FileNotFoundError(msg)

        img = Image.open(path).convert("RGBA")
        img = img.resize((width, height), Image.Resampling.LANCZOS)
        arr = np.array(img, dtype=np.uint8)

        # Convert RGBA -> BGRA
        bgra = arr.copy()
        bgra[:, :, 0] = arr[:, :, 2]
        bgra[:, :, 2] = arr[:, :, 0]
        return bgra

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render the image as a frame.

        Args:
            ctx: The render context for this frame.

        Returns:
            BGRA numpy array of shape (H, W, 4), dtype uint8.
        """
        w = ctx.resolution.width
        h = ctx.resolution.height

        if self._cached_frame is None or self._cached_frame.shape[:2] != (h, w):
            self._cached_frame = self._load(w, h)
            logger.debug("image_loaded", source=str(self.source), size=f"{w}x{h}")

        return self._cached_frame.copy()
