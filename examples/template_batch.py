"""Template Batch -- batch video generation using the Template system.

Creates a ProductCard template that accepts product_name, price, and tagline
parameters, then generates 3 product card variations as separate MP4 files.
"""

from pathlib import Path

from pymotion import ColorClip, Composition, ShapeClip, Template, TextClip
from pymotion.clip.image import ImageClip

assets = Path(__file__).parent / "assets"
output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)


class ProductCard(Template):
    """Reusable product card video template."""

    product_name: str
    price: float
    tagline: str
    brand_color: str = "#FF6B6B"

    def build(self) -> Composition:
        """Build a 5-second product card composition."""
        comp = Composition(width=1080, height=1080, fps=30, duration=150)

        bg = ColorClip(color=self.brand_color)
        bg.set_duration(150)

        logo = ImageClip(source=assets / "logo.png")
        logo.set_duration(150).set_position(440, 80)

        name_text = TextClip(
            text=self.product_name,
            font="Arial",
            size=56.0,
            color="#FFFFFF",
        )
        name_text.set_duration(150).set_position(540, 450)

        price_text = TextClip(
            text=f"${self.price:.2f}",
            font="Arial",
            size=72.0,
            color="#FFFFFF",
        )
        price_text.set_duration(150).set_position(540, 540)

        tagline_text = TextClip(
            text=self.tagline,
            font="Arial",
            size=32.0,
            color="#FFFFFFCC",
        )
        tagline_text.set_duration(150).set_position(540, 650)

        divider = ShapeClip.rect(x=390, y=610, w=300, h=3, fill="#FFFFFF")
        divider.set_duration(150).set_opacity(0.6)

        comp.add(bg, logo, name_text, price_text, divider, tagline_text)
        return comp


products = [
    {
        "product_name": "Wireless Headphones",
        "price": 79.99,
        "tagline": "Immersive sound, all day comfort",
        "brand_color": "#2d3436",
    },
    {
        "product_name": "Smart Watch Pro",
        "price": 199.00,
        "tagline": "Your health, your schedule, your style",
        "brand_color": "#0984e3",
    },
    {
        "product_name": "Bluetooth Speaker",
        "price": 49.95,
        "tagline": "Big sound in a small package",
        "brand_color": "#6c5ce7",
    },
]

for product in products:
    template = ProductCard(**product)
    comp = template.build()
    filename = product["product_name"].lower().replace(" ", "_") + ".mp4"
    comp.render(str(output_dir / filename), preset="h264_1080p")
