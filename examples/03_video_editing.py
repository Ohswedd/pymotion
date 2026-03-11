"""EX03 — Clip Editing Operations.

Use-case: A before/after edit reel demonstrating every clip manipulation
operation in PyMotion.

Features exercised:
  VideoClip, clip.subclip, clip.split, clip.join, clip.repeat,
  clip.freeze_frame, clip.speed, clip.speed_ramp, clip.reverse,
  clip.time_remap, clip.stabilize, clip.create_proxy,
  concatenate, CrossDissolve,
  pip, grid, split_screen, stack,
  MotionTracker, StabilizedClip, ProxyClip,
  clear_proxy_cache, proxy_cache_size,
  PushLeft, PushRight, PushUp, PushDown,
  CoverLeft, CoverRight, CoverUp, CoverDown,
  SubClip, JoinedClip, ConcatenatedClip, RepeatedClip,
  FreezeFrameClip, SpeedClip, SpeedRampClip, ReversedClip,
  TimeRemappedClip

Output: 1920x1080, 30fps, 60s, preset h264_fast -> outputs/03_editing.mp4
Estimated render time: ~120s
"""

from __future__ import annotations

from pathlib import Path

import pymotion as pm

ASSETS = Path(__file__).parent / "assets"
OUTPUT_DIR = Path(__file__).parent.parent / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

SEG = 150  # 5s per segment at 30fps


def main() -> None:
    video_path = str(ASSETS / "sample_footage.mp4")
    src = pm.VideoClip(video_path)
    src.set_duration(300)  # 10s at 30fps

    audit_dir = Path(__file__).parent.parent / "audit"
    audit_dir.mkdir(exist_ok=True)

    # ── Exercise all clip operations ──────────────────────────────────────
    sub = src.subclip(30, 180)
    print(f"1. SubClip: {type(sub).__name__}, dur={sub.duration}")

    left, right = src.split(150)
    joined = left.join(right)
    print(f"2. split+join: {type(joined).__name__}, dur={joined.duration}")

    c1 = src.subclip(0, 90)
    c2 = src.subclip(120, 210)
    concat = pm.concatenate([c1, c2], transition=pm.CrossDissolve(), transition_duration=15)
    print(f"3. ConcatenatedClip: {type(concat).__name__}, dur={concat.duration}")

    rep = src.subclip(0, 50).repeat(3)
    print(f"4. RepeatedClip: {type(rep).__name__}, dur={rep.duration}")

    frozen = src.freeze_frame(frame=60, duration=30)
    print(f"5. FreezeFrameClip: {type(frozen).__name__}, dur={frozen.duration}")

    fast = src.speed(2.0)
    print(f"6. SpeedClip(2x): {type(fast).__name__}, dur={fast.duration}")

    slow = src.speed(0.5)
    print(f"7. SpeedClip(0.5x): {type(slow).__name__}, dur={slow.duration}")

    slow_of = src.speed(0.5, interpolation="optical_flow")
    print(f"8. SpeedClip(optical_flow): {type(slow_of).__name__}")

    ramped = src.speed_ramp(keyframes=[(0, 0.5), (75, 1.0), (150, 2.0)])
    print(f"9. SpeedRampClip: {type(ramped).__name__}, dur={ramped.duration}")

    rev = src.reverse()
    print(f"10. ReversedClip: {type(rev).__name__}, dur={rev.duration}")

    remap_curve = pm.KeyframeTrack(
        keyframes=[
            pm.Keyframe(0, 0.0),
            pm.Keyframe(75, 200.0),
            pm.Keyframe(150, 50.0),
        ]
    )
    remapped = src.time_remap(remap_curve)
    print(f"11. TimeRemappedClip: {type(remapped).__name__}")

    stabilized = src.stabilize(smoothing=30, border_mode="crop")
    print(f"12. StabilizedClip: {type(stabilized).__name__}")

    # ── Tracking ──────────────────────────────────────────────────────────
    tracker = pm.MotionTracker(clip=src, region=(800, 400, 200, 200))
    data = tracker.track()
    kfs = tracker.to_keyframes("position").keyframes
    print(f"13. Tracked {len(data)} frames, keyframes={len(kfs)}")

    # ── Layout helpers ────────────────────────────────────────────────────
    a = src.subclip(0, 90)
    a.set_duration(90)
    b = src.subclip(60, 150)
    b.set_duration(90)

    pip_c = pm.pip(a, b, position="bottom-right", size=(480, 270), shadow=True)
    print(f"14. pip: {pip_c.resolution.width}x{pip_c.resolution.height}")

    ss = pm.split_screen([a, b], layout="horizontal")
    print(f"15. split_screen: {ss.resolution.width}x{ss.resolution.height}")

    grid_c = pm.grid(
        [src.subclip(0, 60), src.subclip(60, 120), src.subclip(120, 180), src.subclip(180, 240)],
        rows=2,
        cols=2,
        gap=8,
    )
    print(f"16. grid: {grid_c.resolution.width}x{grid_c.resolution.height}")

    st = pm.stack([a, b], direction="horizontal", gap=4)
    print(f"17. stack: {st.resolution.width}x{st.resolution.height}")

    # ── Transitions ───────────────────────────────────────────────────────
    print(
        f"18. Push: {pm.PushLeft.__name__}, {pm.PushRight.__name__}, "
        f"{pm.PushUp.__name__}, {pm.PushDown.__name__}"
    )
    print(
        f"    Cover: {pm.CoverLeft.__name__}, {pm.CoverRight.__name__}, "
        f"{pm.CoverUp.__name__}, {pm.CoverDown.__name__}"
    )

    # ── Build video output: reel of operations ────────────────────────────
    # Use a fresh VideoClip — stabilize/tracker pollute the source frame cache
    vid = pm.VideoClip(video_path)
    vid.set_duration(300)

    segments = []

    # Original
    s = vid.subclip(0, SEG)
    s.set_duration(SEG)
    segments.append(s)

    # 2x speed
    s = vid.speed(2.0)
    s.set_duration(SEG)
    segments.append(s)

    # Reverse
    s = vid.reverse()
    s.set_duration(SEG)
    segments.append(s)

    # 0.5x slow motion
    s = vid.speed(0.5)
    s.set_duration(SEG)
    segments.append(s)

    # Freeze frame
    s = vid.freeze_frame(frame=60, duration=30)
    s.set_duration(SEG)
    segments.append(s)

    # Speed ramp
    s = vid.speed_ramp(keyframes=[(0, 0.3), (75, 1.0), (150, 2.0)])
    s.set_duration(SEG)
    segments.append(s)

    # Repeat (3x)
    s = vid.subclip(0, 50).repeat(3)
    s.set_duration(SEG)
    segments.append(s)

    # Time remap
    s = vid.time_remap(remap_curve)
    s.set_duration(SEG)
    segments.append(s)

    # Subclip
    s = vid.subclip(50, 200)
    s.set_duration(SEG)
    segments.append(s)

    # Optical flow slow-mo
    s = vid.speed(0.5, interpolation="optical_flow")
    s.set_duration(SEG)
    segments.append(s)

    # Original (outro)
    s = vid.subclip(100, 250)
    s.set_duration(SEG)
    segments.append(s)

    # Another subclip
    s = vid.subclip(0, 150)
    s.set_duration(SEG)
    segments.append(s)

    full = pm.concatenate(segments, transition=pm.CrossDissolve(), transition_duration=10)
    comp = pm.Composition(width=1920, height=1080, fps=30, duration=1800)
    comp.add(full)

    # ── Audit frames ─────────────────────────────────────────────────────
    for fn in [0, 150, 450, 900, 1350]:
        try:
            comp.export_frame(frame=fn, output=audit_dir / f"ex03_f{fn}.png")
        except (ValueError, RuntimeError) as e:
            print(f"  Audit f{fn} skipped: {e}")
    print("Audit frames exported")

    # ── Render ────────────────────────────────────────────────────────────
    output_path = OUTPUT_DIR / "03_editing.mp4"
    comp.render(str(output_path), preset="h264_fast")
    print(f"Rendered: {output_path} ({output_path.stat().st_size / 1024 / 1024:.1f} MB)")

    # ── Proxy demo (after render) ─────────────────────────────────────────
    proxy_src = pm.VideoClip(video_path)
    proxy_src.set_duration(300)
    proxy = proxy_src.create_proxy(scale=0.25)
    print(f"19. ProxyClip: {type(proxy).__name__}")
    print(f"    Cache: {pm.proxy_cache_size()} bytes")
    pm.clear_proxy_cache(older_than_days=0)
    print(f"    After cleanup: {pm.proxy_cache_size()} bytes")


if __name__ == "__main__":
    main()
