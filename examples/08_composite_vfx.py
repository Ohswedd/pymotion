"""VFX Compositing Demo — PyMotion showcase.

Demonstrates professional compositing techniques: adjustment layers,
bezier and gradient masks, null-object parenting, chroma keying,
track mattes, blend modes, and expression-driven animation.  Produces
a 60-second, 30 fps composition with no external assets.

Showcased features:
    - AdjustmentLayer with colour correction effects
    - BezierMask for shape-based reveals
    - LinearGradientMask for gradient fades
    - NullObject parenting with orbiting child clips
    - Expression-driven rotation and position animation
    - TrackMatte (alpha mode) for shaped text reveals
    - Multiple blend modes (ADD, SCREEN, MULTIPLY)
    - ChromaKey on a green ColorClip
    - Multi-layer composite with 10+ tracks
"""

from __future__ import annotations

import math
from pathlib import Path

import structlog

from pymotion import (
    AdjustmentLayer,
    BezierMask,
    BezierPoint,
    BlendMode,
    Brightness,
    ChromaKey,
    ColorClip,
    Composition,
    Contrast,
    GradientClip,
    LinearGradientMask,
    NullObject,
    Saturation,
    ShapeClip,
    TextClip,
    Track,
    TrackMatte,
    Vignette,
    wiggle,
)
from pymotion.utils.math import Vec2

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
WIDTH = 1920
HEIGHT = 1080
FPS = 30
DURATION_SEC = 60
DURATION_FRAMES = FPS * DURATION_SEC  # 1800
CX = WIDTH / 2.0
CY = HEIGHT / 2.0


# ---------------------------------------------------------------------------
# Composition builder
# ---------------------------------------------------------------------------


def build_composition() -> Composition:
    """Assemble the VFX compositing demo."""
    comp = Composition(
        width=WIDTH,
        height=HEIGHT,
        fps=FPS,
        duration=DURATION_FRAMES,
        background="#0a0a14",
    )

    # ════════════════════════════════════════════════════════════════════
    # Track 1 — Dark gradient base
    # ════════════════════════════════════════════════════════════════════
    base_track = Track(name="base")
    base_bg = GradientClip(
        width=WIDTH,
        height=HEIGHT,
        color_start="#0a0a1e",
        color_end="#1a0a28",
        direction="radial",
    )
    base_bg.set_duration(DURATION_FRAMES).at(0)
    base_track.add(base_bg)
    comp.add_track(base_track)

    # ════════════════════════════════════════════════════════════════════
    # Track 2 — Chroma-keyed green screen demonstration
    # ════════════════════════════════════════════════════════════════════
    key_track = Track(name="chroma_key")

    # Green background with a coloured shape "subject" on top
    green_bg = ColorClip(width=600, height=400, color="#00FF00")
    green_bg.set_duration(DURATION_FRAMES).at(0)
    green_bg.set_position(100.0, 100.0)
    green_bg.add_effect(ChromaKey(color="#00FF00", tolerance=0.35, spill_suppression=0.6))
    key_track.add(green_bg)

    # "Subject" rectangle that remains after keying (non-green)
    subject = ShapeClip.rectangle(200, 200, fill_color="#E8475F")
    subject.set_duration(DURATION_FRAMES).at(0)
    subject.set_position(300.0, 200.0)
    subject.set_expression("position.x", lambda ctx: 300.0 + 50.0 * math.sin(ctx.time * 0.8))
    subject.set_expression("position.y", lambda ctx: 200.0 + 30.0 * math.cos(ctx.time * 1.2))
    key_track.add(subject)

    # Label
    key_label = TextClip(text="ChromaKey Demo", font_size=24, color="#AAAAAA")
    key_label.set_duration(DURATION_FRAMES).at(0).set_position(200.0, 80.0).set_opacity(0.7)
    key_track.add(key_label)

    comp.add_track(key_track)

    # ════════════════════════════════════════════════════════════════════
    # Track 3 — BezierMask reveal on a gradient panel
    # ════════════════════════════════════════════════════════════════════
    mask_track = Track(name="bezier_mask")

    masked_panel = GradientClip(
        width=500,
        height=400,
        color_start="#FF006E",
        color_end="#8338EC",
        direction="horizontal",
    )
    masked_panel.set_duration(DURATION_FRAMES).at(0)
    masked_panel.set_position(1300.0, 100.0)

    # Diamond-shaped bezier mask
    diamond_points = [
        BezierPoint(vertex=Vec2(250.0, 0.0)),
        BezierPoint(vertex=Vec2(500.0, 200.0)),
        BezierPoint(vertex=Vec2(250.0, 400.0)),
        BezierPoint(vertex=Vec2(0.0, 200.0)),
    ]
    diamond_mask = BezierMask(points=diamond_points, feather=12.0)
    masked_panel.add_mask(diamond_mask)
    mask_track.add(masked_panel)

    # Label
    bm_label = TextClip(text="BezierMask Reveal", font_size=24, color="#AAAAAA")
    bm_label.set_duration(DURATION_FRAMES).at(0).set_position(1400.0, 80.0).set_opacity(0.7)
    mask_track.add(bm_label)

    comp.add_track(mask_track)

    # ════════════════════════════════════════════════════════════════════
    # Track 4 — LinearGradientMask fade on a colour block
    # ════════════════════════════════════════════════════════════════════
    grad_mask_track = Track(name="gradient_mask")

    faded_block = ColorClip(width=500, height=300, color="#FFBE0B")
    faded_block.set_duration(DURATION_FRAMES).at(0)
    faded_block.set_position(100.0, 600.0)

    grad_mask = LinearGradientMask(
        start=Vec2(0.0, 0.0),
        end=Vec2(500.0, 0.0),
        feather=0.0,
    )
    faded_block.add_mask(grad_mask)
    grad_mask_track.add(faded_block)

    gm_label = TextClip(text="LinearGradientMask", font_size=24, color="#AAAAAA")
    gm_label.set_duration(DURATION_FRAMES).at(0).set_position(180.0, 580.0).set_opacity(0.7)
    grad_mask_track.add(gm_label)

    comp.add_track(grad_mask_track)

    # ════════════════════════════════════════════════════════════════════
    # Track 5 — NullObject parenting with orbiting children
    # ════════════════════════════════════════════════════════════════════
    orbit_track = Track(name="orbit")

    anchor = NullObject()
    anchor.set_duration(DURATION_FRAMES).at(0)
    anchor.set_position(CX, CY)
    # Spin the anchor slowly
    anchor.set_expression("rotation", lambda ctx: ctx.time * 30.0)
    orbit_track.add(anchor)

    orbit_colors = ["#FF006E", "#00FF87", "#00D4FF", "#FFBE0B", "#8338EC"]
    orbit_radius = 220.0

    for i, col in enumerate(orbit_colors):
        angle_offset = (2 * math.pi / len(orbit_colors)) * i
        orb = ShapeClip.circle(radius=20, fill_color=col)
        orb.set_duration(DURATION_FRAMES).at(0)
        # Position relative to parent — parent rotation will orbit them
        ox = orbit_radius * math.cos(angle_offset)
        oy = orbit_radius * math.sin(angle_offset)
        orb.set_position(ox, oy)
        orb.parent = anchor
        orb.set_opacity(0.8)

        # Each orb also wiggles slightly
        orb.set_expression("position.x", wiggle(1.5, 15.0, seed=i * 7))
        orbit_track.add(orb)

    orbit_label = TextClip(text="NullObject Parenting", font_size=24, color="#AAAAAA")
    orbit_label.set_duration(DURATION_FRAMES).at(0)
    orbit_label.set_position(CX - 110, CY + orbit_radius + 40).set_opacity(0.7)
    orbit_track.add(orbit_label)

    comp.add_track(orbit_track)

    # ════════════════════════════════════════════════════════════════════
    # Track 6 — TrackMatte (text shape used as alpha source)
    # ════════════════════════════════════════════════════════════════════
    matte_track = Track(name="track_matte")

    # The matte source — large white text (alpha channel drives visibility)
    matte_source = TextClip(text="VFX", font_size=200, color="#FFFFFF")
    matte_source.set_duration(DURATION_FRAMES).at(0)
    matte_source.set_position(700.0, 600.0)

    # Gradient that will be revealed through the text shape
    matte_fill = GradientClip(
        width=600,
        height=250,
        color_start="#FF006E",
        color_end="#00D4FF",
        direction="horizontal",
    )
    matte_fill.set_duration(DURATION_FRAMES).at(0)
    matte_fill.set_position(700.0, 600.0)

    track_matte = TrackMatte(source=matte_source, mode="alpha")
    matte_fill.add_mask(track_matte)
    matte_track.add(matte_fill)

    comp.add_track(matte_track)

    # ════════════════════════════════════════════════════════════════════
    # Track 7 — Blend mode demonstration strips
    # ════════════════════════════════════════════════════════════════════
    blend_track = Track(name="blend_demos")

    blend_modes = [
        (BlendMode.ADD, "#FF006E", "ADD"),
        (BlendMode.SCREEN, "#00FF87", "SCREEN"),
        (BlendMode.MULTIPLY, "#FFBE0B", "MULTIPLY"),
    ]
    for j, (mode, col, label) in enumerate(blend_modes):
        strip = ShapeClip.rectangle(180, 80, fill_color=col)
        strip.set_duration(DURATION_FRAMES).at(0)
        strip.set_position(1400.0, 580.0 + j * 100.0)
        strip.set_opacity(0.6)
        strip.blend_mode = mode
        blend_track.add(strip)

        lbl = TextClip(text=label, font_size=18, color="#FFFFFF")
        lbl.set_duration(DURATION_FRAMES).at(0)
        lbl.set_position(1450.0, 605.0 + j * 100.0)
        lbl.set_opacity(0.9)
        blend_track.add(lbl)

    bm_title = TextClip(text="Blend Modes", font_size=24, color="#AAAAAA")
    bm_title.set_duration(DURATION_FRAMES).at(0)
    bm_title.set_position(1420.0, 550.0).set_opacity(0.7)
    blend_track.add(bm_title)

    comp.add_track(blend_track)

    # ════════════════════════════════════════════════════════════════════
    # Track 8 — Expression-animated floating shapes
    # ════════════════════════════════════════════════════════════════════
    expr_track = Track(name="expressions", blend_mode=BlendMode.ADD)

    for i in range(8):
        shape = ShapeClip.circle(radius=12 + i * 4, fill_color="#ffffff10")
        shape.set_duration(DURATION_FRAMES).at(0)
        base_x = 200.0 + i * 200.0
        base_y = HEIGHT * 0.92
        shape.set_position(base_x, base_y)
        shape.set_opacity(0.15)
        # Gentle floating sine motion
        shape.set_expression(
            "position.y",
            lambda ctx, _by=base_y, _i=i: _by + 20.0 * math.sin(ctx.time * (0.5 + _i * 0.15)),
        )
        expr_track.add(shape)

    comp.add_track(expr_track)

    # ════════════════════════════════════════════════════════════════════
    # Track 9 — Section titles with timed visibility
    # ════════════════════════════════════════════════════════════════════
    title_track = Track(name="titles")

    sections = [
        (0, "COMPOSITING FUNDAMENTALS"),
        (450, "MASKING & KEYING"),
        (900, "PARENTING & EXPRESSIONS"),
        (1350, "FINAL COMPOSITE"),
    ]
    for start, label in sections:
        title = TextClip(text=label, font_size=36, color="#FFFFFF")
        title.set_duration(120).at(start)
        title.set_position(WIDTH / 2 - 18 * len(label) * 0.5, 30.0)
        title.set_expression(
            "opacity",
            lambda ctx: (
                min(1.0, ctx.local_frame / 20.0)
                if ctx.local_frame < 20
                else max(0.0, 1.0 - (ctx.local_frame - 100) / 20.0)
                if ctx.local_frame > 100
                else 1.0
            ),
        )
        title_track.add(title)

    comp.add_track(title_track)

    # ════════════════════════════════════════════════════════════════════
    # Track 10 — AdjustmentLayer (global colour correction)
    # ════════════════════════════════════════════════════════════════════
    adj_track = Track(name="adjustment")
    adj = AdjustmentLayer(
        effects=[
            Contrast(value=1.1),
            Brightness(value=0.05),
            Saturation(value=1.15),
            Vignette(strength=0.4),
        ]
    )
    adj.set_duration(DURATION_FRAMES).at(0)
    adj_track.add(adj)
    comp.add_track(adj_track)

    return comp


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Render the VFX compositing demo."""
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "08_composite_vfx.mp4"

    logger.info("building_composition")
    comp = build_composition()

    logger.info("rendering", output=str(output_path))
    comp.render(str(output_path), preset="h264_1080p")
    logger.info("render_complete", output=str(output_path))


if __name__ == "__main__":
    main()
