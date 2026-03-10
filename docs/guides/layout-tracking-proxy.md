# Layout, Tracking & Proxy

## Picture-in-Picture

Overlay a clip onto a main clip at a specific position and size:

```python
from pymotion import pip, ColorClip

main = ColorClip("#1a1a2e")
main.set_duration(150)

overlay = ColorClip("#e94560")
overlay.set_duration(150)

comp = pip(main, overlay, position="bottom-right", size=(320, 180))
comp.render("pip.mp4")
```

### Named anchors

The `position` parameter accepts pixel tuples or named anchors:

| Anchor | Position |
|--------|----------|
| `"top-left"` | Upper-left corner |
| `"top-center"` | Top edge, centered |
| `"top-right"` | Upper-right corner |
| `"center-left"` | Left edge, centered |
| `"center"` | Dead center |
| `"center-right"` | Right edge, centered |
| `"bottom-left"` | Lower-left corner |
| `"bottom-center"` | Bottom edge, centered |
| `"bottom-right"` | Lower-right corner |

## Grid

Arrange clips in a rows-by-columns grid:

```python
from pymotion import grid, ColorClip

clips = [
    ColorClip("#e94560").set_duration(90),
    ColorClip("#0f3460").set_duration(90),
    ColorClip("#16213e").set_duration(90),
    ColorClip("#533483").set_duration(90),
]

comp = grid(clips, rows=2, cols=2, gap=10, background="#000000")
comp.render("grid.mp4")
```

Each clip is auto-scaled to fit its cell.

## Split screen

Divide the frame into regions for each clip:

```python
from pymotion import split_screen, ColorClip

left = ColorClip("#e94560").set_duration(90)
right = ColorClip("#0f3460").set_duration(90)

# Built-in layouts
comp = split_screen([left, right], layout="horizontal")
comp = split_screen([left, right], layout="vertical")

# Quad split (4 clips)
comp = split_screen(clips, layout="quad")
```

For custom layouts, pass a list of normalized `(x, y, w, h)` rectangles:

```python
comp = split_screen(clips, layout=[
    (0.0, 0.0, 0.7, 1.0),   # main: left 70%
    (0.7, 0.0, 0.3, 0.5),   # top-right: 30% x 50%
    (0.7, 0.5, 0.3, 0.5),   # bottom-right: 30% x 50%
])
```

## Stack

Stack clips side-by-side or top-to-bottom:

```python
from pymotion import stack, ColorClip

a = ColorClip("#e94560").set_duration(90)
b = ColorClip("#0f3460").set_duration(90)

comp = stack([a, b], direction="horizontal", gap=5)
comp = stack([a, b], direction="vertical", gap=5)
```

The output resolution is calculated automatically from the clips.

---

## Motion tracking

Track a region across frames and extract position data:

```python
from pymotion import MotionTracker, VideoClip

source = VideoClip("footage.mp4")
tracker = MotionTracker(clip=source, region=(100, 100, 50, 50))

# Track returns {frame_index: Vec2} positions
positions = tracker.track()

# Convert to keyframes for animation
kf = tracker.to_keyframes("position")
```

### Follow tracker

Bind tracking data to another clip's position:

```python
from pymotion import MotionTracker, VideoClip, TextClip

source = VideoClip("footage.mp4")
tracker = MotionTracker(clip=source, region=(100, 100, 50, 50))
tracker.track()

label = TextClip("Target", font_size=24, color="#FF0000")
label.set_duration(source.duration)
label.follow_tracker(tracker, prop="position", offset=(0, -30))
```

The label will follow the tracked region with a 30-pixel vertical offset.

## Video stabilization

Smooth out camera shake:

```python
stabilized = clip.stabilize(smoothing=30)
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `smoothing` | `30` | Window size for motion smoothing (larger = smoother) |

The stabilized clip pre-computes motion offsets and shifts each frame
to counteract camera movement.

---

## Proxy workflow

Generate low-resolution proxies for faster preview rendering:

```python
proxy = clip.create_proxy(scale=0.25)
```

The proxy is cached on disk in `~/.pymotion/proxies/`. If the same clip
and scale are requested again, the cached proxy is reused.

### Cache management

```python
from pymotion import clear_proxy_cache, proxy_cache_size

# Total bytes used
size = proxy_cache_size()
print(f"Proxy cache: {size / 1024 / 1024:.1f} MB")

# Remove proxies older than 30 days
removed = clear_proxy_cache(older_than_days=30)
print(f"Removed {removed} stale proxies")
```

### Custom cache directory

```python
from pathlib import Path

proxy = clip.create_proxy(scale=0.5, cache_dir=Path("/tmp/my_proxies"))
```
