"""EX06 — Particles & Visual Effects.

Use-case: A VFX showcase reel with particle presets, distortion effects,
light effects, and post-processing applied to scenic footage.

Features exercised:
  ParticleSystem, Emitter,
  sparkles, Sparkles, fire, Fire, rain, Rain,
  confetti, Confetti, smoke, Smoke, stars, Stars,
  FilmGrain, MotionBlur, GodRays, NeonGlow, LightLeak, Bloom, Sharpen,
  LensFlare, LensFlareLight,
  Fisheye, PerspectiveWarp, Ripple, Twirl, WaveWarp,
  RevealLeft, RevealRight, RevealUp, RevealDown,
  Glitch, FilmBurn, MorphWarp, PageTurn, PixelDissolve,
  ScaleDissolve, Shatter, Vortex, ZoomBlur, ZoomIn, ZoomOut

Output: 1920x1080, 30fps, ~42s, preset h264_fast -> outputs/06_vfx.mp4
Estimated render time: ~120s
"""

from __future__ import annotations

from pathlib import Path

import pymotion as pm
from pymotion.design.tokens import ACCENT, CHART_COLORS, NEUTRAL, STATUS, get_theme

ASSETS = Path(__file__).parent / "assets"
OUTPUT_DIR = Path(__file__).parent.parent / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

SEC = 75  # 2.5s per section at 30fps
TOTAL = SEC * 17  # 17 sections = ~42s


def main() -> None:
    comp = pm.Composition(width=1920, height=1080, fps=30, duration=TOTAL)

    # ── Background gradient ──────────────────────────────────────────────
    bg_track = pm.Track(name="bg")
    theme = get_theme()
    bg = pm.GradientClip(color_start=theme.background, color_end=theme.surface, direction=135.0)
    bg.set_duration(TOTAL)
    bg_track.clips.append(bg)
    comp.tracks.append(bg_track)

    # ── Section 1: ParticleSystem + Emitter (custom) ─────────────────────
    offset = 0
    emitter = pm.Emitter(
        position=pm.Vec2(960, 800),
        rate=20.0,
        lifetime=(40.0, 80.0),
        speed=(2.0, 6.0),
        angle=(240.0, 300.0),
        size=(3.0, 8.0),
        color_over_life=[
            CHART_COLORS[6],  # orange
            STATUS.error,  # red
            NEUTRAL.n900,  # fade to dark
        ],
        opacity_over_life=[1.0, 0.8, 0.0],
        gravity=pm.Vec2(0.0, -0.05),
        drag=0.02,
        turbulence=0.5,
    )
    ps = pm.ParticleSystem(width=1920, height=1080)
    ps.add_emitter(emitter)
    ps_clip = ps.to_clip(duration=SEC)
    ps_clip.at(offset)

    sec1 = pm.Track(name="sec1_custom_particles")
    sec1.clips.append(ps_clip)
    comp.tracks.append(sec1)
    print(f"1. ParticleSystem + Emitter: rate={emitter.rate}, emitters=1")

    # ── Section 2: sparkles preset ───────────────────────────────────────
    offset = SEC
    sp = pm.sparkles()
    sp_clip = sp.to_clip(duration=SEC)
    sp_clip.at(offset)
    sec2 = pm.Track(name="sec2_sparkles")
    sec2.clips.append(sp_clip)
    comp.tracks.append(sec2)
    # Verify alias
    print(f"2. sparkles: {type(sp).__name__}, Sparkles alias={pm.Sparkles is pm.sparkles}")

    # ── Section 3: fire preset ───────────────────────────────────────────
    offset = SEC * 2
    fi = pm.fire()
    fi_clip = fi.to_clip(duration=SEC)
    fi_clip.at(offset)
    sec3 = pm.Track(name="sec3_fire")
    sec3.clips.append(fi_clip)
    comp.tracks.append(sec3)
    print(f"3. fire: {type(fi).__name__}, Fire alias={pm.Fire is pm.fire}")

    # ── Section 4: confetti preset ───────────────────────────────────────
    offset = SEC * 3
    co = pm.confetti()
    co_clip = co.to_clip(duration=SEC)
    co_clip.at(offset)
    sec4 = pm.Track(name="sec4_confetti")
    sec4.clips.append(co_clip)
    comp.tracks.append(sec4)
    print(f"4. confetti: Confetti alias={pm.Confetti is pm.confetti}")

    # ── Section 5: smoke preset ──────────────────────────────────────────
    offset = SEC * 4
    sm = pm.smoke()
    sm_clip = sm.to_clip(duration=SEC)
    sm_clip.at(offset)
    sec5 = pm.Track(name="sec5_smoke")
    sec5.clips.append(sm_clip)
    comp.tracks.append(sec5)
    print(f"5. smoke: Smoke alias={pm.Smoke is pm.smoke}")

    # ── Section 6: rain preset ───────────────────────────────────────────
    offset = SEC * 5
    ra = pm.rain()
    ra_clip = ra.to_clip(duration=SEC)
    ra_clip.at(offset)
    sec6 = pm.Track(name="sec6_rain")
    sec6.clips.append(ra_clip)
    comp.tracks.append(sec6)
    print(f"6. rain: Rain alias={pm.Rain is pm.rain}")

    # ── Section 7: stars preset ──────────────────────────────────────────
    offset = SEC * 6
    st = pm.stars()
    st_clip = st.to_clip(duration=SEC)
    st_clip.at(offset)
    sec7 = pm.Track(name="sec7_stars")
    sec7.clips.append(st_clip)
    comp.tracks.append(sec7)
    print(f"7. stars: Stars alias={pm.Stars is pm.stars}")

    # ── Section 8: FilmGrain + MotionBlur + Sharpen ──────────────────────
    offset = SEC * 7
    sec8 = pm.Track(name="sec8_postfx")
    img8 = pm.ImageClip(str(ASSETS / "product_hero.jpg"))
    img8.set_duration(SEC).at(offset)
    img8.add_effect(pm.FilmGrain(strength=0.4, size=1.5, monochrome=True))
    img8.add_effect(pm.MotionBlur(angle=45.0, distance=8.0))
    img8.add_effect(pm.Sharpen(amount=1.5))
    sec8.clips.append(img8)
    comp.tracks.append(sec8)
    print("8. FilmGrain + MotionBlur + Sharpen applied")

    # ── Section 9: GodRays + NeonGlow + LightLeak ────────────────────────
    offset = SEC * 8
    sec9 = pm.Track(name="sec9_light")
    img9 = pm.ImageClip(str(ASSETS / "product_a.jpg"))
    img9.set_duration(SEC).at(offset)
    img9.add_effect(pm.GodRays(position=pm.Vec2(0.3, 0.1), intensity=0.6, decay=0.93, samples=40))
    img9.add_effect(pm.NeonGlow(color=ACCENT.a500, radius=10.0, strength=0.8, threshold=40.0))
    img9.add_effect(
        pm.LightLeak(color=CHART_COLORS[6], position=pm.Vec2(0.8, 0.2), intensity=0.5, size=0.5)
    )
    sec9.clips.append(img9)
    comp.tracks.append(sec9)
    print("9. GodRays + NeonGlow + LightLeak applied")

    # ── Section 10: LensFlare + LensFlareLight + Bloom ───────────────────
    offset = SEC * 9
    sec10 = pm.Track(name="sec10_lens")
    img10 = pm.ImageClip(str(ASSETS / "product_b.jpg"))
    img10.set_duration(SEC).at(offset)
    img10.add_effect(pm.LensFlare(position=pm.Vec2(0.7, 0.3), intensity=0.5, color="#FFE6B3"))
    img10.add_effect(pm.LensFlareLight(position=pm.Vec2(0.3, 0.4), intensity=0.35, color="#FFF2CC"))
    img10.add_effect(pm.Bloom(radius=8.0, strength=0.3, threshold=200.0, iterations=3))
    sec10.clips.append(img10)
    comp.tracks.append(sec10)
    print("10. LensFlare + LensFlareLight + Bloom applied")

    # ── Section 11: Fisheye + PerspectiveWarp + Ripple ───────────────────
    offset = SEC * 10
    sec11 = pm.Track(name="sec11_distort_a")
    img11 = pm.ImageClip(str(ASSETS / "product_c.jpg"))
    img11.set_duration(SEC).at(offset)
    img11.add_effect(pm.Fisheye(strength=0.3))
    img11.add_effect(
        pm.PerspectiveWarp(
            corners=(
                pm.Vec2(0.05, 0.05),
                pm.Vec2(0.95, 0.0),
                pm.Vec2(1.0, 1.0),
                pm.Vec2(0.0, 0.95),
            )
        )
    )
    img11.add_effect(
        pm.Ripple(center=pm.Vec2(0.5, 0.5), amplitude=8.0, frequency=0.08, decay=0.005)
    )
    sec11.clips.append(img11)
    comp.tracks.append(sec11)
    print("11. Fisheye + PerspectiveWarp + Ripple applied")

    # ── Section 12: Twirl + WaveWarp ─────────────────────────────────────
    offset = SEC * 11
    sec12 = pm.Track(name="sec12_distort_b")
    img12 = pm.ImageClip(str(ASSETS / "product_hero.jpg"))
    img12.set_duration(SEC).at(offset)
    img12.add_effect(pm.Twirl(center=pm.Vec2(0.5, 0.5), angle=0.8, radius=200.0))
    img12.add_effect(pm.WaveWarp(amplitude=12.0, frequency=0.04, phase=0.0, axis="x"))
    sec12.clips.append(img12)
    comp.tracks.append(sec12)
    print("12. Twirl + WaveWarp applied")

    # Helper: create a transition demo concatenation on its own track
    def _trans_demo(
        name: str,
        trans: pm.Transition,
        sec_offset: int,
        label: str,
    ) -> None:
        t = pm.Track(name=name)
        a = pm.ImageClip(str(ASSETS / "product_hero.jpg"))
        a.set_duration(SEC)
        b = pm.ImageClip(str(ASSETS / "product_a.jpg"))
        b.set_duration(SEC)
        c = pm.concatenate([a, b], transition=trans, transition_duration=30)
        c.at(sec_offset)
        t.clips.append(c)
        comp.tracks.append(t)
        print(label)

    # ── Section 13: RevealLeft + RevealRight + RevealUp ─────────────────
    _trans_demo("sec13a", pm.RevealLeft(), SEC * 12, "13a. RevealLeft")
    _trans_demo("sec13b", pm.RevealRight(), SEC * 12, "13b. RevealRight")
    _trans_demo("sec13c", pm.RevealUp(), SEC * 12, "13c. RevealUp")

    # ── Section 14: RevealDown + Glitch + FilmBurn ──────────────────────
    _trans_demo("sec14a", pm.RevealDown(), SEC * 13, "14a. RevealDown")
    _trans_demo("sec14b", pm.Glitch(), SEC * 13, "14b. Glitch")
    _trans_demo("sec14c", pm.FilmBurn(), SEC * 13, "14c. FilmBurn")

    # ── Section 15: MorphWarp + PageTurn + PixelDissolve ────────────────
    _trans_demo("sec15a", pm.MorphWarp(), SEC * 14, "15a. MorphWarp")
    _trans_demo("sec15b", pm.PageTurn(), SEC * 14, "15b. PageTurn")
    _trans_demo("sec15c", pm.PixelDissolve(), SEC * 14, "15c. PixelDissolve")

    # ── Section 16: ScaleDissolve + Shatter + Vortex ────────────────────
    _trans_demo("sec16a", pm.ScaleDissolve(), SEC * 15, "16a. ScaleDissolve")
    _trans_demo("sec16b", pm.Shatter(), SEC * 15, "16b. Shatter")
    _trans_demo("sec16c", pm.Vortex(), SEC * 15, "16c. Vortex")

    # ── Section 17: ZoomBlur + ZoomIn + ZoomOut ─────────────────────────
    _trans_demo("sec17a", pm.ZoomBlur(), SEC * 16, "17a. ZoomBlur")
    _trans_demo("sec17b", pm.ZoomIn(), SEC * 16, "17b. ZoomIn")
    _trans_demo("sec17c", pm.ZoomOut(), SEC * 16, "17c. ZoomOut")

    # ── Audit frames ─────────────────────────────────────────────────────
    audit_dir = Path(__file__).parent.parent / "audit"
    audit_dir.mkdir(exist_ok=True)
    for sec_idx in range(17):
        mid = sec_idx * SEC + SEC // 2
        try:
            comp.export_frame(frame=mid, output=audit_dir / f"ex06_sec{sec_idx + 1}.png")
        except (ValueError, RuntimeError) as e:
            print(f"  Audit sec{sec_idx + 1} skipped: {e}")
    print("Audit frames exported")

    # ── Render ───────────────────────────────────────────────────────────
    output_path = OUTPUT_DIR / "06_vfx.mp4"
    comp.render(str(output_path), preset="h264_fast")
    size_mb = output_path.stat().st_size / 1024 / 1024
    print(f"Rendered: {output_path} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
