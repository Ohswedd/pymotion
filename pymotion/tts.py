"""TTSClip — text-to-speech audio generation.

Generates audio clips from text using system TTS, OpenAI, or
ElevenLabs engines. Returns a standard AudioClip-compatible format
that works with AudioMixer.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import numpy as np

from pymotion.utils.logging import get_logger

logger = get_logger(__name__)

#: Supported TTS engine types.
TTSEngine = Literal["system", "openai", "elevenlabs"]


@dataclass
class TTSClip:
    """Generate an audio clip from text using text-to-speech.

    Supports three engine backends:

    - ``"system"``: Uses ``pyttsx3`` (zero network dependencies).
    - ``"openai"``: Uses OpenAI TTS API (requires ``openai`` package
      and ``OPENAI_API_KEY`` environment variable).
    - ``"elevenlabs"``: Uses ElevenLabs API (requires ``elevenlabs``
      package and ``ELEVEN_API_KEY`` environment variable).

    Args:
        text: Text to synthesize.
        voice: Voice name or ID (engine-specific).
        engine: TTS engine to use.
        speed: Speech rate multiplier (1.0 = normal).
        pitch: Pitch adjustment (engine-specific, 0.0–2.0).
        sample_rate: Output sample rate in Hz.
    """

    text: str = ""
    voice: str = "default"
    engine: TTSEngine = "system"
    speed: float = 1.0
    pitch: float = 1.0
    sample_rate: int = 48000
    _samples: np.ndarray | None = field(default=None, repr=False)

    def generate(self) -> np.ndarray:
        """Synthesize speech and return audio samples.

        Returns:
            Float64 audio samples of shape ``(n_samples, 2)`` (stereo).

        Raises:
            ImportError: If the required engine package is not installed.
            RuntimeError: If synthesis fails.
        """
        if not self.text:
            self._samples = np.zeros((0, 2), dtype=np.float64)
            return self._samples

        if self.engine == "system":
            samples = self._generate_system()
        elif self.engine == "openai":
            samples = self._generate_openai()
        elif self.engine == "elevenlabs":
            samples = self._generate_elevenlabs()
        else:
            msg = f"Unsupported TTS engine: {self.engine}"
            raise ValueError(msg)

        self._samples = samples
        logger.debug(
            "tts_generated",
            engine=self.engine,
            text_length=len(self.text),
            samples=len(samples),
        )
        return samples

    def get_samples(self) -> np.ndarray:
        """Get the generated audio samples (generates if not cached).

        Returns:
            Float64 audio samples of shape ``(n_samples, 2)``.
        """
        if self._samples is not None:
            return self._samples
        return self.generate()

    def _generate_system(self) -> np.ndarray:
        """Generate speech using pyttsx3 system TTS.

        Returns:
            Float64 stereo audio samples.

        Raises:
            ImportError: If pyttsx3 is not installed.
        """
        try:
            import pyttsx3  # type: ignore[import-not-found]  # noqa: PLC0415
        except ImportError:
            msg = "pyttsx3 is required for system TTS. Install it with: pip install pyttsx3"
            raise ImportError(msg)  # noqa: B904

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            engine_inst: Any = pyttsx3.init()
            engine_inst.setProperty("rate", int(200 * self.speed))

            if self.voice != "default":
                voices = engine_inst.getProperty("voices")
                for v in voices:
                    if self.voice.lower() in v.name.lower():
                        engine_inst.setProperty("voice", v.id)
                        break

            engine_inst.save_to_file(self.text, tmp_path)
            engine_inst.runAndWait()

            return self._decode_wav(tmp_path)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def _generate_openai(self) -> np.ndarray:
        """Generate speech using OpenAI TTS API.

        Returns:
            Float64 stereo audio samples.

        Raises:
            ImportError: If openai package is not installed.
        """
        try:
            import openai  # noqa: PLC0415
        except ImportError:
            msg = "openai is required for OpenAI TTS. Install it with: pip install openai"
            raise ImportError(msg)  # noqa: B904

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            client: Any = openai.OpenAI()
            voice = self.voice if self.voice != "default" else "alloy"
            response: Any = client.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=self.text,
                speed=self.speed,
            )
            response.stream_to_file(tmp_path)
            return self._decode_wav(tmp_path)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def _generate_elevenlabs(self) -> np.ndarray:
        """Generate speech using ElevenLabs API.

        Returns:
            Float64 stereo audio samples.

        Raises:
            ImportError: If elevenlabs package is not installed.
        """
        try:
            from elevenlabs.client import ElevenLabs  # type: ignore[import-not-found]  # noqa: PLC0415, I001
        except ImportError:
            msg = (
                "elevenlabs is required for ElevenLabs TTS. Install it with: pip install elevenlabs"
            )
            raise ImportError(msg)  # noqa: B904

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            client: Any = ElevenLabs()
            voice = self.voice if self.voice != "default" else "Rachel"
            audio_gen: Any = client.generate(
                text=self.text,
                voice=voice,
                model="eleven_monolingual_v1",
            )
            with open(tmp_path, "wb") as f:
                for chunk in audio_gen:
                    f.write(chunk)
            return self._decode_wav(tmp_path)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def _decode_wav(self, path: str) -> np.ndarray:
        """Decode an audio file to float64 stereo via FFmpeg.

        Args:
            path: Path to the audio file.

        Returns:
            Float64 audio samples (n_samples, 2).
        """
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg is None:
            msg = "ffmpeg not found on PATH."
            raise RuntimeError(msg)

        cmd = [
            ffmpeg,
            "-v",
            "quiet",
            "-i",
            path,
            "-f",
            "f64le",
            "-acodec",
            "pcm_f64le",
            "-ac",
            "2",
            "-ar",
            str(self.sample_rate),
            "pipe:1",
        ]

        result = subprocess.run(  # noqa: S603
            cmd,
            shell=False,
            capture_output=True,
            timeout=60,
        )

        if result.returncode != 0 or len(result.stdout) == 0:
            logger.warning("tts_decode_failed", path=path)
            return np.zeros((0, 2), dtype=np.float64)

        samples = np.frombuffer(result.stdout, dtype=np.float64)
        return samples.reshape(-1, 2)
