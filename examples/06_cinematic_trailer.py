"""Cinematic Trailer — PyMotion showcase.

Demonstrates the film-look pipeline: 24 fps, letterbox bars, film grain,
dramatic transitions, colour grading, and animated text reveals.  Produces
a 90-second cinematic trailer with no external assets.

Showcased features:
    - 24 fps cinematic framerate
    - Letterbox bars (2.39:1 aspect ratio overlay)
    - Dark dramatic colour palette with gradient backgrounds
    - FilmGrain effect for organic texture
    - GlitchText and SplitReveal animated text presets
    - IrisIn / IrisOut transitions via concatenate()
    - Colour grading: Contrast, SplitToning, Vignette, BleachBypass
    - Fade-to-black between acts (FadeToBlack transition)
    - Typewriter final title card
"""

from __future__ import annotations

from pathlib import Path

import structlog

from pymotion import (
    AdjustmentLayer,
    AudioClip,
    BleachBypass,
    BlendMode,
    Color,
    ColorClip,
    Composition,
    Contrast,
    FilmGrain,
    GradientClip,
    ImageClip,
    ShapeClip,
    SplitReveal,
    SplitToning,
    TextClip,
    Track,
    Typewriter,
    Vignette,
)
from pymotion.text.animated import GlitchText
from pymotion.utils.math import Vec2

logger = structlog.get_logger(__name__)

ASSETS = Path(__file__).parent / "assets"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
WIDTH = 1920
HEIGHT = 1080
FPS = 24
DURATION_SEC = 90
DURATION_FRAMES = FPS * DURATION_SEC  # 2160

# Letterbox bar height for 2.39:1 inside 16:9
LETTERBOX_H = int((HEIGHT - WIDTH / 2.39) / 2)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _letterbox_bar(y: float, duration: int, start: int = 0) -> ColorClip:
    """Create a black letterbox bar."""
    bar = ColorClip(width=WIDTH, height=LETTERBOX_H, color="#000000")
    bar.set_duration(duration).at(start).set_position(0.0, y)
    return bar


def _act_background(
    color_start: str,
    color_end: str,
    duration: int,
    start: int,
    direction: str = "radial",
) -> GradientClip:
    """Create a full-frame gradient background for an act."""
    bg = GradientClip(
        width=WIDTH,
        height=HEIGHT,
        color_start=color_start,
        color_end=color_end,
        direction=direction,
    )
    bg.set_duration(duration).at(start)
    return bg


def _section_title(
    text: str,
    y: float,
    start: int,
    duration: int,
    font_size: float = 64.0,
) -> TextClip:
    """Simple centred title with fade-in / fade-out expression."""
    clip = TextClip(text=text, font_size=font_size, color="#E0E0E0")
    clip.set_duration(duration).at(start)
    clip.set_position(WIDTH / 2 - font_size * len(text) * 0.25, y)
    clip.set_expression(
        "opacity",
        lambda ctx, _d=duration: (
            min(1.0, ctx.local_frame / 18.0)
            if ctx.local_frame < 18
            else max(0.0, 1.0 - (ctx.local_frame - (_d - 18)) / 18.0)
            if ctx.local_frame > _d - 18
            else 1.0
        ),
    )
    return clip


# ---------------------------------------------------------------------------
# Composition builder
# ---------------------------------------------------------------------------


def build_composition() -> Composition:
    """Assemble the three-act cinematic trailer."""
    comp = Composition(
        width=WIDTH,
        height=HEIGHT,
        fps=FPS,
        duration=DURATION_FRAMES,
        background="#000000",
    )

    # Frame boundaries for three acts + opening/closing
    # Opening : frames    0 –  168  (7 s)
    # Act I   : frames  168 –  720  (23 s)
    # Act II  : frames  720 – 1440  (30 s)
    # Act III : frames 1440 – 1920  (20 s)
    # Closing : frames 1920 – 2160  (10 s)

    # ── Background track ────────────────────────────────────────────────
    bg_track = Track(name="backgrounds")

    # Opening — deep black / dark blue
    bg_track.add(_act_background("#000000", "#0a0a1a", 168, 0))
    # Act I — dark teal
    bg_track.add(_act_background("#050f14", "#0a1e28", 552, 168, "vertical"))
    # Act II — dark crimson
    bg_track.add(_act_background("#140505", "#280a0a", 720, 720, "horizontal"))
    # Act III — deep purple
    bg_track.add(_act_background("#0a0514", "#1a0a28", 480, 1440, "radial"))
    # Closing — black
    bg_track.add(_act_background("#000000", "#050505", 240, 1920))

    # Optional cinematic landscape backgrounds per act
    _act_images = [
        (168, 552, "cine_landscape_1.jpg", 0.15),  # Act I
        (720, 720, "cine_landscape_2.jpg", 0.20),  # Act II
        (1440, 480, "cine_landscape_3.jpg", 0.25),  # Act III
        (1920, 240, "cine_landscape_4.jpg", 0.15),  # Closing
    ]
    for start_f, dur, filename, opacity in _act_images:
        img_path = ASSETS / filename
        if img_path.exists():
            landscape = ImageClip(str(img_path), fit_mode="cover")
            landscape.set_duration(dur).at(start_f).set_opacity(opacity)
            bg_track.add(landscape)
            logger.info("asset_loaded", file=filename, act_start=start_f)

    comp.add_track(bg_track)

    # ── Geometric accents track ─────────────────────────────────────────
    accent_track = Track(name="accents", blend_mode=BlendMode.ADD)

    # Thin horizontal lines sliding in per act
    for i, (start_f, col) in enumerate(
        [
            (180, "#1a3040"),
            (732, "#401a1a"),
            (1452, "#2a1a40"),
        ]
    ):
        line = ShapeClip.rectangle(WIDTH, 1, fill_color=col)
        y_pos = HEIGHT * (0.35 + 0.1 * i)
        line.set_duration(480).at(start_f).set_position(0.0, y_pos).set_opacity(0.4)
        line.set_expression(
            "opacity",
            lambda ctx, _: min(0.4, ctx.local_frame / 48.0 * 0.4),
        )
        accent_track.add(line)

    # Decorative circles
    for i in range(4):
        ring = ShapeClip.circle(
            radius=80 + i * 60,
            fill_color="#00000000",
            stroke_color="#ffffff08",
            stroke_width=1.0,
        )
        ring.set_duration(DURATION_FRAMES).at(0)
        ring.set_position(WIDTH * 0.7, HEIGHT * 0.4)
        ring.set_opacity(0.08)
        accent_track.add(ring)

    comp.add_track(accent_track)

    # ── Text track — dramatic reveals ──────────────────────────────────
    text_track = Track(name="text")

    # Opening glitch title
    opening_glitch = GlitchText(
        text="PYMOTION",
        font_size=96.0,
        color=Color(0.9, 0.9, 0.9, 1.0),
        glitch_intensity=0.5,
        position=Vec2(WIDTH / 2 - 280, HEIGHT / 2 - 50),
    )
    opening_glitch.set_duration(120).at(24)
    text_track.add(opening_glitch)

    # "presents" subtitle
    presents = TextClip(text="P R E S E N T S", font_size=28, color="#888888")
    presents.set_duration(96).at(48).set_position(WIDTH / 2 - 120, HEIGHT / 2 + 60)
    presents.set_expression(
        "opacity",
        lambda ctx: min(1.0, ctx.local_frame / 24.0) if ctx.local_frame < 24 else 1.0,
    )
    text_track.add(presents)

    # Act I title — SplitReveal
    act1_title = SplitReveal(
        text="ACT I: AWAKENING",
        font_size=56.0,
        color=Color(0.8, 0.9, 1.0, 1.0),
        reveal_frames=18,
        position=Vec2(WIDTH / 2 - 250, HEIGHT / 2 - 30),
    )
    act1_title.set_duration(144).at(192)
    text_track.add(act1_title)

    # Act I descriptive lines
    lines_act1 = [
        "In a world of pure code...",
        "frames become reality.",
    ]
    for j, line in enumerate(lines_act1):
        t = _section_title(line, HEIGHT * 0.55 + j * 50, 360 + j * 72, 168, 36.0)
        text_track.add(t)

    # Act II title — GlitchText
    act2_glitch = GlitchText(
        text="ACT II: CONVERGENCE",
        font_size=56.0,
        color=Color(1.0, 0.6, 0.6, 1.0),
        glitch_intensity=0.35,
        position=Vec2(WIDTH / 2 - 290, HEIGHT / 2 - 30),
    )
    act2_glitch.set_duration(144).at(744)
    text_track.add(act2_glitch)

    # Act II descriptive lines
    lines_act2 = [
        "Layers collapse. Pixels ignite.",
        "The composition takes form.",
    ]
    for j, line in enumerate(lines_act2):
        t = _section_title(line, HEIGHT * 0.55 + j * 50, 960 + j * 72, 168, 36.0)
        text_track.add(t)

    # Act III title — SplitReveal
    act3_title = SplitReveal(
        text="ACT III: RENDER",
        font_size=56.0,
        color=Color(0.8, 0.7, 1.0, 1.0),
        reveal_frames=18,
        position=Vec2(WIDTH / 2 - 220, HEIGHT / 2 - 30),
    )
    act3_title.set_duration(144).at(1464)
    text_track.add(act3_title)

    lines_act3 = [
        "Every frame, a masterpiece.",
        "Every pixel, intentional.",
    ]
    for j, line in enumerate(lines_act3):
        t = _section_title(line, HEIGHT * 0.55 + j * 50, 1632 + j * 72, 144, 36.0)
        text_track.add(t)

    # Closing — Typewriter title
    closing_tw = Typewriter(
        text="COMING SOON",
        font_size=80.0,
        color=Color(1.0, 1.0, 1.0, 1.0),
        chars_per_frame=0.3,
        position=Vec2(WIDTH / 2 - 300, HEIGHT / 2 - 50),
    )
    closing_tw.set_duration(192).at(1944)
    text_track.add(closing_tw)

    # Date subtitle
    date_text = TextClip(text="2 0 2 6", font_size=32, color="#AAAAAA")
    date_text.set_duration(144).at(2016).set_position(WIDTH / 2 - 60, HEIGHT / 2 + 50)
    date_text.set_expression(
        "opacity",
        lambda ctx: min(1.0, ctx.local_frame / 24.0),
    )
    text_track.add(date_text)

    comp.add_track(text_track)

    # ── Fade-to-black overlays between acts ─────────────────────────────
    fade_track = Track(name="fades")
    fade_points = [156, 708, 1428, 1908]  # frame before each act boundary
    for fp in fade_points:
        fade = ColorClip(width=WIDTH, height=HEIGHT, color="#000000")
        fade.set_duration(24).at(fp).set_opacity(0.0)
        fade.set_expression(
            "opacity",
            lambda ctx: (
                min(1.0, ctx.local_frame / 12.0)
                if ctx.local_frame < 12
                else max(0.0, 1.0 - (ctx.local_frame - 12) / 12.0)
            ),
        )
        fade_track.add(fade)
    comp.add_track(fade_track)

    # ── Letterbox bars (topmost visual layer) ───────────────────────────
    bar_track = Track(name="letterbox")
    bar_track.add(_letterbox_bar(0.0, DURATION_FRAMES))
    bar_track.add(_letterbox_bar(float(HEIGHT - LETTERBOX_H), DURATION_FRAMES))
    comp.add_track(bar_track)

    # ── Adjustment layer — film grade ──────────────────────────────────
    grade_track = Track(name="grade")
    adj = AdjustmentLayer(
        effects=[
            Contrast(value=1.25),
            SplitToning(
                highlight_color=Color.parse("#d4c5a0"),
                shadow_color=Color.parse("#1a2a3a"),
                balance=0.4,
            ),
            BleachBypass(strength=0.2),
            FilmGrain(strength=0.12),
            Vignette(strength=0.6),
        ]
    )
    adj.set_duration(DURATION_FRAMES).at(0)
    grade_track.add(adj)
    comp.add_track(grade_track)

    # Attach cinematic soundtrack if available
    _music_path = ASSETS / "music_cinematic.wav"
    if _music_path.exists():
        music = AudioClip(str(_music_path), volume=0.7)
        comp.audio_clips = [music]
        logger.info("audio_attached", source="music_cinematic.wav")

    return comp


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Render the cinematic trailer example."""
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "06_cinematic_trailer.mp4"

    logger.info("building_composition")
    comp = build_composition()

    logger.info("rendering", output=str(output_path))
    comp.render(str(output_path), preset="h264_1080p")
    logger.info("render_complete", output=str(output_path))


if __name__ == "__main__":
    main()
