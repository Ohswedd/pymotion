"""Example 09 — Audio & Color Science Showcase.

Demonstrates v1.5 professional audio and color science features:
advanced audio mixing with bus routing and LUFS normalization,
audio visualization clips, captions, TTS integration, ACES color
pipeline, HSL secondary grading, video scopes, and EDL export.

Niche: Broadcast post-production / color grading workflows
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from pymotion import (
    AudioClipData,
    AudioMixer,
    BarChartClip,
    CaptionSegment,
    ChannelLayout,
    ColorClip,
    Composition,
    HistogramClip,
    LowerThird,
    ParadeScopeClip,
    SpectrumClip,
    TextClip,
    Track,
    TTSClip,
    VectorscopeClip,
    WaveformClip,
    WaveformScopeClip,
    WordTimestamp,
    aces_to_srgb,
    audio_crossfade,
    export_subtitles,
    srgb_to_aces,
)
from pymotion.utils.color import Color

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def demo_surround_bus_mixing() -> None:
    """5.1 surround mixing with bus routing and LUFS normalization."""
    mixer = AudioMixer(sample_rate=48000, channels=6, layout=ChannelLayout.SURROUND_51)

    # Synthetic dialogue (mono center)
    dialogue = np.random.default_rng(42).standard_normal((48000 * 3, 2)) * 0.4
    mixer.add(AudioClipData(samples=dialogue, start_sample=0), track="narrator")

    # Synthetic music (stereo)
    music = np.random.default_rng(7).standard_normal((48000 * 5, 2)) * 0.3
    mixer.add(AudioClipData(samples=music, start_sample=0), track="bg_music")

    # Create buses
    mixer.create_bus("dialogue")
    mixer.create_bus("music")
    mixer.assign_track_to_bus("narrator", "dialogue")
    mixer.assign_track_to_bus("bg_music", "music")
    mixer.set_bus_volume("dialogue", 1.0)
    mixer.set_bus_volume("music", 0.5)

    # Normalize to -14 LUFS for streaming
    mixer.normalize(target_lufs=-14)

    output = mixer.render()
    print(f"Surround mix: {output.shape[0]} samples, {output.shape[1]} channels")


def demo_audio_crossfade() -> None:
    """Crossfade two audio clips with equal-power curve."""
    rng = np.random.default_rng(42)
    clip_a = rng.standard_normal((48000 * 3, 2)) * 0.5
    clip_b = rng.standard_normal((48000 * 3, 2)) * 0.5

    result = audio_crossfade(clip_a, clip_b, fade_samples=24000, curve="equal_power")
    print(f"Crossfaded audio: {result.shape[0]} samples")


def demo_audio_visualization() -> None:
    """Audio waveform and spectrum visualization clips."""
    comp = Composition(1920, 1080, fps=30, duration=90)

    samples = np.random.default_rng(42).standard_normal((48000 * 3, 2)) * 0.5

    bg_track = Track(name="bg")
    bg = ColorClip(color="#0a0a1a").set_duration(90)
    bg_track.add(bg)

    # Waveform clip (top half)
    wave_track = Track(name="waveform")
    wave = WaveformClip(
        audio_samples=samples,
        style="bars",
        color="#00FF88",
        background="#111111",
        sample_rate=48000,
    )
    wave.set_duration(90).set_position(60.0, 60.0)
    wave_track.add(wave)

    # Spectrum clip (bottom half)
    spec_track = Track(name="spectrum")
    spectrum = SpectrumClip(
        audio_samples=samples,
        bands=32,
        style="bars",
        color_map=["#FF3366", "#FFCC00", "#00FF88"],
        sample_rate=48000,
    )
    spectrum.set_duration(90).set_position(60.0, 560.0)
    spec_track.add(spectrum)

    # Label
    label_track = Track(name="label")
    label = TextClip("Audio Visualization", font="Arial", size=36.0, color="#FFFFFF")
    label.set_duration(90).set_position(700.0, 20.0)
    label_track.add(label)

    comp.add_track(bg_track)
    comp.add_track(wave_track)
    comp.add_track(spec_track)
    comp.add_track(label_track)
    comp.render(str(OUTPUT_DIR / "09a_audio_viz.mp4"), preset="h264_1080p")


def demo_captions() -> None:
    """Caption segment creation and subtitle export."""
    segments = [
        CaptionSegment(
            start_time=0.0,
            end_time=2.0,
            text="Welcome to the broadcast.",
            words=[
                WordTimestamp(word="Welcome", start=0.0, end=0.5),
                WordTimestamp(word="to", start=0.5, end=0.7),
                WordTimestamp(word="the", start=0.7, end=0.9),
                WordTimestamp(word="broadcast.", start=0.9, end=2.0),
            ],
        ),
        CaptionSegment(
            start_time=2.5,
            end_time=5.0,
            text="Today we analyze Q4 results.",
        ),
    ]

    srt_path = OUTPUT_DIR / "09_captions.srt"
    export_subtitles(segments, str(srt_path), format="srt")
    print(f"Exported SRT: {srt_path}")


def demo_tts() -> None:
    """TTS clip generation (system engine — no API key required)."""
    tts = TTSClip(
        text="Quarterly revenue exceeded expectations by 25 percent.",
        engine="system",
        speed=1.0,
    )

    # TTSClip generates float64 stereo samples
    # In a real pipeline, these feed into AudioMixer
    try:
        samples = tts.generate()
        print(f"TTS generated: {samples.shape[0]} samples")
    except (ImportError, RuntimeError) as e:
        print(f"TTS skipped (missing dependency): {e}")


def demo_aces_pipeline() -> None:
    """ACES color space round-trip conversion."""
    # Create a synthetic colorful frame
    frame = np.zeros((64, 64, 4), dtype=np.uint8)
    frame[:, :, 0] = 50  # B
    frame[:, :, 1] = 120  # G
    frame[:, :, 2] = 200  # R
    frame[:, :, 3] = 255  # A

    # Convert to ACES AP0 (scene-linear)
    aces = srgb_to_aces(frame)
    print(f"ACES AP0 range: [{aces.min():.4f}, {aces.max():.4f}]")

    # Boost exposure in scene-linear space
    aces *= 1.3

    # Convert back with ACES filmic tone mapping
    graded = aces_to_srgb(aces)
    print(f"Graded frame: {graded.shape}, dtype={graded.dtype}")


def demo_color_grading() -> None:
    """HSL secondary grading and video scopes."""
    comp = Composition(1920, 1080, fps=30, duration=90)

    bg_track = Track(name="bg")
    bg = ColorClip(color="#2E4057").set_duration(90)
    bg_track.add(bg)

    # Chart as main content
    chart_track = Track(name="chart")
    chart = BarChartClip(
        data={"Jan": 80, "Feb": 110, "Mar": 95, "Apr": 140},
        animate_duration=30,
        theme="neon",
        title="Monthly Growth",
        show_values=True,
    )
    chart.set_duration(90)
    chart_track.add(chart)

    # Lower third with HSL secondary grade info
    lt_track = Track(name="lower_third")
    lt = LowerThird(
        name="Color Science Demo",
        title="HSL Secondary + Scopes",
        style="modern",
        animate_in=15,
        animate_out=15,
    )
    lt.set_duration(60).at(15)
    lt_track.add(lt)

    comp.add_track(bg_track)
    comp.add_track(chart_track)
    comp.add_track(lt_track)
    comp.render(str(OUTPUT_DIR / "09b_color_grading.mp4"), preset="h264_1080p")


def demo_video_scopes() -> None:
    """Render video scope visualizations from a synthetic frame."""
    # Create a colorful test frame
    source = np.zeros((64, 64, 4), dtype=np.uint8)
    source[:32, :32, 2] = 255  # Red quadrant
    source[:32, 32:, 1] = 255  # Green quadrant
    source[32:, :32, 0] = 255  # Blue quadrant
    source[32:, 32:] = [128, 128, 128, 255]  # Gray quadrant
    source[:, :, 3] = 255

    comp = Composition(1920, 540, fps=30, duration=60)

    bg_track = Track(name="bg")
    bg = ColorClip(color="#000000").set_duration(60)
    bg_track.add(bg)

    # Four scopes side by side
    scopes_track = Track(name="scopes")

    waveform = WaveformScopeClip(source_frame=source, color=Color.parse("#00FF00"))
    waveform.set_duration(60).set_position(0.0, 0.0)
    scopes_track.add(waveform)

    vectorscope = VectorscopeClip(source_frame=source)
    vectorscope.set_duration(60).set_position(480.0, 0.0)
    scopes_track.add(vectorscope)

    histogram = HistogramClip(source_frame=source, channels="rgb")
    histogram.set_duration(60).set_position(960.0, 0.0)
    scopes_track.add(histogram)

    parade = ParadeScopeClip(source_frame=source)
    parade.set_duration(60).set_position(1440.0, 0.0)
    scopes_track.add(parade)

    # Labels
    label_track = Track(name="labels")
    for i, name in enumerate(["Waveform", "Vectorscope", "Histogram", "Parade"]):
        label = TextClip(name, font="Arial", size=18.0, color="#AAAAAA")
        label.set_duration(60).set_position(i * 480.0 + 180.0, 510.0)
        label_track.add(label)

    comp.add_track(bg_track)
    comp.add_track(scopes_track)
    comp.add_track(label_track)
    comp.render(str(OUTPUT_DIR / "09c_video_scopes.mp4"), preset="h264_1080p")


def demo_edl_export() -> None:
    """Export a composition as CMX 3600 EDL."""
    comp = Composition(1920, 1080, fps=30, duration=300)

    bg = ColorClip(color="#0D1B2A").set_duration(300)
    comp.add(bg)

    edl_path = OUTPUT_DIR / "09_project.edl"
    comp.export_edl(edl_path)
    print(f"EDL exported: {edl_path}")


if __name__ == "__main__":
    demo_surround_bus_mixing()
    demo_audio_crossfade()
    demo_audio_visualization()
    demo_captions()
    demo_tts()
    demo_aces_pipeline()
    demo_color_grading()
    demo_video_scopes()
    demo_edl_export()
