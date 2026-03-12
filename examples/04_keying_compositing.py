"""EX04 — Keying & Compositing.

Use-case: A green-screen subject composited over a scenic background
with color grading, track mattes, and transition effects.
Each section is labeled with the effect being demonstrated.

Features exercised:
  ChromaKey, LumaKey, ColorKey, DifferenceKey,
  AdjustmentLayer (keying context), TrackMatte (alpha matte),
  SplitToning, ChromaticAberration,
  SlideLeft, CircularWipe, IrisIn, IrisOut, ColorMatch

Output: 1920x1080, 30fps, 22s, preset h264_fast -> outputs/04_keying.mp4
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

import pymotion as pm
from pymotion.design.tokens import NEUTRAL, get_theme

ASSETS = Path(__file__).parent / "assets"
OUTPUT_DIR = Path(__file__).parent.parent / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

SEC = 60  # 2s per section at 30fps
TOTAL = SEC * 11  # 11 sections = 22s


def _add_label(track: pm.Track, text: str, offset: int, dur: int) -> None:
    """Add an effect name label to the top-left safe zone."""
    theme = get_theme()
    lbl = pm.TextClip(text=text, size=32, color=theme.text)
    lbl.set_duration(dur - 10).at(offset + 5).set_position(120, 100).set_opacity(0.85)
    track.clips.append(lbl)
    sub = pm.TextClip(text="Keying & Compositing", size=14, color=NEUTRAL.n500)
    sub.set_duration(dur - 10).at(offset + 5).set_position(120, 145).set_opacity(0.4)
    track.clips.append(sub)


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
    # SCENE: chromakey | 60f | Primary: keyed subject | Secondary: label
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
    _add_label(sec1_track, "ChromaKey", 0, SEC)
    comp.tracks.append(sec1_track)
    print("1. ChromaKey: tolerance=0.35, spill=0.6")

    # ── Section 2: LumaKey ───────────────────────────────────────────────
    sec2_track = pm.Track(name="sec2_lumakey")
    gs2 = pm.VideoClip(gs_path)
    gs2.set_duration(SEC).at(SEC)
    gs2.add_effect(pm.LumaKey(threshold=0.5, softness=0.15, invert=False))
    sec2_track.clips.append(gs2)
    _add_label(sec2_track, "LumaKey", SEC, SEC)
    comp.tracks.append(sec2_track)
    print("2. LumaKey: threshold=0.5")

    # ── Section 3: ColorKey ──────────────────────────────────────────────
    sec3_track = pm.Track(name="sec3_colorkey")
    gs3 = pm.VideoClip(gs_path)
    gs3.set_duration(SEC).at(SEC * 2)
    gs3.add_effect(pm.ColorKey(color="#00FF00", tolerance=0.3, softness=0.1))
    sec3_track.clips.append(gs3)
    _add_label(sec3_track, "ColorKey", SEC * 2, SEC)
    comp.tracks.append(sec3_track)
    print("3. ColorKey: color=#00FF00")

    # ── Section 4: DifferenceKey ─────────────────────────────────────────
    sec4_track = pm.Track(name="sec4_diffkey")
    ref_frame = np.zeros((1080, 1920, 4), dtype=np.uint8)
    ref_frame[:, :, 1] = 255  # Green channel
    ref_frame[:, :, 3] = 255  # Alpha
    gs4 = pm.VideoClip(gs_path)
    gs4.set_duration(SEC).at(SEC * 3)
    gs4.add_effect(pm.DifferenceKey(reference=ref_frame, tolerance=0.25, softness=0.1))
    sec4_track.clips.append(gs4)
    _add_label(sec4_track, "DifferenceKey", SEC * 3, SEC)
    comp.tracks.append(sec4_track)
    print("4. DifferenceKey: ref=green")

    # ── Section 5: AdjustmentLayer with SplitToning ──────────────────────
    sec5_track = pm.Track(name="sec5_adjustment")
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
    _add_label(sec5_track, "SplitToning", SEC * 4, SEC)
    comp.tracks.append(sec5_track)
    print("5. AdjustmentLayer + SplitToning")

    # ── Section 6: TrackMatte (alpha matte) ──────────────────────────────
    sec6_track = pm.Track(name="sec6_trackmatte")
    footage6 = pm.ImageClip(str(ASSETS / "product_b.jpg"))
    footage6.set_duration(SEC).at(SEC * 5)
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
    _add_label(sec6_track, "TrackMatte — Alpha", SEC * 5, SEC)
    comp.tracks.append(sec6_track)
    print("6. TrackMatte: mode=alpha")

    # ── Section 7: ChromaticAberration + ColorMatch ──────────────────────
    sec7_track = pm.Track(name="sec7_effects")
    footage7 = pm.ImageClip(str(ASSETS / "product_c.jpg"))
    footage7.set_duration(SEC).at(SEC * 6)
    footage7.add_effect(pm.ChromaticAberration(offset=5.0, angle=45.0))
    warm_ref = np.full((1, 1, 4), [180, 200, 240, 255], dtype=np.uint8)
    footage7.add_effect(pm.ColorMatch(reference_frame=warm_ref))
    sec7_track.clips.append(footage7)
    _add_label(sec7_track, "ChromaticAberration + ColorMatch", SEC * 6, SEC)
    comp.tracks.append(sec7_track)
    print("7. ChromaticAberration + ColorMatch")

    # ── Section 8: SlideLeft transition ───────────────────────────────────
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
    _add_label(sec8_track, "SlideLeft Transition", SEC * 7, SEC)
    comp.tracks.append(sec8_track)
    print("8. SlideLeft transition")

    # ── Section 9: CircularWipe transition ────────────────────────────────
    sec9_track = pm.Track(name="sec9_circwipe")
    cw_a = pm.ImageClip(str(ASSETS / "product_a.jpg"))
    cw_a.set_duration(SEC)
    cw_b = pm.ImageClip(str(ASSETS / "product_b.jpg"))
    cw_b.set_duration(SEC)
    cw_concat = pm.concatenate(
        [cw_a, cw_b],
        transition=pm.CircularWipe(),
        transition_duration=30,
    )
    cw_concat.at(SEC * 8)
    sec9_track.clips.append(cw_concat)
    _add_label(sec9_track, "CircularWipe", SEC * 8, SEC)
    comp.tracks.append(sec9_track)
    print("9. CircularWipe transition")

    # ── Section 10: IrisIn transition ─────────────────────────────────────
    sec10_track = pm.Track(name="sec10_irisin")
    ii_a = pm.ImageClip(str(ASSETS / "product_hero.jpg"))
    ii_a.set_duration(SEC)
    ii_b = pm.ImageClip(str(ASSETS / "product_c.jpg"))
    ii_b.set_duration(SEC)
    ii_concat = pm.concatenate(
        [ii_a, ii_b],
        transition=pm.IrisIn(),
        transition_duration=30,
    )
    ii_concat.at(SEC * 9)
    sec10_track.clips.append(ii_concat)
    _add_label(sec10_track, "IrisIn", SEC * 9, SEC)
    comp.tracks.append(sec10_track)
    print("10. IrisIn transition")

    # ── Section 11: IrisOut transition ────────────────────────────────────
    sec11_track = pm.Track(name="sec11_irisout")
    io_a = pm.ImageClip(str(ASSETS / "product_b.jpg"))
    io_a.set_duration(SEC)
    io_b = pm.ImageClip(str(ASSETS / "product_a.jpg"))
    io_b.set_duration(SEC)
    io_concat = pm.concatenate(
        [io_a, io_b],
        transition=pm.IrisOut(),
        transition_duration=30,
    )
    io_concat.at(SEC * 10)
    sec11_track.clips.append(io_concat)
    _add_label(sec11_track, "IrisOut", SEC * 10, SEC)
    comp.tracks.append(sec11_track)
    print("11. IrisOut transition")

    # ── Render ───────────────────────────────────────────────────────────
    output_path = OUTPUT_DIR / "04_keying.mp4"
    comp.render(str(output_path), preset="h264_fast")
    size_mb = output_path.stat().st_size / 1024 / 1024
    print(f"Rendered: {output_path} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
