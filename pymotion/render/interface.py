"""RendererInterface — abstract base class for all rendering backends.

Defines the contract that Backend2D, Backend3D, and any future
rendering backends must implement.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from pymotion.clip.base import Clip, RenderContext


class RendererInterface(ABC):
    """Abstract base class for rendering backends.

    Each backend renders specific clip types into BGRA numpy arrays.
    """

    @abstractmethod
    def can_render(self, clip: Clip) -> bool:
        """Check whether this backend can render the given clip type.

        Args:
            clip: The clip to check.

        Returns:
            True if this backend handles the clip type.
        """
        ...

    @abstractmethod
    def render_frame(self, clip: Clip, ctx: RenderContext) -> np.ndarray:
        """Render a single frame of the given clip.

        Args:
            clip: The clip to render.
            ctx: Render context for this frame.

        Returns:
            BGRA numpy array of shape (H, W, 4), dtype uint8.
        """
        ...
