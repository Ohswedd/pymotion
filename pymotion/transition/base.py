"""Transition abstract base class.

Transitions blend between two clip frames over a specified duration.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np


@dataclass
class Transition(ABC):
    """Abstract base class for all transitions.

    A transition blends between an outgoing clip (A) and an incoming clip (B)
    over a specified number of frames.

    Args:
        duration: Transition duration in frames.
    """

    duration: int = 30

    @abstractmethod
    def render_frame(
        self,
        clip_a: np.ndarray,
        clip_b: np.ndarray,
        progress: float,
    ) -> np.ndarray:
        """Render a single frame of the transition.

        Args:
            clip_a: Outgoing clip frame (BGRA, uint8).
            clip_b: Incoming clip frame (BGRA, uint8).
            progress: Transition progress (0.0 = all A, 1.0 = all B).

        Returns:
            Blended BGRA frame.
        """
        ...
