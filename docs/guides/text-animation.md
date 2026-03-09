# Text Animation

PyMotion ships with animated text presets that reveal, scramble, or count
text over time. Each preset is a `Clip` subclass you can add directly to a
composition -- no manual keyframing required.

## Available presets

| Preset | Effect |
|--------|--------|
| `Typewriter` | Characters appear one by one with an optional blinking cursor. |
| `WordByWord` | Words fade in sequentially. |
| `LetterByLetter` | Letters appear at a fixed interval. |
| `KineticText` | Words slide in from the side with eased motion. |
| `Scramble` | Characters cycle through random glyphs before settling. |
| `GlitchText` | Randomized character replacement with chromatic offset. |
| `SplitReveal` | Text splits into top/bottom halves that slide together. |
| `CountUp` | Animates a number from a start value to an end value. |
| `CountDown` | Animates a number from a start value down to an end value. |

## Typewriter

```python
from pymotion import Composition, ColorClip, Typewriter, Color, Vec2

comp = Composition(1920, 1080, fps=30, duration=120)

bg = ColorClip("#0f0f23")
bg.set_duration(120)

tw = Typewriter(
    text="Hello, PyMotion!",
    font_size=48.0,
    color=Color.parse("#00ff88"),
    chars_per_frame=0.5,
    cursor=True,
    position=Vec2(200.0, 500.0),
)
tw.set_duration(120)

comp.add(bg, tw)
comp.render("typewriter.mp4")
```

The `chars_per_frame` parameter controls typing speed. A value of `0.5`
means one new character every two frames.

## WordByWord

```python
from pymotion import WordByWord, Color, Vec2

wbw = WordByWord(
    text="This sentence appears one word at a time",
    font_size=36.0,
    color=Color.parse("#ffffff"),
    frames_per_word=10,
    position=Vec2(100.0, 400.0),
)
wbw.set_duration(150)
```

## KineticText

Words slide in from the right with a cubic ease-out curve:

```python
from pymotion import KineticText, Color, Vec2

kinetic = KineticText(
    text="Motion is everything",
    font_size=42.0,
    color=Color.parse("#e94560"),
    frames_per_word=15,
    position=Vec2(100.0, 500.0),
)
kinetic.set_duration(120)
```

## Scramble

Characters cycle through random glyphs before settling into the final text:

```python
from pymotion import Scramble, Color, Vec2

scramble = Scramble(
    text="DECRYPTED",
    font_size=56.0,
    color=Color.parse("#00ff00"),
    scramble_frames=5,
    position=Vec2(300.0, 500.0),
    seed=42,
)
scramble.set_duration(90)
```

## CountUp and CountDown

Animate numeric values with optional prefix, suffix, and decimal places:

```python
from pymotion import CountUp, CountDown, Color, Vec2

# Count from 0 to 1000
counter = CountUp(
    start_value=0.0,
    end_value=1000.0,
    font_size=64.0,
    color=Color.parse("#ffffff"),
    prefix="$",
    suffix="",
    decimals=0,
    position=Vec2(800.0, 500.0),
)
counter.set_duration(90)

# Count from 10 down to 0
countdown = CountDown(
    start_value=10.0,
    end_value=0.0,
    font_size=72.0,
    color=Color.parse("#ff4444"),
    position=Vec2(900.0, 500.0),
)
countdown.set_duration(300)
```

## Tips

- All animated text presets are `Clip` subclasses. Add them to a composition
  with `comp.add()` like any other clip.
- Text input is automatically sanitized for security.
- Use `set_duration()` to control how long the animation plays. The preset
  paces its reveal based on the clip's total duration.
- The `seed` parameter on `Scramble` and `GlitchText` makes the animation
  deterministic and reproducible across renders.
