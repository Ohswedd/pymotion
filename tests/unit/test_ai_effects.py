"""Tests for AI-powered visual effects."""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pytest

from pymotion.clip.base import RenderContext, Resolution, TimeRange
from pymotion.effects.ai import RemoveBackground, ReplaceBackground


def _make_frame(h: int = 100, w: int = 100) -> np.ndarray:
    """Create a solid BGRA test frame."""
    frame = np.zeros((h, w, 4), dtype=np.uint8)
    frame[:, :, 0] = 50  # B
    frame[:, :, 1] = 100  # G
    frame[:, :, 2] = 150  # R
    frame[:, :, 3] = 255  # A
    return frame


def _make_ctx(frame: int = 0) -> RenderContext:
    """Create a minimal RenderContext."""
    return RenderContext(
        frame=frame,
        fps=30,
        resolution=Resolution(100, 100),
        time_range=TimeRange(0, 60),
        local_frame=frame,
        progress=0.0,
    )


class TestRemoveBackgroundInit:
    """Tests for RemoveBackground initialization."""

    def test_default_params(self) -> None:
        effect = RemoveBackground()
        assert effect.model == "u2net"
        assert effect.alpha_matting is False
        assert effect.foreground_threshold == 240
        assert effect.background_threshold == 10

    def test_custom_model(self) -> None:
        effect = RemoveBackground(model="isnet-general-use")
        assert effect.model == "isnet-general-use"

    def test_alpha_matting_enabled(self) -> None:
        effect = RemoveBackground(alpha_matting=True, foreground_threshold=200)
        assert effect.alpha_matting is True
        assert effect.foreground_threshold == 200

    def test_empty_model_raises(self) -> None:
        with pytest.raises(ValueError, match="model name must not be empty"):
            RemoveBackground(model="")

    def test_invalid_foreground_threshold_raises(self) -> None:
        with pytest.raises(ValueError, match="foreground_threshold must be 0–255"):
            RemoveBackground(foreground_threshold=300)

    def test_invalid_background_threshold_raises(self) -> None:
        with pytest.raises(ValueError, match="background_threshold must be 0–255"):
            RemoveBackground(background_threshold=-1)

    def test_boundary_thresholds(self) -> None:
        """Edge values 0 and 255 should be valid."""
        effect = RemoveBackground(foreground_threshold=0, background_threshold=255)
        assert effect.foreground_threshold == 0
        assert effect.background_threshold == 255


class TestRemoveBackgroundApply:
    """Tests for RemoveBackground.apply with mocked rembg."""

    def test_apply_converts_bgra_to_rgba_and_back(self) -> None:
        """Verify BGRA → RGBA conversion for rembg, and RGBA → BGRA on return."""
        import sys

        frame = _make_frame()
        ctx = _make_ctx()

        # Mock rembg.remove to return the input unchanged (identity)
        mock_remove = MagicMock(side_effect=lambda img, **kw: img.copy())
        mock_session = MagicMock()

        rembg_mock = MagicMock()
        rembg_mock.remove = mock_remove
        rembg_mock.new_session = MagicMock(return_value=mock_session)

        effect = RemoveBackground()

        try:
            sys.modules["rembg"] = rembg_mock
            result = effect.apply(frame, ctx)

            # Since mock returns input unchanged, BGRA→RGBA→BGRA is identity
            np.testing.assert_array_equal(result[:, :, 0], frame[:, :, 0])  # B
            np.testing.assert_array_equal(result[:, :, 1], frame[:, :, 1])  # G
            np.testing.assert_array_equal(result[:, :, 2], frame[:, :, 2])  # R
            np.testing.assert_array_equal(result[:, :, 3], frame[:, :, 3])  # A

            # Verify rembg.remove was called with RGBA input
            call_args = mock_remove.call_args
            rgba_input = call_args[0][0]
            # R channel of RGBA should equal R channel (idx 2) of BGRA frame
            np.testing.assert_array_equal(rgba_input[:, :, 0], frame[:, :, 2])  # R
            np.testing.assert_array_equal(rgba_input[:, :, 2], frame[:, :, 0])  # B
        finally:
            if "rembg" in sys.modules:
                del sys.modules["rembg"]

    def test_apply_passes_session_and_params(self) -> None:
        """Verify session and alpha matting params are passed to rembg.remove."""
        import sys

        frame = _make_frame(50, 50)
        ctx = _make_ctx()

        mock_remove = MagicMock(side_effect=lambda img, **kw: img.copy())
        mock_session = MagicMock()

        rembg_mock = MagicMock()
        rembg_mock.remove = mock_remove
        rembg_mock.new_session = MagicMock(return_value=mock_session)

        effect = RemoveBackground(
            alpha_matting=True,
            foreground_threshold=200,
            background_threshold=20,
        )

        try:
            sys.modules["rembg"] = rembg_mock
            effect.apply(frame, ctx)

            call_kwargs = mock_remove.call_args[1]
            assert call_kwargs["session"] is mock_session
            assert call_kwargs["alpha_matting"] is True
            assert call_kwargs["alpha_matting_foreground_threshold"] == 200
            assert call_kwargs["alpha_matting_background_threshold"] == 20
        finally:
            if "rembg" in sys.modules:
                del sys.modules["rembg"]

    def test_apply_with_alpha_mask_output(self) -> None:
        """Verify that rembg alpha output is correctly transferred to result."""
        import sys

        frame = _make_frame(50, 50)
        ctx = _make_ctx()

        def mock_remove_fn(img: np.ndarray, **kwargs: object) -> np.ndarray:
            """Return image with alpha set to half-transparent."""
            out = img.copy()
            out[:, :, 3] = 128  # Set alpha to 128
            return out

        rembg_mock = MagicMock()
        rembg_mock.remove = mock_remove_fn
        rembg_mock.new_session = MagicMock(return_value=MagicMock())

        effect = RemoveBackground()

        try:
            sys.modules["rembg"] = rembg_mock
            result = effect.apply(frame, ctx)

            # Alpha channel should be 128 (from mock)
            assert np.all(result[:, :, 3] == 128)
            # Color channels should be preserved (BGRA→RGBA→BGRA round-trip)
            np.testing.assert_array_equal(result[:, :, 0], frame[:, :, 0])
            np.testing.assert_array_equal(result[:, :, 1], frame[:, :, 1])
            np.testing.assert_array_equal(result[:, :, 2], frame[:, :, 2])
        finally:
            if "rembg" in sys.modules:
                del sys.modules["rembg"]

    def test_session_cached(self) -> None:
        """Verify that the rembg session is created once and reused."""
        import sys

        mock_session = MagicMock()
        rembg_mock = MagicMock()
        rembg_mock.new_session = MagicMock(return_value=mock_session)
        rembg_mock.remove = MagicMock(side_effect=lambda img, **kw: img.copy())

        effect = RemoveBackground()

        try:
            sys.modules["rembg"] = rembg_mock
            frame = _make_frame(20, 20)
            ctx = _make_ctx()

            effect.apply(frame, ctx)
            effect.apply(frame, ctx)

            # new_session should only be called once
            rembg_mock.new_session.assert_called_once_with("u2net")
        finally:
            if "rembg" in sys.modules:
                del sys.modules["rembg"]


class TestRemoveBackgroundImportError:
    """Tests for ImportError when rembg is not installed."""

    def test_apply_raises_import_error(self) -> None:
        """apply() should raise ImportError with install hint if rembg missing."""
        import sys

        # Make sure rembg is not importable
        original = sys.modules.get("rembg")
        sys.modules["rembg"] = None  # type: ignore[assignment]

        try:
            effect = RemoveBackground()
            frame = _make_frame(20, 20)
            ctx = _make_ctx()

            with pytest.raises(ImportError, match="rembg is required"):
                effect.apply(frame, ctx)
        finally:
            if original is not None:
                sys.modules["rembg"] = original
            else:
                sys.modules.pop("rembg", None)

    def test_get_session_raises_import_error(self) -> None:
        """_get_session() should raise ImportError with install hint."""
        import sys

        original = sys.modules.get("rembg")
        sys.modules["rembg"] = None  # type: ignore[assignment]

        try:
            effect = RemoveBackground()
            with pytest.raises(ImportError, match="pymotion-studio\\[ai\\]"):
                effect._get_session()
        finally:
            if original is not None:
                sys.modules["rembg"] = original
            else:
                sys.modules.pop("rembg", None)


class TestRemoveBackgroundPublicAPI:
    """Test that RemoveBackground is accessible from the public API."""

    def test_importable_from_pymotion(self) -> None:
        from pymotion import RemoveBackground as RemoveBg

        assert RemoveBg is RemoveBackground

    def test_is_effect_subclass(self) -> None:
        from pymotion.effects.base import Effect

        assert issubclass(RemoveBackground, Effect)

    def test_apply_method_exists(self) -> None:
        effect = RemoveBackground()
        assert hasattr(effect, "apply")
        assert callable(effect.apply)


def _make_mock_bg_clip(h: int = 100, w: int = 100) -> MagicMock:
    """Create a mock clip that returns a solid blue BGRA frame."""
    bg_frame = np.zeros((h, w, 4), dtype=np.uint8)
    bg_frame[:, :, 0] = 200  # B
    bg_frame[:, :, 1] = 100  # G
    bg_frame[:, :, 2] = 50  # R
    bg_frame[:, :, 3] = 255  # A
    mock_clip = MagicMock()
    mock_clip.render_frame = MagicMock(return_value=bg_frame)
    return mock_clip


class TestReplaceBackgroundInit:
    """Tests for ReplaceBackground initialization."""

    def test_default_params(self) -> None:
        bg = _make_mock_bg_clip()
        effect = ReplaceBackground(new_bg=bg)
        assert effect.model == "u2net"
        assert effect.alpha_matting is False
        assert effect.new_bg is bg

    def test_custom_model(self) -> None:
        bg = _make_mock_bg_clip()
        effect = ReplaceBackground(new_bg=bg, model="isnet-general-use")
        assert effect.model == "isnet-general-use"

    def test_internal_remove_bg_created(self) -> None:
        bg = _make_mock_bg_clip()
        effect = ReplaceBackground(
            new_bg=bg, model="isnet-general-use", alpha_matting=True, foreground_threshold=200
        )
        assert isinstance(effect._remove_bg, RemoveBackground)
        assert effect._remove_bg.model == "isnet-general-use"
        assert effect._remove_bg.alpha_matting is True
        assert effect._remove_bg.foreground_threshold == 200


class TestReplaceBackgroundApply:
    """Tests for ReplaceBackground.apply with mocked rembg."""

    def test_fully_opaque_foreground(self) -> None:
        """When rembg returns alpha=255, result should be the foreground."""
        import sys

        frame = _make_frame(50, 50)
        ctx = _make_ctx()
        bg = _make_mock_bg_clip(50, 50)

        # Mock rembg to return unchanged (alpha stays 255 = full foreground)
        rembg_mock = MagicMock()
        rembg_mock.remove = MagicMock(side_effect=lambda img, **kw: img.copy())
        rembg_mock.new_session = MagicMock(return_value=MagicMock())

        effect = ReplaceBackground(new_bg=bg)

        try:
            sys.modules["rembg"] = rembg_mock
            result = effect.apply(frame, ctx)

            # With alpha=255, composite should be very close to foreground
            # (±1 from integer rounding in alpha blend formula)
            assert np.max(np.abs(result[:, :, 0].astype(int) - frame[:, :, 0].astype(int))) <= 1
            assert np.max(np.abs(result[:, :, 1].astype(int) - frame[:, :, 1].astype(int))) <= 1
            assert np.max(np.abs(result[:, :, 2].astype(int) - frame[:, :, 2].astype(int))) <= 1
            # Result should be fully opaque
            assert np.all(result[:, :, 3] == 255)
        finally:
            sys.modules.pop("rembg", None)

    def test_fully_transparent_foreground(self) -> None:
        """When rembg returns alpha=0, result should be the background."""
        import sys

        frame = _make_frame(50, 50)
        ctx = _make_ctx()
        bg_clip = _make_mock_bg_clip(50, 50)
        bg_frame = bg_clip.render_frame(ctx)

        def mock_remove_fn(img: np.ndarray, **kwargs: object) -> np.ndarray:
            out = img.copy()
            out[:, :, 3] = 0  # Fully transparent
            return out

        rembg_mock = MagicMock()
        rembg_mock.remove = mock_remove_fn
        rembg_mock.new_session = MagicMock(return_value=MagicMock())

        effect = ReplaceBackground(new_bg=bg_clip)

        try:
            sys.modules["rembg"] = rembg_mock
            result = effect.apply(frame, ctx)

            # With alpha=0, composite should be very close to background
            assert np.max(np.abs(result[:, :, 0].astype(int) - bg_frame[:, :, 0].astype(int))) <= 1
            assert np.max(np.abs(result[:, :, 1].astype(int) - bg_frame[:, :, 1].astype(int))) <= 1
            assert np.max(np.abs(result[:, :, 2].astype(int) - bg_frame[:, :, 2].astype(int))) <= 1
        finally:
            sys.modules.pop("rembg", None)

    def test_half_transparent_blending(self) -> None:
        """When alpha=128, result should be roughly 50/50 blend."""
        import sys

        fg_frame = np.zeros((10, 10, 4), dtype=np.uint8)
        fg_frame[:, :, 0] = 0  # B
        fg_frame[:, :, 1] = 0  # G
        fg_frame[:, :, 2] = 200  # R
        fg_frame[:, :, 3] = 255  # A

        ctx = _make_ctx()
        bg_clip = MagicMock()
        bg_frame = np.zeros((10, 10, 4), dtype=np.uint8)
        bg_frame[:, :, 0] = 200  # B
        bg_frame[:, :, 1] = 0  # G
        bg_frame[:, :, 2] = 0  # R
        bg_frame[:, :, 3] = 255  # A
        bg_clip.render_frame = MagicMock(return_value=bg_frame)

        def mock_remove_fn(img: np.ndarray, **kwargs: object) -> np.ndarray:
            out = img.copy()
            out[:, :, 3] = 128
            return out

        rembg_mock = MagicMock()
        rembg_mock.remove = mock_remove_fn
        rembg_mock.new_session = MagicMock(return_value=MagicMock())

        effect = ReplaceBackground(new_bg=bg_clip)

        try:
            sys.modules["rembg"] = rembg_mock
            result = effect.apply(fg_frame, ctx)

            # B channel: fg=0, bg=200, alpha=128 → ~100
            assert 90 <= result[0, 0, 0] <= 110
            # R channel: fg=200, bg=0, alpha=128 → ~100
            assert 90 <= result[0, 0, 2] <= 110
        finally:
            sys.modules.pop("rembg", None)

    def test_bg_render_frame_called_with_ctx(self) -> None:
        """Verify new_bg.render_frame is called with the same ctx."""
        import sys

        frame = _make_frame(50, 50)
        ctx = _make_ctx(frame=5)
        bg = _make_mock_bg_clip(50, 50)

        rembg_mock = MagicMock()
        rembg_mock.remove = MagicMock(side_effect=lambda img, **kw: img.copy())
        rembg_mock.new_session = MagicMock(return_value=MagicMock())

        effect = ReplaceBackground(new_bg=bg)

        try:
            sys.modules["rembg"] = rembg_mock
            effect.apply(frame, ctx)
            bg.render_frame.assert_called_once_with(ctx)
        finally:
            sys.modules.pop("rembg", None)


class TestReplaceBackgroundPublicAPI:
    """Test that ReplaceBackground is accessible from the public API."""

    def test_importable_from_pymotion(self) -> None:
        from pymotion import ReplaceBackground as ReplaceBg

        assert ReplaceBg is ReplaceBackground

    def test_is_effect_subclass(self) -> None:
        from pymotion.effects.base import Effect

        assert issubclass(ReplaceBackground, Effect)
