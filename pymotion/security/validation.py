"""Input sanitization, path validation, and asset checks.

Provides security boundary functions that must be called at every
point where external input enters PyMotion.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from pymotion.utils.color import Color
from pymotion.utils.logging import get_logger

logger = get_logger(__name__)

# Magic bytes for common image/audio/video formats
_MAGIC_SIGNATURES: dict[str, list[bytes]] = {
    "image": [
        b"\x89PNG",  # PNG
        b"\xff\xd8\xff",  # JPEG
        b"RIFF",  # WEBP (RIFF container)
        b"GIF87a",  # GIF
        b"GIF89a",  # GIF
        b"<svg",  # SVG
    ],
    "audio": [
        b"ID3",  # MP3 with ID3 tag
        b"\xff\xfb",  # MP3 without tag
        b"\xff\xf3",  # MP3 without tag
        b"RIFF",  # WAV (RIFF container)
        b"fLaC",  # FLAC
        b"OggS",  # OGG
    ],
    "video": [
        b"\x00\x00\x00",  # MP4/MOV (ftyp box)
        b"\x1a\x45\xdf\xa3",  # WebM/MKV
    ],
}

# Control characters to strip (except newline, tab, carriage return)
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def validate_path(path: str | Path, base_dirs: list[Path]) -> Path:
    """Resolve and validate a file path against allowed base directories.

    Prevents path traversal attacks by ensuring the resolved path falls
    within one of the allowed base directories.

    Args:
        path: The file path to validate.
        base_dirs: List of allowed base directories.

    Returns:
        The resolved, validated Path.

    Raises:
        ValueError: If the path is outside all allowed base directories.
        FileNotFoundError: If the path does not exist.
    """
    resolved = Path(path).resolve()
    real = Path(os.path.realpath(resolved))

    # Check that the real path (after resolving symlinks) is within allowed dirs
    for base in base_dirs:
        base_resolved = base.resolve()
        try:
            real.relative_to(base_resolved)
            if not real.exists():
                msg = f"File does not exist: {real}"
                raise FileNotFoundError(msg)
            logger.debug("path_validated", path=str(real), base=str(base_resolved))
            return real
        except ValueError:
            continue

    msg = f"Path '{real}' is outside allowed directories: {[str(b) for b in base_dirs]}"
    raise ValueError(msg)


def validate_color(value: str) -> Color:
    """Parse and validate a color string.

    Args:
        value: Color string (hex, CSS name, etc.).

    Returns:
        Validated Color instance.

    Raises:
        ValueError: If the string is not a valid color.
    """
    return Color.parse(value)


def validate_asset_magic(path: Path, expected_types: list[str]) -> None:
    """Verify file magic bytes match expected media type.

    Reads the first bytes of a file and checks them against known
    magic byte signatures for the expected file types.

    Args:
        path: Path to the file to check.
        expected_types: List of expected types ("image", "audio", "video").

    Raises:
        ValueError: If the file's magic bytes don't match any expected type.
        FileNotFoundError: If the file does not exist.
    """
    if not path.exists():
        msg = f"File does not exist: {path}"
        raise FileNotFoundError(msg)

    with open(path, "rb") as f:
        header = f.read(16)

    for expected_type in expected_types:
        signatures = _MAGIC_SIGNATURES.get(expected_type, [])
        for sig in signatures:
            if header.startswith(sig):
                logger.debug(
                    "magic_validated",
                    path=str(path),
                    type=expected_type,
                )
                return

    msg = (
        f"File '{path.name}' does not match expected types {expected_types}. "
        f"Header bytes: {header[:8]!r}"
    )
    raise ValueError(msg)


# File size limits per §9.1
_FILE_SIZE_LIMITS: dict[str, int] = {
    "image": 100 * 1024 * 1024,  # 100 MB
    "audio": 500 * 1024 * 1024,  # 500 MB
    "video": 500 * 1024 * 1024,  # 500 MB (no explicit limit in PRD, match audio)
    "model": 200 * 1024 * 1024,  # 200 MB (3D models)
}


def validate_file_size(path: Path, asset_type: str) -> None:
    """Validate that a file does not exceed the size limit for its type.

    Args:
        path: Path to the file.
        asset_type: Asset type key ("image", "audio", "video", "model").

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file exceeds the size limit or type is unknown.
    """
    if not path.exists():
        msg = f"File does not exist: {path}"
        raise FileNotFoundError(msg)

    limit = _FILE_SIZE_LIMITS.get(asset_type)
    if limit is None:
        msg = f"Unknown asset type '{asset_type}'. Known: {list(_FILE_SIZE_LIMITS.keys())}"
        raise ValueError(msg)

    size = path.stat().st_size
    if size > limit:
        limit_mb = limit / (1024 * 1024)
        size_mb = size / (1024 * 1024)
        msg = (
            f"File '{path.name}' ({size_mb:.1f} MB) exceeds "
            f"{asset_type} size limit of {limit_mb:.0f} MB"
        )
        raise ValueError(msg)

    logger.debug("file_size_validated", path=str(path), size=size, type=asset_type)


def sanitize_text(text: str, max_length: int = 10_000) -> str:
    """Strip null bytes and control characters from user-provided text.

    Keeps printable characters, newlines, tabs, and carriage returns.

    Args:
        text: The raw text input to sanitize.
        max_length: Maximum allowed text length.

    Returns:
        Sanitized text string.

    Raises:
        ValueError: If text exceeds max_length after sanitization.
    """
    # Remove null bytes and control characters
    cleaned = _CONTROL_CHAR_RE.sub("", text)

    if len(cleaned) > max_length:
        msg = f"Text exceeds maximum length of {max_length} characters (got {len(cleaned)})"
        raise ValueError(msg)

    return cleaned
