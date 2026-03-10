"""ImageClip — display static images within a composition.

Supports PNG, JPG, WEBP formats. Images are loaded lazily on first render.
Preserves aspect ratio by default with configurable fit modes.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Self

import numpy as np
from PIL import Image

from pymotion.clip.base import Clip, RenderContext
from pymotion.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ImageClip(Clip):
    """A clip that displays a static image.

    Supports three fit modes for scaling:
    - "contain": Scale to fit within bounds, preserving aspect ratio (default).
    - "cover": Scale to fill bounds, cropping excess while preserving ratio.
    - "stretch": Stretch to fill bounds exactly (ignores aspect ratio).

    Args:
        source: Path to the image file.
        fit_mode: How to scale the image ("contain", "cover", "stretch").
    """

    source: str | Path = ""
    fit_mode: Literal["contain", "cover", "stretch"] = "contain"
    _cached_frame: np.ndarray | None = None
    _original_img: Image.Image | None = None

    def __init__(
        self,
        source: str | Path,
        *,
        fit_mode: Literal["contain", "cover", "stretch"] = "contain",
        **kwargs: object,
    ) -> None:
        """Initialize an ImageClip with the given source path.

        Args:
            source: Path to the image file.
            fit_mode: How to scale the image.
            **kwargs: Additional Clip parameters.
        """
        super().__init__()
        self.source = Path(source)
        self.fit_mode = fit_mode
        self._cached_frame = None
        self._original_img = None

    def set_fit_mode(self, mode: Literal["contain", "cover", "stretch"]) -> Self:
        """Set the image fit mode.

        Args:
            mode: How to scale the image.

        Returns:
            Self for method chaining.
        """
        self.fit_mode = mode
        self._cached_frame = None
        return self

    def _load_original(self) -> Image.Image:
        """Load the original image from disk (cached).

        Returns:
            PIL Image in RGBA mode.

        Raises:
            FileNotFoundError: If the image file does not exist.
        """
        if self._original_img is not None:
            return self._original_img

        path = Path(self.source)
        if not path.exists():
            msg = f"Image file not found: {path}"
            raise FileNotFoundError(msg)

        self._original_img = Image.open(path).convert("RGBA")
        return self._original_img

    def _load(self, width: int, height: int) -> np.ndarray:
        """Load and convert the image to BGRA format with fit mode.

        Args:
            width: Target frame width.
            height: Target frame height.

        Returns:
            BGRA numpy array of shape (height, width, 4).
        """
        img = self._load_original()
        src_w, src_h = img.size

        if self.fit_mode == "stretch":
            resized = img.resize((width, height), Image.Resampling.LANCZOS)
            return self._rgba_to_bgra(np.array(resized, dtype=np.uint8))

        if self.fit_mode == "cover":
            # Scale up to cover the entire area, then center-crop
            scale = max(width / src_w, height / src_h)
            new_w = max(1, int(src_w * scale + 0.5))
            new_h = max(1, int(src_h * scale + 0.5))
            resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            # Center crop
            left = (new_w - width) // 2
            top = (new_h - height) // 2
            cropped = resized.crop((left, top, left + width, top + height))
            return self._rgba_to_bgra(np.array(cropped, dtype=np.uint8))

        # "contain" — fit within bounds preserving aspect ratio
        scale = min(width / src_w, height / src_h)
        new_w = max(1, int(src_w * scale + 0.5))
        new_h = max(1, int(src_h * scale + 0.5))
        resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        arr = self._rgba_to_bgra(np.array(resized, dtype=np.uint8))
        return arr

    @staticmethod
    def _rgba_to_bgra(arr: np.ndarray) -> np.ndarray:
        """Convert RGBA numpy array to BGRA in-place.

        Args:
            arr: RGBA uint8 array.

        Returns:
            BGRA uint8 array (same buffer, channels swapped).
        """
        bgra = arr.copy()
        bgra[:, :, 0] = arr[:, :, 2]
        bgra[:, :, 2] = arr[:, :, 0]
        return bgra

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render the image as a frame, respecting position and fit mode.

        Args:
            ctx: The render context for this frame.

        Returns:
            BGRA numpy array of shape (H, W, 4), dtype uint8.
        """
        fw = ctx.resolution.width
        fh = ctx.resolution.height

        if self._cached_frame is not None and self._cached_frame.shape[:2] == (fh, fw):
            return self._cached_frame

        frame = np.zeros((fh, fw, 4), dtype=np.uint8)
        img_arr = self._load(fw, fh)
        ih, iw = img_arr.shape[:2]

        # Compute placement position
        px = int(self._position.x)
        py = int(self._position.y)

        if self.fit_mode == "stretch" or self.fit_mode == "cover":
            # These modes produce full-frame images; position is offset
            if px == 0 and py == 0:
                frame = img_arr
            else:
                src_y0 = max(0, -py)
                src_x0 = max(0, -px)
                dst_y0 = max(0, py)
                dst_x0 = max(0, px)
                copy_h = min(ih - src_y0, fh - dst_y0)
                copy_w = min(iw - src_x0, fw - dst_x0)
                if copy_h > 0 and copy_w > 0:
                    frame[dst_y0 : dst_y0 + copy_h, dst_x0 : dst_x0 + copy_w] = img_arr[
                        src_y0 : src_y0 + copy_h, src_x0 : src_x0 + copy_w
                    ]
        else:
            # "contain" — center the scaled image, then apply position offset
            cx = (fw - iw) // 2 + px
            cy = (fh - ih) // 2 + py
            src_y0 = max(0, -cy)
            src_x0 = max(0, -cx)
            dst_y0 = max(0, cy)
            dst_x0 = max(0, cx)
            copy_h = min(ih - src_y0, fh - dst_y0)
            copy_w = min(iw - src_x0, fw - dst_x0)
            if copy_h > 0 and copy_w > 0:
                frame[dst_y0 : dst_y0 + copy_h, dst_x0 : dst_x0 + copy_w] = img_arr[
                    src_y0 : src_y0 + copy_h, src_x0 : src_x0 + copy_w
                ]

        self._cached_frame = frame
        logger.debug(
            "image_loaded",
            source=str(self.source),
            size=f"{iw}x{ih}",
            fit=self.fit_mode,
            frame=f"{fw}x{fh}",
        )
        return self._cached_frame
