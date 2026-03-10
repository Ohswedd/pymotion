"""Tests for captions & subtitles — parsing, export, styles."""

from __future__ import annotations

from pathlib import Path

import pytest

from pymotion.captions import (
    AutoCaptions,
    CaptionSegment,
    SubtitleClip,
    WordTimestamp,
    export_subtitles,
    get_caption_style,
    import_subtitles,
    parse_ass,
    parse_srt,
    parse_vtt,
)

# ── SRT Parsing ──────────────────────────────────────────────────────

_SAMPLE_SRT = """1
00:00:01,000 --> 00:00:04,000
Hello, world!

2
00:00:05,500 --> 00:00:08,200
This is a test subtitle.

3
00:00:10,000 --> 00:00:12,500
Multi-line
subtitle text.
"""


class TestParseSrt:
    """Tests for SRT parsing."""

    def test_parse_basic(self) -> None:
        segments = parse_srt(_SAMPLE_SRT)
        assert len(segments) == 3

    def test_parse_timestamps(self) -> None:
        segments = parse_srt(_SAMPLE_SRT)
        assert abs(segments[0].start_sec - 1.0) < 0.01
        assert abs(segments[0].end_sec - 4.0) < 0.01
        assert abs(segments[1].start_sec - 5.5) < 0.01

    def test_parse_text(self) -> None:
        segments = parse_srt(_SAMPLE_SRT)
        assert segments[0].text == "Hello, world!"
        assert segments[1].text == "This is a test subtitle."

    def test_parse_multiline(self) -> None:
        segments = parse_srt(_SAMPLE_SRT)
        assert "Multi-line\nsubtitle text." == segments[2].text

    def test_parse_empty(self) -> None:
        segments = parse_srt("")
        assert len(segments) == 0


# ── VTT Parsing ──────────────────────────────────────────────────────

_SAMPLE_VTT = """WEBVTT

00:00:01.000 --> 00:00:04.000
Hello, VTT!

00:00:05.500 --> 00:00:08.200
Second subtitle.
"""


class TestParseVtt:
    """Tests for VTT parsing."""

    def test_parse_basic(self) -> None:
        segments = parse_vtt(_SAMPLE_VTT)
        assert len(segments) == 2

    def test_parse_timestamps(self) -> None:
        segments = parse_vtt(_SAMPLE_VTT)
        assert abs(segments[0].start_sec - 1.0) < 0.01
        assert abs(segments[0].end_sec - 4.0) < 0.01

    def test_parse_text(self) -> None:
        segments = parse_vtt(_SAMPLE_VTT)
        assert segments[0].text == "Hello, VTT!"

    def test_parse_short_timestamps(self) -> None:
        """VTT allows MM:SS.mmm format."""
        vtt = "WEBVTT\n\n01:30.000 --> 02:00.000\nShort format.\n"
        segments = parse_vtt(vtt)
        assert len(segments) == 1
        assert abs(segments[0].start_sec - 90.0) < 0.01


# ── ASS Parsing ──────────────────────────────────────────────────────

_SAMPLE_ASS = """[Script Info]
Title: Test

[V4+ Styles]
Format: Name, Fontname, Fontsize
Style: Default,Arial,20

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:01.00,0:00:04.00,Default,,0,0,0,,Hello from ASS!
Dialogue: 0,0:00:05.50,0:00:08.20,Default,,0,0,0,,{\\b1}Bold{\\b0} text.
"""


class TestParseAss:
    """Tests for ASS/SSA parsing."""

    def test_parse_basic(self) -> None:
        segments = parse_ass(_SAMPLE_ASS)
        assert len(segments) == 2

    def test_parse_timestamps(self) -> None:
        segments = parse_ass(_SAMPLE_ASS)
        assert abs(segments[0].start_sec - 1.0) < 0.01
        assert abs(segments[0].end_sec - 4.0) < 0.01

    def test_strip_formatting_tags(self) -> None:
        segments = parse_ass(_SAMPLE_ASS)
        assert segments[1].text == "Bold text."


# ── Subtitle Import ──────────────────────────────────────────────────


class TestImportSubtitles:
    """Tests for import_subtitles()."""

    def test_import_srt(self, tmp_path: Path) -> None:
        srt_file = tmp_path / "test.srt"
        srt_file.write_text(_SAMPLE_SRT, encoding="utf-8")
        segments = import_subtitles(srt_file)
        assert len(segments) == 3

    def test_import_vtt(self, tmp_path: Path) -> None:
        vtt_file = tmp_path / "test.vtt"
        vtt_file.write_text(_SAMPLE_VTT, encoding="utf-8")
        segments = import_subtitles(vtt_file)
        assert len(segments) == 2

    def test_import_ass(self, tmp_path: Path) -> None:
        ass_file = tmp_path / "test.ass"
        ass_file.write_text(_SAMPLE_ASS, encoding="utf-8")
        segments = import_subtitles(ass_file)
        assert len(segments) == 2

    def test_import_unsupported_format(self, tmp_path: Path) -> None:
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("not subtitles", encoding="utf-8")
        with pytest.raises(ValueError, match="Unsupported subtitle format"):
            import_subtitles(txt_file)

    def test_import_nonexistent_file(self) -> None:
        with pytest.raises(FileNotFoundError):
            import_subtitles("/nonexistent/path.srt")


# ── Subtitle Export ──────────────────────────────────────────────────


class TestExportSubtitles:
    """Tests for export_subtitles()."""

    def test_export_srt(self, tmp_path: Path) -> None:
        segments = [
            CaptionSegment(text="Hello", start_sec=1.0, end_sec=4.0),
            CaptionSegment(text="World", start_sec=5.5, end_sec=8.0),
        ]
        out = tmp_path / "output.srt"
        export_subtitles(segments, out, fmt="srt")
        content = out.read_text()
        assert "00:00:01,000 --> 00:00:04,000" in content
        assert "Hello" in content
        assert "World" in content

    def test_export_vtt(self, tmp_path: Path) -> None:
        segments = [
            CaptionSegment(text="Test", start_sec=0.0, end_sec=2.5),
        ]
        out = tmp_path / "output.vtt"
        export_subtitles(segments, out, fmt="vtt")
        content = out.read_text()
        assert content.startswith("WEBVTT")
        assert "00:00:00.000 --> 00:00:02.500" in content

    def test_export_roundtrip_srt(self, tmp_path: Path) -> None:
        """Export then re-import SRT should preserve data."""
        segments = [
            CaptionSegment(text="Round trip", start_sec=1.0, end_sec=3.0),
        ]
        out = tmp_path / "roundtrip.srt"
        export_subtitles(segments, out, fmt="srt")
        reimported = parse_srt(out.read_text())
        assert len(reimported) == 1
        assert reimported[0].text == "Round trip"
        assert abs(reimported[0].start_sec - 1.0) < 0.01

    def test_export_unsupported_format(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="Unsupported export format"):
            export_subtitles([], tmp_path / "out.txt", fmt="xyz")


# ── Caption Styles ───────────────────────────────────────────────────


class TestCaptionStyles:
    """Tests for caption style presets."""

    def test_get_known_style(self) -> None:
        style = get_caption_style("netflix")
        assert "font_size" in style
        assert "color" in style

    def test_all_styles_exist(self) -> None:
        for name in ("netflix", "youtube", "tiktok", "karaoke"):
            style = get_caption_style(name)
            assert isinstance(style, dict)

    def test_unknown_style_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown caption style"):
            get_caption_style("nonexistent")

    def test_karaoke_style_has_highlight(self) -> None:
        style = get_caption_style("karaoke")
        assert "highlight_color" in style


# ── SubtitleClip ─────────────────────────────────────────────────────


class TestSubtitleClip:
    """Tests for SubtitleClip."""

    def test_init_and_parse(self, tmp_path: Path) -> None:
        srt_file = tmp_path / "test.srt"
        srt_file.write_text(_SAMPLE_SRT, encoding="utf-8")
        clip = SubtitleClip(srt_path=srt_file)
        assert len(clip.segments) == 3

    def test_get_text_at(self, tmp_path: Path) -> None:
        srt_file = tmp_path / "test.srt"
        srt_file.write_text(_SAMPLE_SRT, encoding="utf-8")
        clip = SubtitleClip(srt_path=srt_file)
        assert clip.get_text_at(2.0) == "Hello, world!"
        assert clip.get_text_at(6.0) == "This is a test subtitle."
        assert clip.get_text_at(9.0) is None

    def test_get_text_at_frame(self, tmp_path: Path) -> None:
        srt_file = tmp_path / "test.srt"
        srt_file.write_text(_SAMPLE_SRT, encoding="utf-8")
        clip = SubtitleClip(srt_path=srt_file, fps=30)
        # Frame 60 = 2.0 seconds
        assert clip.get_text_at_frame(60) == "Hello, world!"
        # Frame 270 = 9.0 seconds → no caption
        assert clip.get_text_at_frame(270) is None


# ── Data Classes ─────────────────────────────────────────────────────


class TestCaptionSegment:
    """Tests for CaptionSegment dataclass."""

    def test_init(self) -> None:
        seg = CaptionSegment(text="Test", start_sec=0.0, end_sec=1.0)
        assert seg.text == "Test"
        assert seg.words is None

    def test_with_words(self) -> None:
        words = [
            WordTimestamp(word="Hello", start_sec=0.0, end_sec=0.5),
            WordTimestamp(word="world", start_sec=0.5, end_sec=1.0),
        ]
        seg = CaptionSegment(text="Hello world", start_sec=0.0, end_sec=1.0, words=words)
        assert len(seg.words) == 2


class TestWordTimestamp:
    """Tests for WordTimestamp dataclass."""

    def test_init(self) -> None:
        wt = WordTimestamp(word="hello", start_sec=0.0, end_sec=0.3)
        assert wt.word == "hello"


class TestAutoCaptions:
    """Tests for AutoCaptions (without Whisper installed)."""

    def test_init(self) -> None:
        import numpy as np

        audio = np.zeros(16000, dtype=np.float64)
        ac = AutoCaptions(audio=audio, model="tiny")
        assert ac.model == "tiny"
        assert len(ac.segments) == 0

    def test_transcribe_without_whisper(self) -> None:
        """Should raise ImportError if whisper is not installed."""
        import numpy as np

        audio = np.zeros(16000, dtype=np.float64)
        ac = AutoCaptions(audio=audio)
        # This may pass or raise ImportError depending on environment
        try:
            ac.transcribe()
        except ImportError as e:
            assert "openai-whisper" in str(e)
