# Clip Operations

PyMotion provides a full set of non-destructive clip manipulation methods.
Every operation returns a new wrapper clip, leaving the original unchanged.

## Split

Split a clip into two at a given frame:

```python
from pymotion import ColorClip

clip = ColorClip("#1a1a2e")
clip.set_duration(120)

first, second = clip.split(60)
# first: frames 0-59, second: frames 60-119
```

## Join

Concatenate two clips sequentially:

```python
intro = ColorClip("#e94560")
intro.set_duration(60)

main = ColorClip("#1a1a2e")
main.set_duration(120)

combined = intro.join(main)
# combined.duration == 180
```

## Subclip

Extract a portion of a clip:

```python
clip = ColorClip("#1a1a2e")
clip.set_duration(300)

highlight = clip.subclip(60, 180)
# highlight.duration == 120
```

## Repeat

Loop a clip N times:

```python
loop = ColorClip("#1a1a2e")
loop.set_duration(30)

repeated = loop.repeat(4)
# repeated.duration == 120
```

## Freeze frame

Hold a single frame for a given duration:

```python
clip = ColorClip("#1a1a2e")
clip.set_duration(120)

frozen = clip.freeze_frame(frame=30, duration=60)
# Holds frame 30 for 60 frames, then resumes
```

## Concatenate

Merge a list of clips with optional transitions:

```python
from pymotion import ColorClip, concatenate, CrossDissolve

clips = [
    ColorClip("#e94560").set_duration(60),
    ColorClip("#1a1a2e").set_duration(60),
    ColorClip("#0f3460").set_duration(60),
]

# Simple concatenation
joined = concatenate(clips)

# With transitions
joined = concatenate(clips, transition=CrossDissolve(), transition_duration=15)
```

## Speed

Change playback speed uniformly:

```python
clip = ColorClip("#1a1a2e")
clip.set_duration(120)

fast = clip.speed(2.0)    # 2x speed, duration = 60
slow = clip.speed(0.5)    # half speed, duration = 240
```

For slow-motion with optical flow interpolation (requires OpenCV):

```python
smooth_slow = clip.speed(0.25, interpolation="optical_flow")
```

Falls back to frame duplication if OpenCV is unavailable.

## Speed ramp

Variable speed within one clip using keyframe pairs of `(frame, factor)`:

```python
clip = ColorClip("#1a1a2e")
clip.set_duration(120)

ramped = clip.speed_ramp([(0, 1.0), (30, 0.25), (90, 2.0), (120, 1.0)])
```

The speed interpolates linearly between each keyframe pair.

## Reverse

Play a clip backwards:

```python
reversed_clip = clip.reverse()
```

## Time remap

Arbitrary time remapping via a `KeyframeTrack` that maps output frames
to source frames:

```python
from pymotion import Keyframe, KeyframeTrack

curve = KeyframeTrack(keyframes=[
    Keyframe(frame=0, value=0.0),
    Keyframe(frame=30, value=60.0),    # jump ahead
    Keyframe(frame=60, value=30.0),    # go back
    Keyframe(frame=90, value=90.0),    # resume
])

remapped = clip.time_remap(curve)
```

## Combining operations

Operations are chainable:

```python
result = (
    clip
    .subclip(30, 150)
    .speed(1.5)
    .reverse()
    .repeat(2)
)
```

Each method returns a new clip, so the original is never modified.
