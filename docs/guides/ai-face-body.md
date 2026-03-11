# AI Face & Body

PyMotion v2.0 includes face detection, tracking, and automatic face
blurring. These features use OpenCV's DNN module under the hood and
are available with `pip install "pymotion-studio[ai]"`.

## Face detection

`FaceDetector` analyzes a clip and returns bounding boxes for all
detected faces per frame:

```python
from pymotion import FaceDetector

detector = FaceDetector(
    clip=my_clip,
    method="haar",         # "haar" (fast) or "dnn" (more accurate)
    min_confidence=0.7,    # Minimum confidence for DNN method
)
faces = detector.detect()
# Returns: {0: [(x, y, w, h), ...], 1: [(x, y, w, h), ...], ...}
# Keys are frame indices, values are lists of bounding boxes
```

The `min_confidence` parameter filters out low-quality detections
(DNN method only). The `"haar"` method is fast but less accurate;
`"dnn"` is more robust for varied lighting and angles.

## Face tracking

`FaceTracker` extends detection with temporal tracking — it follows
detected faces across frames and assigns consistent IDs using
centroid tracking:

```python
from pymotion import FaceTracker

tracker = FaceTracker(
    clip=my_clip,
    max_distance=100.0,  # Max pixel distance to match faces across frames
)
tracks = tracker.track()
# Returns: {face_id: {frame: (cx, cy), ...}, ...}
# Each face_id is a consistent identifier across frames
```

The `max_distance` parameter controls how far a face can move between
frames and still be considered the same identity.

## Automatic face blur

`FaceBlur` combines detection and blurring in one step — it detects
all faces and applies a Gaussian blur:

```python
from pymotion import FaceBlur

blur = FaceBlur(
    clip=my_clip,
    strength=5,    # Blur kernel size multiplier (1–10)
    method="haar",  # "haar" or "dnn"
)
blur_regions = blur.get_blur_regions()
# Returns: {frame: [(x, y, w, h), ...], ...}
```

The `strength` parameter is a kernel size multiplier (1–10). Higher
values produce stronger anonymization. The `method` parameter
controls the underlying face detection algorithm.

This is useful for privacy compliance — automatically blur all faces
in user-generated content or surveillance footage before publication.
