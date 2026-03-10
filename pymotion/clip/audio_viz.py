"""Audio visualization clips — waveform, spectrum, spectrogram, reactive.

Renders audio data as animated video clips using Cairo, providing
waveform displays, frequency spectrum bars, scrolling spectrograms,
and audio-reactive visual effects.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import cairo
import numpy as np

from pymotion.clip.base import Clip, RenderContext
from pymotion.utils.color import Color
from pymotion.utils.logging import get_logger

if TYPE_CHECKING:
    from pymotion.effects.base import Effect

logger = get_logger(__name__)


def _surface_to_frame(surface: cairo.ImageSurface, h: int, w: int) -> np.ndarray:
    """Convert a Cairo surface to a BGRA numpy array.

    Args:
        surface: The Cairo image surface.
        h: Frame height.
        w: Frame width.

    Returns:
        BGRA numpy array of shape (h, w, 4), dtype uint8.
    """
    buf = surface.get_data()
    return np.ndarray(shape=(h, w, 4), dtype=np.uint8, buffer=bytes(buf)).copy()


@dataclass
class WaveformClip(Clip):
    """Animated audio waveform visualization.

    Renders an audio waveform as a scrolling or static display. The
    waveform amplitude is drawn as filled bars or a continuous line.

    Args:
        audio: Float64 audio samples, shape ``(n_samples,)`` or
               ``(n_samples, channels)``. If stereo, channels are averaged.
        style: Waveform rendering style (``"bars"`` or ``"line"``).
        color: Waveform color.
        background: Background color.
        sample_rate: Audio sample rate in Hz.
        line_width: Line width for ``"line"`` style.
    """

    audio: np.ndarray = field(default_factory=lambda: np.zeros(0, dtype=np.float64))
    style: str = "bars"
    color: Color = field(default_factory=lambda: Color.parse("#00FF87"))
    background: Color = field(default_factory=lambda: Color.parse("#0A0A0A"))
    sample_rate: int = 48000
    line_width: float = 2.0

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render a waveform visualization frame.

        Args:
            ctx: The render context for this frame.

        Returns:
            BGRA numpy array of shape (H, W, 4), dtype uint8.
        """
        w = ctx.resolution.width
        h = ctx.resolution.height

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        cr: cairo.Context[cairo.ImageSurface] = cairo.Context(surface)

        # Background
        bg = self.background
        cr.set_source_rgba(bg.r, bg.g, bg.b, bg.a)
        cr.paint()

        audio = self._mono_audio()
        if len(audio) == 0:
            return _surface_to_frame(surface, h, w)

        # Determine visible window based on current frame
        samples_per_frame = self.sample_rate // max(ctx.fps, 1)
        window_samples = samples_per_frame * w // 4  # Show ~w/4 frames of audio
        center_sample = ctx.local_frame * samples_per_frame
        start = max(0, center_sample - window_samples // 2)
        end = min(len(audio), start + window_samples)
        if end - start <= 0:
            return _surface_to_frame(surface, h, w)

        window = audio[start:end]

        # Downsample to width
        n_bins = min(w, len(window))
        if n_bins == 0:
            return _surface_to_frame(surface, h, w)

        bin_size = len(window) // n_bins
        if bin_size == 0:
            bin_size = 1
        amplitudes = np.array(
            [np.max(np.abs(window[i * bin_size : (i + 1) * bin_size])) for i in range(n_bins)],
            dtype=np.float64,
        )

        c = self.color
        cr.set_source_rgba(c.r, c.g, c.b, c.a)

        if self.style == "line":
            cr.set_line_width(self.line_width)
            mid_y = h / 2.0
            for i, amp in enumerate(amplitudes):
                x = i * w / n_bins
                y = mid_y - amp * mid_y * 0.9
                if i == 0:
                    cr.move_to(x, y)
                else:
                    cr.line_to(x, y)
            # Mirror
            for i in range(len(amplitudes) - 1, -1, -1):
                x = i * w / n_bins
                y = mid_y + amplitudes[i] * mid_y * 0.9
                cr.line_to(x, y)
            cr.close_path()
            cr.fill()
        else:
            # Bars style
            bar_w = max(1.0, w / n_bins - 1)
            mid_y = h / 2.0
            for i, amp in enumerate(amplitudes):
                x = i * w / n_bins
                bar_h = amp * mid_y * 0.9
                cr.rectangle(x, mid_y - bar_h, bar_w, bar_h * 2)
            cr.fill()

        return _surface_to_frame(surface, h, w)

    def _mono_audio(self) -> np.ndarray:
        """Convert audio to mono float64.

        Returns:
            Mono audio array.
        """
        if len(self.audio) == 0:
            return self.audio
        if self.audio.ndim == 2:
            out: np.ndarray = np.mean(self.audio, axis=1)
            return out
        return self.audio.astype(np.float64)


@dataclass
class SpectrumClip(Clip):
    """Animated frequency spectrum bar visualization.

    Renders audio as vertical frequency bars using FFT analysis.

    Args:
        audio: Float64 audio samples.
        bands: Number of frequency bands to display.
        style: Rendering style (``"bars"`` or ``"smooth"``).
        color_map: List of colors for band gradient (low to high freq).
        background: Background color.
        sample_rate: Audio sample rate in Hz.
    """

    audio: np.ndarray = field(default_factory=lambda: np.zeros(0, dtype=np.float64))
    bands: int = 32
    style: str = "bars"
    color_map: list[Color] = field(
        default_factory=lambda: [
            Color.parse("#00FF87"),
            Color.parse("#00D4FF"),
            Color.parse("#FF00E5"),
        ]
    )
    background: Color = field(default_factory=lambda: Color.parse("#0A0A0A"))
    sample_rate: int = 48000

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render a frequency spectrum frame.

        Args:
            ctx: The render context for this frame.

        Returns:
            BGRA numpy array of shape (H, W, 4), dtype uint8.
        """
        w = ctx.resolution.width
        h = ctx.resolution.height

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        cr: cairo.Context[cairo.ImageSurface] = cairo.Context(surface)

        bg = self.background
        cr.set_source_rgba(bg.r, bg.g, bg.b, bg.a)
        cr.paint()

        audio = self._mono_audio()
        if len(audio) == 0:
            return _surface_to_frame(surface, h, w)

        # Extract FFT window at current frame
        fft_size = 2048
        samples_per_frame = self.sample_rate // max(ctx.fps, 1)
        center = ctx.local_frame * samples_per_frame
        start = max(0, center - fft_size // 2)
        end = min(len(audio), start + fft_size)

        if end - start < 16:
            return _surface_to_frame(surface, h, w)

        window = audio[start:end]
        # Apply Hann window
        hann = np.hanning(len(window))
        windowed = window * hann

        # FFT
        spectrum = np.abs(np.fft.rfft(windowed))
        spectrum = spectrum[1:]  # Drop DC
        if len(spectrum) == 0:
            return _surface_to_frame(surface, h, w)

        # Bin into bands (logarithmic spacing)
        n_bands = min(self.bands, len(spectrum))
        band_edges = np.logspace(0, np.log10(len(spectrum)), n_bands + 1, dtype=np.int64)
        band_edges = np.clip(band_edges, 0, len(spectrum))

        magnitudes = np.zeros(n_bands, dtype=np.float64)
        for i in range(n_bands):
            lo = int(band_edges[i])
            hi = max(lo + 1, int(band_edges[i + 1]))
            magnitudes[i] = np.mean(spectrum[lo:hi])

        # Normalize
        peak = np.max(magnitudes)
        if peak > 0:
            magnitudes /= peak

        # Draw bars
        bar_w = max(1.0, (w - (n_bands - 1) * 2) / n_bands)
        gap = 2.0

        for i in range(n_bands):
            x = i * (bar_w + gap)
            bar_h = magnitudes[i] * h * 0.9
            y = h - bar_h

            # Interpolate color from color_map
            t = i / max(n_bands - 1, 1)
            c = self._lerp_color(t)
            cr.set_source_rgba(c.r, c.g, c.b, c.a)

            if self.style == "smooth":
                # Rounded top
                radius = min(bar_w / 2, 4)
                cr.new_path()
                cr.arc(x + radius, y + radius, radius, math.pi, 1.5 * math.pi)
                cr.arc(x + bar_w - radius, y + radius, radius, 1.5 * math.pi, 0)
                cr.line_to(x + bar_w, h)
                cr.line_to(x, h)
                cr.close_path()
                cr.fill()
            else:
                cr.rectangle(x, y, bar_w, bar_h)
                cr.fill()

        return _surface_to_frame(surface, h, w)

    def _mono_audio(self) -> np.ndarray:
        """Convert audio to mono."""
        if len(self.audio) == 0:
            return self.audio
        if self.audio.ndim == 2:
            out: np.ndarray = np.mean(self.audio, axis=1)
            return out
        return self.audio.astype(np.float64)

    def _lerp_color(self, t: float) -> Color:
        """Interpolate color from color_map.

        Args:
            t: Progress (0.0 to 1.0).

        Returns:
            Interpolated color.
        """
        if not self.color_map:
            return Color(1.0, 1.0, 1.0, 1.0)
        if len(self.color_map) == 1:
            return self.color_map[0]

        n = len(self.color_map) - 1
        idx = min(int(t * n), n - 1)
        frac = t * n - idx

        a = self.color_map[idx]
        b = self.color_map[min(idx + 1, n)]
        return Color(
            r=a.r + (b.r - a.r) * frac,
            g=a.g + (b.g - a.g) * frac,
            b=a.b + (b.b - a.b) * frac,
            a=a.a + (b.a - a.a) * frac,
        )


@dataclass
class SpectrogramClip(Clip):
    """Scrolling spectrogram visualization.

    Renders a time-frequency display where the x-axis represents
    time and the y-axis represents frequency. Color encodes magnitude.

    Args:
        audio: Float64 audio samples.
        style: Rendering style (``"heatmap"``).
        fft_size: FFT window size.
        sample_rate: Audio sample rate in Hz.
        color_low: Color for low magnitude.
        color_high: Color for high magnitude.
    """

    audio: np.ndarray = field(default_factory=lambda: np.zeros(0, dtype=np.float64))
    style: str = "heatmap"
    fft_size: int = 1024
    sample_rate: int = 48000
    color_low: Color = field(default_factory=lambda: Color.parse("#0A0A2E"))
    color_high: Color = field(default_factory=lambda: Color.parse("#FF00E5"))

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render a spectrogram frame.

        Args:
            ctx: The render context for this frame.

        Returns:
            BGRA numpy array of shape (H, W, 4), dtype uint8.
        """
        w = ctx.resolution.width
        h = ctx.resolution.height

        audio = self._mono_audio()
        if len(audio) == 0:
            frame = np.zeros((h, w, 4), dtype=np.uint8)
            bg = self.color_low
            frame[:, :, 0] = int(bg.b * 255)
            frame[:, :, 1] = int(bg.g * 255)
            frame[:, :, 2] = int(bg.r * 255)
            frame[:, :, 3] = 255
            return frame

        # Compute STFT columns for the visible window
        hop = self.sample_rate // max(ctx.fps, 1)
        n_freq = self.fft_size // 2

        # We render `w` columns (time steps)
        center_sample = ctx.local_frame * hop
        start_col = center_sample - (w // 2) * hop

        # Pre-compute entire spectrogram slice
        mag_matrix = np.zeros((n_freq, w), dtype=np.float64)

        for col in range(w):
            sample_start = start_col + col * hop
            if sample_start < 0 or sample_start + self.fft_size > len(audio):
                continue
            chunk = audio[sample_start : sample_start + self.fft_size]
            windowed = chunk * np.hanning(len(chunk))
            spec = np.abs(np.fft.rfft(windowed))[1 : n_freq + 1]
            mag_matrix[:, col] = spec

        # Normalize
        peak = np.max(mag_matrix)
        if peak > 0:
            mag_matrix /= peak

        # Log scale for better visibility
        mag_matrix = np.log1p(mag_matrix * 10) / np.log1p(10)

        # Build BGRA frame
        frame = np.zeros((h, w, 4), dtype=np.uint8)

        # Map magnitude to color (interpolate between color_low and color_high)
        cl = self.color_low
        ch = self.color_high

        for y in range(h):
            # Map y to frequency bin (invert: high freq at top)
            freq_idx = int((1.0 - y / h) * (n_freq - 1))
            freq_idx = max(0, min(n_freq - 1, freq_idx))

            for x in range(w):
                t = mag_matrix[freq_idx, x]
                r = cl.r + (ch.r - cl.r) * t
                g = cl.g + (ch.g - cl.g) * t
                b = cl.b + (ch.b - cl.b) * t
                frame[y, x, 0] = int(b * 255)
                frame[y, x, 1] = int(g * 255)
                frame[y, x, 2] = int(r * 255)
                frame[y, x, 3] = 255

        return frame

    def _mono_audio(self) -> np.ndarray:
        """Convert audio to mono."""
        if len(self.audio) == 0:
            return self.audio
        if self.audio.ndim == 2:
            out: np.ndarray = np.mean(self.audio, axis=1)
            return out
        return self.audio.astype(np.float64)


@dataclass
class AudioReactiveEffect:
    """Drives a visual effect parameter from audio amplitude.

    Analyzes audio in a specific frequency band and maps the amplitude
    to a visual effect property value each frame.

    Args:
        effect: The visual effect instance to modulate.
        audio: Float64 audio samples.
        property_name: Name of the effect property to modulate
                       (e.g. ``"value"``, ``"strength"``).
        band: Frequency band to react to — ``"low"`` (20–200 Hz),
              ``"mid"`` (200–2000 Hz), ``"high"`` (2000–20000 Hz),
              or ``"full"`` (all frequencies).
        sensitivity: Amplitude multiplier (higher = more reactive).
        sample_rate: Audio sample rate in Hz.
        min_value: Minimum output value.
        max_value: Maximum output value.
    """

    effect: Effect
    audio: np.ndarray = field(default_factory=lambda: np.zeros(0, dtype=np.float64))
    property_name: str = "strength"
    band: str = "full"
    sensitivity: float = 1.0
    sample_rate: int = 48000
    min_value: float = 0.0
    max_value: float = 1.0

    def get_value(self, frame: int, fps: int) -> float:
        """Compute the modulated value for a given frame.

        Args:
            frame: Frame number.
            fps: Frames per second.

        Returns:
            Modulated value clamped to [min_value, max_value].
        """
        audio = self._mono_audio()
        if len(audio) == 0:
            return self.min_value

        # Extract window around current frame
        samples_per_frame = self.sample_rate // max(fps, 1)
        center = frame * samples_per_frame
        fft_size = 2048
        start = max(0, center - fft_size // 2)
        end = min(len(audio), start + fft_size)

        if end - start < 16:
            return self.min_value

        window = audio[start:end]
        windowed = window * np.hanning(len(window))

        spectrum = np.abs(np.fft.rfft(windowed))
        freqs = np.fft.rfftfreq(len(window), d=1.0 / self.sample_rate)

        # Select frequency band
        if self.band == "low":
            mask = (freqs >= 20) & (freqs <= 200)
        elif self.band == "mid":
            mask = (freqs >= 200) & (freqs <= 2000)
        elif self.band == "high":
            mask = (freqs >= 2000) & (freqs <= 20000)
        else:  # "full"
            mask = freqs >= 20

        band_spectrum = spectrum[mask]
        if len(band_spectrum) == 0:
            return self.min_value

        # RMS of band
        rms = float(np.sqrt(np.mean(band_spectrum**2)))
        normalized = min(1.0, rms * self.sensitivity / max(np.max(spectrum), 1e-10))

        value = self.min_value + (self.max_value - self.min_value) * normalized
        clamped: float = max(self.min_value, min(self.max_value, value))
        return clamped

    def apply_to_frame(self, frame_data: np.ndarray, frame: int, fps: int) -> np.ndarray:
        """Apply the modulated effect to a video frame.

        Sets the effect's property to the audio-reactive value and
        applies the effect.

        Args:
            frame_data: BGRA frame array.
            frame: Frame number.
            fps: Frames per second.

        Returns:
            Processed frame.
        """
        from pymotion.clip.base import RenderContext, Resolution, TimeRange  # noqa: PLC0415

        value = self.get_value(frame, fps)
        if hasattr(self.effect, self.property_name):
            setattr(self.effect, self.property_name, value)

        h, w = frame_data.shape[:2]
        dummy_ctx = RenderContext(
            frame=frame,
            fps=fps,
            resolution=Resolution(w, h),
            time_range=TimeRange(0, frame + 1),
            local_frame=frame,
            progress=0.0,
        )
        result: np.ndarray = self.effect.apply(frame_data, dummy_ctx)
        return result

    def _mono_audio(self) -> np.ndarray:
        """Convert audio to mono."""
        if len(self.audio) == 0:
            return self.audio
        if self.audio.ndim == 2:
            out: np.ndarray = np.mean(self.audio, axis=1)
            return out
        return self.audio.astype(np.float64)
