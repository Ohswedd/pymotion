# Motion Graphics Components

PyMotion ships with reusable, animated overlay clips for common video
production elements: lower thirds, logo reveals, CTAs, social handles,
countdowns, and more.

## Lower third

`LowerThird` displays a name and title with 8 design styles and
slide-in/out animation.

```python
from pymotion import LowerThird, Composition, Track

comp = Composition(1920, 1080, fps=30, duration=120)

lt = LowerThird(
    name="Jane Smith",
    title="Lead Engineer",
    style="modern",      # 8 styles available
    animate_in=15,
    animate_out=15,
)
lt.set_duration(120)

track = Track(name="lower_third")
track.add(lt)
comp.add_track(track)
```

Available styles: `"modern"`, `"clean"`, `"bold"`, `"minimal"`,
`"news"`, `"gradient_bar"`, `"corporate"`, `"neon"`.

## Logo reveal

`LogoReveal` animates a logo area with 6 reveal styles.

```python
from pymotion import LogoReveal
from pymotion.utils.color import Color

logo = LogoReveal(
    style="shatter",       # fade, slice, grow, glitch, draw, shatter
    reveal_duration=30,
    logo_color=Color.parse("#D4AF37"),
    logo_size=(300.0, 150.0),
)
logo.set_duration(90)
```

## Call to action

`CallToAction` renders a button-style CTA with a pop-in animation.

```python
from pymotion import CallToAction

cta = CallToAction(
    text="Subscribe Now!",
    sub_text="Join 100K+ creators",
    style="subscribe",   # subscribe, buy, visit, default
    animate_in=15,
)
cta.set_duration(90)
```

## Social handle

`SocialHandle` renders a platform-styled handle overlay with the
platform's brand color.

```python
from pymotion import SocialHandle

handle = SocialHandle(
    platform="youtube",   # youtube, instagram, tiktok, x, linkedin
    handle="@pymotion",
    animate_in=15,
)
handle.set_duration(90)
```

## Countdown

`Countdown` displays an animated countdown timer. Use `"numbers"` for
a simple digit display or `"clock"` for `M:SS` format.

```python
from pymotion import Countdown

timer = Countdown(
    from_n=10,
    count_duration=300,   # 10 seconds at 30fps
    style="numbers",      # "numbers" or "clock"
    size=120.0,
)
timer.set_duration(300)
```

## Quote card

`QuoteCard` renders a styled quote with word wrapping and fade-in
animation. Four visual styles are available.

```python
from pymotion import QuoteCard

quote = QuoteCard(
    text="The only way to do great work is to love what you do.",
    attribution="— Steve Jobs",
    style="elegant",      # elegant, light, minimal, default
    animate_in=20,
)
quote.set_duration(120)
```

## Divider

`Divider` draws an animated line between video sections.

```python
from pymotion import Divider

div = Divider(
    style="wave",          # line, dashed, dots, gradient, wave
    direction="horizontal",
    div_duration=20,
)
div.set_duration(60)
```

## Transition title

`TransitionTitle` renders a full-screen title card with enter/exit
animation.

```python
from pymotion import TransitionTitle

title = TransitionTitle(
    text="Chapter 2: The Journey",
    style="slide_up",     # fade, slide_up, zoom, split, default
    animate_in=15,
    animate_out=15,
    font_size=56.0,
)
title.set_duration(90)
```

## Watermark

`Watermark` renders persistent branded text at a named position.

```python
from pymotion import Watermark

wm = Watermark(
    image_or_text="© PyMotion 2026",
    position="bottom-right",   # top-left, top-right, bottom-left, bottom-right, center
    watermark_opacity=0.3,
    font_size=16.0,
)
wm.set_duration(300)
```

---

## Device mockups

Wrap content clips inside device frames for app demos and screen
recordings.

### Browser mockup

```python
from pymotion import BrowserMockup, ColorClip

content = ColorClip(color="#2563EB").set_duration(90)
browser = BrowserMockup(
    content_clip=content,
    mockup_theme="dark",       # "light" or "dark"
    url_text="https://pymotion.dev",
    animate_in_frames=15,
)
browser.set_duration(90)
```

### Phone mockup

```python
from pymotion import PhoneMockup, ColorClip

content = ColorClip(color="#10B981").set_duration(90)
phone = PhoneMockup(
    content_clip=content,
    model="dynamic_island",    # "flat", "notch", "dynamic_island"
    animate_in_frames=15,
)
phone.set_duration(90)
```

### Desktop mockup

```python
from pymotion import DesktopMockup, ColorClip

content = ColorClip(color="#6366F1").set_duration(90)
desktop = DesktopMockup(
    content_clip=content,
    os_theme="macos",          # "macos", "windows", "minimal"
    window_title="My Application",
    animate_in_frames=15,
)
desktop.set_duration(90)
```

All mockups support `animate_in_frames` and `animate_out_frames` for
smooth entrance and exit animations, plus standard Clip transform
properties (position, scale, rotation, opacity).
