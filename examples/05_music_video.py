"""Audio-Reactive Music Video — PyMotion showcase.

Demonstrates audio visualization, particle effects, expression-driven
animation, and blend mode compositing.  Generates a 120-second, 60 fps
music video driven entirely by synthetic audio (no external files).

Showcased features:
    - Synthetic audio generation with numpy sine waves
    - WaveformClip and SpectrumClip audio visualizations
    - AudioReactiveEffect modulating visual parameters
    - Particle systems (fire, sparkles) with BlendMode.ADD
    - Expression-driven animation (wiggle, custom sine)
    - NeonGlow, Bloom, Vignette, ChromaticAberration effects
    - Multiple blend-mode layers (ADD, SCREEN)
    - GradientClip and ColorClip backgrounds
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import structlog

from pymotion import (
    AdjustmentLayer,
    AudioClip,
    AudioReactiveEffect,
    BlendMode,
    Bloom,
    ChromaticAberration,
    Color,
    ColorClip,
    Composition,
    Contrast,
    GradientClip,
    ImageClip,
    NeonGlow,
    ShapeClip,
    SpectrumClip,
    TextClip,
    Track,
    Vignette,
    WaveformClip,
    fire,
    sparkles,
    wiggle,
)

logger = structlog.get_logger(__name__)

ASSETS = Path(__file__).parent / "assets"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
WIDTH = 1920
HEIGHT = 1080
FPS = 60
DURATION_SEC = 120
DURATION_FRAMES = FPS * DURATION_SEC  # 7200
SAMPLE_RATE = 48000


# ---------------------------------------------------------------------------
# Synthetic audio
# ---------------------------------------------------------------------------


def _generate_audio(duration_sec: int, sample_rate: int) -> np.ndarray:
    """Build a layered synthetic audio signal from sine waves.

    Creates bass, mid, and high frequency components with slow amplitude
    modulation so the visualizers have interesting dynamics.

    Returns:
        Mono float64 audio array of shape ``(n_samples,)``.
    """
    n = duration_sec * sample_rate
    t = np.linspace(0.0, duration_sec, n, dtype=np.float64)

    # Bass pulse (60 Hz, amplitude-modulated at 0.5 Hz)
    bass = np.sin(2 * np.pi * 60 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.5 * t))

    # Mid chord (220 Hz + 330 Hz, AM at 1/3 Hz)
    mid = (0.3 * np.sin(2 * np.pi * 220 * t) + 0.2 * np.sin(2 * np.pi * 330 * t)) * (
        0.4 + 0.6 * np.sin(2 * np.pi * (1.0 / 3.0) * t)
    )

    # High shimmer (880 Hz, AM at 2 Hz)
    high = 0.15 * np.sin(2 * np.pi * 880 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 2.0 * t))

    # Percussive hits every 0.5 s — short decaying bursts
    hit_period = int(0.5 * sample_rate)
    perc = np.zeros(n, dtype=np.float64)
    for start in range(0, n, hit_period):
        length = min(int(0.05 * sample_rate), n - start)
        decay = np.exp(-np.linspace(0, 8, length))
        perc[start : start + length] += (
            0.4 * decay * np.sin(2 * np.pi * 150 * np.linspace(0, length / sample_rate, length))
        )

    signal = bass + mid + high + perc
    # Normalize to [-1, 1]
    peak = np.max(np.abs(signal))
    if peak > 0:
        signal /= peak
    return signal


# ---------------------------------------------------------------------------
# Composition builder
# ---------------------------------------------------------------------------


def build_composition() -> Composition:
    """Assemble the music-video composition."""
    # Prefer real music asset; fall back to synthetic audio for visualizers
    _music_path = ASSETS / "music_electronic.wav"
    if _music_path.exists():
        _music_clip = AudioClip(str(_music_path), volume=0.8)
        logger.info("music_asset_loaded", file="music_electronic.wav")
    else:
        _music_clip = None

    audio = _generate_audio(DURATION_SEC, SAMPLE_RATE)
    logger.info("audio_generated", samples=len(audio))

    comp = Composition(
        width=WIDTH,
        height=HEIGHT,
        fps=FPS,
        duration=DURATION_FRAMES,
        background="#050510",
    )

    # -- Track 1: animated gradient background --------------------------------
    bg_track = Track(name="background")
    gradient = GradientClip(
        width=WIDTH,
        height=HEIGHT,
        color_start="#0a001a",
        color_end="#1a0030",
        direction="radial",
    )
    gradient.set_duration(DURATION_FRAMES).at(0)
    gradient.set_expression(
        "opacity",
        lambda ctx: 0.7 + 0.3 * math.sin(ctx.time * 0.2),
    )
    bg_track.add(gradient)

    # Optional stock photo backgrounds for each section
    _section_bgs = [
        (0, "mv_bg_1.jpg", 0.2),
        (1800, "mv_bg_2.jpg", 0.25),
        (3600, "mv_bg_3.jpg", 0.3),
    ]
    for start_frame, filename, opacity in _section_bgs:
        img_path = ASSETS / filename
        if img_path.exists():
            bg_img = ImageClip(str(img_path), fit_mode="cover")
            bg_img.set_duration(1800).at(start_frame).set_opacity(opacity)
            bg_track.add(bg_img)
            logger.info("asset_loaded", file=filename, start=start_frame)

    comp.add_track(bg_track)

    # -- Track 2: waveform visualisation --------------------------------------
    wave_track = Track(name="waveform")
    waveform = WaveformClip(
        audio=audio,
        style="line",
        color=Color.parse("#00FF87"),
        background=Color.parse("#00000000"),
        sample_rate=SAMPLE_RATE,
    )
    waveform.set_duration(DURATION_FRAMES).at(0).set_opacity(0.6)
    waveform.set_position(0.0, HEIGHT * 0.55)
    wave_track.add(waveform)
    wave_track.blend_mode = BlendMode.ADD
    comp.add_track(wave_track)

    # -- Track 3: spectrum analyser -------------------------------------------
    spec_track = Track(name="spectrum")
    spectrum = SpectrumClip(
        audio=audio,
        bands=48,
        style="smooth",
        color_map=[
            Color.parse("#FF006E"),
            Color.parse("#FB5607"),
            Color.parse("#FFBE0B"),
        ],
        background=Color.parse("#00000000"),
        sample_rate=SAMPLE_RATE,
    )
    spectrum.set_duration(DURATION_FRAMES).at(0).set_opacity(0.5)
    spectrum.set_position(0.0, HEIGHT * 0.25)
    spec_track.add(spectrum)
    spec_track.blend_mode = BlendMode.SCREEN
    comp.add_track(spec_track)

    # -- Track 4: fire particles (bottom) ------------------------------------
    fire_track = Track(name="fire", blend_mode=BlendMode.ADD)
    fire_ps = fire(WIDTH, HEIGHT)
    fire_clip = fire_ps.to_clip(DURATION_FRAMES).at(0)
    fire_clip.set_opacity(0.7)
    fire_track.add(fire_clip)
    comp.add_track(fire_track)

    # -- Track 5: sparkle particles (centre) ---------------------------------
    spark_track = Track(name="sparkles", blend_mode=BlendMode.ADD)
    spark_ps = sparkles(WIDTH, HEIGHT)
    spark_clip = spark_ps.to_clip(DURATION_FRAMES).at(0)
    spark_clip.set_opacity(0.5)
    spark_clip.set_expression("opacity", lambda ctx: 0.3 + 0.4 * abs(math.sin(ctx.time * 1.5)))
    spark_track.add(spark_clip)
    comp.add_track(spark_track)

    # -- Track 6: neon accent shapes with wiggle expressions ------------------
    accent_track = Track(name="accents", blend_mode=BlendMode.ADD)

    for i in range(6):
        circle = ShapeClip.circle(
            radius=40 + i * 15,
            fill_color="#00000000",
            stroke_color=["#FF006E", "#00FF87", "#00D4FF", "#FFBE0B", "#8338EC", "#FF5400"][i],
            stroke_width=2.0,
        )
        cx = WIDTH * (0.15 + 0.14 * i)
        cy = HEIGHT * 0.5
        circle.set_duration(DURATION_FRAMES).at(0)
        circle.set_position(cx, cy)
        circle.set_opacity(0.35)
        circle.set_expression("position.x", wiggle(0.8 + i * 0.2, 60.0, seed=i))
        circle.set_expression("position.y", wiggle(0.6 + i * 0.15, 40.0, seed=i + 100))
        accent_track.add(circle)

    comp.add_track(accent_track)

    # -- Track 7: section titles (appear at key moments) ---------------------
    text_track = Track(name="titles")
    sections = [
        (0, "OVERTURE"),
        (1800, "RISING PULSE"),
        (3600, "NEON CASCADE"),
        (5400, "FINALE"),
    ]
    for start_frame, label in sections:
        title = TextClip(text=label, font_size=72, color="#FFFFFF")
        title.set_duration(180).at(start_frame)
        title.set_position(WIDTH / 2 - 200, HEIGHT * 0.12)
        title.set_opacity(0.0)
        # Fade in then out via expression
        title.set_expression(
            "opacity",
            lambda ctx, _dur=180: (
                min(1.0, ctx.local_frame / 30.0)
                if ctx.local_frame < 30
                else max(0.0, 1.0 - (ctx.local_frame - (_dur - 30)) / 30.0)
                if ctx.local_frame > _dur - 30
                else 1.0
            ),
        )
        text_track.add(title)

    comp.add_track(text_track)

    # -- Track 8: beat pulse (colour overlay reacting to audio) ---------------
    pulse_track = Track(name="pulse", blend_mode=BlendMode.ADD)
    pulse = ColorClip(width=WIDTH, height=HEIGHT, color="#FF006E")
    pulse.set_duration(DURATION_FRAMES).at(0).set_opacity(0.0)

    neon = NeonGlow(strength=0.6)
    _reactive = AudioReactiveEffect(
        effect=neon,
        audio=audio,
        property_name="strength",
        band="low",
        sensitivity=2.5,
        sample_rate=SAMPLE_RATE,
        min_value=0.0,
        max_value=1.0,
    )
    pulse.add_effect(neon)
    # Drive opacity by bass amplitude via expression
    pulse.set_expression(
        "opacity",
        lambda ctx: min(0.25, 0.25 * abs(math.sin(ctx.time * math.pi * 2))),
    )
    pulse_track.add(pulse)
    comp.add_track(pulse_track)

    # -- Track 9: adjustment layer — global grade -----------------------------
    grade_track = Track(name="grade")
    adj = AdjustmentLayer(
        effects=[
            Vignette(),
            Bloom(strength=0.15),
            ChromaticAberration(strength=0.004),
            Contrast(value=1.15),
        ]
    )
    adj.set_duration(DURATION_FRAMES).at(0)
    grade_track.add(adj)
    comp.add_track(grade_track)

    # Attach real music audio when available (replaces synthetic sine waves)
    if _music_clip is not None:
        comp.audio_clips = [_music_clip]
        logger.info("audio_attached", source="music_electronic.wav")

    return comp


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Render the music-video example."""
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "05_music_video.mp4"

    logger.info("building_composition")
    comp = build_composition()

    logger.info("rendering", output=str(output_path))
    comp.render(str(output_path), preset="h264_1080p")
    logger.info("render_complete", output=str(output_path))


if __name__ == "__main__":
    main()
