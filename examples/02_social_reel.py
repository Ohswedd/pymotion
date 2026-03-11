"""Vertical social media reel — 1080x1920, 60 seconds at 60fps (3600 frames).

Demonstrates: vertical format for Instagram/TikTok, fast-paced editing,
bold text overlays with KineticText, CountDown intro, ProgressBar animation,
SocialHandle overlay, confetti particle burst, CallToAction component,
GradientClip backgrounds, quick section cuts, and energetic color palette.

All visuals are self-contained — no external asset files required.
"""

from __future__ import annotations

from pathlib import Path

import structlog

from pymotion import (
    AdjustmentLayer,
    BlendMode,
    CallToAction,
    Composition,
    CountDown,
    Countdown,
    GradientClip,
    KineticText,
    ProgressBar,
    ShapeClip,
    SocialHandle,
    TextClip,
    Track,
    TransitionTitle,
    Vignette,
    confetti,
)
from pymotion.utils.color import Color
from pymotion.utils.math import Vec2

logger = structlog.get_logger(__name__)

# ── Constants ─────────────────────────────────────────────────────────
WIDTH, HEIGHT = 1080, 1920
FPS = 60
TOTAL_FRAMES = 3600  # 60 seconds

# Energetic color palette
GRADIENT_START = "#FF6B35"
GRADIENT_END = "#F72585"
ACCENT_YELLOW = "#FFE500"
ACCENT_CYAN = "#00D4FF"
ACCENT_GREEN = "#00FF87"
BG_DARK = "#0A0A14"
TEXT_WHITE = "#FFFFFF"
TEXT_DARK = "#1A1A2E"


def _build_composition() -> Composition:
    """Assemble the vertical social reel composition."""
    comp = Composition(
        width=WIDTH,
        height=HEIGHT,
        fps=FPS,
        duration=TOTAL_FRAMES,
        background=BG_DARK,
    )

    # ── Track 1: Background gradients per section ─────────────────────
    bg_track = Track(name="backgrounds")

    # Section timings (in frames at 60fps)
    # Intro countdown: 0-360 (6s)
    # Section 1 "The Problem": 360-1080 (12s)
    # Section 2 "The Solution": 1080-1800 (12s)
    # Section 3 "Results": 1800-2700 (15s)
    # CTA outro: 2700-3600 (15s)

    sections = [
        ("#0A0A14", "#1A103D", 0, 360),
        ("#F72585", "#7209B7", 360, 720),
        ("#3A0CA3", "#4361EE", 720, 1440),
        ("#4CC9F0", "#4361EE", 1440, 2160),
        ("#7209B7", "#F72585", 2160, 2880),
        ("#0A0A14", "#1A103D", 2880, 3600),
    ]
    for c_start, c_end, frame_start, frame_end in sections:
        grad = GradientClip(
            color_start=c_start,
            color_end=c_end,
            direction=180.0,
        )
        grad.set_duration(frame_end - frame_start).at(frame_start)
        bg_track.add(grad)

    comp.add_track(bg_track)

    # ── Track 2: Decorative shapes ────────────────────────────────────
    decor_track = Track(name="decorations")

    # Horizontal accent bars between sections
    bar_positions = [360, 720, 1440, 2160, 2880]
    for bar_start in bar_positions:
        bar = ShapeClip.rect(
            x=0,
            y=HEIGHT // 2 - 3,
            w=WIDTH,
            h=6,
            fill=ACCENT_YELLOW,
        )
        bar.set_duration(30).at(bar_start).set_opacity(0.8)
        decor_track.add(bar)

    # Side accent strips
    left_strip = ShapeClip.rect(
        x=0,
        y=0,
        w=6,
        h=HEIGHT,
        fill=ACCENT_CYAN,
    )
    left_strip.set_duration(TOTAL_FRAMES).at(0).set_opacity(0.5)
    decor_track.add(left_strip)

    right_strip = ShapeClip.rect(
        x=WIDTH - 6,
        y=0,
        w=6,
        h=HEIGHT,
        fill=ACCENT_CYAN,
    )
    right_strip.set_duration(TOTAL_FRAMES).at(0).set_opacity(0.5)
    decor_track.add(right_strip)

    comp.add_track(decor_track)

    # ── Track 3: Countdown intro (0-360) ──────────────────────────────
    countdown_track = Track(name="countdown")

    # Visual countdown 3 -> 0
    cd = Countdown(
        from_n=3,
        count_duration=300,
        style="numbers",
        color=Color(1.0, 1.0, 1.0, 1.0),
        size=200.0,
    )
    cd.set_duration(300).at(30)
    countdown_track.add(cd)

    # "GET READY" text
    ready_text = TextClip(
        text="GET READY",
        font_size=36.0,
        color=ACCENT_YELLOW,
    )
    ready_text.set_duration(240).at(60).set_position(
        WIDTH / 2 - 120,
        HEIGHT / 2 + 200,
    )
    countdown_track.add(ready_text)

    comp.add_track(countdown_track)

    # ── Track 4: Main kinetic text content ────────────────────────────
    text_track = Track(name="text")

    # Section headers with TransitionTitle
    section_headers = [
        ("THE PROBLEM", "zoom", 380),
        ("THE SOLUTION", "slide_up", 740),
        ("THE RESULTS", "fade", 1460),
        ("JOIN US", "split", 2900),
    ]
    for header_text, style, start in section_headers:
        header = TransitionTitle(
            text=header_text,
            style=style,
            title_duration=80,
            animate_in=15,
            animate_out=15,
            font_size=64.0,
        )
        header.set_duration(80).at(start)
        text_track.add(header)

    # Kinetic text blocks — bold statements
    kinetic_blocks = [
        ("Video editing is SLOW", Vec2(80.0, 600.0), 500, 180),
        ("Rendering takes HOURS", Vec2(80.0, 600.0), 700, 120),
        ("Code-first is FAST", Vec2(80.0, 600.0), 860, 180),
        ("Write. Render. Ship.", Vec2(80.0, 600.0), 1060, 180),
        ("10x FASTER", Vec2(120.0, 700.0), 1560, 240),
        ("GPU Accelerated", Vec2(100.0, 700.0), 1820, 200),
        ("Production Ready", Vec2(100.0, 700.0), 2060, 200),
    ]
    for kt_text, pos, start, dur in kinetic_blocks:
        kt = KineticText(
            text=kt_text,
            font_size=56.0,
            color=Color(1.0, 1.0, 1.0, 1.0),
            frames_per_word=10,
            position=pos,
        )
        kt.set_duration(dur).at(start)
        text_track.add(kt)

    # CountDown for dramatic reveal
    dramatic_cd = CountDown(
        start_value=100.0,
        end_value=0.0,
        font_size=96.0,
        color=Color.parse(ACCENT_YELLOW),
        suffix="%",
        position=Vec2(WIDTH / 2 - 120, HEIGHT / 2 - 100),
    )
    dramatic_cd.set_duration(300).at(1500)
    text_track.add(dramatic_cd)

    # Supporting labels
    support_labels = [
        ("Manual effort eliminated", Vec2(200.0, HEIGHT / 2 + 80), 1600, 180),
        ("Fully automated pipeline", Vec2(180.0, HEIGHT / 2 + 160), 1700, 180),
    ]
    for lbl_text, pos, start, dur in support_labels:
        lbl = TextClip(
            text=lbl_text,
            font_size=28.0,
            color=TEXT_WHITE,
        )
        lbl.set_duration(dur).at(start).set_position(pos.x, pos.y)
        text_track.add(lbl)

    comp.add_track(text_track)

    # ── Track 5: Progress bar ─────────────────────────────────────────
    progress_track = Track(name="progress")

    # Animated progress bar showing video completion
    progress = ProgressBar(
        value=lambda frame: min(1.0, frame / TOTAL_FRAMES),
        bar_width=WIDTH - 80.0,
        bar_height=8.0,
        fill_color=Color.parse(ACCENT_CYAN),
        bg_color=Color(1.0, 1.0, 1.0, 0.15),
        radius=4.0,
    )
    progress.set_duration(TOTAL_FRAMES).at(0).set_position(40.0, HEIGHT - 60.0)
    progress_track.add(progress)

    comp.add_track(progress_track)

    # ── Track 6: Social handle ────────────────────────────────────────
    social_track = Track(name="social")

    handle = SocialHandle(
        platform="instagram",
        handle="@pymotion.dev",
        animate_in=20,
    )
    handle.set_duration(TOTAL_FRAMES - 120).at(60)
    social_track.add(handle)

    comp.add_track(social_track)

    # ── Track 7: Confetti burst ───────────────────────────────────────
    particle_track = Track(name="particles", blend_mode=BlendMode.ADD)

    # Confetti at climax — results section
    confetti_sys = confetti(WIDTH, HEIGHT)
    confetti_clip = confetti_sys.to_clip(duration=360)
    confetti_clip.at(2160)
    particle_track.add(confetti_clip)

    # Second burst at CTA
    confetti_sys2 = confetti(WIDTH, HEIGHT)
    confetti_clip2 = confetti_sys2.to_clip(duration=300)
    confetti_clip2.at(3000)
    particle_track.add(confetti_clip2)

    comp.add_track(particle_track)

    # ── Track 8: CTA ──────────────────────────────────────────────────
    cta_track = Track(name="cta")

    cta = CallToAction(
        text="Follow for More",
        sub_text="Link in Bio",
        style="subscribe",
        animate_in=20,
    )
    cta.set_duration(420).at(3060)
    cta_track.add(cta)

    comp.add_track(cta_track)

    # ── Track 9: Global effects ───────────────────────────────────────
    fx_track = Track(name="effects")

    vignette = AdjustmentLayer()
    vignette.add_effect(Vignette(strength=0.5, radius=0.75, feather=0.4))
    vignette.set_duration(TOTAL_FRAMES).at(0)
    fx_track.add(vignette)

    comp.add_track(fx_track)

    return comp


def main() -> None:
    """Build and render the social reel video."""
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "02_social_reel.mp4"

    logger.info("building_composition", width=WIDTH, height=HEIGHT, fps=FPS)
    comp = _build_composition()

    logger.info("rendering", output=str(output_path))
    comp.render(str(output_path), preset="h264_1080p")
    logger.info("render_complete", output=str(output_path))


if __name__ == "__main__":
    main()
