"""Audio analysis — BeatDetector, OnsetDetector, WaveformExtractor.

Provides tools for detecting beats, onsets (transients), and extracting
waveform amplitude envelopes from audio data. Uses librosa for analysis.
"""

from __future__ import annotations

import numpy as np

from pymotion.utils.logging import get_logger

logger = get_logger(__name__)


class BeatDetector:
    """Detects beat positions in audio data.

    Uses librosa's beat tracking to find rhythmic beat positions
    and returns them as frame numbers.
    """

    def detect(
        self,
        audio: np.ndarray,
        sample_rate: int,
        fps: int = 30,
    ) -> list[int]:
        """Detect beat positions and return as video frame numbers.

        Args:
            audio: Audio samples as 1D float array (mono).
            sample_rate: Audio sample rate in Hz.
            fps: Video frame rate for converting beat times to frames.

        Returns:
            List of beat positions as video frame numbers.
        """
        import librosa

        # Ensure mono
        if audio.ndim > 1:
            mono = np.mean(audio, axis=1)
        else:
            mono = audio

        mono_float = mono.astype(np.float32)

        _tempo, beat_frames_audio = librosa.beat.beat_track(
            y=mono_float,
            sr=sample_rate,
        )

        # Convert audio frames (hop-based) to time, then to video frames
        beat_times: np.ndarray = librosa.frames_to_time(beat_frames_audio, sr=sample_rate)

        video_frames = [int(round(t * fps)) for t in beat_times]
        logger.info(
            "beats_detected",
            count=len(video_frames),
            sample_rate=sample_rate,
            fps=fps,
        )
        return video_frames


class OnsetDetector:
    """Detects onset (transient) positions in audio data.

    Onsets are points where a new sound event begins — more granular
    than beats, capturing individual notes, hits, and transients.
    """

    def detect(
        self,
        audio: np.ndarray,
        sample_rate: int,
        fps: int = 30,
    ) -> list[int]:
        """Detect onset positions and return as video frame numbers.

        Args:
            audio: Audio samples as 1D float array (mono).
            sample_rate: Audio sample rate in Hz.
            fps: Video frame rate for converting onset times to frames.

        Returns:
            List of onset positions as video frame numbers.
        """
        import librosa

        if audio.ndim > 1:
            mono = np.mean(audio, axis=1)
        else:
            mono = audio

        mono_float = mono.astype(np.float32)

        onset_frames_audio = librosa.onset.onset_detect(
            y=mono_float,
            sr=sample_rate,
        )

        onset_times: np.ndarray = librosa.frames_to_time(onset_frames_audio, sr=sample_rate)

        video_frames = [int(round(t * fps)) for t in onset_times]
        logger.info(
            "onsets_detected",
            count=len(video_frames),
            sample_rate=sample_rate,
            fps=fps,
        )
        return video_frames


class WaveformExtractor:
    """Extracts amplitude envelope from audio for visualization.

    Produces a downsampled amplitude array suitable for rendering
    waveform displays or driving animation keyframes.
    """

    def extract(self, audio: np.ndarray, n_points: int) -> np.ndarray:
        """Extract amplitude envelope sampled at n_points.

        Args:
            audio: Audio samples as 1D or 2D float array.
            n_points: Number of output sample points.

        Returns:
            1D float32 array of amplitude values (0.0 to 1.0) with
            length n_points.

        Raises:
            ValueError: If n_points is less than 1.
        """
        if n_points < 1:
            msg = f"n_points must be >= 1, got {n_points}"
            raise ValueError(msg)

        # Convert to mono if stereo
        if audio.ndim > 1:
            mono = np.mean(audio, axis=1)
        else:
            mono = audio.copy()

        mono = mono.astype(np.float32)
        total = len(mono)

        if total == 0:
            return np.zeros(n_points, dtype=np.float32)

        # Divide audio into n_points chunks and take max abs in each
        chunk_size = max(1, total // n_points)
        envelope = np.zeros(n_points, dtype=np.float32)

        for i in range(n_points):
            start = i * chunk_size
            end = min(start + chunk_size, total)
            if start < total:
                envelope[i] = float(np.max(np.abs(mono[start:end])))

        # Normalize to 0-1 range
        peak = float(np.max(envelope))
        if peak > 0:
            envelope /= peak

        return envelope
