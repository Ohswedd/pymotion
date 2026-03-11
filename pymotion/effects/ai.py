"""AI-powered visual effects.

All AI effects require optional dependencies. Each effect raises
``ImportError`` with an install hint if the required package is missing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from pymotion.clip.base import RenderContext
from pymotion.effects.base import Effect
from pymotion.utils.logging import get_logger

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
