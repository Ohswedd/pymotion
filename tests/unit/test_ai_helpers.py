"""Tests for AI-powered smart editing helpers."""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pytest

from pymotion.ai import (
    AutoColor,
    AutoEdit,
    ContentAwareCrop,
    FaceBlur,
    FaceDetector,
    FaceTracker,
    HighlightDetector,
    MusicGeneration,
    SceneDetector,
    SilenceRemover,
    SoundFXGeneration,
    VoiceConversion,
)
from pymotion.clip.base import RenderContext


def _make_mock_clip(
    duration: int = 60, width: int = 100, height: int = 100, fps: int = 30
) -> MagicMock:
    """Create a mock clip with configurable properties."""
    clip = MagicMock()
    clip.start = 0
    clip.end = duration
    clip.width = width
    clip.height = height
    clip.fps = fps

    # Default: return random frames
    def render_frame(ctx: RenderContext) -> np.ndarray:
        rng = np.random.default_rng(ctx.frame)
        return rng.integers(0, 256, (height, width, 4), dtype=np.uint8)

    clip.render_frame = MagicMock(side_effect=render_frame)
    return clip


def _make_uniform_clip(
    duration: int = 60, width: int = 50, height: int = 50, value: int = 128
) -> MagicMock:
    """Create a mock clip that returns uniform frames."""
    clip = MagicMock()
    clip.start = 0
    clip.end = duration
    clip.width = width
    clip.height = height
    clip.fps = 30

    frame = np.full((height, width, 4), value, dtype=np.uint8)

    clip.render_frame = MagicMock(return_value=frame)
    return clip


# ============================================================
# SceneDetector
# ============================================================


class TestSceneDetectorInit:
    """Tests for SceneDetector initialization."""

    def test_defaults(self) -> None:
        clip = _make_mock_clip()
        sd = SceneDetector(clip=clip)
        assert sd.threshold == 0.3
        assert sd.min_scene_length == 15

    def test_invalid_threshold(self) -> None:
        with pytest.raises(ValueError, match="threshold must be between"):
            SceneDetector(clip=MagicMock(), threshold=1.5)

    def test_invalid_min_scene_length(self) -> None:
        with pytest.raises(ValueError, match="min_scene_length must be >= 1"):
            SceneDetector(clip=MagicMock(), min_scene_length=0)


class TestSceneDetectorDetect:
    """Tests for SceneDetector.detect."""

    def test_always_includes_frame_zero(self) -> None:
        clip = _make_uniform_clip(duration=10)
        sd = SceneDetector(clip=clip, threshold=0.5)
        result = sd.detect()
        assert result[0] == 0

    def test_uniform_clip_has_no_extra_boundaries(self) -> None:
        clip = _make_uniform_clip(duration=30)
        sd = SceneDetector(clip=clip, threshold=0.1)
        result = sd.detect()
        assert result == [0]

    def test_single_frame_clip(self) -> None:
        clip = _make_uniform_clip(duration=1)
        sd = SceneDetector(clip=clip)
        assert sd.detect() == [0]

    def test_detects_scene_change(self) -> None:
        """Clip with abrupt change should detect a boundary."""
        clip = MagicMock()
        clip.start = 0
        clip.end = 30
        clip.width = 20
        clip.height = 20
        clip.fps = 30

        def render(ctx: RenderContext) -> np.ndarray:
            if ctx.frame < 15:
                return np.zeros((20, 20, 4), dtype=np.uint8)
            return np.full((20, 20, 4), 255, dtype=np.uint8)

        clip.render_frame = MagicMock(side_effect=render)

        sd = SceneDetector(clip=clip, threshold=0.3, min_scene_length=1)
        result = sd.detect()
        assert 0 in result
        assert 15 in result


class TestSceneDetectorPublicAPI:
    """Test SceneDetector public API."""

    def test_importable(self) -> None:
        from pymotion import SceneDetector as SD  # noqa: N817

        assert SD is SceneDetector


# ============================================================
# SilenceRemover
# ============================================================


class TestSilenceRemoverInit:
    """Tests for SilenceRemover initialization."""

    def test_defaults(self) -> None:
        sr = SilenceRemover(clip=MagicMock())
        assert sr.threshold_db == -40.0
        assert sr.min_silence_sec == 0.5

    def test_invalid_threshold_db(self) -> None:
        with pytest.raises(ValueError, match="threshold_db must be <= 0"):
            SilenceRemover(clip=MagicMock(), threshold_db=5.0)

    def test_invalid_min_silence(self) -> None:
        with pytest.raises(ValueError, match="min_silence_sec must be > 0"):
            SilenceRemover(clip=MagicMock(), min_silence_sec=0)


class TestSilenceRemoverDetect:
    """Tests for SilenceRemover.detect_silence and remove."""

    def test_silent_clip_detected(self) -> None:
        clip = _make_uniform_clip(duration=60, value=0)
        sr = SilenceRemover(clip=clip, threshold_db=-20, min_silence_sec=0.1)
        silent = sr.detect_silence()
        assert len(silent) >= 1

    def test_remove_returns_active_segments(self) -> None:
        """Non-silent clip should have active segments."""
        clip = _make_mock_clip(duration=60)  # Random frames have high variance
        sr = SilenceRemover(clip=clip, threshold_db=-60, min_silence_sec=0.1)
        active = sr.remove()
        assert len(active) >= 1
        total = sum(e - s for s, e in active)
        assert total > 0


class TestSilenceRemoverPublicAPI:
    """Test SilenceRemover public API."""

    def test_importable(self) -> None:
        from pymotion import SilenceRemover as SR  # noqa: N817

        assert SR is SilenceRemover


# ============================================================
# HighlightDetector
# ============================================================


class TestHighlightDetectorInit:
    """Tests for HighlightDetector initialization."""

    def test_defaults(self) -> None:
        hd = HighlightDetector(clip=MagicMock())
        assert hd.criteria == "visual"
        assert hd.top_n == 5
        assert hd.segment_length == 90

    def test_invalid_criteria(self) -> None:
        with pytest.raises(ValueError, match="criteria must be one of"):
            HighlightDetector(clip=MagicMock(), criteria="invalid")

    def test_invalid_top_n(self) -> None:
        with pytest.raises(ValueError, match="top_n must be >= 1"):
            HighlightDetector(clip=MagicMock(), top_n=0)


class TestHighlightDetectorDetect:
    """Tests for HighlightDetector.detect."""

    def test_returns_segments(self) -> None:
        clip = _make_mock_clip(duration=120)
        hd = HighlightDetector(clip=clip, top_n=2, segment_length=30)
        highlights = hd.detect()
        assert len(highlights) <= 2
        for start, end in highlights:
            assert start < end

    def test_visual_criteria(self) -> None:
        clip = _make_mock_clip(duration=60)
        hd = HighlightDetector(clip=clip, criteria="visual", top_n=1, segment_length=20)
        highlights = hd.detect()
        assert len(highlights) >= 1

    def test_motion_criteria(self) -> None:
        clip = _make_mock_clip(duration=60)
        hd = HighlightDetector(clip=clip, criteria="motion", top_n=1, segment_length=20)
        highlights = hd.detect()
        assert len(highlights) >= 1


class TestHighlightDetectorPublicAPI:
    """Test HighlightDetector public API."""

    def test_importable(self) -> None:
        from pymotion import HighlightDetector as HD  # noqa: N817

        assert HD is HighlightDetector


# ============================================================
# ContentAwareCrop
# ============================================================


class TestContentAwareCropInit:
    """Tests for ContentAwareCrop initialization."""

    def test_defaults(self) -> None:
        cac = ContentAwareCrop(clip=MagicMock())
        assert cac.target_ratio == "9:16"
        assert cac.smoothing == 15

    def test_invalid_ratio_format(self) -> None:
        with pytest.raises(ValueError, match="must be 'W:H' format"):
            ContentAwareCrop(clip=MagicMock(), target_ratio="invalid")

    def test_invalid_ratio_values(self) -> None:
        with pytest.raises(ValueError, match="must contain integers"):
            ContentAwareCrop(clip=MagicMock(), target_ratio="a:b")

    def test_invalid_ratio_zero(self) -> None:
        with pytest.raises(ValueError, match="must be positive"):
            ContentAwareCrop(clip=MagicMock(), target_ratio="0:16")

    def test_invalid_smoothing(self) -> None:
        with pytest.raises(ValueError, match="smoothing must be >= 1"):
            ContentAwareCrop(clip=MagicMock(), smoothing=0)


class TestContentAwareCropAnalyze:
    """Tests for ContentAwareCrop.analyze."""

    def test_returns_crops_per_frame(self) -> None:
        clip = _make_mock_clip(duration=10, width=100, height=100)
        cac = ContentAwareCrop(clip=clip, target_ratio="9:16", smoothing=3)
        crops = cac.analyze()
        assert len(crops) == 10
        for x, y, w, h in crops:
            assert x >= 0
            assert y >= 0
            assert w > 0
            assert h > 0
            assert x + w <= 100
            assert y + h <= 100


class TestContentAwareCropPublicAPI:
    """Test ContentAwareCrop public API."""

    def test_importable(self) -> None:
        from pymotion import ContentAwareCrop as CAC  # noqa: N817

        assert CAC is ContentAwareCrop


# ============================================================
# AutoColor
# ============================================================


class TestAutoColorInit:
    """Tests for AutoColor initialization."""

    def test_defaults(self) -> None:
        ac = AutoColor(clip=MagicMock())
        assert ac.strength == 1.0

    def test_invalid_strength(self) -> None:
        with pytest.raises(ValueError, match="strength must be between"):
            AutoColor(clip=MagicMock(), strength=1.5)


class TestAutoColorAnalyze:
    """Tests for AutoColor.analyze."""

    def test_returns_correction_dict(self) -> None:
        clip = _make_mock_clip(duration=10)
        ac = AutoColor(clip=clip)
        result = ac.analyze()
        assert "white_balance_r" in result
        assert "white_balance_b" in result
        assert "exposure" in result
        assert "contrast" in result

    def test_zero_duration_clip(self) -> None:
        clip = _make_uniform_clip(duration=0)
        ac = AutoColor(clip=clip)
        result = ac.analyze()
        assert result["contrast"] == 1.0


class TestAutoColorPublicAPI:
    """Test AutoColor public API."""

    def test_importable(self) -> None:
        from pymotion import AutoColor as AC  # noqa: N817

        assert AC is AutoColor


# ============================================================
# AutoEdit
# ============================================================


class TestAutoEditInit:
    """Tests for AutoEdit initialization."""

    def test_defaults(self) -> None:
        ae = AutoEdit(clips=[MagicMock()])
        assert ae.style == "fast"
        assert ae.target_duration == 900

    def test_invalid_style(self) -> None:
        with pytest.raises(ValueError, match="style must be one of"):
            AutoEdit(clips=[MagicMock()], style="invalid")

    def test_empty_clips_raises(self) -> None:
        with pytest.raises(ValueError, match="clips list must not be empty"):
            AutoEdit(clips=[])

    def test_invalid_duration(self) -> None:
        with pytest.raises(ValueError, match="target_duration must be >= 1"):
            AutoEdit(clips=[MagicMock()], target_duration=0)


class TestAutoEditEdit:
    """Tests for AutoEdit.edit."""

    def test_returns_edl(self) -> None:
        clip = _make_mock_clip(duration=120)
        ae = AutoEdit(clips=[clip], style="fast", target_duration=60)
        edl = ae.edit()
        assert isinstance(edl, list)
        for clip_idx, start, end in edl:
            assert clip_idx >= 0
            assert start < end

    def test_multiple_clips(self) -> None:
        clips = [_make_mock_clip(duration=60) for _ in range(3)]
        ae = AutoEdit(clips=clips, style="smooth", target_duration=90)
        edl = ae.edit()
        assert len(edl) >= 1


class TestAutoEditPublicAPI:
    """Test AutoEdit public API."""

    def test_importable(self) -> None:
        from pymotion import AutoEdit as AE  # noqa: N817

        assert AE is AutoEdit


# ============================================================
# 2.0.4 Face & Body
# ============================================================


class TestFaceDetectorInit:
    """Tests for FaceDetector initialization."""

    def test_defaults(self) -> None:
        fd = FaceDetector(clip=MagicMock())
        assert fd.method == "haar"
        assert fd.min_confidence == 0.5

    def test_invalid_method(self) -> None:
        with pytest.raises(ValueError, match="method must be one of"):
            FaceDetector(clip=MagicMock(), method="invalid")

    def test_invalid_confidence(self) -> None:
        with pytest.raises(ValueError, match="min_confidence must be between"):
            FaceDetector(clip=MagicMock(), min_confidence=1.5)


class TestFaceDetectorDetect:
    """Tests for FaceDetector.detect with mocked OpenCV."""

    def test_detect_returns_dict(self) -> None:
        import sys

        clip = _make_mock_clip(duration=5, width=50, height=50)

        cv2_mock = MagicMock()
        cv2_mock.data = MagicMock()
        cv2_mock.data.haarcascades = "/fake/path/"
        cascade_mock = MagicMock()
        cascade_mock.detectMultiScale = MagicMock(return_value=np.array([[10, 10, 20, 20]]))
        cv2_mock.CascadeClassifier = MagicMock(return_value=cascade_mock)
        cv2_mock.cvtColor = MagicMock(return_value=np.zeros((50, 50), dtype=np.uint8))
        cv2_mock.COLOR_BGR2GRAY = 6

        fd = FaceDetector(clip=clip)

        try:
            sys.modules["cv2"] = cv2_mock
            result = fd.detect()
            assert isinstance(result, dict)
            assert len(result) == 5
            for _frame_idx, faces in result.items():
                assert isinstance(faces, list)
                for x, _y, w, _h in faces:
                    assert x >= 0
                    assert w > 0
        finally:
            sys.modules.pop("cv2", None)

    def test_import_error(self) -> None:
        import sys

        sys.modules["cv2"] = None  # type: ignore[assignment]
        try:
            fd = FaceDetector(clip=_make_mock_clip(duration=1))
            with pytest.raises(ImportError, match="opencv-python"):
                fd.detect()
        finally:
            sys.modules.pop("cv2", None)


class TestFaceDetectorPublicAPI:
    """Test FaceDetector public API."""

    def test_importable(self) -> None:
        from pymotion import FaceDetector as FD  # noqa: N817

        assert FD is FaceDetector


class TestFaceTrackerInit:
    """Tests for FaceTracker initialization."""

    def test_defaults(self) -> None:
        ft = FaceTracker(clip=MagicMock())
        assert ft.max_distance == 100.0

    def test_invalid_max_distance(self) -> None:
        with pytest.raises(ValueError, match="max_distance must be > 0"):
            FaceTracker(clip=MagicMock(), max_distance=0)


class TestFaceTrackerTrack:
    """Tests for FaceTracker.track with mocked OpenCV."""

    def test_track_returns_dict(self) -> None:
        import sys

        clip = _make_mock_clip(duration=3, width=50, height=50)

        cv2_mock = MagicMock()
        cv2_mock.data = MagicMock()
        cv2_mock.data.haarcascades = "/fake/"
        cascade_mock = MagicMock()
        # Return one face at similar positions
        cascade_mock.detectMultiScale = MagicMock(return_value=np.array([[10, 10, 20, 20]]))
        cv2_mock.CascadeClassifier = MagicMock(return_value=cascade_mock)
        cv2_mock.cvtColor = MagicMock(return_value=np.zeros((50, 50), dtype=np.uint8))
        cv2_mock.COLOR_BGR2GRAY = 6

        ft = FaceTracker(clip=clip)

        try:
            sys.modules["cv2"] = cv2_mock
            tracks = ft.track()
            assert isinstance(tracks, dict)
            # Should have at least one track
            assert len(tracks) >= 1
        finally:
            sys.modules.pop("cv2", None)

    def test_to_keyframes(self) -> None:
        import sys

        clip = _make_mock_clip(duration=3, width=50, height=50)

        cv2_mock = MagicMock()
        cv2_mock.data = MagicMock()
        cv2_mock.data.haarcascades = "/fake/"
        cascade_mock = MagicMock()
        cascade_mock.detectMultiScale = MagicMock(return_value=np.array([[10, 10, 20, 20]]))
        cv2_mock.CascadeClassifier = MagicMock(return_value=cascade_mock)
        cv2_mock.cvtColor = MagicMock(return_value=np.zeros((50, 50), dtype=np.uint8))
        cv2_mock.COLOR_BGR2GRAY = 6

        ft = FaceTracker(clip=clip)

        try:
            sys.modules["cv2"] = cv2_mock
            kf = ft.to_keyframes(face_id=0)
            assert isinstance(kf, dict)
        finally:
            sys.modules.pop("cv2", None)

    def test_to_keyframes_missing_id_returns_empty(self) -> None:
        import sys

        clip = _make_mock_clip(duration=2, width=50, height=50)

        cv2_mock = MagicMock()
        cv2_mock.data = MagicMock()
        cv2_mock.data.haarcascades = "/fake/"
        cascade_mock = MagicMock()
        cascade_mock.detectMultiScale = MagicMock(return_value=np.array([]))
        cv2_mock.CascadeClassifier = MagicMock(return_value=cascade_mock)
        cv2_mock.cvtColor = MagicMock(return_value=np.zeros((50, 50), dtype=np.uint8))
        cv2_mock.COLOR_BGR2GRAY = 6

        ft = FaceTracker(clip=clip)

        try:
            sys.modules["cv2"] = cv2_mock
            kf = ft.to_keyframes(face_id=999)
            assert kf == {}
        finally:
            sys.modules.pop("cv2", None)


class TestFaceTrackerPublicAPI:
    """Test FaceTracker public API."""

    def test_importable(self) -> None:
        from pymotion import FaceTracker as FT  # noqa: N817

        assert FT is FaceTracker


class TestFaceBlurInit:
    """Tests for FaceBlur initialization."""

    def test_defaults(self) -> None:
        fb = FaceBlur(clip=MagicMock())
        assert fb.strength == 5
        assert fb.method == "haar"

    def test_invalid_strength(self) -> None:
        with pytest.raises(ValueError, match="strength must be between"):
            FaceBlur(clip=MagicMock(), strength=0)
        with pytest.raises(ValueError, match="strength must be between"):
            FaceBlur(clip=MagicMock(), strength=11)

    def test_invalid_method(self) -> None:
        with pytest.raises(ValueError, match="method must be one of"):
            FaceBlur(clip=MagicMock(), method="invalid")


class TestFaceBlurApply:
    """Tests for FaceBlur.apply_blur with mocked OpenCV."""

    def test_apply_blur_to_regions(self) -> None:
        import sys

        frame = np.full((50, 50, 4), 128, dtype=np.uint8)
        regions = [(10, 10, 20, 20)]

        cv2_mock = MagicMock()
        cv2_mock.GaussianBlur = MagicMock(return_value=np.zeros((20, 20, 3), dtype=np.uint8))

        fb = FaceBlur(clip=MagicMock())

        try:
            sys.modules["cv2"] = cv2_mock
            result = fb.apply_blur(frame, regions)
            assert result.shape == frame.shape
            cv2_mock.GaussianBlur.assert_called_once()
        finally:
            sys.modules.pop("cv2", None)

    def test_apply_blur_empty_regions(self) -> None:
        import sys

        frame = np.full((50, 50, 4), 128, dtype=np.uint8)
        cv2_mock = MagicMock()

        fb = FaceBlur(clip=MagicMock())

        try:
            sys.modules["cv2"] = cv2_mock
            result = fb.apply_blur(frame, [])
            np.testing.assert_array_equal(result, frame)
        finally:
            sys.modules.pop("cv2", None)

    def test_import_error(self) -> None:
        import sys

        sys.modules["cv2"] = None  # type: ignore[assignment]
        try:
            fb = FaceBlur(clip=MagicMock())
            frame = np.zeros((20, 20, 4), dtype=np.uint8)
            with pytest.raises(ImportError, match="opencv-python"):
                fb.apply_blur(frame, [(0, 0, 10, 10)])
        finally:
            sys.modules.pop("cv2", None)


class TestFaceBlurPublicAPI:
    """Test FaceBlur public API."""

    def test_importable(self) -> None:
        from pymotion import FaceBlur as FB  # noqa: N817

        assert FB is FaceBlur


# ============================================================
# 2.0.5 AI Voice & Audio
# ============================================================


class TestVoiceConversionInit:
    """Tests for VoiceConversion initialization."""

    def test_defaults(self) -> None:
        vc = VoiceConversion(clip=MagicMock(), target_voice_sample="voice.wav")
        assert vc.target_voice_sample == "voice.wav"
        assert vc.strength == 1.0

    def test_empty_sample_raises(self) -> None:
        with pytest.raises(ValueError, match="target_voice_sample must not be empty"):
            VoiceConversion(clip=MagicMock(), target_voice_sample="")

    def test_invalid_strength(self) -> None:
        with pytest.raises(ValueError, match="strength must be between"):
            VoiceConversion(clip=MagicMock(), target_voice_sample="v.wav", strength=1.5)


class TestVoiceConversionConvert:
    """Tests for VoiceConversion.convert."""

    def test_convert_returns_stereo_array(self) -> None:
        import sys

        torch_mock = MagicMock()
        vc = VoiceConversion(clip=MagicMock(), target_voice_sample="voice.wav")

        try:
            sys.modules["torch"] = torch_mock
            result = vc.convert()
            assert result.ndim == 2
            assert result.shape[1] == 2
            assert result.dtype == np.float64
        finally:
            sys.modules.pop("torch", None)

    def test_import_error(self) -> None:
        import sys

        sys.modules["torch"] = None  # type: ignore[assignment]
        try:
            vc = VoiceConversion(clip=MagicMock(), target_voice_sample="v.wav")
            with pytest.raises(ImportError, match="torch"):
                vc.convert()
        finally:
            sys.modules.pop("torch", None)


class TestVoiceConversionPublicAPI:
    """Test VoiceConversion public API."""

    def test_importable(self) -> None:
        from pymotion import VoiceConversion as VC  # noqa: N817

        assert VC is VoiceConversion


class TestMusicGenerationInit:
    """Tests for MusicGeneration initialization."""

    def test_defaults(self) -> None:
        mg = MusicGeneration(prompt="upbeat")
        assert mg.duration == 10.0
        assert mg.tempo == 120
        assert mg.sample_rate == 48000

    def test_empty_prompt_raises(self) -> None:
        with pytest.raises(ValueError, match="prompt must not be empty"):
            MusicGeneration(prompt="")

    def test_invalid_duration(self) -> None:
        with pytest.raises(ValueError, match="duration must be > 0"):
            MusicGeneration(prompt="test", duration=0)

    def test_invalid_tempo(self) -> None:
        with pytest.raises(ValueError, match="tempo must be between"):
            MusicGeneration(prompt="test", tempo=10)

    def test_invalid_sample_rate(self) -> None:
        with pytest.raises(ValueError, match="sample_rate must be >= 8000"):
            MusicGeneration(prompt="test", sample_rate=100)


class TestMusicGenerationGenerate:
    """Tests for MusicGeneration.generate."""

    def test_import_error_torch(self) -> None:
        import sys

        sys.modules["torch"] = None  # type: ignore[assignment]
        try:
            mg = MusicGeneration(prompt="test")
            with pytest.raises(ImportError, match="torch"):
                mg.generate()
        finally:
            sys.modules.pop("torch", None)

    def test_import_error_transformers(self) -> None:
        import sys

        torch_mock = MagicMock()
        sys.modules["torch"] = torch_mock
        sys.modules["transformers"] = None  # type: ignore[assignment]

        try:
            mg = MusicGeneration(prompt="test")
            with pytest.raises(ImportError, match="transformers"):
                mg.generate()
        finally:
            sys.modules.pop("torch", None)
            sys.modules.pop("transformers", None)


class TestMusicGenerationPublicAPI:
    """Test MusicGeneration public API."""

    def test_importable(self) -> None:
        from pymotion import MusicGeneration as MG  # noqa: N817

        assert MG is MusicGeneration


class TestSoundFXGenerationInit:
    """Tests for SoundFXGeneration initialization."""

    def test_defaults(self) -> None:
        sfx = SoundFXGeneration(description="thunder")
        assert sfx.duration == 2.0
        assert sfx.sample_rate == 48000

    def test_empty_description_raises(self) -> None:
        with pytest.raises(ValueError, match="description must not be empty"):
            SoundFXGeneration(description="")

    def test_invalid_duration(self) -> None:
        with pytest.raises(ValueError, match="duration must be > 0"):
            SoundFXGeneration(description="test", duration=0)

    def test_invalid_sample_rate(self) -> None:
        with pytest.raises(ValueError, match="sample_rate must be >= 8000"):
            SoundFXGeneration(description="test", sample_rate=100)


class TestSoundFXGenerationGenerate:
    """Tests for SoundFXGeneration.generate."""

    def test_generate_returns_stereo(self) -> None:
        import sys

        torch_mock = MagicMock()

        sfx = SoundFXGeneration(description="thunder", duration=1.0)

        try:
            sys.modules["torch"] = torch_mock
            result = sfx.generate()
            assert result.ndim == 2
            assert result.shape[1] == 2
            assert result.dtype == np.float64
            # Should be ~48000 samples for 1 second
            assert result.shape[0] == 48000
        finally:
            sys.modules.pop("torch", None)

    def test_import_error(self) -> None:
        import sys

        sys.modules["torch"] = None  # type: ignore[assignment]
        try:
            sfx = SoundFXGeneration(description="test")
            with pytest.raises(ImportError, match="torch"):
                sfx.generate()
        finally:
            sys.modules.pop("torch", None)

    def test_deterministic_output(self) -> None:
        """Same description should produce same output."""
        import sys

        sys.modules["torch"] = MagicMock()
        try:
            sfx1 = SoundFXGeneration(description="rain", duration=0.5)
            sfx2 = SoundFXGeneration(description="rain", duration=0.5)
            r1 = sfx1.generate()
            r2 = sfx2.generate()
            np.testing.assert_array_equal(r1, r2)
        finally:
            sys.modules.pop("torch", None)


class TestSoundFXGenerationPublicAPI:
    """Test SoundFXGeneration public API."""

    def test_importable(self) -> None:
        from pymotion import SoundFXGeneration as SoundFX  # noqa: N817

        assert SoundFX is SoundFXGeneration
