"""Color pipeline — color space conversion, LUT, and tone mapping.

Provides LUT loading (.cube format), trilinear interpolation,
color grading (lift/gamma/gain/saturation), and tone mapping.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from pymotion.security.validation import validate_path
from pymotion.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class LUT3D:
    """3D Look-Up Table for color transformation.

    Args:
        size: Grid size (e.g., 33 for a 33x33x33 LUT).
        data: RGB values as float32 array of shape (size, size, size, 3).
        title: Optional LUT title from file header.
    """

    size: int
    data: np.ndarray
    title: str = ""


def parse_cube_lut(source: str) -> LUT3D:
    """Parse a .cube LUT file.

    Supports 3D LUT format with TITLE, LUT_3D_SIZE, DOMAIN_MIN,
    DOMAIN_MAX, and data lines.

    Args:
        source: .cube file content as string.

    Returns:
        Parsed LUT3D instance.

    Raises:
        ValueError: If the file format is invalid.
    """
    title = ""
    size = 0
    domain_min = np.array([0.0, 0.0, 0.0], dtype=np.float32)
    domain_max = np.array([1.0, 1.0, 1.0], dtype=np.float32)
    values: list[list[float]] = []

    for line in source.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("TITLE"):
            title = line.split('"')[1] if '"' in line else line.split(None, 1)[1]
        elif line.startswith("LUT_3D_SIZE"):
            size = int(line.split()[1])
        elif line.startswith("DOMAIN_MIN"):
            parts = line.split()[1:]
            domain_min = np.array([float(x) for x in parts], dtype=np.float32)
        elif line.startswith("DOMAIN_MAX"):
            parts = line.split()[1:]
            domain_max = np.array([float(x) for x in parts], dtype=np.float32)
        elif line.startswith("LUT_1D_SIZE"):
            # Skip 1D LUT lines
            continue
        else:
            # Try to parse as data line
            parts = line.split()
            if len(parts) >= 3:
                try:
                    values.append([float(parts[0]), float(parts[1]), float(parts[2])])
                except ValueError:
                    continue

    if size == 0:
        msg = "Missing LUT_3D_SIZE in .cube file"
        raise ValueError(msg)

    expected = size * size * size
    if len(values) != expected:
        msg = f"Expected {expected} LUT entries for size {size}, got {len(values)}"
        raise ValueError(msg)

    # Reshape data into (size, size, size, 3) — R varies fastest
    data = np.array(values, dtype=np.float32).reshape(size, size, size, 3)

    # Scale data from domain to 0-1 if needed
    scale = domain_max - domain_min
    if not np.allclose(scale, [1.0, 1.0, 1.0]) or not np.allclose(domain_min, [0.0, 0.0, 0.0]):
        data = (data - domain_min) / np.maximum(scale, 1e-10)

    logger.info("lut_loaded", title=title, size=size, entries=len(values))
    return LUT3D(size=size, data=data, title=title)


def load_cube_lut(
    path: str | Path,
    base_dirs: list[Path] | None = None,
) -> LUT3D:
    """Load a .cube LUT file from disk.

    Args:
        path: Path to the .cube file.
        base_dirs: Allowed directories for path validation.

    Returns:
        Parsed LUT3D.

    Raises:
        ValueError: If the file is invalid.
    """
    p = Path(path)
    if base_dirs is None:
        base_dirs = [p.parent.resolve()]
    validated = validate_path(p, base_dirs)
    content = validated.read_text(encoding="utf-8")
    return parse_cube_lut(content)


def apply_lut_trilinear(frame: np.ndarray, lut: LUT3D) -> np.ndarray:
    """Apply a 3D LUT to a frame using trilinear interpolation.

    Args:
        frame: BGRA numpy array, shape (H, W, 4), dtype uint8.
        lut: The 3D LUT to apply.

    Returns:
        BGRA numpy array with LUT applied.
    """
    h, w = frame.shape[:2]
    # Extract RGB (from BGRA)
    b_ch = frame[:, :, 0].astype(np.float32) / 255.0
    g_ch = frame[:, :, 1].astype(np.float32) / 255.0
    r_ch = frame[:, :, 2].astype(np.float32) / 255.0

    size = lut.size
    max_idx = size - 1

    # Scale to LUT indices
    r_idx = r_ch * max_idx
    g_idx = g_ch * max_idx
    b_idx = b_ch * max_idx

    # Floor and ceil indices
    r0 = np.clip(np.floor(r_idx).astype(np.int32), 0, max_idx - 1)
    g0 = np.clip(np.floor(g_idx).astype(np.int32), 0, max_idx - 1)
    b0 = np.clip(np.floor(b_idx).astype(np.int32), 0, max_idx - 1)
    r1 = np.minimum(r0 + 1, max_idx)
    g1 = np.minimum(g0 + 1, max_idx)
    b1 = np.minimum(b0 + 1, max_idx)

    # Fractional parts
    rf = r_idx - r0.astype(np.float32)
    gf = g_idx - g0.astype(np.float32)
    bf = b_idx - b0.astype(np.float32)

    # Trilinear interpolation (8 corners)
    # .cube format: R varies fastest → data[b, g, r]
    c000 = lut.data[b0, g0, r0]
    c001 = lut.data[b1, g0, r0]
    c010 = lut.data[b0, g1, r0]
    c011 = lut.data[b1, g1, r0]
    c100 = lut.data[b0, g0, r1]
    c101 = lut.data[b1, g0, r1]
    c110 = lut.data[b0, g1, r1]
    c111 = lut.data[b1, g1, r1]

    rf_3d = rf[:, :, np.newaxis]
    gf_3d = gf[:, :, np.newaxis]
    bf_3d = bf[:, :, np.newaxis]

    # Interpolate along R (axis 2 of the LUT = third index)
    c00 = c000 * (1 - rf_3d) + c100 * rf_3d
    c01 = c001 * (1 - rf_3d) + c101 * rf_3d
    c10 = c010 * (1 - rf_3d) + c110 * rf_3d
    c11 = c011 * (1 - rf_3d) + c111 * rf_3d

    # Interpolate along G (axis 1)
    c0 = c00 * (1 - gf_3d) + c10 * gf_3d
    c1 = c01 * (1 - gf_3d) + c11 * gf_3d

    # Interpolate along B (axis 0)
    result_rgb = c0 * (1 - bf_3d) + c1 * bf_3d

    # Convert back to uint8 BGRA
    result_rgb_u8 = np.clip(result_rgb * 255.0, 0, 255).astype(np.uint8)
    output = frame.copy()
    output[:, :, 2] = result_rgb_u8[:, :, 0]  # R
    output[:, :, 1] = result_rgb_u8[:, :, 1]  # G
    output[:, :, 0] = result_rgb_u8[:, :, 2]  # B
    return output


@dataclass
class ColorGrade:
    """Color grading parameters.

    Args:
        lift: Shadow color offset (RGB, -1 to 1).
        gamma: Midtone color adjustment (RGB, 0 to 2).
        gain: Highlight color multiplier (RGB, 0 to 2).
        saturation: Global saturation (0 = mono, 1 = normal, 2 = oversaturated).
    """

    lift: tuple[float, float, float] = (0.0, 0.0, 0.0)
    gamma: tuple[float, float, float] = (1.0, 1.0, 1.0)
    gain: tuple[float, float, float] = (1.0, 1.0, 1.0)
    saturation: float = 1.0


def apply_color_grade(frame: np.ndarray, grade: ColorGrade) -> np.ndarray:
    """Apply lift/gamma/gain/saturation color grading.

    Args:
        frame: BGRA numpy array, shape (H, W, 4), dtype uint8.
        grade: Color grading parameters.

    Returns:
        Graded BGRA numpy array.
    """
    # Work in float32 RGB (0-1)
    b_ch = frame[:, :, 0].astype(np.float32) / 255.0
    g_ch = frame[:, :, 1].astype(np.float32) / 255.0
    r_ch = frame[:, :, 2].astype(np.float32) / 255.0

    channels = [r_ch, g_ch, b_ch]

    for i, ch in enumerate(channels):
        # Lift (additive offset, mainly affects shadows)
        ch = ch + grade.lift[i]
        # Gain (multiply, mainly affects highlights)
        ch = ch * grade.gain[i]
        # Gamma (power curve, mainly affects midtones)
        gamma_val = grade.gamma[i]
        if gamma_val > 0 and gamma_val != 1.0:
            ch = np.power(np.clip(ch, 0.0, 1.0), 1.0 / gamma_val)
        channels[i] = ch

    r_ch, g_ch, b_ch = channels

    # Saturation
    if grade.saturation != 1.0:
        luma = 0.2126 * r_ch + 0.7152 * g_ch + 0.0722 * b_ch
        r_ch = luma + (r_ch - luma) * grade.saturation
        g_ch = luma + (g_ch - luma) * grade.saturation
        b_ch = luma + (b_ch - luma) * grade.saturation

    # Clamp and convert back
    output = frame.copy()
    output[:, :, 2] = np.clip(r_ch * 255.0, 0, 255).astype(np.uint8)
    output[:, :, 1] = np.clip(g_ch * 255.0, 0, 255).astype(np.uint8)
    output[:, :, 0] = np.clip(b_ch * 255.0, 0, 255).astype(np.uint8)
    return output


def apply_color_pipeline(
    frame: np.ndarray,
    color_space: str = "srgb",
    lut: LUT3D | None = None,
    grade: ColorGrade | None = None,
) -> np.ndarray:
    """Apply the full color pipeline to a rendered frame.

    Pipeline order: LUT → color grade → output.

    Args:
        frame: BGRA numpy array, shape (H, W, 4), dtype uint8.
        color_space: Target color space (currently only "srgb").
        lut: Optional 3D LUT to apply.
        grade: Optional color grading parameters.

    Returns:
        Processed BGRA frame.
    """
    if color_space != "srgb":
        logger.warning(
            "unsupported_color_space",
            color_space=color_space,
            fallback="srgb",
        )

    result = frame

    if lut is not None:
        result = apply_lut_trilinear(result, lut)

    if grade is not None:
        result = apply_color_grade(result, grade)

    return result
