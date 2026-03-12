"""EX11 — AI Features.

Use-case: A showcase of AI-powered effects, detectors, and generators —
constructed and configured but gracefully handling missing optional deps.

Features exercised:
  RemoveBackground, ReplaceBackground, Upscale, Denoise, Deblur,
  ColorizeClip, FaceDetector, FaceBlur, FaceTracker,
  SceneDetector, SilenceRemover, ContentAwareCrop, AutoColor,
  ObjectSegmentation, RemoveObject, ExtendFrame,
  FrameInterpolation, HighlightDetector, AutoEdit,
  MusicGeneration, SoundFXGeneration, VoiceConversion,
  frame_diff, FrameDiff

Output: 1920x1080, 30fps, 20s, preset h264_fast -> outputs/11_ai.mp4
Estimated render time: ~30s
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

import pymotion as pm

ASSETS = Path(__file__).parent / "assets"
OUTPUT_DIR = Path(__file__).parent.parent / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

SEC = 50  # ~1.7s per section at 30fps
TOTAL = SEC * 12  # 12 sections = 20s


def main() -> None:
    comp = pm.Composition(width=1920, height=1080, fps=30, duration=TOTAL)

    # ── Background ───────────────────────────────────────────────────────
    bg_track = pm.Track(name="bg")
    bg = pm.GradientClip(color_start="#0a0a1a", color_end="#1a1a2e", direction=135.0)
    bg.set_duration(TOTAL)
    bg_track.clips.append(bg)
    comp.tracks.append(bg_track)

    # Each section shows a product image. AI effects are constructed and
    # their parameters printed, but not applied to rendered clips since
    # they require optional GPU/AI packages (rembg, torch, etc.).

    from pymotion.design.tokens import NEUTRAL, get_theme

    theme = get_theme()

    images = [
        "product_hero.jpg",
        "product_a.jpg",
        "product_b.jpg",
        "product_c.jpg",
        "product_hero.jpg",
        "product_a.jpg",
        "product_b.jpg",
        "product_c.jpg",
        "product_hero.jpg",
        "product_a.jpg",
        "product_b.jpg",
        "product_c.jpg",
    ]

    # ADDED: labels for each AI feature — principle 1, identify the primary element
    ai_labels = [
        "RemoveBackground",
        "ReplaceBackground",
        "ObjectSegmentation",
        "Upscale + Denoise",
        "ColorizeClip",
        "ExtendFrame",
        "FrameInterpolation",
        "FaceDetector + FaceBlur",
        "SceneDetector",
        "ContentAwareCrop",
        "AutoEdit + MusicGen",
        "VoiceConversion",
    ]

    for sec_idx in range(12):
        t = pm.Track(name=f"sec{sec_idx + 1}")
        img = pm.ImageClip(str(ASSETS / images[sec_idx]))
        img.set_duration(SEC).at(sec_idx * SEC).set_opacity(0.4)
        t.clips.append(img)
        # Large feature name — primary element
        feat_label = pm.TextClip(
            text=ai_labels[sec_idx],
            size=56,
            color=theme.text,
        )
        feat_label.set_duration(SEC).at(sec_idx * SEC).set_position(960, 460)
        t.clips.append(feat_label)
        # Small "AI Feature" subtitle
        sub_label = pm.TextClip(
            text="AI Feature (optional dependency)",
            size=16,
            color=NEUTRAL.n500,
        )
        sub_label.set_duration(SEC).at(sec_idx * SEC).set_position(960, 540).set_opacity(0.5)
        t.clips.append(sub_label)
        comp.tracks.append(t)

    # ── Section 1: RemoveBackground ─────────────────────────────────────
    rembg = pm.RemoveBackground(model="u2net", alpha_matting=False)
    print(f"1. RemoveBackground: model={rembg.model}, matting={rembg.alpha_matting}")
    print(
        f"   fg_threshold={rembg.foreground_threshold}, bg_threshold={rembg.background_threshold}"
    )

    # ── Section 2: ReplaceBackground ────────────────────────────────────
    new_bg = pm.GradientClip(color_start="#FF6633", color_end="#FFC300", direction=90.0)
    new_bg.set_duration(SEC)
    replace_bg = pm.ReplaceBackground(new_bg=new_bg, model="u2net")
    print(f"2. ReplaceBackground: model={replace_bg.model}")

    # ── Section 3: ObjectSegmentation + RemoveObject ────────────────────
    obj_seg = pm.ObjectSegmentation(prompt="product", threshold=0.5, model="vit_b")
    print(f"3. ObjectSegmentation: prompt={obj_seg.prompt}, model={obj_seg.model}")

    mask_array = np.zeros((1080, 1920), dtype=np.uint8)
    mask_array[400:700, 800:1100] = 255
    rm_obj = pm.RemoveObject(mask=mask_array, method="telea", inpaint_radius=5)
    print(f"   RemoveObject: method={rm_obj.method}, radius={rm_obj.inpaint_radius}")

    # ── Section 4: Upscale + Denoise + Deblur ───────────────────────────
    upscale = pm.Upscale(factor=2)
    denoise = pm.Denoise(strength=0.6)
    deblur = pm.Deblur(strength=0.7, kernel_size=5)
    print(f"4. Upscale: factor={upscale.factor}")
    print(f"   Denoise: strength={denoise.strength}")
    print(f"   Deblur: strength={deblur.strength}, kernel={deblur.kernel_size}")

    # ── Section 5: ColorizeClip ─────────────────────────────────────────
    colorize = pm.ColorizeClip(saturation=1.2)
    print(f"5. ColorizeClip: saturation={colorize.saturation}")

    # ── Section 6: ExtendFrame ──────────────────────────────────────────
    extend = pm.ExtendFrame(direction="all", amount=50, method="telea")
    print(f"6. ExtendFrame: direction={extend.direction}, amount={extend.amount}")

    # ── Section 7: FrameInterpolation ───────────────────────────────────
    interp = pm.FrameInterpolation(factor=2)
    print(f"7. FrameInterpolation: factor={interp.factor}")

    # ── Section 8: FaceDetector + FaceBlur + FaceTracker ────────────────
    dummy_clip = pm.ImageClip(str(ASSETS / "product_hero.jpg"))
    dummy_clip.set_duration(SEC)

    face_det = pm.FaceDetector(clip=dummy_clip, method="haar", min_confidence=0.5)
    print(f"8. FaceDetector: method={face_det.method}, conf={face_det.min_confidence}")

    face_blur = pm.FaceBlur(clip=dummy_clip, strength=5, method="haar")
    print(f"   FaceBlur: strength={face_blur.strength}")

    face_track = pm.FaceTracker(clip=dummy_clip, max_distance=100.0)
    print(f"   FaceTracker: max_distance={face_track.max_distance}")

    # ── Section 9: SceneDetector + SilenceRemover ───────────────────────
    scene_det = pm.SceneDetector(clip=dummy_clip, threshold=0.3, min_scene_length=15)
    print(
        f"9. SceneDetector: threshold={scene_det.threshold}, min_len={scene_det.min_scene_length}"
    )

    silence_rem = pm.SilenceRemover(
        clip=dummy_clip,
        threshold_db=-40.0,
        min_silence_sec=0.5,
    )
    print(
        f"   SilenceRemover: threshold={silence_rem.threshold_db}dB, "
        f"min_silence={silence_rem.min_silence_sec}s"
    )

    # ── Section 10: ContentAwareCrop + AutoColor + HighlightDetector ────
    cac = pm.ContentAwareCrop(clip=dummy_clip, target_ratio="9:16", smoothing=15)
    print(f"10. ContentAwareCrop: ratio={cac.target_ratio}, smoothing={cac.smoothing}")

    auto_color = pm.AutoColor(clip=dummy_clip, strength=0.8)
    print(f"    AutoColor: strength={auto_color.strength}")

    highlight = pm.HighlightDetector(
        clip=dummy_clip,
        criteria="visual",
        top_n=3,
        segment_length=60,
    )
    print(f"    HighlightDetector: criteria={highlight.criteria}, top_n={highlight.top_n}")

    # ── Section 11: AutoEdit + MusicGeneration + SoundFXGeneration ──────
    auto_edit = pm.AutoEdit(clips=[dummy_clip], style="fast", target_duration=300)
    print(f"11. AutoEdit: style={auto_edit.style}, target={auto_edit.target_duration}")

    music_gen = pm.MusicGeneration(
        prompt="upbeat corporate background",
        duration=10.0,
        tempo=120,
    )
    print(f"    MusicGeneration: prompt='{music_gen.prompt[:30]}...', tempo={music_gen.tempo}")

    sfx_gen = pm.SoundFXGeneration(
        description="swoosh transition",
        duration=1.5,
        sample_rate=48000,
    )
    print(f"    SoundFXGeneration: desc='{sfx_gen.description}', dur={sfx_gen.duration}s")

    # ── Section 12: VoiceConversion + frame_diff + FrameDiff ────────────
    vc = pm.VoiceConversion(
        clip=dummy_clip,
        target_voice_sample=str(ASSETS / "voiceover.wav"),
        strength=0.8,
    )
    print(f"12. VoiceConversion: strength={vc.strength}")

    # frame_diff + FrameDiff — these work without optional deps
    frame_a = np.random.default_rng(42).integers(
        0,
        256,
        (100, 100, 4),
        dtype=np.uint8,
    )
    frame_b = np.random.default_rng(99).integers(
        0,
        256,
        (100, 100, 4),
        dtype=np.uint8,
    )
    diff: pm.FrameDiff = pm.frame_diff(frame_a, frame_b)
    print(
        f"    frame_diff: max_diff={diff.max_diff}, "
        f"mean_diff={diff.mean_diff:.1f}, psnr={diff.psnr:.1f}dB"
    )
    print(
        f"    FrameDiff: identical={diff.identical}, "
        f"changed={diff.changed_pixels}/{diff.total_pixels}"
    )

    # ── Audit frames ─────────────────────────────────────────────────────
    audit_dir = Path(__file__).parent.parent / "audit"
    audit_dir.mkdir(exist_ok=True)
    for sec_idx in range(12):
        mid = sec_idx * SEC + SEC // 2
        try:
            comp.export_frame(
                frame=mid,
                output=audit_dir / f"ex11_sec{sec_idx + 1}.png",
            )
        except (ValueError, RuntimeError) as e:
            print(f"  Audit sec{sec_idx + 1} skipped: {e}")
    print("Audit frames exported")

    # ── Render ───────────────────────────────────────────────────────────
    output_path = OUTPUT_DIR / "11_ai.mp4"
    comp.render(str(output_path), preset="h264_fast")
    size_mb = output_path.stat().st_size / 1024 / 1024
    print(f"Rendered: {output_path} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
