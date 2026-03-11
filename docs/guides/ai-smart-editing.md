# AI Smart Editing Helpers

PyMotion v2.0 provides intelligent editing assistants that analyze
clips and automate common editing tasks. These are not effects — they
are analysis tools that return data or modified compositions.

## Scene detection

`SceneDetector` analyzes a clip and returns frame indices where scene
boundaries occur:

```python
from pymotion import SceneDetector

detector = SceneDetector(clip=my_clip, threshold=30.0)
boundaries = detector.detect()
# Returns: [0, 150, 310, 480, ...]  (frame indices)
```

The `threshold` parameter (default `30.0`) controls sensitivity —
lower values detect more subtle transitions, higher values only detect
hard cuts. Detection uses frame-to-frame difference analysis.

## Silence removal

`SilenceRemover` detects and removes silent segments from a clip,
then re-joins the remaining audio:

```python
from pymotion import SilenceRemover

remover = SilenceRemover(
    clip=my_clip,
    threshold_db=-40.0,
    min_silence_sec=0.5,
)
segments = remover.detect()
# Returns: [(0, 120), (180, 300), ...]  (start_frame, end_frame) of non-silent segments
```

Use the returned segments to build a new composition from only the
speaking portions of the clip.

## Highlight detection

`HighlightDetector` scores and extracts the most visually interesting
segments of a clip:

```python
from pymotion import HighlightDetector

detector = HighlightDetector(
    clip=my_clip,
    criteria="motion",  # "motion", "faces", or "combined"
    top_n=5,
)
highlights = detector.detect()
# Returns: [(score, start_frame, end_frame), ...]
```

Segments are ranked by score. The `criteria` parameter controls what
constitutes a "highlight" — motion energy, face presence, or a
weighted combination.

## Content-aware crop (AI reframing)

`ContentAwareCrop` uses saliency detection to intelligently reframe
footage for different aspect ratios:

```python
from pymotion import ContentAwareCrop

cropper = ContentAwareCrop(
    clip=my_clip,
    target_ratio=(9, 16),  # Portrait for TikTok/Reels
    smoothing=10,
)
crop_regions = cropper.analyze()
# Returns: [(x, y, w, h), ...]  per-frame crop regions
```

The `smoothing` parameter controls how gradually the crop window
moves between frames, preventing jarring jumps. This is ideal for
converting 16:9 footage to 9:16 vertical video while keeping subjects
centered.

## Auto color correction

`AutoColor` applies one-click AI color correction to achieve a
neutral, well-exposed baseline:

```python
from pymotion import AutoColor

corrector = AutoColor(clip=my_clip, sample_count=10)
corrections = corrector.analyze()
# Returns: {"brightness": 1.1, "contrast": 1.05, "saturation": 0.95, "white_balance": (1.02, 1.0, 0.98)}
```

The analysis samples frames evenly across the clip and computes
optimal corrections for brightness, contrast, saturation, and white
balance.

## Auto edit

`AutoEdit` takes raw clips and automatically selects the best moments,
cuts on beats, and returns a polished composition:

```python
from pymotion import AutoEdit

editor = AutoEdit(
    clips=[clip_a, clip_b, clip_c],
    style="dynamic",  # "dynamic", "calm", or "narrative"
    target_duration=300,  # frames
)
comp = editor.generate()
# Returns: a Composition with selected segments arranged on the timeline
```

The `style` parameter affects pacing — `"dynamic"` uses shorter cuts
and more motion, `"calm"` prefers longer takes, and `"narrative"`
follows scene structure. If `music` is provided, cuts align to beat
positions.
