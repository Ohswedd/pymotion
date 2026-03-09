"""Built-in transition library — Fade and CrossDissolve for Phase 0.1.

Additional transitions will be added in later phases.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from pymotion.transition.base import Transition


@dataclass
class Fade(Transition):
    """Simple fade transition — clip A fades out, then clip B fades in.

    Args:
        duration: Transition duration in frames.
    """

    def render_frame(
        self,
        clip_a: np.ndarray,
        clip_b: np.ndarray,
        progress: float,
    ) -> np.ndarray:
        """Render a fade transition frame.

        Args:
            clip_a: Outgoing clip frame (BGRA).
            clip_b: Incoming clip frame (BGRA).
            progress: Transition progress (0.0-1.0).

        Returns:
            Blended BGRA frame.
        """
        a = clip_a.astype(np.float32)
        b = clip_b.astype(np.float32)
        result = a * (1.0 - progress) + b * progress
        return np.clip(result, 0, 255).astype(np.uint8)


@dataclass
class CrossDissolve(Transition):
    """Cross-dissolve transition — linear blend from A to B.

    Identical to Fade for now, but semantically distinct as a standard
    video editing term.

    Args:
        duration: Transition duration in frames.
    """

    def render_frame(
        self,
        clip_a: np.ndarray,
        clip_b: np.ndarray,
        progress: float,
    ) -> np.ndarray:
        """Render a cross-dissolve transition frame.

        Args:
            clip_a: Outgoing clip frame (BGRA).
            clip_b: Incoming clip frame (BGRA).
            progress: Transition progress (0.0-1.0).

        Returns:
            Blended BGRA frame.
        """
        a = clip_a.astype(np.float32)
        b = clip_b.astype(np.float32)
        result = a * (1.0 - progress) + b * progress
        return np.clip(result, 0, 255).astype(np.uint8)
