"""EX01 — Layered Product Card.

Use-case: A static-to-animated product card for e-commerce email headers
or website hero sections.

Features exercised:
  Composition, CompositionClip, Track, ColorClip, GradientClip, ImageClip,
  ShapeClip (rect, circle, polygon, line), BlendMode (SCREEN, MULTIPLY,
  OVERLAY), Clip.set_position/set_scale/set_rotation/set_opacity/set_duration/at,
  Clip.add_effect, GaussianBlur, Vignette, Brightness, Contrast,
  Color, Vec2, Vec3, Effect, Align, Resolution, RenderContext, TimeRange,
  Keyframe, KeyframeTrack, animate, AnimatableValue, interpolate,
  EasingFn, get_easing, cubic_bezier, spring, steps,
  OutputPreset, get_preset, PyMotionConfig, get_config, set_config, reset_config,
  Transition, Cut, Fade, DipToColor,
  Bottleneck, ClipTiming, FrameProfile, MemoryReport, RenderProfile,
  benchmark, detect_bottlenecks, memory_report, profile_composition

Output: 1920x1080, 30fps, 30s, preset h264_fast -> outputs/01_core.mp4
Estimated render time: ~30s
"""

from __future__ import annotations

from pathlib import Path

import pymotion as pm

ASSETS = Path(__file__).parent / "assets"
OUTPUT_DIR = Path(__file__).parent.parent / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)


def main() -> None:
    # ── Config ────────────────────────────────────────────────────────────
    cfg = pm.get_config()
    print(f"Config: allow_network={cfg.allow_network}, cache_max={cfg.cache_max_bytes}")
    pm.set_config(pm.PyMotionConfig(allow_network=False))
    pm.reset_config()

    # ── Verify preset existence ───────────────────────────────────────────
    preset = pm.get_preset("h264_fast")
    print(f"Preset: {preset.name}, codec={preset.codec}")

    # ── Demonstrate core types ────────────────────────────────────────────
    c1 = pm.Color.parse("#3366CC")
    c2 = pm.Color(1.0, 0.4, 0.2, 1.0)
    v2 = pm.Vec2(960, 540)
    v3 = pm.Vec3(0.0, 1.0, 0.0)
    res = pm.Resolution(1920, 1080)
    tr = pm.TimeRange(0, 900)
    print(f"Colors: {c1}, {c2}, Vec2: {v2}, Vec3: {v3}, Res: {res}, TR: {tr}")

    # ── Demonstrate animation primitives ──────────────────────────────────
    kf = pm.Keyframe(frame=0, value=0.0)
    track = pm.KeyframeTrack(keyframes=[pm.Keyframe(0, 0.0), pm.Keyframe(30, 1.0)])
    ease_fn = pm.get_easing("ease_in_out_cubic")
    custom_ease = pm.cubic_bezier(0.25, 0.1, 0.25, 1.0)
    spring_val = pm.spring(stiffness=200, damping=15)
    step_val = pm.steps(4)
    interp = pm.interpolate(0.5, 0.0, 100.0)
    anim_val: pm.AnimatableValue = pm.animate(0.0, 1.0, duration=30)
    print(
        f"Keyframe: {kf}, Track: {track}, Easing: {ease_fn}, "
        f"Bezier: {custom_ease}, Spring: {spring_val}, Steps: {step_val}, "
        f"Interp: {interp}, Anim: {anim_val}"
    )

    # ── Demonstrate Effect base, Align, RenderContext, Transitions ────────
    print(f"Effect base: {pm.Effect.__name__}")
    print(f"Align: {pm.Align.CENTER}")
    ctx = pm.RenderContext(
        frame=0,
        fps=30,
        resolution=pm.Resolution(1920, 1080),
        time_range=pm.TimeRange(0, 900),
        local_frame=0,
        progress=0.0,
    )
    print(f"RenderContext: frame={ctx.frame}")
    print(f"Transitions: {pm.Cut.__name__}, {pm.Fade.__name__}, {pm.DipToColor.__name__}")

    # ── Composition ───────────────────────────────────────────────────────
    comp = pm.Composition(width=1920, height=1080, fps=30, duration=900)

    # Track 1: Background gradient with blur
    bg_track = pm.Track(name="background")
    bg = pm.GradientClip(
        color_start="#1a1a2e",
        color_end="#16213e",
        direction=45.0,
        gradient_type="linear",
    )
    bg.set_duration(900)
    bg.add_effect(pm.GaussianBlur(radius=3.0))
    bg_track.clips.append(bg)

    # Track 2: Radial gradient accent
    accent_track = pm.Track(name="accent")
    radial = pm.GradientClip(
        color_start="#e94560",
        color_end="#0f3460",
        gradient_type="radial",
        center_x=0.3,
        center_y=0.4,
        radius=0.6,
    )
    radial.set_duration(900).set_opacity(0.4)
    radial.blend_mode = pm.BlendMode.SCREEN
    accent_track.clips.append(radial)

    # Track 3: Decorative shapes
    shapes_track = pm.Track(name="shapes")

    # Rectangle with stroke
    rect = pm.ShapeClip.rect(
        x=100,
        y=200,
        w=400,
        h=300,
        fill="#2a2a5a",
        stroke="#e94560",
        stroke_width=3.0,
    )
    rect.set_duration(900).set_opacity(0.7).set_rotation(5.0)
    rect.blend_mode = pm.BlendMode.OVERLAY
    shapes_track.clips.append(rect)

    # Circle
    circle = pm.ShapeClip.circle(
        cx=1600,
        cy=300,
        r=120,
        fill="#e94560",
        stroke="#ffffff",
        stroke_width=2.0,
    )
    circle.set_duration(900).set_opacity(0.6)
    circle.blend_mode = pm.BlendMode.MULTIPLY
    shapes_track.clips.append(circle)

    # Polygon (triangle)
    tri = pm.ShapeClip.polygon(
        points=[(1700, 800), (1850, 950), (1550, 950)],
        fill="#0f3460",
    )
    tri.set_duration(900).set_opacity(0.5)
    shapes_track.clips.append(tri)

    # Line
    line = pm.ShapeClip.line(
        x1=100,
        y1=700,
        x2=700,
        y2=700,
        color="#e94560",
        width=3.0,
    )
    line.set_duration(900)
    shapes_track.clips.append(line)

    # Track 4: Product image
    product_track = pm.Track(name="product")
    product = pm.ImageClip(str(ASSETS / "product_hero.png"))
    product.set_duration(900).set_position(960, 540).set_scale(1.2)
    product.add_effect(pm.Brightness(value=1.1))
    product.add_effect(pm.Contrast(value=1.15))
    product_track.clips.append(product)

    # Track 5: Logo top-left
    logo_track = pm.Track(name="logo")
    logo = pm.ImageClip(str(ASSETS / "logo.png"))
    logo.set_duration(900).set_position(120, 80).set_scale(0.3, 0.3)
    logo.set_opacity(0.85)
    logo_track.clips.append(logo)

    # Track 6: Solid color strip (demonstrates ColorClip)
    strip_track = pm.Track(name="strip")
    strip = pm.ColorClip(color="#e94560")
    strip.set_duration(900).set_position(960, 1050).set_scale(1920, 60)
    strip.set_opacity(0.8)
    strip_track.clips.append(strip)

    # Track 7: Vignette effect overlay
    vignette_track = pm.Track(name="vignette")
    vig_bg = pm.ColorClip(color="#000000")
    vig_bg.set_duration(900)
    vig_bg.add_effect(pm.Vignette(strength=0.7, radius=0.75, feather=0.4))
    vig_bg.set_opacity(0.5)
    vignette_track.clips.append(vig_bg)

    # Add all tracks
    comp.tracks.extend(
        [
            bg_track,
            accent_track,
            shapes_track,
            product_track,
            logo_track,
            strip_track,
            vignette_track,
        ]
    )

    # ── Export audit frame ────────────────────────────────────────────────
    audit_dir = Path(__file__).parent.parent / "audit"
    audit_dir.mkdir(exist_ok=True)
    for f_num in [0, 15, 100, 450, 899]:
        comp.export_frame(frame=f_num, output=audit_dir / f"ex01_f{f_num}.png")
    print("Audit frames exported to audit/")

    # ── Profiling & diagnostics ───────────────────────────────────────────
    profile = pm.profile_composition(comp, start=0, end=5)
    print(f"Profile: {profile.total_ms:.1f}ms for {profile.total_frames} frames")
    print(f"  Avg frame: {profile.avg_frame_ms:.1f}ms")

    bottlenecks = pm.detect_bottlenecks(comp, n_frames=5)
    for b in bottlenecks[:3]:
        print(f"  Bottleneck: {b.category} — {b.description} ({b.time_ms:.1f}ms)")

    mem = pm.memory_report(comp, n_frames=3)
    print(f"  Peak memory: {mem.peak_ram_bytes / 1024 / 1024:.1f} MB")

    # ── Render ────────────────────────────────────────────────────────────
    output_path = OUTPUT_DIR / "01_core.mp4"
    comp.render(str(output_path), preset="h264_fast")
    print(f"Rendered: {output_path} ({output_path.stat().st_size / 1024 / 1024:.1f} MB)")


if __name__ == "__main__":
    main()
