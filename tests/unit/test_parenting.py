"""Tests for parenting and hierarchy — v1.3.4."""

from __future__ import annotations

import pytest

from pymotion.clip.base import Clip, NullObject, RenderContext, Resolution, TimeRange
from pymotion.clip.color import ColorClip


def _ctx(frame: int = 0) -> RenderContext:
    return RenderContext(
        frame=frame,
        fps=30,
        resolution=Resolution(width=200, height=100),
        time_range=TimeRange(start=0, end=60),
        local_frame=frame,
        progress=frame / 59,
    )


class TestParentProperty:
    """Test clip.parent getter/setter."""

    def test_default_parent_is_none(self) -> None:
        clip = ColorClip("#FFFFFF").set_duration(30)
        assert clip.parent is None

    def test_set_parent(self) -> None:
        parent = ColorClip("#FF0000").set_duration(30)
        child = ColorClip("#00FF00").set_duration(30)
        child.parent = parent
        assert child.parent is parent

    def test_unset_parent(self) -> None:
        parent = ColorClip("#FF0000").set_duration(30)
        child = ColorClip("#00FF00").set_duration(30)
        child.parent = parent
        child.parent = None
        assert child.parent is None


class TestCircularParenting:
    """Test circular parent detection."""

    def test_self_assignment_raises(self) -> None:
        clip = ColorClip("#FFFFFF").set_duration(30)
        with pytest.raises(ValueError, match="Circular"):
            clip.parent = clip

    def test_two_node_cycle_raises(self) -> None:
        a = ColorClip("#FFFFFF").set_duration(30)
        b = ColorClip("#FFFFFF").set_duration(30)
        a.parent = b
        with pytest.raises(ValueError, match="Circular"):
            b.parent = a

    def test_three_node_cycle_raises(self) -> None:
        a = ColorClip("#FFFFFF").set_duration(30)
        b = ColorClip("#FFFFFF").set_duration(30)
        c = ColorClip("#FFFFFF").set_duration(30)
        a.parent = b
        b.parent = c
        with pytest.raises(ValueError, match="Circular"):
            c.parent = a

    def test_non_circular_chain_ok(self) -> None:
        a = ColorClip("#FFFFFF").set_duration(30)
        b = ColorClip("#FFFFFF").set_duration(30)
        c = ColorClip("#FFFFFF").set_duration(30)
        a.parent = b
        b.parent = c
        # No cycle — should not raise
        assert a.parent is b
        assert b.parent is c
        assert c.parent is None


class TestPositionInheritance:
    """Test position_at with parent chain."""

    def test_no_parent(self) -> None:
        clip = ColorClip("#FFFFFF").set_duration(30)
        clip.set_position(50, 30)
        pos = clip.position_at(0)
        assert pos.x == 50
        assert pos.y == 30

    def test_single_parent(self) -> None:
        parent = ColorClip("#FFFFFF").set_duration(30)
        parent.set_position(100, 200)

        child = ColorClip("#FFFFFF").set_duration(30)
        child.set_position(10, 20)
        child.parent = parent

        pos = child.position_at(0)
        assert pos.x == 110  # 100 + 10 * 1.0
        assert pos.y == 220  # 200 + 20 * 1.0

    def test_parent_scale_affects_child_offset(self) -> None:
        parent = ColorClip("#FFFFFF").set_duration(30)
        parent.set_position(0, 0)
        parent.set_scale(2.0)

        child = ColorClip("#FFFFFF").set_duration(30)
        child.set_position(50, 25)
        child.parent = parent

        pos = child.position_at(0)
        assert pos.x == 100  # 0 + 50 * 2.0
        assert pos.y == 50  # 0 + 25 * 2.0

    def test_chained_parents(self) -> None:
        grandparent = ColorClip("#FFFFFF").set_duration(30)
        grandparent.set_position(100, 100)

        parent = ColorClip("#FFFFFF").set_duration(30)
        parent.set_position(10, 10)
        parent.parent = grandparent

        child = ColorClip("#FFFFFF").set_duration(30)
        child.set_position(5, 5)
        child.parent = parent

        pos = child.position_at(0)
        # grandparent: (100, 100)
        # parent: (100 + 10*1, 100 + 10*1) = (110, 110)
        # child: (110 + 5*1, 110 + 5*1) = (115, 115)
        assert pos.x == 115
        assert pos.y == 115


class TestScaleInheritance:
    """Test scale_at with parent chain."""

    def test_no_parent(self) -> None:
        clip = ColorClip("#FFFFFF").set_duration(30)
        clip.set_scale(2.0, 3.0)
        sc = clip.scale_at(0)
        assert sc.x == 2.0
        assert sc.y == 3.0

    def test_single_parent_multiplies(self) -> None:
        parent = ColorClip("#FFFFFF").set_duration(30)
        parent.set_scale(2.0)

        child = ColorClip("#FFFFFF").set_duration(30)
        child.set_scale(3.0)
        child.parent = parent

        sc = child.scale_at(0)
        assert sc.x == 6.0  # 3 * 2
        assert sc.y == 6.0


class TestRotationInheritance:
    """Test rotation_at with parent chain."""

    def test_no_parent(self) -> None:
        clip = ColorClip("#FFFFFF").set_duration(30)
        clip.set_rotation(45)
        assert clip.rotation_at(0) == 45

    def test_single_parent_sums(self) -> None:
        parent = ColorClip("#FFFFFF").set_duration(30)
        parent.set_rotation(30)

        child = ColorClip("#FFFFFF").set_duration(30)
        child.set_rotation(15)
        child.parent = parent

        assert child.rotation_at(0) == 45  # 15 + 30


class TestOpacityAt:
    """Test opacity_at method."""

    def test_returns_opacity(self) -> None:
        clip = ColorClip("#FFFFFF").set_duration(30)
        clip.set_opacity(0.5)
        assert clip.opacity_at(0) == 0.5


class TestNullObject:
    """Test NullObject as invisible transform anchor."""

    def test_is_clip_subclass(self) -> None:
        null = NullObject()
        assert isinstance(null, Clip)

    def test_renders_transparent(self) -> None:
        null = NullObject()
        null.set_duration(30)
        frame = null.render_frame(_ctx())
        assert frame.shape == (100, 200, 4)
        assert frame.max() == 0

    def test_used_as_parent(self) -> None:
        anchor = NullObject()
        anchor.set_position(200, 150)
        anchor.set_rotation(45)
        anchor.set_duration(30)

        child = ColorClip("#FFFFFF").set_duration(30)
        child.set_position(10, 10)
        child.parent = anchor

        pos = child.position_at(0)
        assert pos.x == 210
        assert pos.y == 160
        assert child.rotation_at(0) == 45

    def test_null_chain(self) -> None:
        n1 = NullObject()
        n1.set_position(100, 0)
        n1.set_duration(30)

        n2 = NullObject()
        n2.set_position(0, 100)
        n2.parent = n1
        n2.set_duration(30)

        clip = ColorClip("#FFFFFF").set_duration(30)
        clip.set_position(5, 5)
        clip.parent = n2

        pos = clip.position_at(0)
        assert pos.x == 105  # 100 + 0 + 5
        assert pos.y == 105  # 0 + 100 + 5

    def test_set_duration_fluent(self) -> None:
        null = NullObject()
        result = null.set_duration(30)
        assert result is null
        assert null.duration == 30


class TestParentingExport:
    """Test public API exports."""

    def test_importable(self) -> None:
        import pymotion as pm

        assert hasattr(pm, "NullObject")
        assert pm.NullObject is NullObject
