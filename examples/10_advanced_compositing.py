"""EX10 — Advanced Compositing.

Use-case: A multi-layered compositing demo with masks, expressions,
path animations, and null objects — the toolbox for complex motion design.

Features exercised:
  NullObject,
  BezierMask, BezierPoint, LinearGradientMask, RadialGradientMask,
  TextMask, Mask, MaskGroup, MaskOp,
  ExpressionContext, ExpressionFn, wiggle, loop_in, loop_out,
  StrokeClip, follow_path, morph_paths

Output: 1920x1080, 30fps, 20s, preset h264_fast -> outputs/10_compositing.mp4
Estimated render time: ~30s
"""

from __future__ import annotations

from pathlib import Path

import pymotion as pm

ASSETS = Path(__file__).parent / "assets"
OUTPUT_DIR = Path(__file__).parent.parent / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

SEC = 100  # ~3.3s per section
TOTAL = SEC * 6  # 6 sections = 20s


def main() -> None:
    comp = pm.Composition(width=1920, height=1080, fps=30, duration=TOTAL)

    # ── Background ───────────────────────────────────────────────────────
    bg_track = pm.Track(name="bg")
    bg = pm.GradientClip(color_start="#0a0a1a", color_end="#1a0a2e", direction=135.0)
    bg.set_duration(TOTAL)
    bg_track.clips.append(bg)
    comp.tracks.append(bg_track)

    # ── Section 1: NullObject + Expressions ──────────────────────────────
    offset = 0
    sec1 = pm.Track(name="sec1_null_expr")

    null = pm.NullObject()
    null.set_duration(SEC).at(offset).set_position(960, 540)
    print(f"1. NullObject: {type(null).__name__}")

    # ExpressionContext
    expr_ctx = pm.ExpressionContext(
        frame=0,
        time=0.0,
        fps=30,
        comp_width=1920,
        comp_height=1080,
        progress=0.0,
        local_frame=0,
    )
    print(f"2. ExpressionContext: frame={expr_ctx.frame}, fps={expr_ctx.fps}")

    # ExpressionFn via wiggle
    wiggle_fn: pm.ExpressionFn = pm.wiggle(freq=2.0, amp=50.0, seed=42)
    wiggle_val = wiggle_fn(expr_ctx)
    print(f"3. wiggle(2.0, 50.0): value at f0={wiggle_val:.1f}")

    # loop_in / loop_out
    def base_fn(ctx: pm.ExpressionContext) -> float:
        return float(ctx.local_frame)

    looped_in = pm.loop_in(duration_frames=30, base_fn=base_fn)
    looped_out = pm.loop_out(duration_frames=30, base_fn=base_fn)
    li_val = looped_in(expr_ctx)
    lo_val = looped_out(expr_ctx)
    print(f"4. loop_in={li_val:.1f}, loop_out={lo_val:.1f}")

    # Apply wiggle to an image clip
    img1 = pm.ImageClip(str(ASSETS / "product_hero.jpg"))
    img1.set_duration(SEC).at(offset).set_opacity(0.8)
    img1.set_expression("position.x", pm.wiggle(freq=1.0, amp=30.0, seed=1))
    sec1.clips.append(null)
    sec1.clips.append(img1)
    comp.tracks.append(sec1)

    # ── Section 2: BezierMask ────────────────────────────────────────────
    offset = SEC
    sec2 = pm.Track(name="sec2_bezier")
    img2 = pm.ImageClip(str(ASSETS / "product_a.jpg"))
    img2.set_duration(SEC).at(offset)

    bezier = pm.BezierMask(
        points=[
            pm.BezierPoint(
                vertex=pm.Vec2(400, 200),
                out_handle=pm.Vec2(600, 100),
            ),
            pm.BezierPoint(
                vertex=pm.Vec2(1500, 300),
                in_handle=pm.Vec2(1300, 100),
            ),
            pm.BezierPoint(
                vertex=pm.Vec2(1400, 800),
                in_handle=pm.Vec2(1600, 600),
            ),
            pm.BezierPoint(
                vertex=pm.Vec2(500, 700),
                out_handle=pm.Vec2(300, 900),
            ),
        ],
        feather=15.0,
        expansion=0.0,
        invert=False,
        opacity=1.0,
    )
    img2.add_mask(bezier, op=pm.MaskOp.ADD)
    sec2.clips.append(img2)
    comp.tracks.append(sec2)
    # Demonstrate MaskGroup data structure
    group = pm.MaskGroup(mask=bezier, op=pm.MaskOp.ADD)
    print(f"5. BezierMask: {len(bezier.points)} points, feather={bezier.feather}")
    print(f"   BezierPoint vertex={bezier.points[0].vertex}")
    print(f"   MaskGroup op={group.op}")

    # ── Section 3: LinearGradientMask + RadialGradientMask ───────────────
    offset = SEC * 2
    sec3 = pm.Track(name="sec3_gradient_masks")
    img3a = pm.ImageClip(str(ASSETS / "product_b.jpg"))
    img3a.set_duration(SEC).at(offset)
    linear_mask = pm.LinearGradientMask(
        start=pm.Vec2(0.0, 0.0),
        end=pm.Vec2(1920.0, 1080.0),
        feather=100.0,
    )
    img3a.add_mask(linear_mask, op=pm.MaskOp.ADD)
    sec3.clips.append(img3a)

    img3b = pm.ImageClip(str(ASSETS / "product_c.jpg"))
    img3b.set_duration(SEC).at(offset).set_opacity(0.7)
    radial_mask = pm.RadialGradientMask(
        center=pm.Vec2(960.0, 540.0),
        radius=400.0,
        feather=50.0,
        invert=True,
    )
    img3b.add_mask(radial_mask, op=pm.MaskOp.SUBTRACT)
    sec3.clips.append(img3b)
    comp.tracks.append(sec3)
    print(f"6. LinearGradientMask: feather={linear_mask.feather}")
    print(f"   RadialGradientMask: r={radial_mask.radius}, invert={radial_mask.invert}")

    # ── Section 4: TextMask + MaskGroup + MaskOp ─────────────────────────
    offset = SEC * 3
    sec4 = pm.Track(name="sec4_textmask")
    img4 = pm.ImageClip(str(ASSETS / "product_hero.jpg"))
    img4.set_duration(SEC).at(offset)
    text_mask = pm.TextMask(
        text="PYMOTION",
        font="sans-serif",
        size=200.0,
        feather=5.0,
        invert=False,
    )
    img4.add_mask(text_mask, op=pm.MaskOp.INTERSECT)
    sec4.clips.append(img4)
    comp.tracks.append(sec4)
    print(f"7. TextMask: text={text_mask.text}, size={text_mask.size}")
    print(f"   MaskOp values: {[e.value for e in pm.MaskOp]}")

    # ── Section 5: StrokeClip + follow_path ──────────────────────────────
    offset = SEC * 4
    sec5 = pm.Track(name="sec5_paths")
    svg_path = "M 100 500 C 400 100 800 900 1200 300 S 1600 700 1800 400"
    stroke = pm.StrokeClip(
        path=svg_path,
        trim_start=0.0,
        trim_end=1.0,
        stroke_color="#00FFAA",
        stroke_width=4.0,
    )
    stroke.set_duration(SEC).at(offset)
    sec5.clips.append(stroke)

    # follow_path on a small shape
    dot = pm.ShapeClip.circle(cx=0, cy=0, r=15, fill="#FF6600")
    dot.set_duration(SEC).at(offset)
    pm.follow_path(dot, svg_path, duration=SEC, align=True)
    sec5.clips.append(dot)
    comp.tracks.append(sec5)
    print(f"8. StrokeClip: width={stroke.stroke_width}")
    print(f"   follow_path: align=True, dur={SEC}")

    # ── Section 6: morph_paths ───────────────────────────────────────────
    offset = SEC * 5
    sec6 = pm.Track(name="sec6_morph")
    path_a = "M 200 200 L 400 200 L 400 400 L 200 400 Z"
    path_b = "M 300 100 L 500 300 L 300 500 L 100 300 Z"
    morphed = pm.morph_paths(path_a, path_b, progress=0.5)
    print(f"9. morph_paths: result={morphed[:40]}...")

    morph_stroke = pm.StrokeClip(
        path=morphed,
        stroke_color="#FF00FF",
        stroke_width=3.0,
    )
    morph_stroke.set_duration(SEC).at(offset)
    sec6.clips.append(morph_stroke)
    comp.tracks.append(sec6)

    # ── Audit frames ─────────────────────────────────────────────────────
    audit_dir = Path(__file__).parent.parent / "audit"
    audit_dir.mkdir(exist_ok=True)
    for sec_idx in range(6):
        mid = sec_idx * SEC + SEC // 2
        try:
            comp.export_frame(frame=mid, output=audit_dir / f"ex10_sec{sec_idx + 1}.png")
        except (ValueError, RuntimeError) as e:
            print(f"  Audit sec{sec_idx + 1} skipped: {e}")
    print("Audit frames exported")

    # ── Render ───────────────────────────────────────────────────────────
    output_path = OUTPUT_DIR / "10_compositing.mp4"
    comp.render(str(output_path), preset="h264_fast")
    size_mb = output_path.stat().st_size / 1024 / 1024
    print(f"Rendered: {output_path} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
