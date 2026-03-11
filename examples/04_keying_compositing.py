"""EX04 — Keying & Compositing.

Use-case: A green-screen subject composited over a scenic background
with color grading, track mattes, and transition effects.

Features exercised:
  ChromaKey, LumaKey, ColorKey, DifferenceKey,
  AdjustmentLayer (keying context), TrackMatte (alpha matte),
  SplitToning, ChromaticAberration,
  SlideLeft, ColorMatch

Output: 1920x1080, 30fps, 16s, preset h264_fast -> outputs/04_keying.mp4
Estimated render time: ~60s
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

import pymotion as pm

ASSETS = Path(__file__).parent / "assets"
OUTPUT_DIR = Path(__file__).parent.parent / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

SEC = 60  # 2s per section at 30fps
TOTAL = SEC * 8  # 8 sections = 16s


def main() -> None:
    gs_path = str(ASSETS / "greenscreen_subject.mp4")

    comp = pm.Composition(width=1920, height=1080, fps=30, duration=TOTAL)

    # ── Background: scenic image for all sections ────────────────────────
    bg_track = pm.Track(name="background")
    bg = pm.ImageClip(str(ASSETS / "product_hero.jpg"))
    bg.set_duration(TOTAL)
    bg_track.clips.append(bg)
    comp.tracks.append(bg_track)

    # ── Section 1: ChromaKey ─────────────────────────────────────────────
    sec1_track = pm.Track(name="sec1_chromakey")
    gs1 = pm.VideoClip(gs_path)
    gs1.set_duration(SEC).at(0)
    gs1.add_effect(
        pm.ChromaKey(
            color="#00FF00",
            tolerance=0.35,
            edge_softness=0.02,
            spill_suppression=0.6,
        )
    )
    sec1_track.clips.append(gs1)
    comp.tracks.append(sec1_track)
    print("1. ChromaKey applied: tolerance=0.35, spill=0.6")

    # ── Section 2: LumaKey ───────────────────────────────────────────────
    sec2_track = pm.Track(name="sec2_lumakey")
    gs2 = pm.VideoClip(gs_path)
    gs2.set_duration(SEC).at(SEC)
    gs2.add_effect(pm.LumaKey(threshold=0.5, softness=0.15, invert=False))
    sec2_track.clips.append(gs2)
    comp.tracks.append(sec2_track)
    print("2. LumaKey applied: threshold=0.5, softness=0.15")

    # ── Section 3: ColorKey ──────────────────────────────────────────────
    sec3_track = pm.Track(name="sec3_colorkey")
    gs3 = pm.VideoClip(gs_path)
    gs3.set_duration(SEC).at(SEC * 2)
    gs3.add_effect(pm.ColorKey(color="#00FF00", tolerance=0.3, softness=0.1))
    sec3_track.clips.append(gs3)
    comp.tracks.append(sec3_track)
    print("3. ColorKey applied: color=#00FF00, tolerance=0.3")

    # ── Section 4: DifferenceKey ─────────────────────────────────────────
    sec4_track = pm.Track(name="sec4_diffkey")
    # Create a reference frame (plain green background)
    ref_frame = np.zeros((1080, 1920, 4), dtype=np.uint8)
    ref_frame[:, :, 1] = 255  # Green channel
    ref_frame[:, :, 3] = 255  # Alpha

    gs4 = pm.VideoClip(gs_path)
    gs4.set_duration(SEC).at(SEC * 3)
    gs4.add_effect(pm.DifferenceKey(reference=ref_frame, tolerance=0.25, softness=0.1))
    sec4_track.clips.append(gs4)
    comp.tracks.append(sec4_track)
    print("4. DifferenceKey applied: ref=green, tolerance=0.25")

    # ── Section 5: AdjustmentLayer with SplitToning ──────────────────────
    sec5_track = pm.Track(name="sec5_adjustment")
    # Show image with adjustment layer grading
    footage5 = pm.ImageClip(str(ASSETS / "product_a.jpg"))
    footage5.set_duration(SEC).at(SEC * 4)
    sec5_track.clips.append(footage5)

    adj = pm.AdjustmentLayer(
        effects=[
            pm.SplitToning(
                highlights_color="#FFE6CC",
                shadows_color="#334D80",
                balance=0.2,
            ),
        ]
    )
    adj.set_duration(SEC).at(SEC * 4)
    sec5_track.clips.append(adj)
    comp.tracks.append(sec5_track)
    print("5. AdjustmentLayer + SplitToning: highlights=#FFE6CC, shadows=#334D80")

    # ── Section 6: TrackMatte (alpha matte) ──────────────────────────────
    sec6_track = pm.Track(name="sec6_trackmatte")
    # Image to be masked
    footage6 = pm.ImageClip(str(ASSETS / "product_b.jpg"))
    footage6.set_duration(SEC).at(SEC * 5)
    # Use a shape as the matte source
    matte_shape = pm.ShapeClip.circle(cx=960, cy=540, r=400, fill="#FFFFFF")
    matte_shape.set_duration(SEC)
    track_matte = pm.TrackMatte(
        source=matte_shape,
        mode="alpha",
        feather=20.0,
        expansion=5.0,
        invert=False,
        opacity=1.0,
    )
    footage6.add_mask(track_matte)
    sec6_track.clips.append(footage6)
    comp.tracks.append(sec6_track)
    print("6. TrackMatte: mode=alpha, feather=20, expansion=5")

    # ── Section 7: ChromaticAberration + ColorMatch ──────────────────────
    sec7_track = pm.Track(name="sec7_effects")
    footage7 = pm.ImageClip(str(ASSETS / "product_c.jpg"))
    footage7.set_duration(SEC).at(SEC * 6)
    footage7.add_effect(pm.ChromaticAberration(offset=5.0, angle=45.0))
    # ColorMatch with a warm-toned reference
    warm_ref = np.full((1, 1, 4), [180, 200, 240, 255], dtype=np.uint8)
    footage7.add_effect(pm.ColorMatch(reference_frame=warm_ref))
    sec7_track.clips.append(footage7)
    comp.tracks.append(sec7_track)
    print("7. ChromaticAberration(5px, 45°) + ColorMatch(warm)")

    # ── Section 8: SlideLeft transition demo ─────────────────────────────
    sec8_track = pm.Track(name="sec8_slide")
    clip_a = pm.ImageClip(str(ASSETS / "product_c.jpg"))
    clip_a.set_duration(SEC)
    clip_b = pm.ImageClip(str(ASSETS / "product_hero.jpg"))
    clip_b.set_duration(SEC)
    slide_concat = pm.concatenate(
        [clip_a, clip_b],
        transition=pm.SlideLeft(),
        transition_duration=30,
    )
    slide_concat.at(SEC * 7)
    sec8_track.clips.append(slide_concat)
    comp.tracks.append(sec8_track)
    print("8. SlideLeft transition: 30 frames overlap")

    # ── Audit frames ─────────────────────────────────────────────────────
    audit_dir = Path(__file__).parent.parent / "audit"
    audit_dir.mkdir(exist_ok=True)
    for sec in range(8):
        mid = sec * SEC + SEC // 2
        try:
            comp.export_frame(frame=mid, output=audit_dir / f"ex04_sec{sec + 1}.png")
        except (ValueError, RuntimeError) as e:
            print(f"  Audit sec{sec + 1} skipped: {e}")
    print("Audit frames exported")

    # ── Render ───────────────────────────────────────────────────────────
    output_path = OUTPUT_DIR / "04_keying.mp4"
    comp.render(str(output_path), preset="h264_fast")
    size_mb = output_path.stat().st_size / 1024 / 1024
    print(f"Rendered: {output_path} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
