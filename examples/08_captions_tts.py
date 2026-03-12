"""EX08 — Captions & TTS.

Use-case: An auto-captioned video with subtitle parsing, export,
text-to-speech generation, and fade transitions.
Each caption segment is visible as styled text on screen.

Features exercised:
  TTSClip,
  AutoCaptions, SubtitleClip, CaptionSegment, WordTimestamp,
  export_subtitles, get_caption_style, import_subtitles,
  parse_srt, parse_vtt, parse_ass, render_caption_frame,
  FadeToBlack, FadeToWhite

Output: 1920x1080, 30fps, 20s, preset h264_fast -> outputs/08_captions.mp4
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

import pymotion as pm
from pymotion.design.tokens import NEUTRAL, get_theme

ASSETS = Path(__file__).parent / "assets"
OUTPUT_DIR = Path(__file__).parent.parent / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

TOTAL = 600  # 20s at 30fps


def main() -> None:
    audit_dir = Path(__file__).parent.parent / "audit"
    audit_dir.mkdir(exist_ok=True)
    theme = get_theme()

    # ── CaptionSegment + WordTimestamp ────────────────────────────────────
    words = [
        pm.WordTimestamp(word="Welcome", start_sec=0.0, end_sec=0.5),
        pm.WordTimestamp(word="to", start_sec=0.5, end_sec=0.7),
        pm.WordTimestamp(word="PyMotion", start_sec=0.7, end_sec=1.2),
    ]
    seg1 = pm.CaptionSegment(text="Welcome to PyMotion", start_sec=0.0, end_sec=3.0, words=words)
    seg2 = pm.CaptionSegment(text="A code-first video framework", start_sec=3.5, end_sec=6.5)
    seg3 = pm.CaptionSegment(text="Build videos with Python", start_sec=7.0, end_sec=10.0)
    seg4 = pm.CaptionSegment(text="Professional quality output", start_sec=10.5, end_sec=13.5)
    seg5 = pm.CaptionSegment(text="Render anywhere", start_sec=14.0, end_sec=17.0)
    seg6 = pm.CaptionSegment(text="Thank you for watching", start_sec=17.5, end_sec=20.0)
    segments = [seg1, seg2, seg3, seg4, seg5, seg6]
    print(f"1. CaptionSegment: {len(segments)} segments")
    print(f"   WordTimestamp: {len(words)} words in seg1")

    # ── parse_srt ────────────────────────────────────────────────────────
    srt_text = (
        "1\n00:00:00,000 --> 00:00:02,000\nWelcome to PyMotion\n\n"
        "2\n00:00:02,500 --> 00:00:05,000\nA code-first video framework\n\n"
    )
    srt_segs = pm.parse_srt(srt_text)
    print(f"2. parse_srt: {len(srt_segs)} segments")

    # ── parse_vtt ────────────────────────────────────────────────────────
    vtt_text = (
        "WEBVTT\n\n"
        "00:00:00.000 --> 00:00:02.000\nWelcome to PyMotion\n\n"
        "00:00:02.500 --> 00:00:05.000\nA code-first framework\n\n"
    )
    vtt_segs = pm.parse_vtt(vtt_text)
    print(f"3. parse_vtt: {len(vtt_segs)} segments")

    # ── parse_ass ────────────────────────────────────────────────────────
    ass_text = (
        "[Script Info]\nTitle: Test\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        "Dialogue: 0,0:00:00.00,0:00:02.00,Default,,0,0,0,,Welcome\n"
        "Dialogue: 0,0:00:02.50,0:00:05.00,Default,,0,0,0,,Framework\n"
    )
    ass_segs = pm.parse_ass(ass_text)
    print(f"4. parse_ass: {len(ass_segs)} segments")

    # ── export_subtitles ─────────────────────────────────────────────────
    srt_out = audit_dir / "ex08_captions.srt"
    pm.export_subtitles(segments, srt_out, fmt="srt")
    print(f"5. export_subtitles: {srt_out.name}")

    # ── import_subtitles ─────────────────────────────────────────────────
    imported = pm.import_subtitles(srt_out)
    print(f"6. import_subtitles: {len(imported)} segments")

    # ── get_caption_style ────────────────────────────────────────────────
    style: dict[str, Any] = pm.get_caption_style("netflix")
    print(f"7. get_caption_style('netflix'): keys={list(style.keys())}")

    # ── render_caption_frame ─────────────────────────────────────────────
    cap_frame = pm.render_caption_frame(
        segments, time_sec=1.0, width=1920, height=1080, style="netflix"
    )
    print(f"8. render_caption_frame: {cap_frame.shape}")

    # ── TTSClip ──────────────────────────────────────────────────────────
    tts = pm.TTSClip(
        text="Welcome to PyMotion, a code-first video framework.",
        voice="default",
        engine="system",
        speed=1.0,
        pitch=1.0,
        sample_rate=48000,
    )
    print(f"9. TTSClip: engine={tts.engine}, voice={tts.voice}")

    # ── AutoCaptions ─────────────────────────────────────────────────────
    mono_audio = np.random.default_rng(42).uniform(-0.1, 0.1, 16000 * 5).astype(np.float32)
    auto_caps = pm.AutoCaptions(
        audio=mono_audio,
        model="base",
        style="netflix",
        sample_rate=16000,
    )
    print(f"10. AutoCaptions: model={auto_caps.model}")

    # ── SubtitleClip ─────────────────────────────────────────────────────
    sub_clip = pm.SubtitleClip(srt_path=str(srt_out), style="netflix", fps=30)
    print(f"11. SubtitleClip: style={sub_clip.style}")

    # ── FadeToBlack + FadeToWhite transitions ────────────────────────────
    ftb = pm.FadeToBlack()
    ftw = pm.FadeToWhite()
    frame_a = np.full((100, 100, 4), [200, 150, 100, 255], dtype=np.uint8)
    frame_b = np.full((100, 100, 4), [50, 100, 200, 255], dtype=np.uint8)
    blended_b = ftb.render_frame(frame_a, frame_b, 0.5)
    blended_w = ftw.render_frame(frame_a, frame_b, 0.5)
    print(f"12. FadeToBlack mid={blended_b[:, :, :3].mean():.0f}")
    print(f"    FadeToWhite mid={blended_w[:, :, :3].mean():.0f}")

    # ── Composition with visible captions ─────────────────────────────────
    comp = pm.Composition(width=1920, height=1080, fps=30, duration=TOTAL)

    # Background
    bg_track = pm.Track(name="bg")
    bg = pm.ColorClip(color=theme.background)
    bg.set_duration(TOTAL)
    bg_track.clips.append(bg)
    comp.tracks.append(bg_track)

    # Content image — dimmed
    img_track = pm.Track(name="content")
    img = pm.ImageClip(str(ASSETS / "product_hero.jpg"))
    img.set_duration(TOTAL).set_opacity(0.3)
    img_track.clips.append(img)
    comp.tracks.append(img_track)

    # ── Visible caption text for each segment ─────────────────────────────
    # ADDED: visible text clips so captions are always on screen
    # Each segment gets its own scene with the caption text as primary element
    cap_track = pm.Track(name="captions")
    caption_styles = ["netflix", "youtube", "tiktok", "netflix", "youtube", "tiktok"]
    for i, seg in enumerate(segments):
        start_frame = int(seg.start_sec * 30)
        end_frame = int(seg.end_sec * 30)
        dur = end_frame - start_frame

        # Exercise render_caption_frame for coverage
        mid_sec = (seg.start_sec + seg.end_sec) / 2.0
        pm.render_caption_frame(
            [seg], time_sec=mid_sec, width=1920, height=1080, style=caption_styles[i]
        )

        # Primary: large caption text — center bottom
        # INCREASED size to 40px: principle 6, text readable at distance
        cap_text = pm.TextClip(
            text=seg.text,
            size=40,
            color=theme.text,
        )
        cap_text.set_duration(dur).at(start_frame).set_position(960, 800)
        cap_track.clips.append(cap_text)

        # Style label — small, bottom-right
        style_lbl = pm.TextClip(
            text=f"{caption_styles[i]} style",
            size=14,
            color=NEUTRAL.n500,
        )
        style_lbl.set_duration(dur).at(start_frame).set_position(1780, 1040).set_opacity(0.4)
        cap_track.clips.append(style_lbl)
    comp.tracks.append(cap_track)

    # Fade transition demo
    fade_track = pm.Track(name="fade_demo")
    fade_a = pm.ImageClip(str(ASSETS / "product_a.jpg"))
    fade_a.set_duration(150)
    fade_b = pm.ImageClip(str(ASSETS / "product_b.jpg"))
    fade_b.set_duration(150)
    faded = pm.concatenate(
        [fade_a, fade_b],
        transition=pm.FadeToBlack(),
        transition_duration=30,
    )
    faded.at(TOTAL - 300)
    fade_track.clips.append(faded)
    comp.tracks.append(fade_track)

    # ── Render ───────────────────────────────────────────────────────────
    output_path = OUTPUT_DIR / "08_captions.mp4"
    comp.render(str(output_path), preset="h264_fast")
    size_mb = output_path.stat().st_size / 1024 / 1024
    print(f"Rendered: {output_path} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
