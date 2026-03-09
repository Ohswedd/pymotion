"""Shared test fixtures for PyMotion test suite."""

from __future__ import annotations

import numpy as np
import pytest

from pymotion.clip.base import Resolution
from pymotion.composition import Composition

# Ensure structlog is properly configured before any loggers are created
from pymotion.utils.logging import configure_logging  # noqa: E402

configure_logging(debug=False)


@pytest.fixture
def blank_comp() -> Composition:
    """1920x1080, 30fps, 1-second composition."""
    return Composition(width=1920, height=1080, fps=30, duration=30)


@pytest.fixture
def small_comp() -> Composition:
    """320x240, 30fps, 10-frame composition for fast tests."""
    return Composition(width=320, height=240, fps=30, duration=10)


@pytest.fixture
def test_image() -> np.ndarray:
    """Standard 320x240 BGRA test image (solid red)."""
    frame = np.zeros((240, 320, 4), dtype=np.uint8)
    frame[:, :, 2] = 255  # R in BGRA position
    frame[:, :, 3] = 255  # A
    return frame


@pytest.fixture
def test_resolution() -> Resolution:
    """Standard test resolution."""
    return Resolution(width=320, height=240)


def assert_frames_equal(
    a: np.ndarray,
    b: np.ndarray,
    tolerance: float = 0.01,
) -> None:
    """Assert two BGRA frames are within tolerance.

    Args:
        a: First frame.
        b: Second frame.
        tolerance: Maximum fraction of differing pixels.
    """
    assert a.shape == b.shape, f"Shape mismatch: {a.shape} vs {b.shape}"
    diff_pixels = np.sum(np.any(a != b, axis=-1))
    total_pixels = a.shape[0] * a.shape[1]
    diff_fraction = diff_pixels / total_pixels
    assert diff_fraction <= tolerance, (
        f"Frames differ by {diff_fraction:.4f} ({diff_pixels}/{total_pixels} pixels), "
        f"tolerance is {tolerance}"
    )
