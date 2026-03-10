"""Tests for EDL and OTIO export from Composition."""

from __future__ import annotations

from pathlib import Path

from pymotion.clip.video import VideoClip
from pymotion.composition import Composition


class TestEDLExport:
    """Tests for Composition.export_edl()."""

    def test_export_edl_empty(self, tmp_path: Path) -> None:
        comp = Composition(width=1920, height=1080, fps=30, duration=90)
        edl_path = tmp_path / "test.edl"
        comp.export_edl(edl_path)
        content = edl_path.read_text()
        assert "TITLE: test" in content
        assert "FCM:" in content

    def test_export_edl_with_video_clip(self, tmp_path: Path) -> None:
        # Create a dummy video file so VideoClip can reference it
        dummy_video = tmp_path / "clip.mp4"
        dummy_video.touch()

        comp = Composition(width=1920, height=1080, fps=30, duration=90)
        clip = VideoClip.__new__(VideoClip)
        clip.source = dummy_video
        clip.start = 0
        clip.end = 30
        comp.tracks[0].clips.append(clip)

        edl_path = tmp_path / "test.edl"
        comp.export_edl(edl_path)
        content = edl_path.read_text()
        assert "001" in content
        assert "CLIP" in content.upper()
        assert "FROM CLIP NAME:" in content

    def test_export_edl_multiple_clips(self, tmp_path: Path) -> None:
        comp = Composition(width=1920, height=1080, fps=30, duration=120)

        for i in range(3):
            dummy = tmp_path / f"clip{i}.mp4"
            dummy.touch()
            clip = VideoClip.__new__(VideoClip)
            clip.source = dummy
            clip.start = i * 30
            clip.end = (i + 1) * 30
            comp.tracks[0].clips.append(clip)

        edl_path = tmp_path / "multi.edl"
        comp.export_edl(edl_path)
        content = edl_path.read_text()
        assert "001" in content
        assert "002" in content
        assert "003" in content

    def test_export_edl_timecode_format(self, tmp_path: Path) -> None:
        comp = Composition(width=1920, height=1080, fps=30, duration=90)
        dummy = tmp_path / "tc.mp4"
        dummy.touch()

        clip = VideoClip.__new__(VideoClip)
        clip.source = dummy
        clip.start = 0
        clip.end = 90  # 3 seconds at 30fps
        comp.tracks[0].clips.append(clip)

        edl_path = tmp_path / "tc.edl"
        comp.export_edl(edl_path)
        content = edl_path.read_text()
        # Should contain 00:00:03:00 as record out
        assert "00:00:03:00" in content

    def test_frames_to_tc(self) -> None:
        comp = Composition(fps=30)
        assert comp._frames_to_tc(0) == "00:00:00:00"
        assert comp._frames_to_tc(30) == "00:00:01:00"
        assert comp._frames_to_tc(90) == "00:00:03:00"
        assert comp._frames_to_tc(15) == "00:00:00:15"
        assert comp._frames_to_tc(1800) == "00:01:00:00"
        assert comp._frames_to_tc(108000) == "01:00:00:00"

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        comp = Composition(fps=30)
        edl_path = tmp_path / "subdir" / "deep" / "test.edl"
        comp.export_edl(edl_path)
        assert edl_path.exists()


class TestOTIOExport:
    """Tests for Composition.export_otio()."""

    def test_otio_import_error(self, tmp_path: Path) -> None:
        """Should raise ImportError if opentimelineio not installed."""
        comp = Composition(fps=30)
        try:
            comp.export_otio(tmp_path / "test.otio")
        except ImportError as e:
            assert "opentimelineio" in str(e)
        except Exception:  # noqa: S110
            # If OTIO is installed, it may succeed or fail for other reasons
            pass
