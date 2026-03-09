"""RenderPipeline — orchestrates the full frame rendering pipeline.

Coordinates backend selection, rendering, compositing, effects,
and color pipeline for each frame. Phase 0.1 uses serial rendering.
"""

from __future__ import annotations

from pymotion.render.backend_2d import CairoRenderer
from pymotion.render.interface import RendererInterface
from pymotion.utils.logging import get_logger

logger = get_logger(__name__)


class RenderPipeline:
    """Orchestrates the full rendering pipeline.

    Manages renderer backends and coordinates the render flow
    from timeline resolution through final frame output.
    """

    def __init__(self) -> None:
        """Initialize the render pipeline with default backends."""
        self.backends: list[RendererInterface] = [
            CairoRenderer(),
        ]
        logger.debug("pipeline_initialized", backends=len(self.backends))
