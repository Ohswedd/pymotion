"""Layout utilities — position resolution and named anchor mapping.

Provides the _resolve_position helper used by pip, grid, split_screen,
and stack to convert named anchors to pixel coordinates.
"""

from __future__ import annotations

# Named anchor → (x_fraction, y_fraction)
_ANCHOR_MAP: dict[str, tuple[float, float]] = {
    "top-left": (0.0, 0.0),
    "top-center": (0.5, 0.0),
    "top-right": (1.0, 0.0),
    "center-left": (0.0, 0.5),
    "center": (0.5, 0.5),
    "center-right": (1.0, 0.5),
    "bottom-left": (0.0, 1.0),
    "bottom-center": (0.5, 1.0),
    "bottom-right": (1.0, 1.0),
}


def _resolve_position(
    anchor: str | tuple[int, int],
    clip_size: tuple[int, int],
    container_size: tuple[int, int],
    margin: int = 10,
) -> tuple[int, int]:
    """Resolve a named anchor or pixel tuple to absolute pixel coordinates.

    For named anchors, positions the clip so it is aligned to the anchor
    point with a margin from the container edge.

    Args:
        anchor: Named anchor string (e.g. ``"bottom-right"``) or
            explicit ``(x, y)`` pixel tuple.
        clip_size: ``(width, height)`` of the clip to position.
        container_size: ``(width, height)`` of the container.
        margin: Pixel margin from container edge for named anchors.

    Returns:
        ``(x, y)`` pixel coordinates for the clip's top-left corner.

    Raises:
        ValueError: If the anchor string is not recognized.
    """
    if isinstance(anchor, tuple):
        return anchor

    anchor_lower = anchor.lower().strip()
    if anchor_lower not in _ANCHOR_MAP:
        valid = ", ".join(sorted(_ANCHOR_MAP.keys()))
        msg = f"Unknown anchor '{anchor}'. Valid anchors: {valid}"
        raise ValueError(msg)

    fx, fy = _ANCHOR_MAP[anchor_lower]
    cw, ch = container_size
    ow, oh = clip_size

    x = int(fx * (cw - ow - 2 * margin) + margin)
    y = int(fy * (ch - oh - 2 * margin) + margin)

    return x, y
