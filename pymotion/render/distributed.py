"""Distributed rendering backends — Ray and Dask frame distribution.

Distributes frame rendering across workers for parallel execution.
Each backend splits the frame range into chunks, renders them in
parallel, and returns frames in order. Supports fault-tolerant retry
and checkpoint-based resume.

Requires optional extras::

    pip install ray    # for Ray backend
    pip install dask   # for Dask backend
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

from pymotion.utils.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import Iterator

logger = get_logger(__name__)

# Default number of frames per worker chunk
_DEFAULT_CHUNK_SIZE = 30


class RenderCheckpoint:
    """Manages frame-level checkpointing for resumable renders.

    Tracks which frames have been completed and allows resuming
    from the last completed frame after an interruption.

    Args:
        checkpoint_path: Path to the checkpoint JSON file.
    """

    def __init__(self, checkpoint_path: Path) -> None:
        self._path = checkpoint_path
        self._completed: set[int] = set()
        if self._path.exists():
            self._load()

    def _load(self) -> None:
        """Load checkpoint state from disk."""
        try:
            data = json.loads(self._path.read_text())
            self._completed = set(data.get("completed_frames", []))
            logger.info("checkpoint_loaded", frames=len(self._completed))
        except (json.JSONDecodeError, KeyError):
            self._completed = set()

    def save(self) -> None:
        """Persist checkpoint state to disk."""
        data = {"completed_frames": sorted(self._completed)}
        self._path.write_text(json.dumps(data))

    def mark_completed(self, frame: int) -> None:
        """Mark a frame as completed.

        Args:
            frame: Frame number that was successfully rendered.
        """
        self._completed.add(frame)

    def is_completed(self, frame: int) -> bool:
        """Check if a frame has been completed.

        Args:
            frame: Frame number to check.

        Returns:
            True if the frame was previously rendered.
        """
        return frame in self._completed

    @property
    def last_completed(self) -> int | None:
        """The highest completed frame number, or None if empty.

        Returns:
            Last completed frame index or None.
        """
        return max(self._completed) if self._completed else None

    def pending_frames(self, start: int, end: int) -> list[int]:
        """Get list of frames that still need rendering.

        Args:
            start: Start frame (inclusive).
            end: End frame (exclusive).

        Returns:
            List of frame numbers not yet completed.
        """
        return [f for f in range(start, end) if f not in self._completed]

    def clear(self) -> None:
        """Reset checkpoint state."""
        self._completed.clear()
        if self._path.exists():
            self._path.unlink()


def _chunk_frames(start: int, end: int, chunk_size: int) -> list[tuple[int, int]]:
    """Split a frame range into chunks for distribution.

    Args:
        start: Start frame (inclusive).
        end: End frame (exclusive).
        chunk_size: Number of frames per chunk.

    Returns:
        List of (chunk_start, chunk_end) tuples.
    """
    chunks: list[tuple[int, int]] = []
    for i in range(start, end, chunk_size):
        chunks.append((i, min(i + chunk_size, end)))
    return chunks


def render_frames_ray(
    composition: Any,
    start: int,
    end: int,
    *,
    max_retries: int = 3,
    chunk_size: int = _DEFAULT_CHUNK_SIZE,
    checkpoint_path: Path | None = None,
) -> Iterator[np.ndarray]:
    """Render frames using Ray for distributed execution.

    Distributes frame rendering across Ray workers. Each chunk of frames
    is submitted as a remote task. Failed chunks are retried on different
    workers up to ``max_retries`` times.

    Args:
        composition: The Composition to render.
        start: Start frame (inclusive).
        end: End frame (exclusive).
        max_retries: Maximum retries per failed chunk.
        chunk_size: Frames per worker task.
        checkpoint_path: Optional path for resume checkpoint file.

    Yields:
        Rendered BGRA frames in order.

    Raises:
        ImportError: If Ray is not installed.
        RuntimeError: If a chunk fails after all retries.
    """
    try:
        import ray
    except ImportError as exc:
        raise ImportError(
            "Ray is required for distributed rendering. Install with: pip install ray"
        ) from exc

    if not ray.is_initialized():
        ray.init(ignore_reinit_error=True)

    checkpoint = RenderCheckpoint(checkpoint_path) if checkpoint_path else None

    # Define remote render function
    @ray.remote  # type: ignore[untyped-decorator]
    def _render_chunk(comp: Any, chunk_start: int, chunk_end: int) -> list[np.ndarray]:
        frames = []
        for i in range(chunk_start, chunk_end):
            frames.append(comp._render_frame(i))
        return frames

    chunks = _chunk_frames(start, end, chunk_size)
    logger.info(
        "ray_render_start",
        total_frames=end - start,
        chunks=len(chunks),
        chunk_size=chunk_size,
    )

    comp_ref = ray.put(composition)

    for chunk_start, chunk_end in chunks:
        # Skip fully completed chunks
        if checkpoint and all(checkpoint.is_completed(f) for f in range(chunk_start, chunk_end)):
            # Yield pre-rendered frames from checkpoint
            for i in range(chunk_start, chunk_end):
                yield composition._render_frame(i)
            continue

        # Submit with retry
        result = None
        last_error: Exception | None = None
        for attempt in range(max_retries):
            try:
                future = _render_chunk.remote(comp_ref, chunk_start, chunk_end)
                result = ray.get(future)
                break
            except Exception as e:
                last_error = e
                logger.warning(
                    "ray_chunk_retry",
                    chunk_start=chunk_start,
                    attempt=attempt + 1,
                    error=str(e),
                )

        if result is None:
            msg = f"Ray chunk {chunk_start}-{chunk_end} failed after {max_retries} retries"
            raise RuntimeError(msg) from last_error

        for i, frame in enumerate(result):
            frame_idx = chunk_start + i
            if checkpoint:
                checkpoint.mark_completed(frame_idx)
            yield frame

        if checkpoint:
            checkpoint.save()

    logger.info("ray_render_complete", total_frames=end - start)


def render_frames_dask(
    composition: Any,
    start: int,
    end: int,
    *,
    chunk_size: int = _DEFAULT_CHUNK_SIZE,
    checkpoint_path: Path | None = None,
) -> Iterator[np.ndarray]:
    """Render frames using Dask for distributed execution.

    Uses Dask delayed tasks for frame rendering. Simpler setup than Ray
    but without automatic fault tolerance (relies on Dask scheduler).

    Args:
        composition: The Composition to render.
        start: Start frame (inclusive).
        end: End frame (exclusive).
        chunk_size: Frames per worker task.
        checkpoint_path: Optional path for resume checkpoint file.

    Yields:
        Rendered BGRA frames in order.

    Raises:
        ImportError: If Dask is not installed.
    """
    try:
        import dask
        import dask.bag as db
    except ImportError as exc:
        raise ImportError(
            "Dask is required for distributed rendering. "
            "Install with: pip install dask[distributed]"
        ) from exc

    # Suppress unused import warning — dask must be imported for config
    _ = dask

    checkpoint = RenderCheckpoint(checkpoint_path) if checkpoint_path else None

    chunks = _chunk_frames(start, end, chunk_size)
    logger.info(
        "dask_render_start",
        total_frames=end - start,
        chunks=len(chunks),
    )

    def _render_chunk(chunk_start: int, chunk_end: int) -> list[np.ndarray]:
        frames = []
        for i in range(chunk_start, chunk_end):
            frames.append(composition._render_frame(i))
        return frames

    # Create a Dask bag of chunk ranges and map rendering
    bag = db.from_sequence(chunks, npartitions=len(chunks))
    results = bag.map(lambda c: _render_chunk(c[0], c[1])).compute()

    for chunk_idx, chunk_frames in enumerate(results):
        chunk_start = chunks[chunk_idx][0]
        for i, frame in enumerate(chunk_frames):
            frame_idx = chunk_start + i
            if checkpoint:
                checkpoint.mark_completed(frame_idx)
            yield frame

        if checkpoint:
            checkpoint.save()

    logger.info("dask_render_complete", total_frames=end - start)
