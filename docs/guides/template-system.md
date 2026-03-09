# Template System

PyMotion's `Template` class lets you define reusable, parameterized video
generators. Declare typed fields, implement `build()`, and render hundreds
of variations from data files or APIs.

## Defining a template

Subclass `Template` and declare parameters as class-level type annotations.
Implement the abstract `build()` method to return a `Composition`:

```python
from pymotion import Template, Composition, ColorClip, TextClip

class SalesBanner(Template):
    headline: str
    discount: int
    bg_color: str = "#1a1a2e"
    duration_frames: int = 90

    def build(self) -> Composition:
        comp = Composition(1920, 1080, fps=30, duration=self.duration_frames)

        bg = ColorClip(self.bg_color)
        bg.set_duration(self.duration_frames)

        title = TextClip(self.headline, font_size=72, color="#ffffff")
        title.set_position(960, 400)
        title.set_duration(self.duration_frames)

        price = TextClip(f"{self.discount}% OFF", font_size=96, color="#00ff88")
        price.set_position(960, 600)
        price.set_duration(self.duration_frames)

        comp.add(bg, title, price)
        return comp
```

## Instantiating and rendering

Pass field values as keyword arguments. Use `render()` as a shortcut for
`build()` followed by `comp.render()`:

```python
banner = SalesBanner(headline="Summer Sale", discount=30)

# Option 1: build then render manually
comp = banner.build()
comp.render("summer_sale.mp4")

# Option 2: render directly
banner.render("summer_sale.mp4")

# With a custom export preset
banner.render("summer_sale.webm", preset="vp9_1080p")
```

## Field validation

Fields are validated against their type annotations at instantiation time.
Invalid values raise `TemplateValidationError`:

```python
from pymotion import TemplateValidationError

try:
    banner = SalesBanner(headline=123, discount=30)
except TemplateValidationError as e:
    print(f"Field '{e.field}': {e}")
    # Field 'headline': expected str, got int
```

### Supported field types

| Type | Validation |
|------|------------|
| `str` | Must be a string. |
| `int` | Must be an integer. |
| `float` | Must be int or float (coerced to float). |
| `bool` | Must be a boolean. |
| `Path` | Must be str or Path; file must exist; security-validated. |
| `Color` | Parsed via `Color.parse()` (hex, CSS names, tuples). |

### Path fields

Path fields are automatically checked for existence and validated against
path traversal attacks:

```python
from pathlib import Path
from pymotion import Template, Composition

class ImageTemplate(Template):
    background: Path
    title: str

    def build(self) -> Composition:
        # self.background is a resolved, validated Path
        ...
```

## Default values

Fields with class-level defaults are optional at instantiation:

```python
class Notification(Template):
    message: str                       # required
    bg_color: str = "#0f0f23"          # optional
    duration_frames: int = 120         # optional

    def build(self) -> Composition:
        comp = Composition(1920, 1080, fps=30, duration=self.duration_frames)
        bg = ColorClip(self.bg_color)
        bg.set_duration(self.duration_frames)
        text = TextClip(self.message, font_size=48, color="#ffffff")
        text.set_position(960, 540)
        text.set_duration(self.duration_frames)
        comp.add(bg, text)
        return comp

# Only message is required
notif = Notification(message="Build succeeded!")
```

## Batch rendering

Loop over data to generate many videos at once:

```python
import csv

class ProductVideo(Template):
    product_name: str
    price: float
    tagline: str = "Order now!"

    def build(self) -> Composition:
        comp = Composition(1920, 1080, fps=30, duration=90)
        bg = ColorClip("#0f0f23")
        bg.set_duration(90)
        name = TextClip(self.product_name, font_size=64, color="#ffffff")
        name.set_position(960, 400)
        name.set_duration(90)
        label = TextClip(f"${self.price:.2f}", font_size=48, color="#00ff88")
        label.set_position(960, 550)
        label.set_duration(90)
        comp.add(bg, name, label)
        return comp

with open("products.csv") as f:
    for row in csv.DictReader(f):
        video = ProductVideo(
            product_name=row["name"],
            price=float(row["price"]),
        )
        video.render(f"output/{row['name']}.mp4")
```

## Multi-format export

Render the same template to several output formats:

```python
template = SalesBanner(headline="Flash Deal", discount=50)

for preset, ext in [("h264_1080p", ".mp4"), ("vp9_1080p", ".webm"), ("gif_480p", ".gif")]:
    template.render(f"output/deal{ext}", preset=preset)
```

## Tips

- Keep templates focused -- one template per video format.
- Use typed fields so validation catches data errors before rendering starts.
- Set sensible defaults to make templates usable with minimal configuration.
- Test with `build()` first to inspect the composition, then use
  `export_frame()` to preview a single frame before committing to a full
  batch render.
- Catch `TemplateValidationError` in batch loops to skip bad rows without
  crashing the entire run.
