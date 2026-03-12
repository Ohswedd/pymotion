"""EX07 — Audio Mixing.

Use-case: A multi-track audio mix with effects, analysis, and
audio-reactive visualizations composited into a video.

Features exercised:
  AudioClip, Silence,
  AudioMixer, AudioBus, AudioClipData, ChannelLayout, SurroundChannel,
  STEREO_CHANNELS, SURROUND_51_CHANNELS,
  EQ, EQBand, Compressor, Limiter, Reverb, Delay,
  NoiseReduction, LowPassFilter, HighPassFilter,
  MultibandCompressor, ConvolutionReverb, PitchShift,
  audio_crossfade,
  WaveformClip, SpectrumClip, SpectrogramClip, AudioReactiveEffect,
  WaveformExtractor, BeatDetector, OnsetDetector, waveform_to_keyframes

Output: 1920x1080, 30fps, 20s, preset h264_fast -> outputs/07_audio.mp4
Estimated render time: ~60s
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

import pymotion as pm

ASSETS = Path(__file__).parent / "assets"
OUTPUT_DIR = Path(__file__).parent.parent / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

TOTAL = 600  # 20s at 30fps


def main() -> None:
    music_path = str(ASSETS / "music_upbeat.wav")
    sfx_path = str(ASSETS / "sfx_impact.wav")
    vo_path = str(ASSETS / "voiceover.wav")
    ir_path = str(ASSETS / "ir_hall.wav")

    # ── AudioClip ────────────────────────────────────────────────────────
    music = pm.AudioClip(music_path, volume=0.8, pan=0.0)
    music.trim(0.0, 20.0)
    music.fade_in(1.0).fade_out(2.0)
    print(f"1. AudioClip: {type(music).__name__}, vol={music.volume}")

    sfx = pm.AudioClip(sfx_path, volume=1.0, pan=-0.3)
    sfx.start_frame = 60
    print(f"2. SFX clip: pan={sfx.pan}")

    vo = pm.AudioClip(vo_path, volume=1.0, pan=0.0)
    vo.start_frame = 150
    print(f"3. Voiceover: start_frame={vo.start_frame}")

    # ── Silence ──────────────────────────────────────────────────────────
    silence = pm.Silence(duration_sec=1.0, sample_rate=48000, channels=2)
    print(f"4. Silence: {silence.duration_sec}s, channels={silence.channels}")

    # ── ChannelLayout + SurroundChannel ──────────────────────────────────
    print(f"5. ChannelLayout: STEREO={pm.ChannelLayout.STEREO}")
    print(f"   SURROUND_51={pm.ChannelLayout.SURROUND_51}")
    print(f"   SurroundChannel.C={pm.SurroundChannel.C}")
    print(f"   STEREO_CHANNELS={pm.STEREO_CHANNELS}")
    print(f"   SURROUND_51_CHANNELS keys={list(pm.SURROUND_51_CHANNELS.keys())}")

    # ── AudioMixer ───────────────────────────────────────────────────────
    mixer = pm.AudioMixer(sample_rate=48000, bit_depth=24, channels=2)
    print(f"6. AudioMixer: sr={mixer.sample_rate}, depth={mixer.bit_depth}")

    # ── AudioClipData ────────────────────────────────────────────────────
    test_samples = np.random.default_rng(42).uniform(-0.5, 0.5, (48000, 2))
    clip_data = pm.AudioClipData(
        samples=test_samples.astype(np.float64),
        start_sample=0,
        sample_rate=48000,
    )
    print(f"7. AudioClipData: samples={clip_data.samples.shape}")

    # Add clips to mixer tracks (auto-creates tracks)
    mixer.add(clip_data, track="music")
    mixer.set_volume("music", 0.7)
    sfx_data = pm.AudioClipData(
        samples=np.random.default_rng(7).uniform(-0.3, 0.3, (24000, 2)).astype(np.float64),
        start_sample=24000,
        sample_rate=48000,
    )
    mixer.add(sfx_data, track="sfx")
    mixer.set_volume("sfx", 1.0)

    # ── AudioBus ─────────────────────────────────────────────────────────
    mixer.create_bus("main_out", volume=0.95, pan=0.0)
    mixer.assign_track_to_bus("music", "main_out")
    mixer.assign_track_to_bus("sfx", "main_out")
    bus = pm.AudioBus(name="submix", volume=0.8, tracks=["music"])
    print(f"8. AudioBus: {bus.name}, tracks={bus.tracks}")

    # ── EQ + EQBand ──────────────────────────────────────────────────────
    eq = pm.EQ(
        bands=[
            pm.EQBand(frequency=80.0, gain_db=3.0, q=0.7, band_type="peak"),
            pm.EQBand(frequency=3000.0, gain_db=-2.0, q=1.0, band_type="peak"),
            pm.EQBand(frequency=10000.0, gain_db=1.5, q=0.5, band_type="peak"),
        ]
    )
    processed = eq.apply(test_samples.astype(np.float64), sample_rate=48000)
    print(f"9. EQ: {len(eq.bands)} bands, output={processed.shape}")

    # ── Compressor ───────────────────────────────────────────────────────
    comp_fx = pm.Compressor(threshold_db=-20.0, ratio=4.0, attack_ms=10.0, release_ms=100.0)
    audio_data = test_samples.astype(np.float64)
    out = comp_fx.apply(audio_data, sample_rate=48000)
    print(f"10. Compressor: threshold={comp_fx.threshold_db}dB, out={out.shape}")

    # ── Limiter ──────────────────────────────────────────────────────────
    limiter = pm.Limiter(threshold_db=-1.0, release_ms=50.0)
    out = limiter.apply(audio_data, sample_rate=48000)
    print(f"11. Limiter: threshold={limiter.threshold_db}dB, out={out.shape}")

    # ── Reverb ───────────────────────────────────────────────────────────
    reverb = pm.Reverb(room_size=0.6, damping=0.4, wet_level=0.3, dry_level=0.7)
    out = reverb.apply(audio_data, sample_rate=48000)
    print(f"12. Reverb: room={reverb.room_size}, out={out.shape}")

    # ── Delay ────────────────────────────────────────────────────────────
    delay = pm.Delay(delay_seconds=0.25, feedback=0.3, mix=0.4)
    out = delay.apply(audio_data, sample_rate=48000)
    print(f"13. Delay: {delay.delay_seconds}s, out={out.shape}")

    # ── PitchShift ───────────────────────────────────────────────────────
    pitch = pm.PitchShift(semitones=2.0)
    out = pitch.apply(audio_data, sample_rate=48000)
    print(f"14. PitchShift: {pitch.semitones} semitones, out={out.shape}")

    # ── NoiseReduction ───────────────────────────────────────────────────
    nr = pm.NoiseReduction(threshold_db=-40.0, ratio=10.0)
    out = nr.apply(audio_data, sample_rate=48000)
    print(f"15. NoiseReduction: threshold={nr.threshold_db}dB, out={out.shape}")

    # ── LowPassFilter + HighPassFilter ───────────────────────────────────
    lpf = pm.LowPassFilter(cutoff_hz=4000.0)
    out = lpf.apply(audio_data, sample_rate=48000)
    print(f"16. LowPassFilter: cutoff={lpf.cutoff_hz}Hz, out={out.shape}")

    hpf = pm.HighPassFilter(cutoff_hz=300.0)
    out = hpf.apply(audio_data, sample_rate=48000)
    print(f"17. HighPassFilter: cutoff={hpf.cutoff_hz}Hz, out={out.shape}")

    # ── MultibandCompressor ──────────────────────────────────────────────
    mbc = pm.MultibandCompressor(
        crossover_freqs=(200.0, 1000.0, 5000.0),
        thresholds_db=(-20.0, -18.0, -16.0, -14.0),
        ratios=(4.0, 3.0, 3.0, 2.0),
    )
    out = mbc.apply(audio_data, sample_rate=48000)
    print(f"18. MultibandCompressor: crossovers={mbc.crossover_freqs}")

    # ── ConvolutionReverb ────────────────────────────────────────────────
    conv_rev = pm.ConvolutionReverb(ir_path=ir_path, wet=0.3, dry=1.0)
    out = conv_rev.apply(audio_data, sample_rate=48000)
    print(f"19. ConvolutionReverb: wet={conv_rev.wet}, out={out.shape}")

    # ── audio_crossfade ──────────────────────────────────────────────────
    clip_a = np.random.default_rng(1).uniform(-0.3, 0.3, (24000, 2))
    clip_b = np.random.default_rng(2).uniform(-0.3, 0.3, (24000, 2))
    crossfaded = pm.audio_crossfade(
        clip_a.astype(np.float64),
        clip_b.astype(np.float64),
        crossfade_samples=4800,
        curve="equal_power",
    )
    print(f"20. audio_crossfade: output={crossfaded.shape}")

    # ── WaveformExtractor ────────────────────────────────────────────────
    extractor = pm.WaveformExtractor()
    mono = test_samples[:, 0].astype(np.float64)
    waveform = extractor.extract(mono, n_points=200)
    print(f"21. WaveformExtractor: {waveform.shape}")

    # ── BeatDetector ─────────────────────────────────────────────────────
    detector = pm.BeatDetector()
    beats = detector.detect(mono, sample_rate=48000, fps=30)
    print(f"22. BeatDetector: {len(beats)} beats detected")

    # ── OnsetDetector ────────────────────────────────────────────────────
    onset = pm.OnsetDetector()
    onsets = onset.detect(mono, sample_rate=48000, fps=30)
    print(f"23. OnsetDetector: {len(onsets)} onsets detected")

    # ── waveform_to_keyframes ────────────────────────────────────────────
    kfs = pm.waveform_to_keyframes(mono, sample_rate=48000, fps=30, min_value=0.0, max_value=1.0)
    print(f"24. waveform_to_keyframes: {len(kfs)} keyframes")

    # ── Composition with audio visualizations ────────────────────────────
    comp = pm.Composition(width=1920, height=1080, fps=30, duration=TOTAL)

    # Background
    bg_track = pm.Track(name="bg")
    bg = pm.GradientClip(color_start="#0a0a1a", color_end="#1a0a2e", direction=135.0)
    bg.set_duration(TOTAL)
    bg_track.clips.append(bg)
    comp.tracks.append(bg_track)

    # Section labels — visible throughout each section so audio-only frames
    # never appear as plain black.
    label_track = pm.Track(name="labels")
    for lbl, start in [
        ("Waveform", 0),
        ("Spectrum", 200),
        ("Spectrogram", 400),
    ]:
        # INCREASED label size 36→48px: principle 6, type does the work
        label = pm.TextClip(text=lbl, size=48, color="#555566")
        label.set_duration(200).at(start).set_position(960, 1000).set_opacity(0.6)
        label_track.clips.append(label)
    comp.tracks.append(label_track)

    # Section 1: WaveformClip (first 200 frames)
    wf_track = pm.Track(name="waveform")
    wf = pm.WaveformClip(
        audio=mono,
        style="bars",
        color=pm.Color.parse("#00FF87"),
        background=pm.Color.parse("#0A0A0A"),
        sample_rate=48000,
        line_width=2.0,
    )
    wf.set_duration(200).at(0).set_position(960, 270).set_scale(1.0)
    wf_track.clips.append(wf)
    comp.tracks.append(wf_track)
    print("25. WaveformClip: style=bars")

    # Section 2: SpectrumClip (frames 200-400)
    sp_track = pm.Track(name="spectrum")
    sp = pm.SpectrumClip(
        audio=mono,
        bands=32,
        style="bars",
        color_map=[
            pm.Color.parse("#00FF87"),
            pm.Color.parse("#00D4FF"),
            pm.Color.parse("#FF00E5"),
        ],
        background=pm.Color.parse("#0A0A0A"),
        sample_rate=48000,
    )
    sp.set_duration(200).at(200).set_position(960, 540)
    sp_track.clips.append(sp)
    comp.tracks.append(sp_track)
    print("26. SpectrumClip: 32 bands")

    # Section 3: SpectrogramClip (frames 400-600)
    sg_track = pm.Track(name="spectrogram")
    sg = pm.SpectrogramClip(
        audio=mono,
        style="heatmap",
        fft_size=1024,
        sample_rate=48000,
        color_low=pm.Color.parse("#0A0A2E"),
        color_high=pm.Color.parse("#FF00E5"),
    )
    sg.set_duration(200).at(400).set_position(960, 810)
    sg_track.clips.append(sg)
    comp.tracks.append(sg_track)
    print("27. SpectrogramClip: fft_size=1024")

    # AudioReactiveEffect — glow reacting to audio
    are = pm.AudioReactiveEffect(
        effect=pm.Glow(radius=10.0, strength=0.5),
        audio=mono,
        property_name="strength",
        band="full",
        sensitivity=1.5,
        sample_rate=48000,
        min_value=0.2,
        max_value=1.0,
    )
    print(f"28. AudioReactiveEffect: property={are.property_name}, sensitivity={are.sensitivity}")

    # ── Audit frames ─────────────────────────────────────────────────────
    audit_dir = Path(__file__).parent.parent / "audit"
    audit_dir.mkdir(exist_ok=True)
    for fn in [50, 150, 300, 450, 550]:
        try:
            comp.export_frame(frame=fn, output=audit_dir / f"ex07_f{fn}.png")
        except (ValueError, RuntimeError) as e:
            print(f"  Audit f{fn} skipped: {e}")
    print("Audit frames exported")

    # ── Render ───────────────────────────────────────────────────────────
    output_path = OUTPUT_DIR / "07_audio.mp4"
    comp.render(str(output_path), preset="h264_fast")
    size_mb = output_path.stat().st_size / 1024 / 1024
    print(f"Rendered: {output_path} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
