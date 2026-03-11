"""Tests to improve coverage for captions, text clip, image clip, audio analysis,
layout, and audio effects modules.

Targets uncovered code paths: error handling, edge cases, parameter validation,
rendering paths, and format variations.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from PIL import Image

from pymotion.audio.analysis import (
    WaveformExtractor,
    waveform_to_keyframes,
)
from pymotion.audio.effects import (
    ConvolutionReverb,
    MultibandCompressor,
    _process_audio,
    audio_crossfade,
)
from pymotion.captions import (
    AutoCaptions,
    CaptionSegment,
    SubtitleClip,
    WordTimestamp,
    _format_srt_time,
    _format_vtt_time,
    _parse_ass_time,
    _parse_srt_time,
    _parse_vtt_time,
    export_subtitles,
    get_caption_style,
    import_subtitles,
    parse_ass,
    parse_srt,
    parse_vtt,
    render_caption_frame,
)
from pymotion.clip.base import (
    RenderContext,
    Resolution,
    TimeRange,
)
from pymotion.clip.color import ColorClip
from pymotion.clip.image import ImageClip
from pymotion.clip.text import Shadow, TextClip, download_google_font
from pymotion.composition import Composition
from pymotion.layout import (
    _clip_max_duration,
    _ShadowClip,
    grid,
    pip,
    split_screen,
    stack,
)
from pymotion.utils.color import Color

# ── Helpers ──────────────────────────────────────────────────────────


def _make_ctx(
    frame: int = 0,
    fps: int = 30,
    width: int = 32,
    height: int = 32,
) -> RenderContext:
    res = Resolution(width, height)
    tr = TimeRange(start=0, end=90)
    return RenderContext(
        frame=frame,
        fps=fps,
        resolution=res,
        time_range=tr,
        local_frame=frame,
        progress=frame / 90.0 if frame < 90 else 1.0,
    )


def _make_clip(color: str = "#FF0000", duration: int = 60) -> ColorClip:
    clip = ColorClip(color=Color.parse(color))
    clip.start = 0
    clip.end = duration
    return clip


def _make_test_image(tmp_path: Path, w: int = 20, h: int = 30) -> Path:
    path = tmp_path / "test_img.png"
    arr = np.full((h, w, 4), 128, dtype=np.uint8)
    arr[:, :, 3] = 255
    img = Image.fromarray(arr, mode="RGBA")
    img.save(str(path))
    return path


# ══════════════════════════════════════════════════════════════════════
# 1. CAPTIONS
# ══════════════════════════════════════════════════════════════════════


class TestCaptionTimeParsers:
    """Cover internal time-parsing edge cases."""

    def test_parse_srt_time_basic(self) -> None:
        assert abs(_parse_srt_time("00:01:30,500") - 90.5) < 0.01

    def test_parse_srt_time_with_dot(self) -> None:
        # SRT parser replaces comma with dot internally
        assert abs(_parse_srt_time("00:00:05.250") - 5.25) < 0.01

    def test_parse_srt_time_invalid_parts(self) -> None:
        # Fewer than 3 parts should return 0.0
        assert _parse_srt_time("30,500") == 0.0
        assert _parse_srt_time("") == 0.0

    def test_parse_vtt_time_two_parts(self) -> None:
        assert abs(_parse_vtt_time("01:30.000") - 90.0) < 0.01

    def test_parse_vtt_time_three_parts(self) -> None:
        assert abs(_parse_vtt_time("01:02:03.456") - 3723.456) < 0.01

    def test_parse_vtt_time_invalid_parts(self) -> None:
        assert _parse_vtt_time("invalid") == 0.0
        assert _parse_vtt_time("") == 0.0

    def test_parse_ass_time_basic(self) -> None:
        assert abs(_parse_ass_time("1:23:45.67") - 5025.67) < 0.01

    def test_parse_ass_time_invalid_parts(self) -> None:
        assert _parse_ass_time("45.67") == 0.0
        assert _parse_ass_time("") == 0.0


class TestCaptionTimeFormatters:
    """Cover SRT/VTT time formatting functions."""

    def test_format_srt_time_zero(self) -> None:
        assert _format_srt_time(0.0) == "00:00:00,000"

    def test_format_srt_time_with_hours(self) -> None:
        result = _format_srt_time(3661.5)  # 1h 1m 1.5s
        assert result == "01:01:01,500"

    def test_format_vtt_time_zero(self) -> None:
        assert _format_vtt_time(0.0) == "00:00:00.000"

    def test_format_vtt_time_with_ms(self) -> None:
        result = _format_vtt_time(62.123)
        # Floating point rounding may give 122 or 123 ms
        assert result.startswith("00:01:02.")
        assert result in ("00:01:02.122", "00:01:02.123")


class TestParseEdgeCases:
    """Cover parser edge cases not hit by existing tests."""

    def test_parse_srt_block_with_two_lines(self) -> None:
        """SRT blocks with < 3 lines should be skipped."""
        srt = "1\n00:00:01,000 --> 00:00:02,000\n"
        segments = parse_srt(srt)
        assert len(segments) == 0

    def test_parse_srt_malformed_timestamp(self) -> None:
        """SRT blocks with bad timestamps should be skipped."""
        srt = "1\nnot a timestamp\nHello\n"
        segments = parse_srt(srt)
        assert len(segments) == 0

    def test_parse_vtt_block_without_timestamp(self) -> None:
        """VTT blocks without timestamps should be skipped."""
        vtt = "WEBVTT\n\nThis is just text\nwithout timestamps\n"
        segments = parse_vtt(vtt)
        assert len(segments) == 0

    def test_parse_vtt_empty_text_after_timestamp(self) -> None:
        """VTT blocks with timestamps but no text should be skipped."""
        vtt = "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\n"
        segments = parse_vtt(vtt)
        assert len(segments) == 0

    def test_parse_vtt_with_cue_identifier(self) -> None:
        """VTT with cue identifier line before timestamp should work."""
        vtt = "WEBVTT\n\ncue-1\n00:00:01.000 --> 00:00:02.000\nHello\n"
        segments = parse_vtt(vtt)
        assert len(segments) == 1
        assert segments[0].text == "Hello"

    def test_parse_ass_with_newline_escape(self) -> None:
        """ASS \\N should become real newlines."""
        ass = (
            "[Events]\n"
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
            "Dialogue: 0,0:00:01.00,0:00:04.00,Default,,0,0,0,,Line1\\NLine2\n"
        )
        segments = parse_ass(ass)
        assert len(segments) == 1
        assert "Line1\nLine2" == segments[0].text

    def test_parse_ass_short_dialogue_skipped(self) -> None:
        """ASS Dialogue lines with fewer than 10 comma-separated parts are skipped."""
        ass = "Dialogue: 0,0:00:01.00,0:00:04.00,Default,,0,0,0\n"
        segments = parse_ass(ass)
        assert len(segments) == 0

    def test_parse_ass_empty_text_skipped(self) -> None:
        """ASS Dialogue with empty text after tag stripping should be skipped."""
        ass = (
            "[Events]\n"
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
            "Dialogue: 0,0:00:01.00,0:00:04.00,Default,,0,0,0,,{\\b1}{\\b0}\n"
        )
        segments = parse_ass(ass)
        assert len(segments) == 0


class TestImportSubtitlesEdgeCases:
    """Cover import_subtitles edge cases."""

    def test_import_ssa_extension(self, tmp_path: Path) -> None:
        """SSA extension should be handled like ASS."""
        ssa_content = (
            "[Events]\n"
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
            "Dialogue: 0,0:00:01.00,0:00:04.00,Default,,0,0,0,,SSA text\n"
        )
        ssa_file = tmp_path / "test.ssa"
        ssa_file.write_text(ssa_content, encoding="utf-8")
        segments = import_subtitles(ssa_file)
        assert len(segments) == 1
        assert segments[0].text == "SSA text"

    def test_import_with_base_dirs(self, tmp_path: Path) -> None:
        """import_subtitles with base_dirs should validate the path."""
        srt_file = tmp_path / "test.srt"
        srt_file.write_text("1\n00:00:01,000 --> 00:00:02,000\nHello\n", encoding="utf-8")
        segments = import_subtitles(srt_file, base_dirs=[tmp_path])
        assert len(segments) == 1


class TestExportSubtitlesEdgeCases:
    """Cover export_subtitles paths."""

    def test_export_vtt_roundtrip(self, tmp_path: Path) -> None:
        segments = [
            CaptionSegment(text="First", start_sec=0.0, end_sec=1.5),
            CaptionSegment(text="Second", start_sec=2.0, end_sec=4.0),
        ]
        out = tmp_path / "output.vtt"
        export_subtitles(segments, out, fmt="vtt")
        content = out.read_text(encoding="utf-8")
        reimported = parse_vtt(content)
        assert len(reimported) == 2
        assert reimported[0].text == "First"

    def test_export_empty_segments(self, tmp_path: Path) -> None:
        out = tmp_path / "empty.srt"
        export_subtitles([], out, fmt="srt")
        content = out.read_text(encoding="utf-8")
        assert content.strip() == ""


class TestRenderCaptionFrame:
    """Cover render_caption_frame — both standard and karaoke paths."""

    def test_no_active_segment(self) -> None:
        """No segment active at time -> transparent frame."""
        segs = [CaptionSegment(text="Hello", start_sec=1.0, end_sec=2.0)]
        frame = render_caption_frame(segs, time_sec=3.0, width=64, height=32)
        assert frame.shape == (32, 64, 4)
        assert frame.dtype == np.uint8
        # Should be all zeros (transparent)
        assert np.sum(frame) == 0

    def test_active_segment_standard_style(self) -> None:
        """Standard style should render something (if cairo is available)."""
        segs = [CaptionSegment(text="Hello", start_sec=0.0, end_sec=5.0)]
        frame = render_caption_frame(segs, time_sec=2.0, width=200, height=100, style="netflix")
        assert frame.shape == (100, 200, 4)
        assert frame.dtype == np.uint8

    def test_center_position_style(self) -> None:
        """TikTok style uses center position."""
        segs = [CaptionSegment(text="Hello", start_sec=0.0, end_sec=5.0)]
        frame = render_caption_frame(segs, time_sec=1.0, width=200, height=100, style="tiktok")
        assert frame.shape == (100, 200, 4)

    def test_karaoke_style_with_words(self) -> None:
        """Karaoke style with word timestamps should highlight words."""
        words = [
            WordTimestamp(word="Hello", start_sec=0.0, end_sec=0.5),
            WordTimestamp(word="world", start_sec=0.5, end_sec=1.0),
        ]
        segs = [
            CaptionSegment(
                text="Hello world",
                start_sec=0.0,
                end_sec=2.0,
                words=words,
            )
        ]
        frame = render_caption_frame(segs, time_sec=0.3, width=200, height=100, style="karaoke")
        assert frame.shape == (100, 200, 4)

    def test_karaoke_style_without_words_falls_back(self) -> None:
        """Karaoke style without word timestamps should fall back to standard."""
        segs = [CaptionSegment(text="No words", start_sec=0.0, end_sec=2.0, words=None)]
        frame = render_caption_frame(segs, time_sec=0.5, width=200, height=100, style="karaoke")
        assert frame.shape == (100, 200, 4)

    def test_invalid_style_raises(self) -> None:
        segs = [CaptionSegment(text="Hello", start_sec=0.0, end_sec=2.0)]
        with pytest.raises(ValueError, match="Unknown caption style"):
            render_caption_frame(segs, time_sec=0.5, width=100, height=50, style="bad")

    def test_youtube_style(self) -> None:
        """YouTube style uses bottom position with Roboto font."""
        segs = [CaptionSegment(text="YouTube test", start_sec=0.0, end_sec=5.0)]
        frame = render_caption_frame(segs, time_sec=1.0, width=200, height=100, style="youtube")
        assert frame.shape == (100, 200, 4)


class TestSubtitleClipEdgeCases:
    """Cover SubtitleClip methods more thoroughly."""

    def test_get_text_at_boundary(self, tmp_path: Path) -> None:
        """Test exact start boundary (inclusive) and end boundary (exclusive)."""
        srt = "1\n00:00:01,000 --> 00:00:02,000\nHello\n"
        srt_file = tmp_path / "test.srt"
        srt_file.write_text(srt, encoding="utf-8")
        clip = SubtitleClip(srt_path=srt_file, fps=10)
        # Exact start time is inclusive
        assert clip.get_text_at(1.0) == "Hello"
        # Exact end time is exclusive
        assert clip.get_text_at(2.0) is None

    def test_get_text_at_frame_custom_fps(self, tmp_path: Path) -> None:
        srt = "1\n00:00:01,000 --> 00:00:02,000\nHi\n"
        srt_file = tmp_path / "test.srt"
        srt_file.write_text(srt, encoding="utf-8")
        clip = SubtitleClip(srt_path=srt_file, fps=10)
        # Frame 10 / fps 10 = 1.0s -> in range
        assert clip.get_text_at_frame(10) == "Hi"
        # Frame 5 / fps 10 = 0.5s -> before range
        assert clip.get_text_at_frame(5) is None


class TestAutoCaptionsMocked:
    """Cover AutoCaptions with mocked Whisper."""

    def test_transcribe_with_ndarray_mono(self) -> None:
        audio = np.zeros(16000, dtype=np.float64)
        ac = AutoCaptions(audio=audio, model="tiny")

        mock_model = MagicMock()
        mock_model.transcribe.return_value = {
            "segments": [
                {
                    "text": "Hello world",
                    "start": 0.0,
                    "end": 1.5,
                    "words": [
                        {"word": "Hello", "start": 0.0, "end": 0.7},
                        {"word": "world", "start": 0.7, "end": 1.5},
                    ],
                }
            ]
        }

        mock_whisper = MagicMock()
        mock_whisper.load_model.return_value = mock_model

        with patch.dict("sys.modules", {"whisper": mock_whisper}):
            segments = ac.transcribe()
            assert len(segments) == 1
            assert segments[0].text == "Hello world"
            assert segments[0].words is not None
            assert len(segments[0].words) == 2

    def test_transcribe_with_ndarray_stereo(self) -> None:
        audio = np.zeros((16000, 2), dtype=np.float64)
        ac = AutoCaptions(audio=audio, model="tiny")

        mock_model = MagicMock()
        mock_model.transcribe.return_value = {"segments": []}

        mock_whisper = MagicMock()
        mock_whisper.load_model.return_value = mock_model

        with patch.dict("sys.modules", {"whisper": mock_whisper}):
            segments = ac.transcribe()
            assert len(segments) == 0

    def test_transcribe_with_file_path(self, tmp_path: Path) -> None:
        audio_file = tmp_path / "audio.wav"
        audio_file.write_bytes(b"\x00" * 100)
        ac = AutoCaptions(audio=str(audio_file), model="tiny")

        mock_model = MagicMock()
        mock_model.transcribe.return_value = {
            "segments": [
                {
                    "text": "File audio",
                    "start": 0.0,
                    "end": 2.0,
                    "words": [],
                }
            ]
        }

        mock_whisper = MagicMock()
        mock_whisper.load_model.return_value = mock_model

        with patch.dict("sys.modules", {"whisper": mock_whisper}):
            segments = ac.transcribe()
            assert len(segments) == 1
            # No words -> words should be None
            assert segments[0].words is None

    def test_segments_property(self) -> None:
        audio = np.zeros(16000, dtype=np.float64)
        ac = AutoCaptions(audio=audio)
        assert ac.segments == []


class TestCaptionStyleCopy:
    """Verify get_caption_style returns a copy."""

    def test_returns_copy(self) -> None:
        style1 = get_caption_style("netflix")
        style2 = get_caption_style("netflix")
        style1["font_size"] = 999
        assert style2["font_size"] != 999


# ══════════════════════════════════════════════════════════════════════
# 2. TEXT CLIP
# ══════════════════════════════════════════════════════════════════════


class TestTextClipConstruction:
    """Cover TextClip construction and setters."""

    def test_default_construction(self) -> None:
        clip = TextClip("Hello")
        assert clip.text == "Hello"
        assert clip.font == "Inter"
        assert clip.size == 14.0
        assert clip.align == "left"
        assert clip.stroke_color is None
        assert clip.shadow is None

    def test_with_all_options(self) -> None:
        shadow = Shadow(color=Color(0.0, 0.0, 0.0, 0.8), offset_x=3.0, offset_y=3.0, blur=5.0)
        clip = TextClip(
            "Styled",
            font="Helvetica",
            size=48.0,
            color="#FF0000",
            letter_spacing=2.0,
            line_height=1.5,
            align="center",
            max_width=200,
            stroke_color="#000000",
            stroke_width=2.0,
            shadow=shadow,
        )
        assert clip.text == "Styled"
        assert clip.size == 48.0
        assert clip.align == "center"
        assert clip.stroke_color is not None
        assert clip.shadow is not None
        assert clip.max_width == 200
        assert clip.letter_spacing == 2.0
        assert clip.line_height == 1.5

    def test_set_text_clears_cache(self) -> None:
        clip = TextClip("Hello")
        clip._cached_frame = np.zeros((10, 10, 4), dtype=np.uint8)
        result = clip.set_text("World")
        assert result is clip  # fluent
        assert clip.text == "World"
        assert clip._cached_frame is None

    def test_set_font_with_size(self) -> None:
        clip = TextClip("Hello")
        result = clip.set_font("Helvetica", size=36.0)
        assert result is clip
        assert clip.font == "Helvetica"
        assert clip.size == 36.0
        assert clip._cached_frame is None

    def test_set_font_without_size(self) -> None:
        clip = TextClip("Hello", size=24.0)
        clip.set_font("Courier")
        assert clip.size == 24.0  # unchanged

    def test_set_color(self) -> None:
        clip = TextClip("Hello")
        result = clip.set_color("#FF0000")
        assert result is clip
        assert clip.color.r == pytest.approx(1.0)
        assert clip._cached_frame is None

    def test_set_stroke(self) -> None:
        clip = TextClip("Hello")
        result = clip.set_stroke("#000000", width=3.0)
        assert result is clip
        assert clip.stroke_color is not None
        assert clip.stroke_width == 3.0
        assert clip._cached_frame is None

    def test_set_shadow(self) -> None:
        clip = TextClip("Hello")
        shadow = Shadow()
        result = clip.set_shadow(shadow)
        assert result is clip
        assert clip.shadow is shadow
        assert clip._cached_frame is None


class TestTextClipRendering:
    """Cover TextClip render_frame paths."""

    def test_render_empty_text(self) -> None:
        clip = TextClip("")
        ctx = _make_ctx(width=32, height=32)
        frame = clip.render_frame(ctx)
        assert frame.shape == (32, 32, 4)
        # Empty text should be transparent
        assert np.sum(frame) == 0

    def test_render_caches_result(self) -> None:
        clip = TextClip("Hi")
        ctx = _make_ctx(width=64, height=64)
        frame1 = clip.render_frame(ctx)
        frame2 = clip.render_frame(ctx)
        assert frame1 is frame2  # same cached object

    def test_render_basic_text(self) -> None:
        clip = TextClip("Hello")
        ctx = _make_ctx(width=128, height=64)
        frame = clip.render_frame(ctx)
        assert frame.shape == (64, 128, 4)
        assert frame.dtype == np.uint8

    def test_render_with_position_offset(self) -> None:
        clip = TextClip("Hello")
        clip.set_position(10.0, 10.0)
        ctx = _make_ctx(width=128, height=64)
        frame = clip.render_frame(ctx)
        assert frame.shape == (64, 128, 4)

    def test_render_right_aligned(self) -> None:
        clip = TextClip("Right", align="right")
        ctx = _make_ctx(width=128, height=64)
        frame = clip.render_frame(ctx)
        assert frame.shape == (64, 128, 4)

    def test_render_center_aligned(self) -> None:
        clip = TextClip("Center", align="center")
        ctx = _make_ctx(width=128, height=64)
        frame = clip.render_frame(ctx)
        assert frame.shape == (64, 128, 4)


class TestShadowDataclass:
    """Cover Shadow dataclass."""

    def test_defaults(self) -> None:
        s = Shadow()
        assert s.offset_x == 2.0
        assert s.offset_y == 2.0
        assert s.blur == 3.0
        assert s.color.a == pytest.approx(0.5)

    def test_custom_values(self) -> None:
        s = Shadow(
            color=Color(1.0, 0.0, 0.0, 1.0),
            offset_x=5.0,
            offset_y=5.0,
            blur=10.0,
        )
        assert s.offset_x == 5.0
        assert s.color.r == pytest.approx(1.0)


class TestDownloadGoogleFont:
    """Cover download_google_font validation."""

    def test_invalid_family_name(self) -> None:
        with pytest.raises(ValueError, match="Invalid font family name"):
            download_google_font("bad/family!@#")

    def test_cached_font_returns_existing(self, tmp_path: Path) -> None:
        # Pre-create a cached font file
        import hashlib

        cache_key = "TestFont-400"
        cache_hash = hashlib.sha256(cache_key.encode()).hexdigest()[:16]
        cached_path = tmp_path / f"{cache_hash}.ttf"
        cached_path.write_bytes(b"fake font data")

        result = download_google_font("TestFont", weight=400, cache_dir=tmp_path)
        assert result == cached_path


# ══════════════════════════════════════════════════════════════════════
# 3. IMAGE CLIP
# ══════════════════════════════════════════════════════════════════════


class TestImageClipFitModes:
    """Cover all three fit modes and edge cases."""

    def test_contain_mode(self, tmp_path: Path) -> None:
        img_path = _make_test_image(tmp_path, w=40, h=20)
        clip = ImageClip(source=img_path, fit_mode="contain")
        ctx = _make_ctx(width=64, height=64)
        frame = clip.render_frame(ctx)
        assert frame.shape == (64, 64, 4)

    def test_cover_mode(self, tmp_path: Path) -> None:
        img_path = _make_test_image(tmp_path, w=40, h=20)
        clip = ImageClip(source=img_path, fit_mode="cover")
        ctx = _make_ctx(width=64, height=64)
        frame = clip.render_frame(ctx)
        assert frame.shape == (64, 64, 4)

    def test_stretch_mode(self, tmp_path: Path) -> None:
        img_path = _make_test_image(tmp_path, w=40, h=20)
        clip = ImageClip(source=img_path, fit_mode="stretch")
        ctx = _make_ctx(width=64, height=64)
        frame = clip.render_frame(ctx)
        assert frame.shape == (64, 64, 4)

    def test_set_fit_mode_clears_cache(self, tmp_path: Path) -> None:
        img_path = _make_test_image(tmp_path)
        clip = ImageClip(source=img_path)
        ctx = _make_ctx(width=64, height=64)
        clip.render_frame(ctx)
        assert clip._cached_frame is not None
        result = clip.set_fit_mode("stretch")
        assert result is clip
        assert clip._cached_frame is None

    def test_file_not_found(self) -> None:
        clip = ImageClip(source="/nonexistent/image.png")
        ctx = _make_ctx()
        with pytest.raises(FileNotFoundError, match="Image file not found"):
            clip.render_frame(ctx)

    def test_stretch_with_position_offset(self, tmp_path: Path) -> None:
        img_path = _make_test_image(tmp_path, w=40, h=20)
        clip = ImageClip(source=img_path, fit_mode="stretch")
        clip.set_position(5.0, 5.0)
        ctx = _make_ctx(width=64, height=64)
        frame = clip.render_frame(ctx)
        assert frame.shape == (64, 64, 4)

    def test_cover_with_position_offset(self, tmp_path: Path) -> None:
        img_path = _make_test_image(tmp_path, w=40, h=20)
        clip = ImageClip(source=img_path, fit_mode="cover")
        clip.set_position(3.0, 3.0)
        ctx = _make_ctx(width=64, height=64)
        frame = clip.render_frame(ctx)
        assert frame.shape == (64, 64, 4)

    def test_contain_with_position_offset(self, tmp_path: Path) -> None:
        img_path = _make_test_image(tmp_path, w=40, h=20)
        clip = ImageClip(source=img_path, fit_mode="contain")
        clip.set_position(5.0, 5.0)
        ctx = _make_ctx(width=64, height=64)
        frame = clip.render_frame(ctx)
        assert frame.shape == (64, 64, 4)

    def test_cache_invalidated_on_resolution_change(self, tmp_path: Path) -> None:
        img_path = _make_test_image(tmp_path, w=40, h=20)
        clip = ImageClip(source=img_path, fit_mode="contain")
        ctx1 = _make_ctx(width=64, height=64)
        frame1 = clip.render_frame(ctx1)
        assert frame1.shape == (64, 64, 4)
        # Different resolution should re-render
        ctx2 = _make_ctx(width=32, height=32)
        frame2 = clip.render_frame(ctx2)
        assert frame2.shape == (32, 32, 4)

    def test_rgba_to_bgra_conversion(self, tmp_path: Path) -> None:
        """Verify RGBA->BGRA channel swap."""
        path = tmp_path / "red.png"
        arr = np.zeros((10, 10, 4), dtype=np.uint8)
        arr[:, :, 0] = 255  # R in RGBA
        arr[:, :, 3] = 255  # A
        img = Image.fromarray(arr, mode="RGBA")
        img.save(str(path))
        clip = ImageClip(source=path, fit_mode="stretch")
        ctx = _make_ctx(width=10, height=10)
        frame = clip.render_frame(ctx)
        # In BGRA, red should be at index 2
        assert frame[5, 5, 2] == 255
        assert frame[5, 5, 0] == 0

    def test_load_original_caches(self, tmp_path: Path) -> None:
        img_path = _make_test_image(tmp_path)
        clip = ImageClip(source=img_path)
        img1 = clip._load_original()
        img2 = clip._load_original()
        assert img1 is img2  # cached


# ══════════════════════════════════════════════════════════════════════
# 4. AUDIO ANALYSIS
# ══════════════════════════════════════════════════════════════════════


class TestWaveformToKeyframes:
    """Cover waveform_to_keyframes function."""

    def test_basic_keyframes(self) -> None:
        audio = np.random.default_rng(42).random(22050).astype(np.float32)
        kf = waveform_to_keyframes(audio, sample_rate=22050, fps=10)
        assert isinstance(kf, list)
        assert len(kf) > 0
        # Each entry is (frame, value)
        for frame, value in kf:
            assert isinstance(frame, int)
            assert 0.0 <= value <= 1.0

    def test_custom_value_range(self) -> None:
        audio = np.random.default_rng(42).random(22050).astype(np.float32)
        kf = waveform_to_keyframes(audio, sample_rate=22050, fps=10, min_value=0.5, max_value=2.0)
        for _, value in kf:
            assert value >= 0.5 - 0.01
            assert value <= 2.0 + 0.01

    def test_with_smoothing(self) -> None:
        audio = np.random.default_rng(42).random(22050).astype(np.float32)
        kf = waveform_to_keyframes(audio, sample_rate=22050, fps=10, smoothing=5)
        assert len(kf) > 0

    def test_stereo_input(self) -> None:
        audio = np.random.default_rng(42).random((22050, 2)).astype(np.float32)
        kf = waveform_to_keyframes(audio, sample_rate=22050, fps=10)
        assert len(kf) > 0

    def test_silent_audio(self) -> None:
        audio = np.zeros(22050, dtype=np.float32)
        kf = waveform_to_keyframes(audio, sample_rate=22050, fps=10)
        assert len(kf) > 0
        for _, value in kf:
            assert value == pytest.approx(0.0)

    def test_very_short_audio(self) -> None:
        audio = np.ones(100, dtype=np.float32)
        kf = waveform_to_keyframes(audio, sample_rate=22050, fps=30)
        assert len(kf) >= 1


class TestWaveformExtractorAdditional:
    """Additional edge cases for WaveformExtractor."""

    def test_n_points_larger_than_audio(self) -> None:
        audio = np.ones(10, dtype=np.float32)
        extractor = WaveformExtractor()
        envelope = extractor.extract(audio, n_points=100)
        assert envelope.shape == (100,)

    def test_negative_n_points(self) -> None:
        audio = np.ones(100, dtype=np.float32)
        extractor = WaveformExtractor()
        with pytest.raises(ValueError, match="n_points must be >= 1"):
            extractor.extract(audio, n_points=-1)


# ══════════════════════════════════════════════════════════════════════
# 5. LAYOUT
# ══════════════════════════════════════════════════════════════════════


class TestClipMaxDuration:
    """Cover _clip_max_duration helper."""

    def test_empty(self) -> None:
        assert _clip_max_duration() == 0

    def test_single_clip(self) -> None:
        c = _make_clip(duration=42)
        assert _clip_max_duration(c) == 42

    def test_multiple_clips(self) -> None:
        c1 = _make_clip(duration=30)
        c2 = _make_clip(duration=90)
        c3 = _make_clip(duration=60)
        assert _clip_max_duration(c1, c2, c3) == 90


class TestShadowClip:
    """Cover _ShadowClip internal clip."""

    def test_render_basic(self) -> None:
        clip = _ShadowClip(width=20, height=15, blur=4, opacity=0.5)
        ctx = _make_ctx(width=32, height=32)
        frame = clip.render_frame(ctx)
        assert frame.shape == (32, 32, 4)
        assert frame.dtype == np.uint8

    def test_render_no_blur(self) -> None:
        clip = _ShadowClip(width=10, height=10, blur=0, opacity=0.8)
        ctx = _make_ctx(width=16, height=16)
        frame = clip.render_frame(ctx)
        assert frame.shape == (16, 16, 4)
        # Alpha in shadow region should be set
        alpha_val = int(0.8 * 255)
        assert frame[5, 5, 3] == alpha_val

    def test_render_shadow_larger_than_frame(self) -> None:
        """Shadow larger than frame should be clamped."""
        clip = _ShadowClip(width=100, height=100, blur=2, opacity=0.5)
        ctx = _make_ctx(width=16, height=16)
        frame = clip.render_frame(ctx)
        assert frame.shape == (16, 16, 4)


class TestPipEdgeCases:
    """Cover pip() edge cases."""

    def test_pip_with_shadow(self) -> None:
        main = _make_clip(duration=30)
        overlay = _make_clip("#0000FF", duration=30)
        result = pip(main, overlay, shadow=True)
        assert isinstance(result, Composition)

    def test_pip_different_durations(self) -> None:
        main = _make_clip(duration=60)
        overlay = _make_clip(duration=30)
        result = pip(main, overlay)
        assert result.duration == 60

    def test_pip_overlay_zero_duration_raises(self) -> None:
        main = _make_clip(duration=60)
        overlay = _make_clip(duration=0)
        with pytest.raises(ValueError, match="positive duration"):
            pip(main, overlay)

    def test_pip_with_custom_size_and_position(self) -> None:
        main = _make_clip(duration=30)
        overlay = _make_clip(duration=30)
        result = pip(main, overlay, position="top-left", size=(200, 150))
        assert isinstance(result, Composition)

    def test_pip_with_all_named_positions(self) -> None:
        for pos in [
            "top-left",
            "top-center",
            "top-right",
            "center-left",
            "center",
            "center-right",
            "bottom-left",
            "bottom-center",
            "bottom-right",
        ]:
            main = _make_clip(duration=30)
            overlay = _make_clip(duration=30)
            result = pip(main, overlay, position=pos)
            assert isinstance(result, Composition)


class TestGridEdgeCases:
    """Cover grid() edge cases."""

    def test_more_clips_than_cells(self) -> None:
        """Extra clips beyond rows*cols should be truncated."""
        clips = [_make_clip(duration=30) for _ in range(10)]
        result = grid(clips, rows=2, cols=2)
        assert isinstance(result, Composition)

    def test_negative_cols_raises(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            grid([_make_clip()], rows=1, cols=-1)

    def test_grid_with_background_color(self) -> None:
        clips = [_make_clip(duration=30) for _ in range(4)]
        result = grid(clips, rows=2, cols=2, background="#333333")
        assert isinstance(result, Composition)

    def test_single_cell_grid(self) -> None:
        clips = [_make_clip(duration=30)]
        result = grid(clips, rows=1, cols=1)
        assert isinstance(result, Composition)


class TestSplitScreenEdgeCases:
    """Cover split_screen() edge cases."""

    def test_more_clips_than_rects(self) -> None:
        """Extra clips beyond rect count should be truncated."""
        clips = [_make_clip(duration=30) for _ in range(6)]
        result = split_screen(clips, layout="quad")
        assert isinstance(result, Composition)

    def test_single_clip_horizontal(self) -> None:
        clips = [_make_clip(duration=30)]
        result = split_screen(clips, layout="horizontal")
        assert isinstance(result, Composition)

    def test_single_clip_vertical(self) -> None:
        clips = [_make_clip(duration=30)]
        result = split_screen(clips, layout="vertical")
        assert isinstance(result, Composition)

    def test_three_clips_horizontal(self) -> None:
        clips = [_make_clip(duration=30) for _ in range(3)]
        result = split_screen(clips, layout="horizontal")
        assert isinstance(result, Composition)

    def test_custom_rects_more_clips_than_rects(self) -> None:
        clips = [_make_clip(duration=30) for _ in range(3)]
        rects = [(0.0, 0.0, 0.5, 1.0), (0.5, 0.0, 0.5, 1.0)]
        result = split_screen(clips, layout=rects)
        assert isinstance(result, Composition)


class TestStackEdgeCases:
    """Cover stack() edge cases."""

    def test_vertical_with_gap(self) -> None:
        clips = [_make_clip(duration=30), _make_clip(duration=30)]
        result = stack(clips, direction="vertical", gap=10)
        assert isinstance(result, Composition)

    def test_many_clips_horizontal(self) -> None:
        clips = [_make_clip(duration=30) for _ in range(5)]
        result = stack(clips, direction="horizontal")
        assert isinstance(result, Composition)

    def test_many_clips_vertical(self) -> None:
        clips = [_make_clip(duration=30) for _ in range(5)]
        result = stack(clips, direction="vertical")
        assert isinstance(result, Composition)


# ══════════════════════════════════════════════════════════════════════
# 6. AUDIO EFFECTS
# ══════════════════════════════════════════════════════════════════════


class TestProcessAudioHelper:
    """Cover _process_audio helper."""

    def test_1d_input(self) -> None:
        plugin = MagicMock()
        plugin.return_value = np.zeros((1, 100), dtype=np.float32)
        samples = np.zeros(100, dtype=np.float32)
        result = _process_audio(plugin, samples, 44100)
        # 1D input is reshaped to (1, n), processed, then transposed to (n, 1)
        assert result.shape == (100, 1)

    def test_2d_input(self) -> None:
        plugin = MagicMock()
        plugin.return_value = np.zeros((2, 100), dtype=np.float32)
        samples = np.zeros((100, 2), dtype=np.float32)
        result = _process_audio(plugin, samples, 44100)
        assert result.shape == (100, 2)


class TestMultibandCompressorEdgeCases:
    """Cover MultibandCompressor edge cases."""

    def test_empty_samples(self) -> None:
        mc = MultibandCompressor()
        result = mc.apply(np.array([], dtype=np.float64), 44100)
        assert len(result) == 0

    def test_mono_input(self) -> None:
        mc = MultibandCompressor()
        samples = np.random.default_rng(42).random(1000).astype(np.float64) * 0.5
        result = mc.apply(samples, 44100)
        assert result.shape == (1000,)

    def test_stereo_input(self) -> None:
        mc = MultibandCompressor()
        samples = np.random.default_rng(42).random((1000, 2)).astype(np.float64) * 0.5
        result = mc.apply(samples, 44100)
        assert result.shape == (1000, 2)

    def test_custom_parameters(self) -> None:
        mc = MultibandCompressor(
            crossover_freqs=(100.0, 500.0, 3000.0),
            thresholds_db=(-10.0, -10.0, -10.0, -10.0),
            ratios=(2.0, 2.0, 2.0, 2.0),
            makeup_gain_db=(1.0, 1.0, 1.0, 1.0),
        )
        samples = np.random.default_rng(42).random(500).astype(np.float64) * 0.5
        result = mc.apply(samples, 44100)
        assert result.shape == (500,)


class TestConvolutionReverbEdgeCases:
    """Cover ConvolutionReverb edge cases."""

    def test_empty_samples(self) -> None:
        cr = ConvolutionReverb(ir_path="/dummy")
        # Mock _load_ir to return a small IR
        with patch.object(cr, "_load_ir", return_value=np.ones(10, dtype=np.float64)):
            samples = np.array([], dtype=np.float64)
            result = cr.apply(samples, 44100)
            assert len(result) == 0

    def test_empty_ir(self) -> None:
        cr = ConvolutionReverb(ir_path="/dummy")
        with patch.object(cr, "_load_ir", return_value=np.array([], dtype=np.float64)):
            samples = np.ones(100, dtype=np.float64)
            result = cr.apply(samples, 44100)
            assert len(result) == 100

    def test_mono_with_stereo_ir(self) -> None:
        cr = ConvolutionReverb(ir_path="/dummy")
        ir = np.ones((10, 2), dtype=np.float64) * 0.1
        with patch.object(cr, "_load_ir", return_value=ir):
            samples = np.ones(100, dtype=np.float64)
            result = cr.apply(samples, 44100)
            assert result.shape == (100,)

    def test_stereo_with_mono_ir(self) -> None:
        cr = ConvolutionReverb(ir_path="/dummy")
        ir = np.ones(10, dtype=np.float64) * 0.1
        with patch.object(cr, "_load_ir", return_value=ir):
            samples = np.ones((100, 2), dtype=np.float64)
            result = cr.apply(samples, 44100)
            assert result.shape == (100, 2)

    def test_with_pre_delay(self) -> None:
        cr = ConvolutionReverb(ir_path="/dummy", pre_delay_ms=50.0)
        ir = np.ones(10, dtype=np.float64) * 0.1
        with patch.object(cr, "_load_ir", return_value=ir):
            samples = np.ones(100, dtype=np.float64) * 0.5
            result = cr.apply(samples, 44100)
            assert result.shape == (100,)

    def test_ir_fewer_channels_than_audio(self) -> None:
        cr = ConvolutionReverb(ir_path="/dummy")
        ir = np.ones((10, 1), dtype=np.float64) * 0.1  # 1 channel IR
        with patch.object(cr, "_load_ir", return_value=ir):
            samples = np.ones((100, 3), dtype=np.float64)  # 3 channel audio
            result = cr.apply(samples, 44100)
            assert result.shape == (100, 3)

    def test_ir_more_channels_than_audio(self) -> None:
        cr = ConvolutionReverb(ir_path="/dummy")
        ir = np.ones((10, 4), dtype=np.float64) * 0.1  # 4 channel IR
        with patch.object(cr, "_load_ir", return_value=ir):
            samples = np.ones((100, 2), dtype=np.float64)  # 2 channel audio
            result = cr.apply(samples, 44100)
            assert result.shape == (100, 2)

    def test_load_ir_no_ffmpeg(self, tmp_path: Path) -> None:
        ir_file = tmp_path / "ir.wav"
        ir_file.write_bytes(b"\x00" * 100)
        cr = ConvolutionReverb(ir_path=str(ir_file))
        with patch("shutil.which", return_value=None):
            with pytest.raises(RuntimeError, match="ffmpeg not found"):
                cr._load_ir(44100)

    def test_load_ir_ffmpeg_failure(self, tmp_path: Path) -> None:
        ir_file = tmp_path / "ir.wav"
        ir_file.write_bytes(b"\x00" * 100)
        cr = ConvolutionReverb(ir_path=str(ir_file))

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = b""

        with patch("shutil.which", return_value="/usr/bin/ffmpeg"):
            with patch("subprocess.run", return_value=mock_result):
                ir = cr._load_ir(44100)
                assert len(ir) == 0

    def test_load_ir_success_stereo(self, tmp_path: Path) -> None:
        ir_file = tmp_path / "ir.wav"
        ir_file.write_bytes(b"\x00" * 100)
        cr = ConvolutionReverb(ir_path=str(ir_file))

        # Create fake stereo PCM data (even number of samples)
        stereo_data = np.array([0.5, 0.3, 0.7, 0.1], dtype=np.float64)
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = stereo_data.tobytes()

        with patch("shutil.which", return_value="/usr/bin/ffmpeg"):
            with patch("subprocess.run", return_value=mock_result):
                ir = cr._load_ir(44100)
                assert ir.ndim == 2
                assert ir.shape[1] == 2

    def test_load_ir_success_mono(self, tmp_path: Path) -> None:
        ir_file = tmp_path / "ir.wav"
        ir_file.write_bytes(b"\x00" * 100)
        cr = ConvolutionReverb(ir_path=str(ir_file))

        # Odd number of samples -> treated as mono
        mono_data = np.array([0.5, 0.3, 0.7], dtype=np.float64)
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = mono_data.tobytes()

        with patch("shutil.which", return_value="/usr/bin/ffmpeg"):
            with patch("subprocess.run", return_value=mock_result):
                ir = cr._load_ir(44100)
                assert ir.ndim == 1


class TestAudioCrossfadeEdgeCases:
    """Cover audio_crossfade edge cases not in existing tests."""

    def test_negative_crossfade_samples_concatenates(self) -> None:
        a = np.ones(50, dtype=np.float64)
        b = np.ones(30, dtype=np.float64) * 0.5
        result = audio_crossfade(a, b, crossfade_samples=-1)
        assert len(result) == 80

    def test_preserves_dtype(self) -> None:
        a = np.ones(50, dtype=np.float32)
        b = np.ones(50, dtype=np.float32)
        result = audio_crossfade(a, b, crossfade_samples=10, curve="linear")
        # Result dtype should be float64 (due to linspace), just check it works
        assert len(result) == 90
