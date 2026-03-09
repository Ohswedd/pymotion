"""Effect abstract base class.

All effects are stateless — they receive a frame and context,
and return a new array with the effect applied.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from pymotion.clip.base import RenderContext


class Effect(ABC):
    """Abstract base class for all visual effects.

    Effects transform a BGRA frame and must return an array of the same shape.
    Effects must be stateless — no side effects.
    """

    @abstractmethod
    def apply(self, frame: np.ndarray, ctx: RenderContext) -> np.ndarray:
        """Apply effect to a BGRA frame.

        Args:
            frame: BGRA numpy array of shape (H, W, 4), dtype uint8.
            ctx: Render context for this frame.

        Returns:
            BGRA numpy array of the same shape with effect applied.
        """
        ...
