"""TimelineResolver and FrameScheduler for keyframe resolution and frame dispatch.

The TimelineResolver pre-resolves all keyframes before the render loop.
The FrameScheduler distributes frames to workers (serial in Phase 0.1).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pymotion.clip.base import Clip
from pymotion.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class FrameState:
    """Resolved state for a single frame.

    Args:
        frame: The frame number.
        active_clips: List of clips active at this frame.
    """

    frame: int
    active_clips: list[Clip] = field(default_factory=list)


class TimelineResolver:
    """Resolves which clips are active at each frame.

    Pre-resolves the timeline once before the render loop begins,
    producing a list of FrameState objects.

    Args:
        clips: All clips in the composition.
        total_frames: Total number of frames.
    """

    def __init__(self, clips: list[Clip], total_frames: int) -> None:
        """Initialize the TimelineResolver.

        Args:
            clips: All clips to resolve.
            total_frames: Total duration in frames.
        """
        self.clips = clips
        self.total_frames = total_frames

    def resolve(self) -> list[FrameState]:
        """Resolve the timeline into per-frame states.

        Returns:
            List of FrameState objects, one per frame.
        """
        frames: list[FrameState] = []
        for frame in range(self.total_frames):
            active = [c for c in self.clips if c.start <= frame < c.end]
            frames.append(FrameState(frame=frame, active_clips=active))

        logger.debug(
            "timeline_resolved",
            total_frames=self.total_frames,
            total_clips=len(self.clips),
        )
        return frames

    def validate(self) -> list[str]:
        """Check for timeline issues and return warnings.

        Returns:
            List of warning messages.
        """
        warnings: list[str] = []
        for clip in self.clips:
            if clip.end > self.total_frames:
                warnings.append(
                    f"Clip extends beyond composition duration: "
                    f"ends at frame {clip.end}, composition has {self.total_frames} frames"
                )
        return warnings


class FrameScheduler:
    """Distributes frames to workers for rendering.

    In Phase 0.1, this is a simple serial scheduler. Parallel rendering
    will be added in a later phase.

    Args:
        total_frames: Total number of frames to schedule.
    """

    def __init__(self, total_frames: int) -> None:
        """Initialize the FrameScheduler.

        Args:
            total_frames: Total frames to render.
        """
        self.total_frames = total_frames

    def schedule(self) -> list[int]:
        """Return the list of frame indices to render in order.

        Returns:
            List of frame indices.
        """
        return list(range(self.total_frames))
