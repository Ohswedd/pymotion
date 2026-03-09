"""Tests for PyMotionConfig and global config management."""

from __future__ import annotations

from pymotion.config import PyMotionConfig, get_config, reset_config, set_config


class TestPyMotionConfig:
    """Tests for the PyMotionConfig dataclass."""

    def setup_method(self) -> None:
        """Reset config before each test."""
        reset_config()

    def teardown_method(self) -> None:
        """Reset config after each test."""
        reset_config()

    def test_default_values(self) -> None:
        """Default config has expected values."""
        cfg = PyMotionConfig()
        assert cfg.allow_network is True
        assert cfg.cache_max_bytes == 512 * 1024 * 1024
        assert cfg.max_image_size == 100 * 1024 * 1024
        assert cfg.max_audio_size == 500 * 1024 * 1024
        assert cfg.max_model_size == 200 * 1024 * 1024
        assert "fonts.googleapis.com" in cfg.font_allowlist
        assert "fonts.gstatic.com" in cfg.font_allowlist

    def test_custom_values(self) -> None:
        """Config can be created with custom values."""
        cfg = PyMotionConfig(
            allow_network=False,
            cache_max_bytes=1024,
            max_image_size=2048,
        )
        assert cfg.allow_network is False
        assert cfg.cache_max_bytes == 1024
        assert cfg.max_image_size == 2048

    def test_get_config_returns_default(self) -> None:
        """get_config returns a default config when none is set."""
        cfg = get_config()
        assert isinstance(cfg, PyMotionConfig)
        assert cfg.allow_network is True

    def test_set_config(self) -> None:
        """set_config replaces the global config."""
        custom = PyMotionConfig(allow_network=False, cache_max_bytes=999)
        set_config(custom)
        cfg = get_config()
        assert cfg.allow_network is False
        assert cfg.cache_max_bytes == 999

    def test_reset_config(self) -> None:
        """reset_config restores defaults."""
        set_config(PyMotionConfig(allow_network=False))
        reset_config()
        cfg = get_config()
        assert cfg.allow_network is True

    def test_get_config_singleton(self) -> None:
        """get_config returns the same instance on repeated calls."""
        c1 = get_config()
        c2 = get_config()
        assert c1 is c2

    def test_font_allowlist_independent(self) -> None:
        """Each config instance has its own font_allowlist."""
        c1 = PyMotionConfig()
        c2 = PyMotionConfig()
        c1.font_allowlist.append("custom.example.com")
        assert "custom.example.com" not in c2.font_allowlist
