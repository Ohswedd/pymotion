"""Tests for distributed rendering and checkpoint system."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pymotion.render.distributed import (
    RenderCheckpoint,
    _chunk_frames,
    render_frames_dask,
    render_frames_ray,
)


class TestChunkFrames:
    """Tests for frame range chunking."""

    def test_even_split(self) -> None:
        chunks = _chunk_frames(0, 30, 10)
        assert chunks == [(0, 10), (10, 20), (20, 30)]

    def test_uneven_split(self) -> None:
        chunks = _chunk_frames(0, 25, 10)
        assert chunks == [(0, 10), (10, 20), (20, 25)]

    def test_single_chunk(self) -> None:
        chunks = _chunk_frames(0, 5, 30)
        assert chunks == [(0, 5)]

    def test_start_offset(self) -> None:
        chunks = _chunk_frames(10, 40, 15)
        assert chunks == [(10, 25), (25, 40)]

    def test_empty_range(self) -> None:
        chunks = _chunk_frames(5, 5, 10)
        assert chunks == []


class TestRenderCheckpoint:
    """Tests for checkpoint save/load/resume."""

    def test_mark_and_check(self, tmp_path: Path) -> None:
        cp = RenderCheckpoint(tmp_path / "cp.json")
        assert not cp.is_completed(0)
        cp.mark_completed(0)
        assert cp.is_completed(0)
        assert not cp.is_completed(1)

    def test_save_and_load(self, tmp_path: Path) -> None:
        path = tmp_path / "cp.json"
        cp = RenderCheckpoint(path)
        cp.mark_completed(0)
        cp.mark_completed(5)
        cp.mark_completed(10)
        cp.save()

        cp2 = RenderCheckpoint(path)
        assert cp2.is_completed(0)
        assert cp2.is_completed(5)
        assert cp2.is_completed(10)
        assert not cp2.is_completed(3)

    def test_last_completed(self, tmp_path: Path) -> None:
        cp = RenderCheckpoint(tmp_path / "cp.json")
        assert cp.last_completed is None
        cp.mark_completed(5)
        cp.mark_completed(3)
        assert cp.last_completed == 5

    def test_pending_frames(self, tmp_path: Path) -> None:
        cp = RenderCheckpoint(tmp_path / "cp.json")
        cp.mark_completed(1)
        cp.mark_completed(3)
        pending = cp.pending_frames(0, 5)
        assert pending == [0, 2, 4]

    def test_clear(self, tmp_path: Path) -> None:
        path = tmp_path / "cp.json"
        cp = RenderCheckpoint(path)
        cp.mark_completed(0)
        cp.save()
        assert path.exists()
        cp.clear()
        assert not path.exists()
        assert cp.last_completed is None

    def test_load_corrupt_file(self, tmp_path: Path) -> None:
        path = tmp_path / "cp.json"
        path.write_text("not valid json{{{")
        cp = RenderCheckpoint(path)
        assert cp.last_completed is None

    def test_checkpoint_json_format(self, tmp_path: Path) -> None:
        path = tmp_path / "cp.json"
        cp = RenderCheckpoint(path)
        cp.mark_completed(2)
        cp.mark_completed(0)
        cp.mark_completed(1)
        cp.save()
        data = json.loads(path.read_text())
        assert data["completed_frames"] == [0, 1, 2]  # Sorted


class TestRayBackend:
    """Tests for Ray distributed rendering (import check only)."""

    def test_ray_raises_import_error(self) -> None:
        """Without ray installed, render_frames_ray raises ImportError."""
        try:
            import ray  # noqa: F401

            pytest.skip("Ray is installed, skipping import error test")
        except ImportError:
            pass

        from unittest.mock import MagicMock

        comp = MagicMock()
        with pytest.raises(ImportError, match="Ray is required"):
            list(render_frames_ray(comp, 0, 10))


class TestDaskBackend:
    """Tests for Dask distributed rendering (import check only)."""

    def test_dask_raises_import_error(self) -> None:
        """Without dask installed, render_frames_dask raises ImportError."""
        try:
            import dask  # noqa: F401

            pytest.skip("Dask is installed, skipping import error test")
        except ImportError:
            pass

        from unittest.mock import MagicMock

        comp = MagicMock()
        with pytest.raises(ImportError, match="Dask is required"):
            list(render_frames_dask(comp, 0, 10))


class TestCompositionBackendParam:
    """Tests for Composition.render() backend parameter."""

    def test_render_accepts_backend_param(self) -> None:
        """Composition.render() signature includes backend parameter."""
        from pymotion.composition import Composition

        comp = Composition(64, 64, fps=30, duration=5)
        # Verify the method signature accepts the parameter
        import inspect

        sig = inspect.signature(comp.render)
        assert "backend" in sig.parameters
        assert sig.parameters["backend"].default == "local"

    def test_render_accepts_checkpoint_path(self) -> None:
        from pymotion.composition import Composition

        comp = Composition(64, 64, fps=30, duration=5)
        import inspect

        sig = inspect.signature(comp.render)
        assert "checkpoint_path" in sig.parameters

    def test_render_accepts_profile(self) -> None:
        from pymotion.composition import Composition

        comp = Composition(64, 64, fps=30, duration=5)
        import inspect

        sig = inspect.signature(comp.render)
        assert "profile" in sig.parameters
        assert sig.parameters["profile"].default is False
