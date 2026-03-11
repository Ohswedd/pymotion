# Distributed Rendering

PyMotion v2.5 supports distributing frame rendering across multiple
machines or processes using Ray or Dask backends. Both backends include
frame-level checkpointing for resumable renders.

## Setup

Install the backend you want:

```bash
pip install ray     # Ray backend
pip install dask    # Dask backend
```

## Using the backend parameter

The simplest way is to pass `backend` to `Composition.render()`:

```python
from pymotion import Composition

comp = Composition(1920, 1080, fps=30, duration=300)
# ... build composition ...

# Distribute across Ray workers
comp.render("output.mp4", backend="ray")

# Or use Dask
comp.render("output.mp4", backend="dask")
```

## Ray backend

Ray provides automatic fault tolerance with retry logic:

```python
from pymotion import render_frames_ray

# Render frames 0-300, retry failed chunks up to 3 times
for frame in render_frames_ray(comp, 0, 300, max_retries=3, chunk_size=30):
    # process each rendered frame
    pass
```

Key features:

- **Chunk-based distribution**: Frames are split into chunks (default 30
  frames each) and submitted as remote tasks.
- **Automatic retry**: Failed chunks are retried on different workers up
  to `max_retries` times.
- **Checkpoint support**: Pass `checkpoint_path` to resume after
  interruption.

## Dask backend

Dask uses delayed tasks for frame rendering:

```python
from pymotion import render_frames_dask

for frame in render_frames_dask(comp, 0, 300, chunk_size=30):
    pass
```

Dask is simpler to set up (no cluster init required for local use) but
does not include built-in retry logic — it relies on the Dask scheduler.

## Checkpointing

Both backends support frame-level checkpointing for resumable renders:

```python
from pymotion import Composition

comp = Composition(1920, 1080, fps=30, duration=9000)  # 5 min video
# ... build composition ...

# Render with checkpoint — if interrupted, resume from last completed frame
comp.render("output.mp4", backend="ray", checkpoint_path="render_checkpoint.json")
```

The checkpoint file is a JSON file tracking which frames have been
completed:

```json
{"completed_frames": [0, 1, 2, 3, 4, 5]}
```

## RenderCheckpoint API

For custom workflows, use the checkpoint class directly:

```python
from pymotion import RenderCheckpoint
from pathlib import Path

cp = RenderCheckpoint(Path("my_checkpoint.json"))

# Mark frames as done
cp.mark_completed(0)
cp.mark_completed(1)
cp.save()

# Check status
print(cp.is_completed(0))    # True
print(cp.last_completed)      # 1
print(cp.pending_frames(0, 10))  # [2, 3, 4, 5, 6, 7, 8, 9]

# Clean up when done
cp.clear()
```

## Ray vs Dask

| Feature | Ray | Dask |
|---------|-----|------|
| Fault tolerance | Built-in retry | Scheduler-dependent |
| Setup | `ray.init()` auto | No init needed (local) |
| Cluster support | Yes (Ray cluster) | Yes (Dask distributed) |
| Overhead | Higher (actor model) | Lower (delayed tasks) |
| Best for | Long renders, unreliable workers | Local parallelism, simple setup |

## Chunk size tuning

The `chunk_size` parameter controls how many frames each worker renders
per task. Smaller chunks give better load balancing but higher overhead:

- **Short compositions** (< 300 frames): `chunk_size=30` (default)
- **Long compositions** (1000+ frames): `chunk_size=60-120`
- **Very long compositions** (10000+ frames): `chunk_size=300`
