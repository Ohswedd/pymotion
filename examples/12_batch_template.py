"""EX12 — Batch Template.

Use-case: A reusable product-ad template that validates inputs,
builds a branded composition, and batch-renders variants — all
driven by the Template ABC.

Features exercised:
  Template, TemplateValidationError

Output: 1920x1080, 30fps, 5s x3 variants, preset h264_fast -> outputs/12_batch_*.mp4
Estimated render time: ~15s
"""

from __future__ import annotations

from pathlib import Path

import pymotion as pm

ASSETS = Path(__file__).parent / "assets"
OUTPUT_DIR = Path(__file__).parent.parent / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

DURATION = 150  # 5s at 30fps


class ProductAdTemplate(pm.Template):
    """A branded product advertisement template.

    Fields:
        product_name: Name shown as the title.
        price: Displayed price value.
        brand_color: Primary brand color (hex string).
        image_path: Path to the product image.
    """

    product_name: str
    price: float
    brand_color: str = "#2563EB"
    image_path: Path = ASSETS / "product_hero.jpg"

    def build(self) -> pm.Composition:
        """Build a 5-second branded product ad."""
        comp = pm.Composition(width=1920, height=1080, fps=30, duration=DURATION)

        # Background gradient using brand color
        bg_track = pm.Track(name="bg")
        bg = pm.GradientClip(
            color_start=self.brand_color,
            color_end="#0a0a1a",
            direction=135.0,
        )
        bg.set_duration(DURATION)
        bg_track.clips.append(bg)
        comp.tracks.append(bg_track)

        # Product image
        img_track = pm.Track(name="product")
        img = pm.ImageClip(str(self.image_path))
        img.set_duration(DURATION).set_opacity(0.9)
        img_track.clips.append(img)
        comp.tracks.append(img_track)

        # Title text
        title_track = pm.Track(name="title")
        title = pm.TextClip(
            text=self.product_name,
            size=72.0,
            color=pm.Color(1.0, 1.0, 1.0, 1.0),
        )
        title.set_duration(DURATION).set_position(960, 200)
        title_track.clips.append(title)
        comp.tracks.append(title_track)

        # Price tag
        price_track = pm.Track(name="price")
        price_text = pm.TextClip(
            text=f"${self.price:.2f}",
            size=48.0,
            color=pm.Color.parse(self.brand_color),
        )
        price_text.set_duration(DURATION).set_position(960, 900)
        price_track.clips.append(price_text)
        comp.tracks.append(price_track)

        return comp


def main() -> None:
    # ── TemplateValidationError demo ────────────────────────────────────
    err = pm.TemplateValidationError("test_field", "expected str, got int")
    print(f"1. TemplateValidationError: field={err.field}, msg={err}")

    # Demonstrate validation catches bad types
    try:
        ProductAdTemplate(product_name=123, price=29.99)  # type: ignore[arg-type]
    except pm.TemplateValidationError as e:
        print(f"2. Validation caught: {e}")

    # ── Build and render three variants ─────────────────────────────────
    variants = [
        {
            "product_name": "Pro Headphones",
            "price": 299.99,
            "brand_color": "#2563EB",
            "image_path": ASSETS / "product_hero.jpg",
        },
        {
            "product_name": "Smart Watch",
            "price": 449.00,
            "brand_color": "#DC2626",
            "image_path": ASSETS / "product_a.jpg",
        },
        {
            "product_name": "Wireless Speaker",
            "price": 149.95,
            "brand_color": "#059669",
            "image_path": ASSETS / "product_b.jpg",
        },
    ]

    audit_dir = Path(__file__).parent.parent / "audit"
    audit_dir.mkdir(exist_ok=True)

    for i, params in enumerate(variants, 1):
        template = ProductAdTemplate(**params)
        print(f"\n--- Variant {i}: {template.product_name} ---")
        print(f"    price=${template.price:.2f}, color={template.brand_color}")

        # Build composition
        composition = template.build()
        print(f"    Composition: {composition.resolution}, dur={composition.duration}")

        # Export audit frame
        try:
            composition.export_frame(
                frame=DURATION // 2,
                output=audit_dir / f"ex12_v{i}.png",
            )
            print("    Audit frame exported")
        except (ValueError, RuntimeError) as e:
            print(f"    Audit skipped: {e}")

        # Render via template.render() convenience method
        output_path = OUTPUT_DIR / f"12_batch_v{i}.mp4"
        template.render(str(output_path), preset="h264_fast")
        size_mb = output_path.stat().st_size / 1024 / 1024
        print(f"    Rendered: {output_path} ({size_mb:.1f} MB)")

    print("\nAll 3 variants rendered successfully")


if __name__ == "__main__":
    main()
