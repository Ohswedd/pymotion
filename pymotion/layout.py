"""Layout helpers — pip, grid, split_screen, stack.

High-level composition functions that arrange clips spatially.
Each returns a Composition with clips positioned and scaled.
"""

from __future__ import annotations

from pymotion.clip.base import Clip
from pymotion.composition import Composition
from pymotion.utils.color import ColorInput
from pymotion.utils.layout import _resolve_position
from pymotion.utils.logging import get_logger

logger = get_logger(__name__)


def _clip_max_duration(*clips: Clip) -> int:
    """Return the maximum duration among the given clips.

    Args:
        *clips: Clips to compare.

    Returns:
        Maximum duration in frames.
    """
    return max(c.duration for c in clips) if clips else 0


def pip(
    main: Clip,
    overlay: Clip,
    position: str | tuple[int, int] = "bottom-right",
    size: tuple[int, int] | None = None,
    border: int | None = None,
    shadow: bool | None = None,
) -> Composition:
    """Composite an overlay clip onto a main clip as picture-in-picture.

    The main clip fills the full composition area. The overlay is
    scaled to ``size`` and placed at ``position``.

    Args:
        main: Background clip (determines output resolution).
        overlay: Foreground clip to overlay.
        position: Named anchor (e.g. ``"bottom-right"``) or
            ``(x, y)`` pixel coordinates for the overlay's top-left.
        size: ``(width, height)`` to scale the overlay to. If None,
            uses half the main width and proportional height.
        border: Border width in pixels around the overlay (drawn as
            white). None for no border.
        shadow: Whether to add a drop shadow. Currently reserved.

    Returns:
        A Composition with the main and overlay clips arranged.

    Raises:
        ValueError: If either clip has zero duration.
    """
    if main.duration <= 0 or overlay.duration <= 0:
        msg = "Both clips must have positive duration for pip"
        raise ValueError(msg)

    # Use main clip's dimensions or default
    main_w = 1920
    main_h = 1080

    if size is None:
        ow, oh = main_w // 4, main_h // 4
    else:
        ow, oh = size

    # Make dimensions even for codec compatibility
    ow = ow + (ow % 2)
    oh = oh + (oh % 2)

    x, y = _resolve_position(position, (ow, oh), (main_w, main_h))

    duration = _clip_max_duration(main, overlay)

    comp = Composition(width=main_w, height=main_h, fps=30, duration=duration)

    main_copy = main
    main_copy.start = 0
    main_copy.end = duration

    overlay_copy = overlay
    overlay_copy.start = 0
    overlay_copy.end = min(overlay.duration, duration)
    overlay_copy.set_position(float(x), float(y))
    overlay_copy.set_scale(ow / main_w, oh / main_h)

    comp.add(main_copy, overlay_copy)

    logger.debug(
        "pip_layout",
        position=str(position),
        overlay_size=(ow, oh),
        duration=duration,
    )

    return comp


def grid(
    clips: list[Clip],
    rows: int,
    cols: int,
    gap: int = 0,
    background: ColorInput = "#000000",
) -> Composition:
    """Arrange clips in a grid layout.

    Clips are placed left-to-right, top-to-bottom. Each clip is
    scaled to fit its cell. Extra cells are left empty.

    Args:
        clips: Clips to arrange.
        rows: Number of rows.
        cols: Number of columns.
        gap: Pixel gap between cells.
        background: Background color for the composition.

    Returns:
        A Composition with clips arranged in a grid.

    Raises:
        ValueError: If clips list is empty or rows/cols are invalid.
    """
    if not clips:
        msg = "Grid requires at least one clip"
        raise ValueError(msg)
    if rows <= 0 or cols <= 0:
        msg = f"Rows and cols must be positive, got {rows}x{cols}"
        raise ValueError(msg)

    # Output resolution: auto-calculate
    total_w = 1920
    total_h = 1080
    cell_w = (total_w - gap * (cols - 1)) // cols
    cell_h = (total_h - gap * (rows - 1)) // rows
    # Ensure even
    cell_w = cell_w - (cell_w % 2)
    cell_h = cell_h - (cell_h % 2)

    duration = _clip_max_duration(*clips)

    comp = Composition(
        width=total_w, height=total_h, fps=30, duration=duration, background=background
    )

    for idx, clip in enumerate(clips):
        if idx >= rows * cols:
            break
        r = idx // cols
        c = idx % cols
        x = c * (cell_w + gap)
        y = r * (cell_h + gap)
        clip.start = 0
        clip.end = min(clip.duration, duration)
        clip.set_position(float(x), float(y))
        clip.set_scale(cell_w / total_w, cell_h / total_h)
        comp.add(clip)

    logger.debug("grid_layout", rows=rows, cols=cols, gap=gap, clips=len(clips))

    return comp


def split_screen(
    clips: list[Clip],
    layout: str | list[tuple[float, float, float, float]] = "horizontal",
) -> Composition:
    """Arrange clips in a split-screen layout.

    Args:
        clips: Clips to arrange.
        layout: Layout mode. One of:
            - ``"horizontal"`` — side by side (2 clips)
            - ``"vertical"`` — stacked top and bottom (2 clips)
            - ``"quad"`` — 2x2 grid (4 clips)
            - List of ``(x, y, w, h)`` normalized rects (0.0-1.0)

    Returns:
        A Composition with clips arranged.

    Raises:
        ValueError: If clips list is empty or layout is invalid.
    """
    if not clips:
        msg = "split_screen requires at least one clip"
        raise ValueError(msg)

    total_w = 1920
    total_h = 1080

    rects: list[tuple[float, float, float, float]]
    if isinstance(layout, list):
        rects = layout
    elif layout == "horizontal":
        n = len(clips)
        rects = [(i / n, 0.0, 1.0 / n, 1.0) for i in range(n)]
    elif layout == "vertical":
        n = len(clips)
        rects = [(0.0, i / n, 1.0, 1.0 / n) for i in range(n)]
    elif layout == "quad":
        rects = [
            (0.0, 0.0, 0.5, 0.5),
            (0.5, 0.0, 0.5, 0.5),
            (0.0, 0.5, 0.5, 0.5),
            (0.5, 0.5, 0.5, 0.5),
        ]
    else:
        msg = (
            f"Unknown layout '{layout}'. Use 'horizontal', 'vertical', 'quad', or a list of rects."
        )
        raise ValueError(msg)

    duration = _clip_max_duration(*clips)
    comp = Composition(width=total_w, height=total_h, fps=30, duration=duration)

    for idx, clip in enumerate(clips):
        if idx >= len(rects):
            break
        rx, ry, rw, rh = rects[idx]
        x = int(rx * total_w)
        y = int(ry * total_h)
        w = int(rw * total_w)
        h = int(rh * total_h)
        clip.start = 0
        clip.end = min(clip.duration, duration)
        clip.set_position(float(x), float(y))
        clip.set_scale(w / total_w, h / total_h)
        comp.add(clip)

    logger.debug("split_screen_layout", layout=str(layout), clips=len(clips))

    return comp


def stack(
    clips: list[Clip],
    direction: str = "horizontal",
    gap: int = 0,
) -> Composition:
    """Stack clips side-by-side or top-to-bottom.

    Auto-calculates output resolution based on clip count and direction.

    Args:
        clips: Clips to stack.
        direction: ``"horizontal"`` (side by side) or ``"vertical"`` (top to bottom).
        gap: Pixel gap between clips.

    Returns:
        A Composition with clips stacked.

    Raises:
        ValueError: If clips list is empty or direction is invalid.
    """
    if not clips:
        msg = "stack requires at least one clip"
        raise ValueError(msg)
    if direction not in ("horizontal", "vertical"):
        msg = f"Direction must be 'horizontal' or 'vertical', got '{direction}'"
        raise ValueError(msg)

    n = len(clips)
    base_w = 1920
    base_h = 1080

    if direction == "horizontal":
        cell_w = (base_w - gap * (n - 1)) // n
        cell_w = cell_w - (cell_w % 2)
        total_w = cell_w * n + gap * (n - 1)
        # Ensure even
        total_w = total_w + (total_w % 2)
        total_h = base_h
    else:
        cell_h = (base_h - gap * (n - 1)) // n
        cell_h = cell_h - (cell_h % 2)
        total_w = base_w
        total_h = cell_h * n + gap * (n - 1)
        total_h = total_h + (total_h % 2)

    duration = _clip_max_duration(*clips)
    comp = Composition(width=total_w, height=total_h, fps=30, duration=duration)

    for idx, clip in enumerate(clips):
        clip.start = 0
        clip.end = min(clip.duration, duration)
        if direction == "horizontal":
            x = idx * (cell_w + gap)
            y = 0
            clip.set_position(float(x), float(y))
            clip.set_scale(cell_w / total_w, 1.0)
        else:
            x = 0
            y = idx * (cell_h + gap)
            clip.set_position(float(x), float(y))
            clip.set_scale(1.0, cell_h / total_h)
        comp.add(clip)

    logger.debug("stack_layout", direction=direction, gap=gap, clips=n)

    return comp
