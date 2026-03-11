# Captions & Subtitles

PyMotion provides a complete subtitle pipeline: import from SRT/VTT/ASS,
render as overlay clips, auto-generate from audio with Whisper, and
export back to SRT or VTT.

## Importing subtitles

Load subtitles from any supported format with auto-detection:

```python
from pymotion import import_subtitles

segments = import_subtitles("captions.srt")
# Returns a list of CaptionSegment objects
for seg in segments:
    print(f"{seg.start_sec:.2f}s - {seg.end_sec:.2f}s: {seg.text}")
```

Or use format-specific parsers directly:

```python
from pymotion import parse_srt, parse_vtt, parse_ass

srt_segments = parse_srt("captions.srt")
vtt_segments = parse_vtt("captions.vtt")
ass_segments = parse_ass("captions.ass")
```

## Rendering subtitles

`SubtitleClip` renders imported segments as an overlay clip:

```python
from pymotion import SubtitleClip, Composition, Track

subs = SubtitleClip(
    file_path="captions.srt",
    style="netflix",
    font_size=42.0,
)
subs.set_duration(300)

comp = Composition(1920, 1080, fps=30, duration=300)
track = Track(name="subtitles")
track.add(subs)
comp.add_track(track)
```

Query which text is active at a given frame:

```python
text = subs.get_text_at_frame(90, fps=30)  # text at frame 90
```

## Auto-captioning with Whisper

`AutoCaptions` generates word-level subtitles from audio using OpenAI
Whisper (requires the `whisper` package):

```python
from pymotion import AutoCaptions

captions = AutoCaptions(
    audio_path="narration.wav",
    model="base",
    style="youtube",
)
segments = captions.generate()
```

The `model` parameter accepts any Whisper model size: `"tiny"`,
`"base"`, `"small"`, `"medium"`, `"large"`.

## Caption styles

Four built-in styles are available via `get_caption_style()`:

```python
from pymotion import get_caption_style

style = get_caption_style("karaoke")
```

| Style | Description |
|-------|-------------|
| `"netflix"` | White text, dark semi-transparent background, bottom-center |
| `"youtube"` | Yellow text, no background, bottom-center |
| `"tiktok"` | Bold white text, center screen, large font |
| `"karaoke"` | Highlights the current word in a contrasting color |

## Exporting subtitles

Export caption segments back to SRT or VTT format:

```python
from pymotion import export_subtitles

export_subtitles(segments, "output.srt", fmt="srt")
export_subtitles(segments, "output.vtt", fmt="vtt")
```

## Word-level timestamps

`WordTimestamp` provides per-word timing from Whisper output, enabling
karaoke-style highlighting:

```python
from pymotion import CaptionSegment, WordTimestamp

segment = CaptionSegment(
    text="Hello world",
    start_sec=1.0,
    end_sec=3.0,
    words=[
        WordTimestamp(word="Hello", start_sec=1.0, end_sec=1.8),
        WordTimestamp(word="world", start_sec=1.9, end_sec=3.0),
    ],
)
```
