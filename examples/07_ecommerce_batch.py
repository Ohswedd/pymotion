"""E-Commerce Batch Product Videos — PyMotion showcase.

Demonstrates a template-driven approach to batch video generation.
A single function produces a polished 15-second product video from
structured data (name, price, features, accent colour).  Four product
variants are rendered in a loop to show batch capability.

Showcased features:
    - Template-style function for repeatable video generation
    - Dynamic text content (product name, price, bullet features)
    - Consistent branding via shared colour palette and layout
    - ShapeClip placeholders for product imagery
    - GradientClip backgrounds with brand colours
    - TextClip for titles, prices, and feature callouts
    - CountUp animated number for the price reveal
    - Typewriter preset for tagline
    - Expression-driven fade-in / fade-out on all elements
    - Batch rendering loop producing multiple output files
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import structlog

from pymotion import (
    Color,
    Composition,
    GradientClip,
    ShapeClip,
    TextClip,
    Track,
    Typewriter,
)
from pymotion.text.animated import CountUp
from pymotion.utils.math import Vec2

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
WIDTH = 1080  # Square / portrait-friendly for social
HEIGHT = 1080
FPS = 30
VIDEO_DURATION_SEC = 15
VIDEO_DURATION_FRAMES = FPS * VIDEO_DURATION_SEC  # 450

# Brand constants
BRAND_FONT_SIZE_TITLE = 56.0
BRAND_FONT_SIZE_PRICE = 72.0
BRAND_FONT_SIZE_FEATURE = 32.0
BRAND_FONT_SIZE_TAG = 28.0


# ---------------------------------------------------------------------------
# Product data model
# ---------------------------------------------------------------------------


@dataclass
class ProductData:
    """Structured product information for video generation."""

    name: str
    price: float
    currency: str = "$"
    features: list[str] = field(default_factory=list)
    accent_color: str = "#FF006E"
    tagline: str = "Shop Now"


# ---------------------------------------------------------------------------
# Video template
# ---------------------------------------------------------------------------


def _fade_expr(duration: int, fade_in: int = 12, fade_out: int = 12):
    """Return an opacity expression with fade in/out."""

    def _fn(ctx, _d=duration, _fi=fade_in, _fo=fade_out):
        if ctx.local_frame < _fi:
            return ctx.local_frame / _fi
        if ctx.local_frame > _d - _fo:
            return max(0.0, 1.0 - (ctx.local_frame - (_d - _fo)) / _fo)
        return 1.0

    return _fn


def render_product_video(product: ProductData, output_path: Path) -> Path:
    """Generate a 15-second product showcase video.

    Layout (top to bottom):
        - Brand gradient background
        - Product name (top third)
        - Product placeholder box (centre)
        - Animated price counter
        - Feature bullets (staggered entrance)
        - Tagline (Typewriter reveal at end)

    Args:
        product: Product data to render.
        output_path: Destination file path.

    Returns:
        The output path.
    """
    comp = Composition(
        width=WIDTH,
        height=HEIGHT,
        fps=FPS,
        duration=VIDEO_DURATION_FRAMES,
        background="#FFFFFF",
    )

    # ── Background ──────────────────────────────────────────────────────
    bg_track = Track(name="background")
    bg = GradientClip(
        width=WIDTH,
        height=HEIGHT,
        color_start="#FFFFFF",
        color_end="#F4F4F8",
        direction="vertical",
    )
    bg.set_duration(VIDEO_DURATION_FRAMES).at(0)
    bg_track.add(bg)
    comp.add_track(bg_track)

    # ── Accent stripe (top bar with brand colour) ───────────────────────
    stripe_track = Track(name="stripe")
    stripe = ShapeClip.rectangle(WIDTH, 6, fill_color=product.accent_color)
    stripe.set_duration(VIDEO_DURATION_FRAMES).at(0).set_position(0.0, 0.0)
    stripe_track.add(stripe)

    # Bottom accent line
    bottom_stripe = ShapeClip.rectangle(WIDTH, 6, fill_color=product.accent_color)
    bottom_stripe.set_duration(VIDEO_DURATION_FRAMES).at(0).set_position(0.0, HEIGHT - 6.0)
    stripe_track.add(bottom_stripe)
    comp.add_track(stripe_track)

    # ── Product name ────────────────────────────────────────────────────
    text_track = Track(name="text")

    name_clip = TextClip(
        text=product.name.upper(),
        font_size=BRAND_FONT_SIZE_TITLE,
        color="#1A1A2E",
    )
    name_clip.set_duration(VIDEO_DURATION_FRAMES - 30).at(15)
    name_clip.set_position(WIDTH / 2 - BRAND_FONT_SIZE_TITLE * len(product.name) * 0.22, 60.0)
    name_clip.set_expression("opacity", _fade_expr(VIDEO_DURATION_FRAMES - 30, 15, 15))
    text_track.add(name_clip)

    # ── Product placeholder box ─────────────────────────────────────────
    product_track = Track(name="product")
    box_w, box_h = 400, 400
    box = ShapeClip.rectangle(box_w, box_h, fill_color="#E8E8F0")
    box.set_duration(VIDEO_DURATION_FRAMES - 60).at(30)
    box.set_position((WIDTH - box_w) / 2.0, 160.0)
    box.set_expression("opacity", _fade_expr(VIDEO_DURATION_FRAMES - 60, 15, 15))
    product_track.add(box)

    # Inner accent border
    border = ShapeClip.rectangle(
        box_w - 20,
        box_h - 20,
        fill_color="#00000000",
        stroke_color=product.accent_color,
        stroke_width=2.0,
    )
    border.set_duration(VIDEO_DURATION_FRAMES - 60).at(30)
    border.set_position((WIDTH - box_w) / 2.0 + 10.0, 170.0)
    border.set_expression("opacity", _fade_expr(VIDEO_DURATION_FRAMES - 60, 20, 15))
    product_track.add(border)

    # "Image" placeholder text inside box
    placeholder = TextClip(text="PRODUCT", font_size=24, color="#AAAAAA")
    placeholder.set_duration(VIDEO_DURATION_FRAMES - 60).at(30)
    placeholder.set_position((WIDTH - 100) / 2.0, 340.0)
    placeholder.set_expression("opacity", _fade_expr(VIDEO_DURATION_FRAMES - 60, 20, 15))
    product_track.add(placeholder)
    comp.add_track(product_track)

    # ── Price (CountUp animation) ───────────────────────────────────────
    price_int = int(product.price)
    price_clip = CountUp(
        start=0,
        end=price_int,
        prefix=product.currency,
        font_size=BRAND_FONT_SIZE_PRICE,
        color=Color.parse(product.accent_color),
        position=Vec2(WIDTH / 2 - 100, 590.0),
    )
    price_clip.set_duration(120).at(60)
    text_track.add(price_clip)

    # Static price after count-up completes
    static_price = TextClip(
        text=f"{product.currency}{product.price:.2f}",
        font_size=BRAND_FONT_SIZE_PRICE,
        color=product.accent_color,
    )
    static_price.set_duration(VIDEO_DURATION_FRAMES - 210).at(180)
    static_price.set_position(WIDTH / 2 - 120, 590.0)
    static_price.set_expression("opacity", _fade_expr(VIDEO_DURATION_FRAMES - 210, 10, 15))
    text_track.add(static_price)

    # ── Feature bullets (staggered entrance) ────────────────────────────
    feature_start = 120
    for i, feat in enumerate(product.features[:4]):
        bullet = TextClip(
            text=f"  {feat}",
            font_size=BRAND_FONT_SIZE_FEATURE,
            color="#333344",
        )
        entry_frame = feature_start + i * 30
        bullet.set_duration(VIDEO_DURATION_FRAMES - entry_frame - 30).at(entry_frame)
        bullet.set_position(160.0, 700.0 + i * 50.0)
        bullet.set_expression(
            "opacity",
            _fade_expr(VIDEO_DURATION_FRAMES - entry_frame - 30, 12, 12),
        )
        text_track.add(bullet)

        # Accent dot
        dot = ShapeClip.circle(radius=5, fill_color=product.accent_color)
        dot.set_duration(VIDEO_DURATION_FRAMES - entry_frame - 30).at(entry_frame)
        dot.set_position(140.0, 710.0 + i * 50.0)
        dot.set_expression(
            "opacity",
            _fade_expr(VIDEO_DURATION_FRAMES - entry_frame - 30, 12, 12),
        )
        product_track.add(dot)

    # ── Tagline (Typewriter at end) ─────────────────────────────────────
    tagline = Typewriter(
        text=product.tagline,
        font_size=BRAND_FONT_SIZE_TAG,
        color=Color(0.1, 0.1, 0.18, 1.0),
        chars_per_frame=0.4,
        position=Vec2(WIDTH / 2 - 80, HEIGHT - 80.0),
    )
    tagline.set_duration(120).at(VIDEO_DURATION_FRAMES - 150)
    text_track.add(tagline)

    comp.add_track(text_track)

    # ── Render ──────────────────────────────────────────────────────────
    logger.info(
        "rendering_product",
        product=product.name,
        output=str(output_path),
    )
    comp.render(str(output_path), preset="h264_1080p")
    logger.info("product_render_complete", product=product.name)
    return output_path


# ---------------------------------------------------------------------------
# Product catalogue
# ---------------------------------------------------------------------------

PRODUCTS: list[ProductData] = [
    ProductData(
        name="Aether Headphones",
        price=299.99,
        features=[
            "Active noise cancellation",
            "40-hour battery life",
            "Spatial audio support",
            "Premium memory foam pads",
        ],
        accent_color="#6C63FF",
        tagline="Hear Everything. Miss Nothing.",
    ),
    ProductData(
        name="Nova Smartwatch",
        price=449.00,
        features=[
            "Always-on AMOLED display",
            "Heart rate + SpO2 monitoring",
            "5 ATM water resistance",
            "7-day battery life",
        ],
        accent_color="#FF6B6B",
        tagline="Your Health. Your Wrist.",
    ),
    ProductData(
        name="Prism Speaker",
        price=179.95,
        features=[
            "360-degree immersive sound",
            "Dual subwoofer array",
            "Multi-room pairing",
            "Recycled aluminium body",
        ],
        accent_color="#00B4D8",
        tagline="Sound Without Boundaries.",
    ),
    ProductData(
        name="Flux Keyboard",
        price=229.00,
        features=[
            "Hot-swappable switches",
            "Per-key RGB lighting",
            "Aircraft-grade aluminium",
            "USB-C + Bluetooth 5.3",
        ],
        accent_color="#2DC653",
        tagline="Type. Create. Dominate.",
    ),
]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Batch-render all product videos."""
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    logger.info("batch_start", count=len(PRODUCTS))

    for idx, product in enumerate(PRODUCTS):
        filename = f"07_product_{idx + 1}_{product.name.lower().replace(' ', '_')}.mp4"
        output_path = output_dir / filename
        render_product_video(product, output_path)

    logger.info("batch_complete", count=len(PRODUCTS))


if __name__ == "__main__":
    main()
