# Batch Generation

PyMotion's template system lets you define reusable, parameterized video
generators. Subclass `Template`, declare typed fields, implement `build()`,
and render hundreds of variations from data.

## The Template class

`Template` is an abstract base class. Subclasses declare parameters as
class-level type annotations with optional defaults. Fields are validated
automatically at instantiation.

```python
from pymotion import Template, Composition, ColorClip, TextClip

class GreetingCard(Template):
    recipient_name: str
    message: str
    bg_color: str = "#1a1a2e"
    duration_frames: int = 150

    def build(self) -> Composition:
        comp = Composition(1920, 1080, fps=30, duration=self.duration_frames)

        bg = ColorClip(self.bg_color)
        bg.set_duration(self.duration_frames)

        title = TextClip(f"Hello, {self.recipient_name}!", font_size=72, color="#e94560")
        title.set_position(960, 400)
        title.set_duration(self.duration_frames)

        body = TextClip(self.message, font_size=36, color="#ffffff")
        body.set_position(960, 600)
        body.set_duration(self.duration_frames)

        comp.add(bg, title, body)
        return comp
```

## Instantiating templates

Pass field values as keyword arguments:

```python
card = GreetingCard(
    recipient_name="Alice",
    message="Wishing you a wonderful day!",
)

# Build the composition
comp = card.build()

# Or render directly
card.render("alice_card.mp4")
```

The `render()` convenience method calls `build()` then `comp.render()` in
one step. You can pass a preset name and any additional render kwargs:

```python
card.render("alice_card.webm", preset="vp9_1080p")
```

## Field validation

Template fields are validated against their type annotations at
instantiation time:

```python
class ProductAd(Template):
    product_name: str
    price: float
    on_sale: bool = False

# These will raise TemplateValidationError:
# ProductAd(product_name=123, price=9.99)       # product_name must be str
# ProductAd(product_name="Widget", price="ten")  # price must be float
# ProductAd()                                     # product_name is required
```

### Supported field types

| Type | Validation |
|------|------------|
| `str` | Must be a string |
| `int` | Must be an integer |
| `float` | Must be int or float (coerced to float) |
| `bool` | Must be a boolean |
| `Path` | Must be str or Path; file must exist; path is security-validated |
| `Color` | Parsed via `Color.parse()` (accepts hex, CSS names, tuples) |

### Path validation

Path fields are automatically security-validated to prevent path traversal:

```python
from pathlib import Path

class ImageOverlay(Template):
    background_image: Path
    overlay_text: str

# The path must exist and pass security validation
template = ImageOverlay(
    background_image="assets/bg.png",
    overlay_text="Sale!",
)
```

## Default values

Fields with class-level defaults are optional:

```python
class Banner(Template):
    headline: str                      # required
    subtitle: str = "Learn more"       # optional, has default
    width: int = 1920                  # optional
    height: int = 1080                 # optional
    bg_color: str = "#000000"          # optional

    def build(self) -> Composition:
        comp = Composition(self.width, self.height, fps=30, duration=90)
        bg = ColorClip(self.bg_color)
        bg.set_duration(90)
        title = TextClip(self.headline, font_size=64, color="#ffffff")
        title.set_position(self.width // 2, self.height // 2 - 50)
        title.set_duration(90)
        sub = TextClip(self.subtitle, font_size=32, color="#aaaaaa")
        sub.set_position(self.width // 2, self.height // 2 + 50)
        sub.set_duration(90)
        comp.add(bg, title, sub)
        return comp

# Only headline is required
banner = Banner(headline="Big Sale Today")
```

## Batch rendering

Loop over data to generate many videos:

```python
import csv

class ProductVideo(Template):
    product_name: str
    price: float
    tagline: str = "Buy now!"

    def build(self) -> Composition:
        comp = Composition(1920, 1080, fps=30, duration=90)
        bg = ColorClip("#0f0f23")
        bg.set_duration(90)
        name = TextClip(self.product_name, font_size=64, color="#ffffff")
        name.set_position(960, 400)
        name.set_duration(90)
        price_label = TextClip(f"${self.price:.2f}", font_size=48, color="#00ff88")
        price_label.set_position(960, 550)
        price_label.set_duration(90)
        tag = TextClip(self.tagline, font_size=32, color="#aaaaaa")
        tag.set_position(960, 700)
        tag.set_duration(90)
        comp.add(bg, name, price_label, tag)
        return comp

# Render from CSV data
with open("products.csv") as f:
    reader = csv.DictReader(f)
    for row in reader:
        video = ProductVideo(
            product_name=row["name"],
            price=float(row["price"]),
            tagline=row.get("tagline", "Buy now!"),
        )
        video.render(f"output/{row['name']}.mp4")
```

## Using different presets per batch

```python
formats = [
    ("h264_1080p", ".mp4"),
    ("vp9_1080p", ".webm"),
    ("gif_480p", ".gif"),
]

template = Banner(headline="Multi-format Export")
for preset, ext in formats:
    template.render(f"output/banner{ext}", preset=preset)
```

## Error handling

Catch `TemplateValidationError` for field validation failures:

```python
from pymotion import Template, TemplateValidationError

class MyTemplate(Template):
    name: str
    count: int

    def build(self):
        ...

try:
    t = MyTemplate(name="test", count="not_a_number")
except TemplateValidationError as e:
    print(f"Validation failed for field '{e.field}': {e}")
```

## Template design tips

1. **Keep templates focused** -- one template per video format. Don't try to
   make a single template handle every variation.
2. **Use typed fields** -- the validation catches data errors before rendering
   starts, saving time on large batches.
3. **Set sensible defaults** -- make the template usable with minimal
   configuration.
4. **Test with `build()` first** -- call `build()` and inspect the composition
   before committing to a full render pass.
5. **Use `export_frame()` for previews** -- render a single frame to verify
   layout before batch-rendering all videos.
