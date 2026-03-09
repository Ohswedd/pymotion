"""PyMotion — A Python-native, code-first video generation framework.

Public API exports for Phase 0.1.
"""

from pymotion.animation.easing import get_easing
from pymotion.animation.keyframe import Keyframe, KeyframeTrack
from pymotion.clip.base import BlendMode, RenderContext, Resolution, TimeRange
from pymotion.clip.color import ColorClip, GradientClip
from pymotion.clip.image import ImageClip
from pymotion.clip.shape import ShapeClip
from pymotion.composition import Composition, Track
from pymotion.effects.base import Effect
from pymotion.effects.visual import GaussianBlur, Vignette
from pymotion.export.presets import OutputPreset
from pymotion.transition.base import Transition
from pymotion.transition.library import CrossDissolve, Fade
from pymotion.utils.color import Color
from pymotion.utils.math import Vec2, Vec3

__all__ = [
    # Composition
    "Composition",
    "Track",
    # Clips
    "ColorClip",
    "GradientClip",
    "ImageClip",
    "ShapeClip",
    # Core types
    "BlendMode",
    "Color",
    "Resolution",
    "RenderContext",
    "TimeRange",
    "Vec2",
    "Vec3",
    # Animation
    "Keyframe",
    "KeyframeTrack",
    "get_easing",
    # Effects
    "Effect",
    "GaussianBlur",
    "Vignette",
    # Transitions
    "Transition",
    "Fade",
    "CrossDissolve",
    # Export
    "OutputPreset",
]

__version__ = "0.1.0-alpha"
