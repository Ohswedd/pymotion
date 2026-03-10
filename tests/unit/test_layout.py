"""Tests for layout helpers — pip, grid, split_screen, stack."""

from __future__ import annotations

import pytest

from pymotion.clip.color import ColorClip
from pymotion.composition import Composition
from pymotion.layout import grid, pip, split_screen, stack
from pymotion.utils.color import Color
from pymotion.utils.layout import _resolve_position


def _make_clip(color: str = "#FF0000", duration: int = 60) -> ColorClip:
    """Create a colored clip for testing."""
    clip = ColorClip(color=Color.parse(color))
    clip.start = 0
    clip.end = duration
    return clip


class TestResolvePosition:
    """Tests for _resolve_position utility."""

    def test_pixel_tuple(self) -> None:
        result = _resolve_position((100, 200), (480, 270), (1920, 1080))
        assert result == (100, 200)

    def test_top_left(self) -> None:
        x, y = _resolve_position("top-left", (480, 270), (1920, 1080))
        assert x == 10  # margin
        assert y == 10

    def test_bottom_right(self) -> None:
        x, y = _resolve_position("bottom-right", (480, 270), (1920, 1080))
        assert x > 1000
        assert y > 500

    def test_center(self) -> None:
        x, y = _resolve_position("center", (480, 270), (1920, 1080))
        assert 500 < x < 900
        assert 300 < y < 500

    def test_invalid_anchor(self) -> None:
        with pytest.raises(ValueError, match="Unknown anchor"):
            _resolve_position("invalid", (480, 270), (1920, 1080))


class TestPip:
    """Tests for pip() function."""

    def test_pip_basic(self) -> None:
        main = _make_clip("#FF0000", 60)
        overlay = _make_clip("#0000FF", 60)
        result = pip(main, overlay)
        assert isinstance(result, Composition)
        assert result.duration == 60

    def test_pip_with_position(self) -> None:
        main = _make_clip("#FF0000", 60)
        overlay = _make_clip("#0000FF", 60)
        result = pip(main, overlay, position="top-left")
        assert isinstance(result, Composition)

    def test_pip_with_size(self) -> None:
        main = _make_clip("#FF0000", 60)
        overlay = _make_clip("#0000FF", 60)
        result = pip(main, overlay, size=(480, 270))
        assert isinstance(result, Composition)

    def test_pip_with_pixel_position(self) -> None:
        main = _make_clip("#FF0000", 60)
        overlay = _make_clip("#0000FF", 60)
        result = pip(main, overlay, position=(100, 100))
        assert isinstance(result, Composition)

    def test_pip_zero_duration(self) -> None:
        main = _make_clip("#FF0000", 0)
        overlay = _make_clip("#0000FF", 60)
        with pytest.raises(ValueError, match="positive duration"):
            pip(main, overlay)


class TestGrid:
    """Tests for grid() function."""

    def test_grid_basic(self) -> None:
        clips = [_make_clip(c, 60) for c in ["#FF0000", "#00FF00", "#0000FF", "#FFFF00"]]
        result = grid(clips, rows=2, cols=2)
        assert isinstance(result, Composition)
        assert result.duration == 60

    def test_grid_with_gap(self) -> None:
        clips = [_make_clip("#FF0000", 60) for _ in range(4)]
        result = grid(clips, rows=2, cols=2, gap=10)
        assert isinstance(result, Composition)

    def test_grid_fewer_clips(self) -> None:
        """Grid with fewer clips than cells should still work."""
        clips = [_make_clip("#FF0000", 60), _make_clip("#00FF00", 60)]
        result = grid(clips, rows=2, cols=2)
        assert isinstance(result, Composition)

    def test_grid_empty(self) -> None:
        with pytest.raises(ValueError, match="at least one clip"):
            grid([], rows=2, cols=2)

    def test_grid_invalid_dims(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            grid([_make_clip()], rows=0, cols=2)


class TestSplitScreen:
    """Tests for split_screen() function."""

    def test_split_horizontal(self) -> None:
        clips = [_make_clip("#FF0000", 60), _make_clip("#0000FF", 60)]
        result = split_screen(clips, layout="horizontal")
        assert isinstance(result, Composition)

    def test_split_vertical(self) -> None:
        clips = [_make_clip("#FF0000", 60), _make_clip("#0000FF", 60)]
        result = split_screen(clips, layout="vertical")
        assert isinstance(result, Composition)

    def test_split_quad(self) -> None:
        clips = [_make_clip(c, 60) for c in ["#FF0000", "#00FF00", "#0000FF", "#FFFF00"]]
        result = split_screen(clips, layout="quad")
        assert isinstance(result, Composition)

    def test_split_custom_rects(self) -> None:
        clips = [_make_clip("#FF0000", 60), _make_clip("#0000FF", 60)]
        rects = [(0.0, 0.0, 0.7, 1.0), (0.7, 0.0, 0.3, 1.0)]
        result = split_screen(clips, layout=rects)
        assert isinstance(result, Composition)

    def test_split_empty(self) -> None:
        with pytest.raises(ValueError, match="at least one clip"):
            split_screen([])

    def test_split_invalid_layout(self) -> None:
        with pytest.raises(ValueError, match="Unknown layout"):
            split_screen([_make_clip()], layout="diagonal")


class TestStack:
    """Tests for stack() function."""

    def test_stack_horizontal(self) -> None:
        clips = [_make_clip("#FF0000", 60), _make_clip("#0000FF", 60)]
        result = stack(clips, direction="horizontal")
        assert isinstance(result, Composition)

    def test_stack_vertical(self) -> None:
        clips = [_make_clip("#FF0000", 60), _make_clip("#0000FF", 60)]
        result = stack(clips, direction="vertical")
        assert isinstance(result, Composition)

    def test_stack_with_gap(self) -> None:
        clips = [_make_clip("#FF0000", 60), _make_clip("#0000FF", 60)]
        result = stack(clips, direction="horizontal", gap=4)
        assert isinstance(result, Composition)

    def test_stack_single_clip(self) -> None:
        clips = [_make_clip("#FF0000", 60)]
        result = stack(clips, direction="horizontal")
        assert isinstance(result, Composition)

    def test_stack_empty(self) -> None:
        with pytest.raises(ValueError, match="at least one clip"):
            stack([])

    def test_stack_invalid_direction(self) -> None:
        with pytest.raises(ValueError, match="must be"):
            stack([_make_clip()], direction="diagonal")
