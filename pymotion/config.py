"""Global configuration for the PyMotion framework.

Provides PyMotionConfig with settings for network access, cache size,
file size limits, and other runtime behavior.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field


@dataclass
class PyMotionConfig:
    """Global configuration for PyMotion.

    Controls network access, asset cache size, file size limits,
    and other runtime behavior. Thread-safe singleton access
    via get_config() / set_config().

    Args:
        allow_network: Whether to allow network requests (e.g., Google Fonts).
        cache_max_bytes: Maximum asset cache size in bytes (default 512 MB).
        max_image_size: Maximum image asset size in bytes (default 100 MB).
        max_audio_size: Maximum audio asset size in bytes (default 500 MB).
        max_model_size: Maximum 3D model size in bytes (default 200 MB).
        font_allowlist: Allowed domains for font downloads.
    """

    allow_network: bool = True
    cache_max_bytes: int = 512 * 1024 * 1024
    max_image_size: int = 100 * 1024 * 1024
    max_audio_size: int = 500 * 1024 * 1024
    max_model_size: int = 200 * 1024 * 1024
    font_allowlist: list[str] = field(
        default_factory=lambda: [
            "fonts.googleapis.com",
            "fonts.gstatic.com",
        ]
    )


_lock = threading.Lock()
_config: PyMotionConfig | None = None


def get_config() -> PyMotionConfig:
    """Get the global PyMotionConfig instance.

    Returns a default config if none has been set.

    Returns:
        The current global configuration.
    """
    global _config  # noqa: PLW0603
    with _lock:
        if _config is None:
            _config = PyMotionConfig()
        return _config


def set_config(config: PyMotionConfig) -> None:
    """Set the global PyMotionConfig instance.

    Args:
        config: The new configuration to use.
    """
    global _config  # noqa: PLW0603
    with _lock:
        _config = config


def reset_config() -> None:
    """Reset the global config to defaults.

    Primarily useful for testing.
    """
    global _config  # noqa: PLW0603
    with _lock:
        _config = None
