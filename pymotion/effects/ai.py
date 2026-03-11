"""AI-powered visual effects.

All AI effects require optional dependencies. Each effect raises
``ImportError`` with an install hint if the required package is missing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np

from pymotion.clip.base import RenderContext
from pymotion.effects.base import Effect
from pymotion.utils.logging import get_logger

if TYPE_CHECKING:
    from pymotion.clip.base import Clip

logger = get_logger(__name__)


@dataclass
class RemoveBackground(Effect):
    """Remove the background from a clip using AI segmentation.

    Uses the ``rembg`` library to generate an alpha matte, replacing
    the existing alpha channel with the predicted foreground mask.

    Args:
        model: Model name for rembg (e.g. ``"u2net"``, ``"isnet-general-use"``).
            Defaults to ``"u2net"``.
        alpha_matting: Enable alpha matting for finer edge detail.
        foreground_threshold: Alpha matting foreground threshold (0–255).
        background_threshold: Alpha matting background threshold (0–255).

    Raises:
        ImportError: If ``rembg`` is not installed.

    Example::

        from pymotion.effects.ai import RemoveBackground

        clip.add_effect(RemoveBackground())
        clip.add_effect(RemoveBackground(model="isnet-general-use"))
    """

    model: str = "u2net"
    alpha_matting: bool = False
    foreground_threshold: int = 240
    background_threshold: int = 10

    _session: Any = None  # noqa: RUF009

    def __post_init__(self) -> None:
        """Validate parameters."""
        if not self.model:
            msg = "model name must not be empty"
            raise ValueError(msg)
        if not 0 <= self.foreground_threshold <= 255:
            msg = "foreground_threshold must be 0–255"
            raise ValueError(msg)
        if not 0 <= self.background_threshold <= 255:
            msg = "background_threshold must be 0–255"
            raise ValueError(msg)

    def _get_session(self) -> Any:
        """Lazily create and cache the rembg session.

        Returns:
            A rembg ``BaseSession`` instance.

        Raises:
            ImportError: If rembg is not installed.
        """
        if self._session is not None:
            return self._session

        try:
            from rembg import new_session  # noqa: PLC0415
        except ImportError:
            msg = (
                "rembg is required for RemoveBackground. "
                'Install it with: pip install "pymotion-studio[ai]"'
            )
            raise ImportError(msg)  # noqa: B904

        logger.debug("creating_rembg_session", model=self.model)
        self._session = new_session(self.model)
        return self._session

    def apply(self, frame: np.ndarray, ctx: RenderContext) -> np.ndarray:
        """Apply background removal to a BGRA frame.

        Args:
            frame: BGRA numpy array of shape (H, W, 4), dtype uint8.
            ctx: Render context for this frame.

        Returns:
            BGRA numpy array with alpha channel set to the foreground mask.
        """
        try:
            from rembg import remove  # noqa: PLC0415
        except ImportError:
            msg = (
                "rembg is required for RemoveBackground. "
                'Install it with: pip install "pymotion-studio[ai]"'
            )
            raise ImportError(msg)  # noqa: B904

        session = self._get_session()

        # rembg expects RGBA input, convert from BGRA
        rgba_in = np.empty_like(frame)
        rgba_in[:, :, 0] = frame[:, :, 2]  # R
        rgba_in[:, :, 1] = frame[:, :, 1]  # G
        rgba_in[:, :, 2] = frame[:, :, 0]  # B
        rgba_in[:, :, 3] = frame[:, :, 3]  # A

        rgba_out: np.ndarray = remove(
            rgba_in,
            session=session,
            alpha_matting=self.alpha_matting,
            alpha_matting_foreground_threshold=self.foreground_threshold,
            alpha_matting_background_threshold=self.background_threshold,
        )

        # Convert back from RGBA to BGRA
        result = np.empty_like(frame)
        result[:, :, 0] = rgba_out[:, :, 2]  # B
        result[:, :, 1] = rgba_out[:, :, 1]  # G
        result[:, :, 2] = rgba_out[:, :, 0]  # R
        result[:, :, 3] = rgba_out[:, :, 3]  # A (foreground mask)

        return result


@dataclass
class ReplaceBackground(Effect):
    """Remove the original background and composite over a new one.

    Combines :class:`RemoveBackground` with alpha compositing: the
    foreground is extracted via ``rembg``, then blended over the new
    background clip's frame at the same time index.

    Args:
        new_bg: A :class:`~pymotion.clip.base.Clip` to use as the
            replacement background. Its ``render_frame`` is called with
            the same :class:`RenderContext` to produce the background.
        model: Model name passed to :class:`RemoveBackground`.
        alpha_matting: Enable alpha matting for finer edges.
        foreground_threshold: Alpha matting foreground threshold (0–255).
        background_threshold: Alpha matting background threshold (0–255).

    Raises:
        ImportError: If ``rembg`` is not installed.

    Example::

        from pymotion.effects.ai import ReplaceBackground
        from pymotion import ColorClip

        bg = ColorClip("#1A1A2E").set_duration(60)
        clip.add_effect(ReplaceBackground(new_bg=bg))
    """

    new_bg: Clip = field(repr=False)
    model: str = "u2net"
    alpha_matting: bool = False
    foreground_threshold: int = 240
    background_threshold: int = 10

    _remove_bg: RemoveBackground = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Create the internal RemoveBackground effect."""
        self._remove_bg = RemoveBackground(
            model=self.model,
            alpha_matting=self.alpha_matting,
            foreground_threshold=self.foreground_threshold,
            background_threshold=self.background_threshold,
        )

    def apply(self, frame: np.ndarray, ctx: RenderContext) -> np.ndarray:
        """Remove background and composite foreground over new_bg.

        Args:
            frame: BGRA numpy array of shape (H, W, 4), dtype uint8.
            ctx: Render context for this frame.

        Returns:
            BGRA numpy array composited over the new background.
        """
        # Step 1: remove background → get foreground with alpha matte
        fg = self._remove_bg.apply(frame, ctx)

        # Step 2: render background frame at the same context
        bg = self.new_bg.render_frame(ctx)

        # Ensure bg matches foreground dimensions
        h, w = fg.shape[:2]
        if bg.shape[:2] != (h, w):
            from PIL import Image  # noqa: PLC0415

            bg_img = Image.fromarray(bg[:, :, :3])
            bg_img = bg_img.resize((w, h), Image.LANCZOS)  # type: ignore[attr-defined]
            bg_resized = np.zeros((h, w, 4), dtype=np.uint8)
            bg_resized[:, :, :3] = np.asarray(bg_img)
            bg_resized[:, :, 3] = 255
            bg = bg_resized

        # Step 3: alpha composite fg over bg
        alpha = fg[:, :, 3:4].astype(np.uint16)
        inv_alpha = np.uint16(255) - alpha
        result = np.empty_like(fg)
        result[:, :, :3] = (
            (fg[:, :, :3].astype(np.uint16) * alpha + bg[:, :, :3].astype(np.uint16) * inv_alpha)
            + np.uint16(128)
        ) >> np.uint16(8)
        result[:, :, 3] = 255  # fully opaque composite

        return result
