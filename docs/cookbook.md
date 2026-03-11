# PyMotion Cookbook

Copy-paste-ready recipes for common video generation tasks.
Every recipe is a complete, runnable script with all imports included.

---

## Editing and Timing

### Split a clip at a frame and keep the second half

```python
from pymotion import ColorClip, Composition

clip = ColorClip("#3498db").set_duration(120)
first, second = clip.split(60)

comp = Composition(1920, 1080, 30, 60)
comp.add(second)
comp.render("second_half.mp4")
```

### Speed-ramp a clip (slow-mo then fast)

```python
from pymotion import ColorClip, Composition

clip = ColorClip("#e74c3c").set_duration(120)
ramped = clip.speed_ramp([(0, 0.5), (60, 0.5), (61, 3.0), (120, 3.0)])

comp = Composition(1920, 1080, 30, ramped.duration)
comp.add(ramped)
comp.render("speed_ramp.mp4")
```

### Concatenate clips with a cross-dissolve transition

```python
from pymotion import ColorClip, Composition, concatenate
from pymotion import CrossDissolve

a = ColorClip("#2ecc71").set_duration(60)
b = ColorClip("#9b59b6").set_duration(60)
c = ColorClip("#e67e22").set_duration(60)

joined = concatenate([a, b, c], transition=CrossDissolve(), transition_duration=15)

comp = Composition(1920, 1080, 30, joined.duration)
comp.add(joined)
comp.render("dissolve.mp4")
```

### Freeze a frame mid-clip

```python
from pymotion import ColorClip, Composition

clip = ColorClip("#1abc9c").set_duration(90)
frozen = clip.freeze_frame(frame=30, duration=45)

comp = Composition(1920, 1080, 30, frozen.duration)
comp.add(frozen)
comp.render("freeze.mp4")
```

### Reverse a clip and loop it three times

```python
from pymotion import ColorClip, Composition

clip = ColorClip("#f39c12").set_duration(30)
reversed_clip = clip.reverse()
looped = reversed_clip.repeat(3)

comp = Composition(1920, 1080, 30, looped.duration)
comp.add(looped)
comp.render("reversed_looped.mp4")
```

---

## Text and Titles

### Styled text with stroke and drop shadow

```python
from pymotion import Composition, TextClip, Shadow

title = TextClip(
    "Hello, PyMotion!",
    font="Arial",
    size=72.0,
    color="#FFFFFF",
    stroke_color="#000000",
    stroke_width=3.0,
    shadow=Shadow(offset_x=4.0, offset_y=4.0, blur=5.0),
)
title.set_duration(90).set_position(200, 400)

comp = Composition(1920, 1080, 30, 90)
comp.add(title)
comp.render("styled_text.mp4")
```

### Typewriter text animation

```python
from pymotion import Composition
from pymotion import Typewriter, Color, Vec2

tw = Typewriter(
    text="Loading systems...",
    font_size=48.0,
    color=Color(0.0, 1.0, 0.0, 1.0),
    chars_per_frame=0.5,
    cursor=True,
    position=Vec2(100.0, 500.0),
)
tw.set_duration(120)

comp = Composition(1920, 1080, 30, 120)
comp.add(tw)
comp.render("typewriter.mp4")
```

### Animated counter (count up to 1000)

```python
from pymotion import Composition
from pymotion import CountUp, Color, Vec2

counter = CountUp(
    start_value=0.0,
    end_value=1000.0,
    font_size=64.0,
    color=Color(1.0, 1.0, 1.0, 1.0),
    prefix="$",
    suffix="",
    decimals=0,
    position=Vec2(800.0, 500.0),
    step_frames=3,
)
counter.set_duration(90)

comp = Composition(1920, 1080, 30, 90)
comp.add(counter)
comp.render("counter.mp4")
```

### Word-by-word reveal

```python
from pymotion import Composition
from pymotion import WordByWord, Color, Vec2

reveal = WordByWord(
    text="This is revealed one word at a time",
    font_size=42.0,
    color=Color(1.0, 1.0, 1.0, 1.0),
    frames_per_word=15,
    position=Vec2(100.0, 500.0),
)
reveal.set_duration(150)

comp = Composition(1920, 1080, 30, 150, background="#1a1a2e")
comp.add(reveal)
comp.render("word_by_word.mp4")
```

---

## Compositing and Masking

### Chroma-key a green screen clip

```python
from pymotion import ColorClip, Composition, Track
from pymotion import ChromaKey

foreground = ColorClip("#00FF00").set_duration(90)
foreground.add_effect(ChromaKey(color="#00FF00", tolerance=0.4, spill_suppression=0.6))

background = ColorClip("#2c3e50").set_duration(90)

comp = Composition(1920, 1080, 30, 90)
comp.add(background)
comp.add(foreground)
comp.render("chroma_key.mp4")
```

### Bezier mask to reveal part of a clip

```python
from pymotion import ColorClip, Composition
from pymotion import BezierMask, BezierPoint, Vec2

clip = ColorClip("#e74c3c").set_duration(90)

mask = BezierMask(
    points=[
        BezierPoint(vertex=Vec2(400.0, 200.0)),
        BezierPoint(vertex=Vec2(1500.0, 200.0)),
        BezierPoint(vertex=Vec2(1500.0, 800.0)),
        BezierPoint(vertex=Vec2(400.0, 800.0)),
    ],
    feather=20.0,
    opacity=1.0,
)
clip.add_mask(mask)

bg = ColorClip("#2c3e50").set_duration(90)

comp = Composition(1920, 1080, 30, 90)
comp.add(bg)
comp.add(clip)
comp.render("bezier_mask.mp4")
```

### Track matte using a shape as the mask source

```python
from pymotion import ColorClip, Composition, ShapeClip
from pymotion import TrackMatte

matte_source = ShapeClip.circle(cx=960, cy=540, r=300, fill="#FFFFFF")
matte_source.set_duration(90)

content = ColorClip("#e74c3c").set_duration(90)
content.add_mask(TrackMatte(source=matte_source, mode="luma"))

bg = ColorClip("#1a1a2e").set_duration(90)

comp = Composition(1920, 1080, 30, 90)
comp.add(bg)
comp.add(content)
comp.render("track_matte.mp4")
```

### Adjustment layer with brightness and contrast

```python
from pymotion import AdjustmentLayer, ColorClip, Composition
from pymotion import Brightness, Contrast

bg = ColorClip("#3498db").set_duration(90)

adj = AdjustmentLayer(effects=[Brightness(value=1.3), Contrast(value=1.5)])
adj.set_duration(90)

comp = Composition(1920, 1080, 30, 90)
comp.add(bg)
comp.add(adj)
comp.render("adjustment_layer.mp4")
```

### Wiggle expression for handheld camera shake

```python
from pymotion import ColorClip, Composition, TextClip
from pymotion import wiggle

title = TextClip("BREAKING NEWS", font="Arial", size=64.0, color="#FF0000")
title.set_duration(90).set_position(500, 450)
title.set_expression("position.x", wiggle(3.0, 8.0, seed=1))
title.set_expression("position.y", wiggle(3.0, 5.0, seed=2))

comp = Composition(1920, 1080, 30, 90)
comp.add(title)
comp.render("wiggle.mp4")
```

---

## Layout

### Picture-in-picture overlay

```python
from pymotion import ColorClip, Composition
from pymotion import pip

main = ColorClip("#2c3e50").set_duration(90)
overlay = ColorClip("#e74c3c").set_duration(90)

comp = pip(main, overlay, position="bottom-right", size=(480, 270))
comp.render("pip.mp4")
```

### 2x2 grid of clips

```python
from pymotion import ColorClip
from pymotion import grid

clips = [
    ColorClip("#e74c3c").set_duration(60),
    ColorClip("#3498db").set_duration(60),
    ColorClip("#2ecc71").set_duration(60),
    ColorClip("#f39c12").set_duration(60),
]

comp = grid(clips, rows=2, cols=2, gap=10, background="#1a1a2e")
comp.render("grid_2x2.mp4")
```

### Parent-child grouping with a NullObject

```python
from pymotion import ColorClip, Composition, NullObject, ShapeClip

anchor = NullObject()
anchor.set_position(960, 540).set_duration(90)

dot1 = ShapeClip.circle(cx=0, cy=0, r=30, fill="#e74c3c")
dot1.set_duration(90)
dot1.parent = anchor

dot2 = ShapeClip.circle(cx=100, cy=0, r=30, fill="#3498db")
dot2.set_duration(90)
dot2.parent = anchor

comp = Composition(1920, 1080, 30, 90, background="#1a1a2e")
comp.add(anchor, dot1, dot2)
comp.render("null_group.mp4")
```

### Nested compositions (pre-comp)

```python
from pymotion import ColorClip, Composition, ShapeClip

inner = Composition(960, 540, 30, 60, background="#2c3e50")
inner.add(ShapeClip.circle(cx=480, cy=270, r=100, fill="#e74c3c").set_duration(60))

outer = Composition(1920, 1080, 30, 60, background="#1a1a2e")
nested_clip = inner.to_clip()
nested_clip.set_position(480, 270)
outer.add(nested_clip)
outer.render("nested_comp.mp4")
```

---

## Audio

### Mix two audio tracks with volume and pan

```python
from pymotion import AudioClip, AudioClipData, AudioMixer

music = AudioClip("music.wav", volume=0.6, pan=-0.3)
sfx = AudioClip("sfx.wav", volume=1.0, pan=0.5)

mixer = AudioMixer(sample_rate=48000, bit_depth=24, channels=2)
mixer.add(AudioClipData(samples=music.get_samples(), start_sample=0), track="music")
mixer.add(AudioClipData(samples=sfx.get_samples(), start_sample=48000), track="sfx")
mixer.set_volume("music", 0.6)
mixer.set_pan("sfx", 0.5)

result = mixer.render()
```

### Sidechain compress music under dialogue

```python
from pymotion import AudioClip, AudioClipData, AudioMixer

dialogue = AudioClip("dialogue.wav", volume=1.0)
music = AudioClip("music.wav", volume=0.8)

mixer = AudioMixer(sample_rate=48000, bit_depth=24, channels=2)
mixer.add(AudioClipData(samples=dialogue.get_samples(), start_sample=0), track="dialogue")
mixer.add(AudioClipData(samples=music.get_samples(), start_sample=0), track="music")
mixer.sidechain("dialogue", "music", threshold_db=-20.0, ratio=4.0, attack_ms=10.0, release_ms=100.0)

result = mixer.render()
```

### Normalize a mix to streaming loudness (-14 LUFS)

```python
from pymotion import AudioClip, AudioClipData, AudioMixer

voice = AudioClip("voice.wav", volume=1.0)

mixer = AudioMixer(sample_rate=48000, bit_depth=24, channels=2)
mixer.add(AudioClipData(samples=voice.get_samples(), start_sample=0), track="voice")
mixer.normalize(target_lufs=-14.0)

result = mixer.render()
```

### Audio with fade in and fade out

```python
from pymotion import AudioClip

clip = AudioClip("narration.wav", volume=1.0)
clip.fade_in(0.5).fade_out(1.0).trim(2.0, 10.0)

samples = clip.get_samples()
print(f"Decoded {samples.shape[0]} stereo samples")
```

---

## Captions and Voiceover

### Import SRT subtitles and render a caption overlay

```python
from pymotion import import_subtitles, render_caption_frame

segments = import_subtitles("subtitles.srt")
frame = render_caption_frame(segments, time_sec=3.5, width=1920, height=1080, style="netflix")
print(f"Caption overlay shape: {frame.shape}")
```

### Export caption segments to VTT format

```python
from pymotion import CaptionSegment, export_subtitles

segments = [
    CaptionSegment(text="Welcome to the show.", start_sec=0.0, end_sec=2.5),
    CaptionSegment(text="Let us get started.", start_sec=3.0, end_sec=5.0),
    CaptionSegment(text="Here is the first topic.", start_sec=5.5, end_sec=8.0),
]

export_subtitles(segments, "captions.vtt", fmt="vtt")
```

### Generate TTS audio from text

```python
from pymotion import TTSClip

tts = TTSClip(text="Welcome to PyMotion.", voice="default", engine="system", speed=1.0)
samples = tts.generate()
print(f"Generated {samples.shape[0]} samples at {tts.sample_rate} Hz")
```

### SubtitleClip for frame-accurate caption lookup

```python
from pymotion import SubtitleClip

subs = SubtitleClip(srt_path="subtitles.srt", style="youtube", fps=30)
for frame in range(0, 150):
    text = subs.get_text_at_frame(frame)
    if text:
        print(f"Frame {frame}: {text}")
```

---

## Batch and Templates

### Define and render a reusable template

```python
from pymotion import Composition, TextClip
from pymotion import Template

class BannerTemplate(Template):
    headline: str
    bg_color: str = "#2c3e50"

    def build(self) -> Composition:
        comp = Composition(1920, 1080, 30, 90, background=self.bg_color)
        title = TextClip(self.headline, font="Arial", size=64.0, color="#FFFFFF")
        title.set_duration(90).set_position(200, 480)
        comp.add(title)
        return comp

banner = BannerTemplate(headline="Summer Sale")
banner.render("banner.mp4")
```

### Batch-render templates from a data list

```python
from pymotion import Composition, TextClip
from pymotion import Template

class SlideTemplate(Template):
    title: str
    subtitle: str
    color: str = "#1a1a2e"

    def build(self) -> Composition:
        comp = Composition(1920, 1080, 30, 60, background=self.color)
        t = TextClip(self.title, font="Arial", size=56.0, color="#FFFFFF")
        t.set_duration(60).set_position(200, 400)
        s = TextClip(self.subtitle, font="Arial", size=32.0, color="#CCCCCC")
        s.set_duration(60).set_position(200, 500)
        comp.add(t, s)
        return comp

slides = [
    {"title": "Intro", "subtitle": "Welcome"},
    {"title": "Chapter 1", "subtitle": "Getting Started"},
    {"title": "Chapter 2", "subtitle": "Advanced Topics"},
]

for i, data in enumerate(slides):
    SlideTemplate(**data).render(f"slide_{i:02d}.mp4")
```

### Export a composition to EDL for NLE round-trip

```python
from pymotion import Composition, ColorClip

comp = Composition(1920, 1080, 30, 120)
comp.add(ColorClip("#FF0000").set_duration(60))
comp.add(ColorClip("#0000FF").set_duration(60).at(60))
comp.export_edl("project.edl")
```

---

## 3D and Particles

### Render a 3D scene with a point light

```python
from pymotion import Composition, Scene3D
from pymotion import Camera, PBRMaterial, PointLight, Color, Vec3

scene = Scene3D(width=1920, height=1080)
scene.camera = Camera(position=Vec3(0.0, 2.0, 5.0), target=Vec3(0.0, 0.0, 0.0), fov=60.0)
scene.add_light(PointLight(position=Vec3(3.0, 4.0, 3.0), color=Color(1.0, 1.0, 1.0), intensity=2.0))

clip = scene.to_clip(duration=90)

comp = Composition(1920, 1080, 30, 90)
comp.add(clip)
comp.export_frame(0, "scene3d_frame.png")
```

### Confetti particle effect

```python
from pymotion import Composition
from pymotion import confetti

ps = confetti(width=1920, height=1080)
clip = ps.to_clip(duration=120)

comp = Composition(1920, 1080, 30, 120, background="#1a1a2e")
comp.add(clip)
comp.render("confetti.mp4")
```

### Fire particles with a dark background

```python
from pymotion import Composition
from pymotion import fire

ps = fire(width=1920, height=1080)
clip = ps.to_clip(duration=150)

comp = Composition(1920, 1080, 30, 150, background="#0a0a0a")
comp.add(clip)
comp.render("fire.mp4")
```

### Custom particle emitter

```python
from pymotion import Composition
from pymotion import Emitter, ParticleSystem, Color, Vec2

ps = ParticleSystem(1920, 1080)
ps.add_emitter(Emitter(
    position=Vec2(960.0, 800.0),
    rate=25.0,
    lifetime=(30.0, 60.0),
    speed=(2.0, 6.0),
    angle=(250.0, 290.0),
    size=(3.0, 8.0),
    color_over_life=[Color(1.0, 0.8, 0.0), Color(1.0, 0.0, 0.0)],
    opacity_over_life=[1.0, 0.0],
    gravity=Vec2(0.0, -0.1),
))
clip = ps.to_clip(duration=120)

comp = Composition(1920, 1080, 30, 120, background="#000000")
comp.add(clip)
comp.render("custom_particles.mp4")
```

---

## Profiling and Debugging

### Benchmark render throughput

```python
from pymotion import ColorClip, Composition
from pymotion import benchmark

comp = Composition(1920, 1080, 30, 120)
comp.add(ColorClip("#3498db").set_duration(120))

result = benchmark(comp, n_frames=60)
print(f"Rendered {result.total_frames} frames in {result.total_ms:.0f} ms")
print(f"Average: {result.avg_frame_ms:.1f} ms/frame ({result.fps_achieved:.1f} fps)")
```

### Profile per-clip render times

```python
from pymotion import ColorClip, Composition, ShapeClip
from pymotion import GaussianBlur, profile_composition

comp = Composition(1920, 1080, 30, 30)
comp.add(ColorClip("#2c3e50").set_duration(30))
blurred = ShapeClip.circle(cx=960, cy=540, r=200, fill="#e74c3c")
blurred.set_duration(30).add_effect(GaussianBlur(radius=10.0))
comp.add(blurred)

profile = profile_composition(comp, start=0, end=10, detailed=True)
for fp in profile.frame_profiles:
    for ct in fp.clip_timings:
        print(f"  Frame {fp.frame}: {ct.clip_type} took {ct.render_ms:.2f} ms")
```

### Detect performance bottlenecks

```python
from pymotion import ColorClip, Composition, ShapeClip
from pymotion import Bloom, detect_bottlenecks

comp = Composition(1920, 1080, 30, 60)
comp.add(ColorClip("#1a1a2e").set_duration(60))
heavy = ShapeClip.rect(x=100, y=100, w=800, h=600, fill="#FF0000")
heavy.set_duration(60).add_effect(Bloom(radius=15.0, strength=0.8, threshold=100.0))
comp.add(heavy)

bottlenecks = detect_bottlenecks(comp, n_frames=20, top_n=3)
for bn in bottlenecks:
    print(f"[{bn.category}] {bn.description} -- {bn.time_ms:.1f} ms ({bn.percentage:.1f}%)")
```

### Compare two frames pixel-by-pixel

```python
import numpy as np
from pymotion import frame_diff

a = np.zeros((1080, 1920, 4), dtype=np.uint8)
a[:, :, :3] = 128
a[:, :, 3] = 255

b = a.copy()
b[200:400, 300:600, 2] = 255  # paint a red rectangle

diff = frame_diff(a, b)
print(f"PSNR: {diff.psnr} dB")
print(f"Changed pixels: {diff.changed_pixels} / {diff.total_pixels}")
print(f"Identical: {diff.identical}")
```

### Measure memory usage during rendering

```python
from pymotion import ColorClip, Composition
from pymotion import memory_report

comp = Composition(1920, 1080, 30, 30)
comp.add(ColorClip("#3498db").set_duration(30))

report = memory_report(comp, n_frames=10)
print(f"Peak RAM: {report.peak_ram_mb:.1f} MB")
for stage, bytes_used in report.per_stage.items():
    print(f"  {stage}: {bytes_used / 1024 / 1024:.1f} MB")
```
