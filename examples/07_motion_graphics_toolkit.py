"""Example 07 — Motion Graphics Toolkit.

Demonstrates v1.3 advanced compositing features: nested compositions,
adjustment layers, masking, expressions, parenting, and path animation.

Niche: Motion graphics / broadcast design
"""

from __future__ import annotations

import math
from pathlib import Path

from pymotion import (
    AdjustmentLayer,
    BezierMask,
    BezierPoint,
    ColorClip,
    Composition,
    LinearGradientMask,
    MaskOp,
    NullObject,
    StrokeClip,
    TextClip,
    Track,
    Vec2,
    Vignette,
    follow_path,
    morph_paths,
    wiggle,
)
from pymotion.effects.color import Brightness, Contrast
from pymotion.text.animated import Typewriter
from pymotion.utils.color import Color

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def make_color_clip(color: str, duration: int = 90) -> ColorClip:
    """Create a color clip with the given hex color and duration."""
    clip = ColorClip(color=Color.parse(color))
    clip.set_duration(duration)
    return clip


# ---------------------------------------------------------------------------
# Demo: Nested compositions (pre-comps)
# ---------------------------------------------------------------------------


def demo_nested_compositions() -> Composition:
    """Build a title card as a pre-comp and nest it in the main comp."""
    # Inner comp: title card at half resolution
    inner = Composition(960, 540, fps=30, duration=90)

    inner_bg_track = Track(name="inner_bg")
    inner_bg = make_color_clip("#E94560", 90)
    inner_bg_track.add(inner_bg)

    inner_text_track = Track(name="inner_text")
    title = TextClip("BREAKING NEWS", font="Arial", size=48.0, color="#FFFFFF")
    title.set_duration(90).set_position(480.0, 270.0)
    inner_text_track.add(title)

    inner.add_track(inner_bg_track)
    inner.add_track(inner_text_track)

    # Outer comp: nest the title card at bottom
    outer = Composition(1920, 1080, fps=30, duration=90)

    bg_track = Track(name="bg")
    bg = make_color_clip("#0D1B2A", 90)
    bg_track.add(bg)

    nested_track = Track(name="nested")
    nested = inner.to_clip()
    nested.set_duration(90).set_position(960.0, 810.0)
    nested_track.add(nested)

    label_track = Track(name="label")
    label = Typewriter(
        text="Nested Composition (pre-comp)",
        font_size=40.0,
        color=Color(1.0, 0.84, 0.0, 1.0),
        chars_per_frame=2.0,
    )
    label.set_duration(90).set_position(960.0, 100.0)
    label_track.add(label)

    outer.add_track(bg_track)
    outer.add_track(nested_track)
    outer.add_track(label_track)
    return outer


# ---------------------------------------------------------------------------
# Demo: Adjustment layer
# ---------------------------------------------------------------------------


def demo_adjustment_layer() -> Composition:
    """Apply a vignette and contrast boost to all layers below."""
    duration = 120
    comp = Composition(1920, 1080, fps=30, duration=duration)

    # Background
    bg_track = Track(name="bg")
    bg = make_color_clip("#1a1a2e", duration)
    bg_track.add(bg)

    # Some content
    content_track = Track(name="content")
    box1 = make_color_clip("#E94560", duration)
    box1.set_position(600.0, 400.0).set_scale(0.3, 0.3)
    content_track.add(box1)

    box2 = make_color_clip("#4FC3F7", duration)
    box2.set_position(1320.0, 400.0).set_scale(0.3, 0.3)
    content_track.add(box2)

    text_track = Track(name="text")
    label = TextClip("Before & After", font="Arial", size=56.0, color="#FFFFFF")
    label.set_duration(duration).set_position(960.0, 700.0)
    text_track.add(label)

    # Adjustment layer on top
    adj_track = Track(name="adjust")
    adj = AdjustmentLayer()
    adj.set_duration(duration)
    adj.add_effect(Vignette(strength=0.6, radius=0.7))
    adj.add_effect(Contrast(value=1.3))
    adj.add_effect(Brightness(value=1.1))
    adj_track.add(adj)

    comp.add_track(bg_track)
    comp.add_track(content_track)
    comp.add_track(text_track)
    comp.add_track(adj_track)
    return comp


# ---------------------------------------------------------------------------
# Demo: Masking
# ---------------------------------------------------------------------------


def demo_masking() -> Composition:
    """Shape masks with boolean operations and gradient masks."""
    duration = 90
    comp = Composition(1920, 1080, fps=30, duration=duration)

    bg_track = Track(name="bg")
    bg = make_color_clip("#0D1B2A", duration)
    bg_track.add(bg)

    # Red clip masked by a diamond bezier shape
    masked_track = Track(name="masked")
    red = make_color_clip("#E94560", duration)
    red.set_position(480.0, 540.0)

    diamond = BezierMask(
        points=[
            BezierPoint(vertex=Vec2(480.0, 240.0)),
            BezierPoint(vertex=Vec2(780.0, 540.0)),
            BezierPoint(vertex=Vec2(480.0, 840.0)),
            BezierPoint(vertex=Vec2(180.0, 540.0)),
        ]
    )
    red.add_mask(diamond, op=MaskOp.ADD)
    masked_track.add(red)

    # Blue clip with a gradient mask (fade from left to right)
    grad_track = Track(name="gradient")
    blue = make_color_clip("#4FC3F7", duration)
    blue.set_position(1440.0, 540.0)

    grad = LinearGradientMask(start=Vec2(1140.0, 540.0), end=Vec2(1740.0, 540.0))
    blue.add_mask(grad, op=MaskOp.ADD)
    grad_track.add(blue)

    label_track = Track(name="label")
    label = Typewriter(
        text="Bezier Mask + Gradient Mask",
        font_size=40.0,
        color=Color(1.0, 0.84, 0.0, 1.0),
        chars_per_frame=2.0,
    )
    label.set_duration(duration).set_position(960.0, 100.0)
    label_track.add(label)

    comp.add_track(bg_track)
    comp.add_track(masked_track)
    comp.add_track(grad_track)
    comp.add_track(label_track)
    return comp


# ---------------------------------------------------------------------------
# Demo: Expressions
# ---------------------------------------------------------------------------


def demo_expressions() -> Composition:
    """Drive position and opacity with expressions and wiggle."""
    duration = 150
    comp = Composition(1920, 1080, fps=30, duration=duration)

    bg_track = Track(name="bg")
    bg = make_color_clip("#0D1B2A", duration)
    bg_track.add(bg)

    # Bouncing box using expressions
    expr_track = Track(name="expr")
    box = make_color_clip("#E94560", duration)
    box.set_scale(0.15, 0.15)

    # Horizontal: linear drift
    box.set_expression("position.x", lambda ctx: 200.0 + ctx.local_frame * 10.0)
    # Vertical: sine bounce
    box.set_expression(
        "position.y",
        lambda ctx: 540.0 + 200.0 * math.sin(ctx.time * 3.0),
    )
    # Rotation: spin
    box.set_expression("rotation", lambda ctx: ctx.local_frame * 4.0)

    expr_track.add(box)

    # Wiggle on a second clip
    wiggle_track = Track(name="wiggle")
    dot = make_color_clip("#D4AF37", duration)
    dot.set_position(960.0, 540.0).set_scale(0.1, 0.1)
    dot.set_expression("position.x", wiggle(3.0, 80.0, seed=1))
    dot.set_expression("position.y", wiggle(2.0, 60.0, seed=2))
    wiggle_track.add(dot)

    label_track = Track(name="label")
    label = Typewriter(
        text="Expressions: bounce + wiggle",
        font_size=40.0,
        color=Color(1.0, 0.84, 0.0, 1.0),
        chars_per_frame=2.0,
    )
    label.set_duration(duration).set_position(960.0, 100.0)
    label_track.add(label)

    comp.add_track(bg_track)
    comp.add_track(expr_track)
    comp.add_track(wiggle_track)
    comp.add_track(label_track)
    return comp


# ---------------------------------------------------------------------------
# Demo: Parenting with NullObject
# ---------------------------------------------------------------------------


def demo_parenting() -> Composition:
    """Rotate a group of clips around a shared pivot using NullObject."""
    duration = 120
    comp = Composition(1920, 1080, fps=30, duration=duration)

    bg_track = Track(name="bg")
    bg = make_color_clip("#0D1B2A", duration)
    bg_track.add(bg)

    # Parent pivot in center, rotating via expression
    pivot = NullObject()
    pivot.set_position(960.0, 540.0).set_duration(duration)
    pivot.set_expression("rotation", lambda ctx: ctx.local_frame * 3.0)

    # Five child dots orbiting the pivot
    orbit_track = Track(name="orbit")
    colors = ["#E94560", "#4FC3F7", "#D4AF37", "#00E676", "#FF6F61"]
    for i, c in enumerate(colors):
        dot = make_color_clip(c, duration)
        dot.parent = pivot
        dot.set_position(float(150 + i * 40), 0.0)
        dot.set_scale(0.06, 0.06)
        orbit_track.add(dot)

    label_track = Track(name="label")
    label = Typewriter(
        text="Parenting: NullObject pivot",
        font_size=40.0,
        color=Color(1.0, 0.84, 0.0, 1.0),
        chars_per_frame=2.0,
    )
    label.set_duration(duration).set_position(960.0, 100.0)
    label_track.add(label)

    comp.add_track(bg_track)
    comp.add_track(orbit_track)
    comp.add_track(label_track)
    return comp


# ---------------------------------------------------------------------------
# Demo: Path animation + StrokeClip
# ---------------------------------------------------------------------------


def demo_path_animation() -> Composition:
    """Animate a clip along an SVG path and draw a stroke."""
    duration = 120
    comp = Composition(1920, 1080, fps=30, duration=duration)

    bg_track = Track(name="bg")
    bg = make_color_clip("#0D1B2A", duration)
    bg_track.add(bg)

    # Draw-on stroke effect
    stroke_track = Track(name="stroke")
    stroke = StrokeClip(
        path="M 300 600 C 600 200 1000 200 1300 600 C 1400 800 1600 800 1700 600",
        stroke_color="#D4AF37",
        stroke_width=3.0,
        trim_start=0.0,
        trim_end=1.0,
    )
    stroke.set_duration(duration)
    stroke_track.add(stroke)

    # Clip following the same path
    follower_track = Track(name="follower")
    dot = make_color_clip("#E94560", duration)
    dot.set_scale(0.04, 0.04)
    follow_path(
        dot,
        "M 300 600 C 600 200 1000 200 1300 600 C 1400 800 1600 800 1700 600",
        duration,
        align=True,
    )
    follower_track.add(dot)

    label_track = Track(name="label")
    label = Typewriter(
        text="Path Animation + StrokeClip",
        font_size=40.0,
        color=Color(1.0, 0.84, 0.0, 1.0),
        chars_per_frame=2.0,
    )
    label.set_duration(duration).set_position(960.0, 100.0)
    label_track.add(label)

    comp.add_track(bg_track)
    comp.add_track(stroke_track)
    comp.add_track(follower_track)
    comp.add_track(label_track)
    return comp


# ---------------------------------------------------------------------------
# Demo: Path morphing
# ---------------------------------------------------------------------------


def demo_path_morphing() -> Composition:
    """Morph between a square and a diamond shape."""
    duration = 90
    comp = Composition(1920, 1080, fps=30, duration=duration)

    bg_track = Track(name="bg")
    bg = make_color_clip("#0D1B2A", duration)
    bg_track.add(bg)

    square = "M 760 340 L 1160 340 L 1160 740 L 760 740 Z"
    diamond = "M 960 240 L 1260 540 L 960 840 L 660 540 Z"

    info_track = Track(name="info")
    for i, progress in enumerate([0.0, 0.25, 0.5, 0.75, 1.0]):
        morphed = morph_paths(square, diamond, progress)
        # Show a StrokeClip of the morphed path at each progress step
        morph_stroke = StrokeClip(
            path=morphed,
            stroke_color="#D4AF37",
            stroke_width=2.0,
        )
        morph_stroke.set_duration(duration)
        info_track.add(morph_stroke)

        info_label = TextClip(
            f"progress={progress:.2f}",
            font="Arial",
            size=24.0,
            color="#FFFFFF",
        )
        x_pos = 200.0 + i * 380.0
        info_label.set_duration(duration).set_position(x_pos, 900.0)
        info_track.add(info_label)

    label_track = Track(name="label")
    label = Typewriter(
        text="Path Morphing: square -> diamond",
        font_size=40.0,
        color=Color(1.0, 0.84, 0.0, 1.0),
        chars_per_frame=2.0,
    )
    label.set_duration(duration).set_position(960.0, 100.0)
    label_track.add(label)

    comp.add_track(bg_track)
    comp.add_track(info_track)
    comp.add_track(label_track)
    return comp


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the v1.3 motion graphics toolkit showcase."""
    print("=== PyMotion v1.3 Motion Graphics Toolkit ===\n")

    demos = [
        ("07_nested_comps.mp4", "Nested compositions", demo_nested_compositions),
        ("07_adjustment_layer.mp4", "Adjustment layer", demo_adjustment_layer),
        ("07_masking.mp4", "Masking", demo_masking),
        ("07_expressions.mp4", "Expressions", demo_expressions),
        ("07_parenting.mp4", "Parenting", demo_parenting),
        ("07_path_animation.mp4", "Path animation", demo_path_animation),
        ("07_path_morphing.mp4", "Path morphing", demo_path_morphing),
    ]

    for i, (filename, label, fn) in enumerate(demos, 1):
        print(f"[{i}/{len(demos)}] {label}...")
        comp = fn()
        comp.render(str(OUTPUT_DIR / filename), preset="h264_1080p")

    print(f"\nAll {len(demos)} demos rendered to examples/output/")


if __name__ == "__main__":
    main()
