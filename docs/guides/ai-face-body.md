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
    confidence=0.7,  # Minimum detection confidence (0.0–1.0)
)
faces = detector.detect()
# Returns: {0: [(x, y, w, h), ...], 1: [(x, y, w, h), ...], ...}
# Keys are frame indices, values are lists of bounding boxes
```

The `confidence` parameter filters out low-quality detections. Higher
values reduce false positives but may miss partially occluded faces.

## Face tracking

`FaceTracker` extends detection with temporal tracking — it follows
detected faces across frames and assigns consistent IDs:

```python
from pymotion import FaceTracker

tracker = FaceTracker(
    clip=my_clip,
    confidence=0.7,
)
tracks = tracker.track()
# Returns: {face_id: [(frame, x, y, w, h), ...], ...}
# Each face_id is a consistent identifier across frames
```

Tracking data is compatible with `MotionTracker` output, so it can
be used with `follow_tracker()` to bind clip positions to faces.

## Automatic face blur

`FaceBlur` combines detection and blurring in one step — it detects
all faces and applies a Gaussian blur:

```python
from pymotion import FaceBlur

blur = FaceBlur(
    clip=my_clip,
    strength=20.0,  # Blur kernel size
    confidence=0.7,
)
result_frame = blur.apply_frame(frame, frame_index=0)
# Returns the frame with all detected faces blurred
```

The `strength` parameter controls blur intensity. Higher values
produce stronger anonymization. Face regions are expanded slightly
(padding) to ensure complete coverage.

This is useful for privacy compliance — automatically blur all faces
in user-generated content or surveillance footage before publication.
