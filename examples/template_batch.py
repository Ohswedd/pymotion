"""Template Batch — Template subclass for batch video generation.

Demonstrates how to create a reusable Template that accepts
parameters and builds a Composition. Useful for generating
many videos from the same layout with different data.
"""

from pymotion import ColorClip, Composition, Template, TextClip


class ProductCard(Template):
    """A product card video template.

    Fields declared as class annotations are validated at init time.
    Default values are optional.
    """

    product_name: str
    price: float
    brand_color: str = "#FF6B6B"
    duration_frames: int = 150

    def build(self) -> Composition:
        """Build a composition from the template parameters."""
        comp = Composition(
            width=1080,
            height=1080,
            fps=30,
            duration=self.duration_frames,
        )

        # Background with brand color
        bg = ColorClip(color=self.brand_color)
        bg.set_duration(self.duration_frames)

        # Product name
        name_text = TextClip(
            text=self.product_name,
            font="Arial",
            size=56.0,
            color="#FFFFFF",
        )
        name_text.set_duration(self.duration_frames).set_position(540, 400)

        # Price tag
        price_text = TextClip(
            text=f"${self.price:.2f}",
            font="Arial",
            size=72.0,
            color="#FFFFFF",
        )
        price_text.set_duration(self.duration_frames).set_position(540, 520)

        comp.add(bg)
        comp.add(name_text)
        comp.add(price_text)

        return comp


# Batch generation — produce multiple videos from a data list
products = [
    {"product_name": "Wireless Headphones", "price": 79.99, "brand_color": "#2d3436"},
    {"product_name": "Smart Watch", "price": 199.00, "brand_color": "#0984e3"},
    {"product_name": "Bluetooth Speaker", "price": 49.95, "brand_color": "#6c5ce7"},
]

for product in products:
    template = ProductCard(**product)
    comp = template.build()
    filename = product["product_name"].lower().replace(" ", "_") + ".mp4"
    comp.render(filename, preset="h264_1080p")
