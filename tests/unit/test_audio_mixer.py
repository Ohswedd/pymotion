"""Tests for the audio mixing system — AudioMixer, AudioClipData."""

from __future__ import annotations

import numpy as np
import pytest

from pymotion.audio.mixer import (
    STEREO_CHANNELS,
    SURROUND_51_CHANNELS,
    AudioBus,
    AudioClipData,
    AudioMixer,
    ChannelLayout,
    SurroundChannel,
)


class TestAudioMixer:
    """Tests for AudioMixer."""

    def test_init_defaults(self) -> None:
        mixer = AudioMixer()
        assert mixer.sample_rate == 48000
        assert mixer.bit_depth == 24
        assert mixer.channels == 2

    def test_render_empty(self) -> None:
        """Rendering with no clips returns empty array."""
        mixer = AudioMixer()
        result = mixer.render()
        assert len(result) == 0
        assert result.dtype == np.int32

    def test_add_single_clip(self) -> None:
        """Add a single clip and render."""
        mixer = AudioMixer()
        samples = np.ones(1000, dtype=np.float64) * 0.5
        clip = AudioClipData(samples=samples, start_sample=0)
        mixer.add(clip)
        result = mixer.render()
        assert len(result) == 1000 * 2  # stereo interleaved
        assert result.dtype == np.int32

    def test_add_stereo_clip(self) -> None:
        """Add a stereo clip and render."""
        mixer = AudioMixer()
        samples = np.ones((1000, 2), dtype=np.float64) * 0.5
        clip = AudioClipData(samples=samples, start_sample=0)
        mixer.add(clip)
        result = mixer.render()
        assert len(result) == 1000 * 2

    def test_add_multiple_clips_same_track(self) -> None:
        """Multiple clips on the same track should mix."""
        mixer = AudioMixer()
        s1 = np.ones(500, dtype=np.float64) * 0.3
        s2 = np.ones(500, dtype=np.float64) * 0.3
        mixer.add(AudioClipData(samples=s1, start_sample=0))
        mixer.add(AudioClipData(samples=s2, start_sample=0))
        result = mixer.render()
        # Should have additive mix (0.3 + 0.3 = 0.6)
        assert len(result) == 500 * 2

    def test_add_clips_different_tracks(self) -> None:
        """Clips on different tracks should mix independently."""
        mixer = AudioMixer()
        s1 = np.ones(500, dtype=np.float64) * 0.5
        s2 = np.ones(500, dtype=np.float64) * 0.5
        mixer.add(AudioClipData(samples=s1), track="music")
        mixer.add(AudioClipData(samples=s2), track="voice")
        result = mixer.render()
        assert len(result) == 500 * 2

    def test_set_volume(self) -> None:
        """Setting volume should scale the track output."""
        mixer = AudioMixer()
        samples = np.ones(100, dtype=np.float64) * 1.0
        mixer.add(AudioClipData(samples=samples), track="music")
        mixer.set_volume("music", 0.5)
        result = mixer.render()
        # With volume 0.5, max val should be about half
        max_val = 2 ** (mixer.bit_depth - 1) - 1
        expected = int(0.5 * max_val)
        # Check first sample (left channel)
        assert abs(result[0] - expected) < 2

    def test_set_volume_nonexistent_track(self) -> None:
        """Setting volume on nonexistent track should raise ValueError."""
        mixer = AudioMixer()
        with pytest.raises(ValueError, match="Track.*not found"):
            mixer.set_volume("nonexistent", 0.5)

    def test_offset_clip(self) -> None:
        """Clip with start_sample > 0 should be offset in the mix."""
        mixer = AudioMixer()
        samples = np.ones(100, dtype=np.float64) * 0.5
        mixer.add(AudioClipData(samples=samples, start_sample=50))
        result = mixer.render()
        # Total should be 150 samples * 2 channels
        assert len(result) == 150 * 2
        # First 50 samples should be zero
        assert result[0] == 0
        assert result[98] == 0

    def test_clipping_at_boundaries(self) -> None:
        """Samples at ±1.0 should be clamped correctly."""
        mixer = AudioMixer()
        # Deliberately exceed 1.0 by mixing two full-volume clips
        s1 = np.ones(100, dtype=np.float64)
        s2 = np.ones(100, dtype=np.float64)
        mixer.add(AudioClipData(samples=s1))
        mixer.add(AudioClipData(samples=s2))
        result = mixer.render()
        max_val = 2 ** (mixer.bit_depth - 1) - 1
        # Should be clamped to max_val
        assert np.max(result) <= max_val

    def test_mono_mixer(self) -> None:
        """Mono mixer should output correctly."""
        mixer = AudioMixer(channels=1)
        samples = np.ones(100, dtype=np.float64) * 0.5
        mixer.add(AudioClipData(samples=samples))
        result = mixer.render()
        assert len(result) == 100  # 1 channel


class TestAudioClipData:
    """Tests for AudioClipData."""

    def test_init_defaults(self) -> None:
        samples = np.zeros(100, dtype=np.float64)
        clip = AudioClipData(samples=samples)
        assert clip.start_sample == 0
        assert clip.sample_rate == 48000

    def test_init_with_offset(self) -> None:
        samples = np.zeros(100, dtype=np.float64)
        clip = AudioClipData(samples=samples, start_sample=1000)
        assert clip.start_sample == 1000


class TestSurroundChannel:
    """Tests for SurroundChannel enum."""

    def test_channel_indices(self) -> None:
        assert SurroundChannel.L == 0
        assert SurroundChannel.R == 1
        assert SurroundChannel.C == 2
        assert SurroundChannel.LFE == 3
        assert SurroundChannel.LS == 4
        assert SurroundChannel.RS == 5

    def test_channel_count(self) -> None:
        assert len(SurroundChannel) == 6


class TestChannelLayout:
    """Tests for ChannelLayout enum."""

    def test_layout_values(self) -> None:
        assert ChannelLayout.MONO == 1
        assert ChannelLayout.STEREO == 2
        assert ChannelLayout.SURROUND_51 == 6


class TestChannelMaps:
    """Tests for channel name-to-index mappings."""

    def test_stereo_channels(self) -> None:
        assert STEREO_CHANNELS == {"L": 0, "R": 1}

    def test_surround_51_channels(self) -> None:
        assert SURROUND_51_CHANNELS == {
            "L": 0,
            "R": 1,
            "C": 2,
            "LFE": 3,
            "Ls": 4,
            "Rs": 5,
        }


class TestSurroundMixing:
    """Tests for 5.1 surround audio mixing."""

    def test_surround_mixer_init(self) -> None:
        """Create a 5.1 surround mixer."""
        mixer = AudioMixer(channels=6)
        assert mixer.channels == 6

    def test_surround_render_empty(self) -> None:
        """Rendering empty 5.1 mixer returns empty array."""
        mixer = AudioMixer(channels=6)
        result = mixer.render()
        assert len(result) == 0
        assert result.dtype == np.int32

    def test_surround_render_mono_clip(self) -> None:
        """Mono clip in 6-channel mixer duplicates across all channels."""
        mixer = AudioMixer(channels=6)
        samples = np.ones(100, dtype=np.float64) * 0.5
        mixer.add(AudioClipData(samples=samples))
        result = mixer.render()
        # 100 samples * 6 channels interleaved
        assert len(result) == 100 * 6

    def test_surround_routing_center_only(self) -> None:
        """Route a track to center channel only."""
        mixer = AudioMixer(channels=6)
        samples = np.ones(100, dtype=np.float64) * 0.8
        mixer.add(AudioClipData(samples=samples), track="dialogue")
        mixer.set_routing("dialogue", {"C": 1.0})
        result = mixer.render()

        # Reshape to (100, 6) to inspect per-channel
        max_val = 2 ** (mixer.bit_depth - 1) - 1
        reshaped = result.reshape(-1, 6)

        # Center channel (index 2) should have signal
        assert reshaped[0, SurroundChannel.C] != 0
        # L, R, LFE, Ls, Rs should be silent
        assert reshaped[0, SurroundChannel.L] == 0
        assert reshaped[0, SurroundChannel.R] == 0
        assert reshaped[0, SurroundChannel.LFE] == 0
        assert reshaped[0, SurroundChannel.LS] == 0
        assert reshaped[0, SurroundChannel.RS] == 0
        # Center should be close to 0.8 * max_val
        expected = int(0.8 * max_val)
        assert abs(reshaped[0, SurroundChannel.C] - expected) < 2

    def test_surround_routing_lfe(self) -> None:
        """Route a track to LFE with reduced gain."""
        mixer = AudioMixer(channels=6)
        samples = np.ones(100, dtype=np.float64) * 1.0
        mixer.add(AudioClipData(samples=samples), track="bass")
        mixer.set_routing("bass", {"LFE": 0.5})
        result = mixer.render()
        reshaped = result.reshape(-1, 6)

        max_val = 2 ** (mixer.bit_depth - 1) - 1
        expected = int(0.5 * max_val)
        assert abs(reshaped[0, SurroundChannel.LFE] - expected) < 2
        # Other channels silent
        assert reshaped[0, SurroundChannel.L] == 0
        assert reshaped[0, SurroundChannel.C] == 0

    def test_surround_routing_multiple_channels(self) -> None:
        """Route a track to front L, R, and center simultaneously."""
        mixer = AudioMixer(channels=6)
        samples = np.ones(100, dtype=np.float64) * 0.5
        mixer.add(AudioClipData(samples=samples), track="music")
        mixer.set_routing("music", {"L": 1.0, "R": 1.0, "C": 0.5})
        result = mixer.render()
        reshaped = result.reshape(-1, 6)

        max_val = 2 ** (mixer.bit_depth - 1) - 1
        # L and R should be at 0.5 * max
        assert abs(reshaped[0, SurroundChannel.L] - int(0.5 * max_val)) < 2
        assert abs(reshaped[0, SurroundChannel.R] - int(0.5 * max_val)) < 2
        # C should be at 0.25 * max (0.5 signal * 0.5 gain)
        assert abs(reshaped[0, SurroundChannel.C] - int(0.25 * max_val)) < 2
        # Surround channels silent
        assert reshaped[0, SurroundChannel.LS] == 0
        assert reshaped[0, SurroundChannel.RS] == 0

    def test_surround_routing_with_enum_keys(self) -> None:
        """Route using SurroundChannel enum values as keys."""
        mixer = AudioMixer(channels=6)
        samples = np.ones(100, dtype=np.float64) * 0.6
        mixer.add(AudioClipData(samples=samples), track="fx")
        mixer.set_routing("fx", {SurroundChannel.LS: 0.8, SurroundChannel.RS: 0.8})
        result = mixer.render()
        reshaped = result.reshape(-1, 6)

        max_val = 2 ** (mixer.bit_depth - 1) - 1
        expected = int(0.6 * 0.8 * max_val)
        assert abs(reshaped[0, SurroundChannel.LS] - expected) < 2
        assert abs(reshaped[0, SurroundChannel.RS] - expected) < 2
        assert reshaped[0, SurroundChannel.C] == 0

    def test_surround_routing_with_int_keys(self) -> None:
        """Route using integer channel indices as keys."""
        mixer = AudioMixer(channels=6)
        samples = np.ones(100, dtype=np.float64) * 0.7
        mixer.add(AudioClipData(samples=samples), track="narration")
        mixer.set_routing("narration", {2: 1.0})  # Center channel
        result = mixer.render()
        reshaped = result.reshape(-1, 6)

        max_val = 2 ** (mixer.bit_depth - 1) - 1
        assert abs(reshaped[0, 2] - int(0.7 * max_val)) < 2

    def test_surround_routing_nonexistent_track_raises(self) -> None:
        """Setting routing on nonexistent track should raise ValueError."""
        mixer = AudioMixer(channels=6)
        with pytest.raises(ValueError, match="Track.*not found"):
            mixer.set_routing("ghost", {"C": 1.0})

    def test_surround_routing_invalid_channel_name_raises(self) -> None:
        """Invalid channel name should raise ValueError."""
        mixer = AudioMixer(channels=6)
        samples = np.ones(100, dtype=np.float64)
        mixer.add(AudioClipData(samples=samples), track="t")
        with pytest.raises(ValueError, match="Unknown channel name"):
            mixer.set_routing("t", {"INVALID": 1.0})

    def test_surround_routing_channel_index_out_of_range_raises(self) -> None:
        """Channel index beyond mixer channels should raise ValueError."""
        mixer = AudioMixer(channels=6)
        samples = np.ones(100, dtype=np.float64)
        mixer.add(AudioClipData(samples=samples), track="t")
        with pytest.raises(ValueError, match="out of range"):
            mixer.set_routing("t", {10: 1.0})

    def test_surround_routing_negative_index_raises(self) -> None:
        """Negative channel index should raise ValueError."""
        mixer = AudioMixer(channels=6)
        samples = np.ones(100, dtype=np.float64)
        mixer.add(AudioClipData(samples=samples), track="t")
        with pytest.raises(ValueError, match="out of range"):
            mixer.set_routing("t", {-1: 1.0})

    def test_surround_multiple_tracks_different_routing(self) -> None:
        """Multiple tracks with different routing should mix correctly."""
        mixer = AudioMixer(channels=6)
        dialogue = np.ones(100, dtype=np.float64) * 0.4
        music = np.ones(100, dtype=np.float64) * 0.3

        mixer.add(AudioClipData(samples=dialogue), track="dialogue")
        mixer.add(AudioClipData(samples=music), track="music")

        mixer.set_routing("dialogue", {"C": 1.0})
        mixer.set_routing("music", {"L": 1.0, "R": 1.0})

        result = mixer.render()
        reshaped = result.reshape(-1, 6)

        max_val = 2 ** (mixer.bit_depth - 1) - 1
        # Center: dialogue at 0.4
        assert abs(reshaped[0, SurroundChannel.C] - int(0.4 * max_val)) < 2
        # L/R: music at 0.3
        assert abs(reshaped[0, SurroundChannel.L] - int(0.3 * max_val)) < 2
        assert abs(reshaped[0, SurroundChannel.R] - int(0.3 * max_val)) < 2

    def test_surround_routing_with_volume(self) -> None:
        """Track volume should combine with routing gain."""
        mixer = AudioMixer(channels=6)
        samples = np.ones(100, dtype=np.float64) * 1.0
        mixer.add(AudioClipData(samples=samples), track="fx")
        mixer.set_volume("fx", 0.5)
        mixer.set_routing("fx", {"Ls": 1.0, "Rs": 1.0})
        result = mixer.render()
        reshaped = result.reshape(-1, 6)

        max_val = 2 ** (mixer.bit_depth - 1) - 1
        # Volume 0.5 * routing gain 1.0 * signal 1.0 = 0.5
        expected = int(0.5 * max_val)
        assert abs(reshaped[0, SurroundChannel.LS] - expected) < 2

    def test_stereo_routing_with_string_keys(self) -> None:
        """Routing works for stereo mixers too (L/R names)."""
        mixer = AudioMixer(channels=2)
        samples = np.ones(100, dtype=np.float64) * 0.6
        mixer.add(AudioClipData(samples=samples), track="mono_src")
        mixer.set_routing("mono_src", {"L": 1.0})  # Left only
        result = mixer.render()
        reshaped = result.reshape(-1, 2)

        max_val = 2 ** (mixer.bit_depth - 1) - 1
        assert abs(reshaped[0, 0] - int(0.6 * max_val)) < 2
        assert reshaped[0, 1] == 0  # Right silent

    def test_channel_layout_as_mixer_channels(self) -> None:
        """ChannelLayout enum values work as mixer channel count."""
        mixer = AudioMixer(channels=ChannelLayout.SURROUND_51)
        assert mixer.channels == 6
        mixer_stereo = AudioMixer(channels=ChannelLayout.STEREO)
        assert mixer_stereo.channels == 2


class TestAudioBus:
    """Tests for audio bus routing."""

    def test_audio_bus_dataclass(self) -> None:
        """AudioBus has correct defaults."""
        bus = AudioBus(name="music")
        assert bus.name == "music"
        assert bus.volume == 1.0
        assert bus.pan == 0.0
        assert bus.tracks == []
        assert bus.routing is None

    def test_create_bus(self) -> None:
        """Create a named bus on the mixer."""
        mixer = AudioMixer()
        mixer.create_bus("dialogue", volume=0.8)
        assert "dialogue" in mixer._buses
        assert mixer._buses["dialogue"].volume == 0.8

    def test_create_duplicate_bus_raises(self) -> None:
        """Creating a bus with a duplicate name raises ValueError."""
        mixer = AudioMixer()
        mixer.create_bus("music")
        with pytest.raises(ValueError, match="already exists"):
            mixer.create_bus("music")

    def test_assign_track_to_bus(self) -> None:
        """Assign a track to a bus."""
        mixer = AudioMixer()
        samples = np.ones(100, dtype=np.float64) * 0.5
        mixer.add(AudioClipData(samples=samples), track="vocals")
        mixer.create_bus("dialogue")
        mixer.assign_track_to_bus("vocals", "dialogue")
        assert "vocals" in mixer._buses["dialogue"].tracks

    def test_assign_track_to_bus_idempotent(self) -> None:
        """Assigning the same track twice doesn't duplicate it."""
        mixer = AudioMixer()
        samples = np.ones(100, dtype=np.float64)
        mixer.add(AudioClipData(samples=samples), track="vocals")
        mixer.create_bus("dialogue")
        mixer.assign_track_to_bus("vocals", "dialogue")
        mixer.assign_track_to_bus("vocals", "dialogue")
        assert mixer._buses["dialogue"].tracks.count("vocals") == 1

    def test_assign_nonexistent_track_raises(self) -> None:
        mixer = AudioMixer()
        mixer.create_bus("music")
        with pytest.raises(ValueError, match="Track.*not found"):
            mixer.assign_track_to_bus("ghost", "music")

    def test_assign_to_nonexistent_bus_raises(self) -> None:
        mixer = AudioMixer()
        samples = np.ones(100, dtype=np.float64)
        mixer.add(AudioClipData(samples=samples), track="vocals")
        with pytest.raises(ValueError, match="Bus.*not found"):
            mixer.assign_track_to_bus("vocals", "ghost")

    def test_bus_volume_scales_output(self) -> None:
        """Bus volume scales all tracks on the bus."""
        mixer = AudioMixer()
        samples = np.ones(100, dtype=np.float64) * 1.0
        mixer.add(AudioClipData(samples=samples), track="music")
        mixer.create_bus("music_bus", volume=0.5)
        mixer.assign_track_to_bus("music", "music_bus")
        result = mixer.render()
        reshaped = result.reshape(-1, 2)

        max_val = 2 ** (mixer.bit_depth - 1) - 1
        expected = int(0.5 * max_val)
        assert abs(reshaped[0, 0] - expected) < 2

    def test_set_bus_volume(self) -> None:
        """set_bus_volume updates bus volume."""
        mixer = AudioMixer()
        samples = np.ones(100, dtype=np.float64) * 1.0
        mixer.add(AudioClipData(samples=samples), track="music")
        mixer.create_bus("music_bus")
        mixer.assign_track_to_bus("music", "music_bus")
        mixer.set_bus_volume("music_bus", 0.25)
        result = mixer.render()
        reshaped = result.reshape(-1, 2)

        max_val = 2 ** (mixer.bit_depth - 1) - 1
        expected = int(0.25 * max_val)
        assert abs(reshaped[0, 0] - expected) < 2

    def test_set_bus_volume_nonexistent_raises(self) -> None:
        mixer = AudioMixer()
        with pytest.raises(ValueError, match="Bus.*not found"):
            mixer.set_bus_volume("ghost", 0.5)

    def test_set_bus_pan(self) -> None:
        """Bus pan applies to all tracks on the bus."""
        mixer = AudioMixer()
        samples = np.ones(100, dtype=np.float64) * 0.5
        mixer.add(AudioClipData(samples=samples), track="fx")
        mixer.create_bus("fx_bus")
        mixer.assign_track_to_bus("fx", "fx_bus")
        mixer.set_bus_pan("fx_bus", 1.0)  # Full right
        result = mixer.render()
        reshaped = result.reshape(-1, 2)
        # Left should be near zero, right should have signal
        assert abs(reshaped[0, 0]) < 2
        assert reshaped[0, 1] != 0

    def test_set_bus_pan_nonexistent_raises(self) -> None:
        mixer = AudioMixer()
        with pytest.raises(ValueError, match="Bus.*not found"):
            mixer.set_bus_pan("ghost", 0.5)

    def test_bus_volume_keyframes(self) -> None:
        """Bus volume automation via keyframes."""
        mixer = AudioMixer()
        samples = np.ones(100, dtype=np.float64) * 1.0
        mixer.add(AudioClipData(samples=samples), track="music")
        mixer.create_bus("music_bus")
        mixer.assign_track_to_bus("music", "music_bus")
        # Fade from 0 to 1 over 100 samples
        mixer.set_bus_volume_keyframes("music_bus", [(0, 0.0), (99, 1.0)])
        result = mixer.render()
        reshaped = result.reshape(-1, 2)
        # First sample should be near zero
        assert abs(reshaped[0, 0]) < 2
        # Last sample should be near max
        max_val = 2 ** (mixer.bit_depth - 1) - 1
        assert abs(reshaped[99, 0] - max_val) < max_val * 0.05

    def test_set_bus_volume_keyframes_nonexistent_raises(self) -> None:
        mixer = AudioMixer()
        with pytest.raises(ValueError, match="Bus.*not found"):
            mixer.set_bus_volume_keyframes("ghost", [(0, 1.0)])

    def test_bus_routing_surround(self) -> None:
        """Bus with channel routing in 5.1 mode."""
        mixer = AudioMixer(channels=6)
        samples = np.ones(100, dtype=np.float64) * 0.6
        mixer.add(AudioClipData(samples=samples), track="dialogue")
        mixer.create_bus("dialogue_bus")
        mixer.assign_track_to_bus("dialogue", "dialogue_bus")
        mixer.set_bus_routing("dialogue_bus", {"C": 1.0, "LFE": 0.3})
        result = mixer.render()
        reshaped = result.reshape(-1, 6)

        max_val = 2 ** (mixer.bit_depth - 1) - 1
        assert abs(reshaped[0, SurroundChannel.C] - int(0.6 * max_val)) < 2
        assert abs(reshaped[0, SurroundChannel.LFE] - int(0.6 * 0.3 * max_val)) < 2
        assert reshaped[0, SurroundChannel.L] == 0

    def test_set_bus_routing_nonexistent_raises(self) -> None:
        mixer = AudioMixer(channels=6)
        with pytest.raises(ValueError, match="Bus.*not found"):
            mixer.set_bus_routing("ghost", {"C": 1.0})

    def test_set_bus_routing_invalid_channel_raises(self) -> None:
        mixer = AudioMixer(channels=6)
        mixer.create_bus("test")
        with pytest.raises(ValueError, match="Unknown channel name"):
            mixer.set_bus_routing("test", {"INVALID": 1.0})

    def test_multiple_buses_mix_together(self) -> None:
        """Multiple buses with different tracks mix into master."""
        mixer = AudioMixer()
        s1 = np.ones(100, dtype=np.float64) * 0.3
        s2 = np.ones(100, dtype=np.float64) * 0.2
        mixer.add(AudioClipData(samples=s1), track="vocals")
        mixer.add(AudioClipData(samples=s2), track="guitar")

        mixer.create_bus("dialogue")
        mixer.create_bus("music")
        mixer.assign_track_to_bus("vocals", "dialogue")
        mixer.assign_track_to_bus("guitar", "music")

        result = mixer.render()
        reshaped = result.reshape(-1, 2)

        max_val = 2 ** (mixer.bit_depth - 1) - 1
        expected = int(0.5 * max_val)  # 0.3 + 0.2
        assert abs(reshaped[0, 0] - expected) < 2

    def test_unbused_tracks_still_render(self) -> None:
        """Tracks not assigned to any bus still render directly to master."""
        mixer = AudioMixer()
        s1 = np.ones(100, dtype=np.float64) * 0.4
        s2 = np.ones(100, dtype=np.float64) * 0.3
        mixer.add(AudioClipData(samples=s1), track="direct")
        mixer.add(AudioClipData(samples=s2), track="bused")

        mixer.create_bus("music_bus")
        mixer.assign_track_to_bus("bused", "music_bus")

        result = mixer.render()
        reshaped = result.reshape(-1, 2)

        max_val = 2 ** (mixer.bit_depth - 1) - 1
        expected = int(0.7 * max_val)  # 0.4 direct + 0.3 via bus
        assert abs(reshaped[0, 0] - expected) < 2

    def test_bus_pan_keyframes(self) -> None:
        """Bus pan automation via keyframes."""
        mixer = AudioMixer()
        samples = np.ones(100, dtype=np.float64) * 0.5
        mixer.add(AudioClipData(samples=samples), track="music")
        mixer.create_bus("music_bus")
        mixer.assign_track_to_bus("music", "music_bus")
        # Pan from full left to full right
        mixer.set_bus_pan_keyframes("music_bus", [(0, -1.0), (99, 1.0)])
        result = mixer.render()
        reshaped = result.reshape(-1, 2)
        # At start: full left → left channel loud, right near zero
        assert abs(reshaped[0, 1]) < abs(reshaped[0, 0])
        # At end: full right → right channel loud, left near zero
        assert abs(reshaped[99, 0]) < abs(reshaped[99, 1])

    def test_set_bus_pan_keyframes_nonexistent_raises(self) -> None:
        mixer = AudioMixer()
        with pytest.raises(ValueError, match="Bus.*not found"):
            mixer.set_bus_pan_keyframes("ghost", [(0, 0.0)])

    def test_frame_accurate_track_volume_automation(self) -> None:
        """Track volume automation is sample-accurate."""
        mixer = AudioMixer()
        samples = np.ones(1000, dtype=np.float64) * 1.0
        mixer.add(AudioClipData(samples=samples), track="t")
        # Step from 0.0 at sample 0 to 1.0 at sample 999
        mixer.set_volume_keyframes("t", [(0, 0.0), (999, 1.0)])
        result = mixer.render()
        reshaped = result.reshape(-1, 2)
        max_val = 2 ** (mixer.bit_depth - 1) - 1
        # Sample at midpoint should be ~0.5
        mid = reshaped[500, 0]
        expected_mid = int(500 / 999 * max_val)
        assert abs(mid - expected_mid) < max_val * 0.02

    def test_track_volume_and_bus_volume_stack(self) -> None:
        """Track volume and bus volume multiply together."""
        mixer = AudioMixer()
        samples = np.ones(100, dtype=np.float64) * 1.0
        mixer.add(AudioClipData(samples=samples), track="vocals")
        mixer.set_volume("vocals", 0.5)  # Track at 50%
        mixer.create_bus("dialogue", volume=0.5)  # Bus at 50%
        mixer.assign_track_to_bus("vocals", "dialogue")

        result = mixer.render()
        reshaped = result.reshape(-1, 2)

        max_val = 2 ** (mixer.bit_depth - 1) - 1
        # 1.0 * 0.5 (track) * 0.5 (bus) = 0.25
        expected = int(0.25 * max_val)
        assert abs(reshaped[0, 0] - expected) < 2


class TestLUFSNormalization:
    """Tests for LUFS loudness normalization."""

    def test_normalize_method_sets_target(self) -> None:
        """normalize() stores the target LUFS value."""
        mixer = AudioMixer()
        mixer.normalize(target_lufs=-14.0)
        assert mixer._target_lufs == -14.0

    def test_normalize_default(self) -> None:
        """Default target is -14 LUFS (streaming)."""
        mixer = AudioMixer()
        mixer.normalize()
        assert mixer._target_lufs == -14.0

    def test_measure_lufs_silence(self) -> None:
        """Silent audio measures as very low LUFS."""
        samples = np.zeros((48000, 2), dtype=np.float64)
        lufs = AudioMixer._measure_lufs(samples, 48000)
        assert lufs <= -60.0

    def test_measure_lufs_empty(self) -> None:
        """Empty audio returns -70 LUFS."""
        samples = np.zeros((0, 2), dtype=np.float64)
        lufs = AudioMixer._measure_lufs(samples, 48000)
        assert lufs == -70.0

    def test_measure_lufs_sine(self) -> None:
        """A full-scale sine wave should measure near 0 LUFS."""
        t = np.arange(48000 * 2, dtype=np.float64) / 48000  # 2 seconds
        sine = np.sin(2 * np.pi * 1000 * t) * 1.0  # Full scale
        stereo = np.column_stack([sine, sine])
        lufs = AudioMixer._measure_lufs(stereo, 48000)
        # Full-scale 1kHz sine should be around -3 to +3 LUFS
        assert -5.0 < lufs < 5.0

    def test_normalize_increases_quiet_signal(self) -> None:
        """Normalization boosts a quiet signal."""
        mixer = AudioMixer()
        # Very quiet sine wave
        t = np.arange(48000, dtype=np.float64) / 48000
        quiet = np.sin(2 * np.pi * 440 * t) * 0.01  # ~ -40 dBFS
        stereo = np.column_stack([quiet, quiet])
        mixer.add(AudioClipData(samples=stereo))

        # Without normalization
        result_raw = mixer.render()
        rms_raw = np.sqrt(np.mean(result_raw.astype(np.float64) ** 2))

        # With normalization to -14 LUFS
        mixer.normalize(target_lufs=-14.0)
        result_norm = mixer.render()
        rms_norm = np.sqrt(np.mean(result_norm.astype(np.float64) ** 2))

        # Normalized should be louder
        assert rms_norm > rms_raw

    def test_normalize_reduces_loud_signal(self) -> None:
        """Normalization attenuates a loud signal."""
        mixer = AudioMixer()
        t = np.arange(48000, dtype=np.float64) / 48000
        loud = np.sin(2 * np.pi * 440 * t) * 0.9  # Near full scale
        stereo = np.column_stack([loud, loud])
        mixer.add(AudioClipData(samples=stereo))

        # Without normalization
        result_raw = mixer.render()
        rms_raw = np.sqrt(np.mean(result_raw.astype(np.float64) ** 2))

        # With normalization to -23 LUFS (broadcast, should be quieter)
        mixer.normalize(target_lufs=-23.0)
        result_norm = mixer.render()
        rms_norm = np.sqrt(np.mean(result_norm.astype(np.float64) ** 2))

        assert rms_norm < rms_raw

    def test_normalize_silent_mix_no_crash(self) -> None:
        """Normalizing a silent mix should not crash or produce NaN."""
        mixer = AudioMixer()
        samples = np.zeros(48000, dtype=np.float64)
        mixer.add(AudioClipData(samples=samples))
        mixer.normalize(target_lufs=-14.0)
        result = mixer.render()
        assert not np.any(np.isnan(result))
        assert np.all(result == 0)

    def test_lufs_surround_channel_weighting(self) -> None:
        """LUFS measurement applies surround channel weighting."""
        # Same signal, but in surround Ls/Rs channels should read louder
        # than front L/R due to +1.5 dB weighting
        t = np.arange(48000, dtype=np.float64) / 48000
        sine = np.sin(2 * np.pi * 1000 * t) * 0.5

        # Front L/R only
        front = np.zeros((48000, 6), dtype=np.float64)
        front[:, 0] = sine
        front[:, 1] = sine

        # Surround Ls/Rs only (same level)
        surround = np.zeros((48000, 6), dtype=np.float64)
        surround[:, 4] = sine
        surround[:, 5] = sine

        lufs_front = AudioMixer._measure_lufs(front, 48000)
        lufs_surr = AudioMixer._measure_lufs(surround, 48000)

        # Surround channels should measure louder due to weighting
        assert lufs_surr > lufs_front
