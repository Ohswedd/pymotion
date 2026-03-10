"""Tests for proxy workflow — generation, caching, and cleanup."""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pytest

from pymotion.clip.base import RenderContext, Resolution, TimeRange
from pymotion.clip.color import ColorClip
from pymotion.proxy import (
    ProxyClip,
    _resize_nearest,
    clear_proxy_cache,
    create_proxy,
    proxy_cache_size,
)
from pymotion.utils.color import Color


def _make_clip(color: str = "#FF0000", duration: int = 30) -> ColorClip:
    clip = ColorClip(color=Color.parse(color))
    clip.start = 0
    clip.end = duration
    return clip


def _ctx(local_frame: int = 0, duration: int = 30) -> RenderContext:
    return RenderContext(
        frame=local_frame,
        fps=30,
        resolution=Resolution(width=64, height=64),
        time_range=TimeRange(start=0, end=duration),
        local_frame=local_frame,
        progress=local_frame / max(duration - 1, 1),
    )


class TestProxyClip:
    """Tests for ProxyClip rendering."""

    def test_render_missing_source(self) -> None:
        proxy = ProxyClip()
        proxy.source = Path("/nonexistent/proxy.file")
        proxy._width = 64
        proxy._height = 64
        proxy._frame_count = 10
        frame = proxy.render_frame(_ctx(local_frame=0, duration=10))
        assert frame.shape == (64, 64, 4)
        assert np.all(frame == 0)

    def test_render_from_file(self, tmp_path: Path) -> None:
        w, h, n = 32, 32, 5
        frames = np.random.randint(0, 255, (n, h, w, 4), dtype=np.uint8)
        proxy_file = tmp_path / "test.proxy"
        with open(proxy_file, "wb") as f:
            for i in range(n):
                f.write(frames[i].tobytes())

        proxy = ProxyClip()
        proxy.source = proxy_file
        proxy._width = w
        proxy._height = h
        proxy._frame_count = n

        ctx = RenderContext(
            frame=2,
            fps=30,
            resolution=Resolution(width=w, height=h),
            time_range=TimeRange(start=0, end=n),
            local_frame=2,
            progress=2 / (n - 1),
        )
        result = proxy.render_frame(ctx)
        assert result.shape == (h, w, 4)
        np.testing.assert_array_equal(result, frames[2])

    def test_render_scales_up(self, tmp_path: Path) -> None:
        w, h, n = 16, 16, 3
        frames = np.random.randint(0, 255, (n, h, w, 4), dtype=np.uint8)
        proxy_file = tmp_path / "test.proxy"
        with open(proxy_file, "wb") as f:
            for i in range(n):
                f.write(frames[i].tobytes())

        proxy = ProxyClip()
        proxy.source = proxy_file
        proxy._width = w
        proxy._height = h
        proxy._frame_count = n

        ctx = RenderContext(
            frame=0,
            fps=30,
            resolution=Resolution(width=64, height=64),
            time_range=TimeRange(start=0, end=n),
            local_frame=0,
            progress=0.0,
        )
        result = proxy.render_frame(ctx)
        assert result.shape == (64, 64, 4)

    def test_render_clamps_frame_index(self, tmp_path: Path) -> None:
        w, h, n = 8, 8, 2
        frames = np.random.randint(0, 255, (n, h, w, 4), dtype=np.uint8)
        proxy_file = tmp_path / "test.proxy"
        with open(proxy_file, "wb") as f:
            for i in range(n):
                f.write(frames[i].tobytes())

        proxy = ProxyClip()
        proxy.source = proxy_file
        proxy._width = w
        proxy._height = h
        proxy._frame_count = n

        ctx = RenderContext(
            frame=10,
            fps=30,
            resolution=Resolution(width=w, height=h),
            time_range=TimeRange(start=0, end=n),
            local_frame=10,
            progress=1.0,
        )
        result = proxy.render_frame(ctx)
        # Should clamp to last frame
        np.testing.assert_array_equal(result, frames[n - 1])


class TestCreateProxy:
    """Tests for create_proxy()."""

    def test_basic_creation(self, tmp_path: Path) -> None:
        clip = _make_clip(duration=5)
        proxy = create_proxy(clip, scale=0.5, cache_dir=tmp_path)
        assert isinstance(proxy, ProxyClip)
        assert proxy.source.exists()
        assert proxy._frame_count == 5
        assert proxy.duration == 5

    def test_cache_reuse(self, tmp_path: Path) -> None:
        clip = _make_clip(duration=3)
        p1 = create_proxy(clip, scale=0.25, cache_dir=tmp_path)
        p2 = create_proxy(clip, scale=0.25, cache_dir=tmp_path)
        assert p1.source == p2.source

    def test_invalid_scale_zero(self, tmp_path: Path) -> None:
        clip = _make_clip(duration=5)
        with pytest.raises(ValueError, match="scale"):
            create_proxy(clip, scale=0.0, cache_dir=tmp_path)

    def test_invalid_scale_negative(self, tmp_path: Path) -> None:
        clip = _make_clip(duration=5)
        with pytest.raises(ValueError, match="scale"):
            create_proxy(clip, scale=-0.5, cache_dir=tmp_path)

    def test_invalid_scale_over_one(self, tmp_path: Path) -> None:
        clip = _make_clip(duration=5)
        with pytest.raises(ValueError, match="scale"):
            create_proxy(clip, scale=1.5, cache_dir=tmp_path)

    def test_scale_one_valid(self, tmp_path: Path) -> None:
        clip = _make_clip(duration=3)
        proxy = create_proxy(clip, scale=1.0, cache_dir=tmp_path)
        assert isinstance(proxy, ProxyClip)

    def test_zero_duration_clip(self, tmp_path: Path) -> None:
        clip = _make_clip(duration=0)
        with pytest.raises(ValueError, match="zero duration"):
            create_proxy(clip, cache_dir=tmp_path)

    def test_proxy_renders_correctly(self, tmp_path: Path) -> None:
        clip = _make_clip(color="#00FF00", duration=3)
        proxy = create_proxy(clip, scale=0.5, cache_dir=tmp_path)
        ctx = RenderContext(
            frame=0,
            fps=30,
            resolution=Resolution(width=proxy._width, height=proxy._height),
            time_range=TimeRange(start=0, end=3),
            local_frame=0,
            progress=0.0,
        )
        frame = proxy.render_frame(ctx)
        assert frame.shape[2] == 4
        assert frame.dtype == np.uint8

    def test_creates_cache_dir(self, tmp_path: Path) -> None:
        cache = tmp_path / "nested" / "proxy_cache"
        clip = _make_clip(duration=2)
        create_proxy(clip, cache_dir=cache)
        assert cache.exists()


class TestClearProxyCache:
    """Tests for clear_proxy_cache()."""

    def test_clear_empty_dir(self, tmp_path: Path) -> None:
        removed = clear_proxy_cache(cache_dir=tmp_path)
        assert removed == 0

    def test_clear_nonexistent_dir(self, tmp_path: Path) -> None:
        removed = clear_proxy_cache(cache_dir=tmp_path / "nope")
        assert removed == 0

    def test_clear_old_files(self, tmp_path: Path) -> None:
        # Create a proxy file with old mtime
        old_file = tmp_path / "old.proxy"
        old_file.write_bytes(b"\x00" * 100)
        old_mtime = time.time() - (60 * 86400)  # 60 days ago
        import os

        os.utime(old_file, (old_mtime, old_mtime))

        removed = clear_proxy_cache(older_than_days=30, cache_dir=tmp_path)
        assert removed == 1
        assert not old_file.exists()

    def test_keeps_recent_files(self, tmp_path: Path) -> None:
        recent = tmp_path / "recent.proxy"
        recent.write_bytes(b"\x00" * 100)
        removed = clear_proxy_cache(older_than_days=30, cache_dir=tmp_path)
        assert removed == 0
        assert recent.exists()

    def test_ignores_non_proxy_files(self, tmp_path: Path) -> None:
        other = tmp_path / "data.txt"
        other.write_bytes(b"hello")
        old_mtime = time.time() - (60 * 86400)
        import os

        os.utime(other, (old_mtime, old_mtime))

        removed = clear_proxy_cache(older_than_days=30, cache_dir=tmp_path)
        assert removed == 0
        assert other.exists()


class TestProxyCacheSize:
    """Tests for proxy_cache_size()."""

    def test_empty_cache(self, tmp_path: Path) -> None:
        size = proxy_cache_size(cache_dir=tmp_path)
        assert size == 0

    def test_nonexistent_dir(self, tmp_path: Path) -> None:
        size = proxy_cache_size(cache_dir=tmp_path / "nope")
        assert size == 0

    def test_counts_proxy_files(self, tmp_path: Path) -> None:
        (tmp_path / "a.proxy").write_bytes(b"\x00" * 100)
        (tmp_path / "b.proxy").write_bytes(b"\x00" * 200)
        (tmp_path / "c.txt").write_bytes(b"\x00" * 999)
        size = proxy_cache_size(cache_dir=tmp_path)
        assert size == 300


class TestResizeNearest:
    """Tests for _resize_nearest helper."""

    def test_identity(self) -> None:
        frame = np.random.randint(0, 255, (10, 10, 4), dtype=np.uint8)
        result = _resize_nearest(frame, 10, 10)
        np.testing.assert_array_equal(result, frame)

    def test_upscale(self) -> None:
        frame = np.random.randint(0, 255, (4, 4, 4), dtype=np.uint8)
        result = _resize_nearest(frame, 8, 8)
        assert result.shape == (8, 8, 4)

    def test_downscale(self) -> None:
        frame = np.random.randint(0, 255, (16, 16, 4), dtype=np.uint8)
        result = _resize_nearest(frame, 4, 4)
        assert result.shape == (4, 4, 4)


class TestClipCreateProxy:
    """Tests for Clip.create_proxy() convenience method."""

    def test_create_proxy_method(self, tmp_path: Path) -> None:
        clip = _make_clip(duration=5)
        proxy = clip.create_proxy(scale=0.5, cache_dir=tmp_path)
        assert isinstance(proxy, ProxyClip)
        assert proxy.duration == 5
