"""PyMotion — A Python-native, code-first video generation framework.

Public API exports for Phase 0.2.
"""

from pymotion.animation.easing import (
    EasingFn,
    cubic_bezier,
    get_easing,
    steps,
)
from pymotion.animation.interpolator import AnimatableValue, interpolate
from pymotion.animation.keyframe import Keyframe, KeyframeTrack
from pymotion.animation.spring import spring
from pymotion.audio.effects import EQ, Compressor, EQBand, Limiter
from pymotion.audio.mixer import AudioClipData, AudioMixer
from pymotion.clip.audio import AudioClip
from pymotion.clip.base import BlendMode, RenderContext, Resolution, TimeRange
from pymotion.clip.color import ColorClip, GradientClip
from pymotion.clip.image import ImageClip
from pymotion.clip.shape import ShapeClip
from pymotion.clip.text import Shadow, TextClip
from pymotion.clip.video import VideoClip
from pymotion.composition import Composition, Track
from pymotion.effects.base import Effect
from pymotion.effects.visual import GaussianBlur, Vignette
from pymotion.export.presets import OutputPreset, get_preset
from pymotion.transition.base import Transition
from pymotion.transition.library import (
    CoverLeft,
    CoverRight,
    CrossDissolve,
    Cut,
    DipToColor,
    Fade,
    FadeToBlack,
    FadeToWhite,
    PushDown,
    PushLeft,
    PushRight,
    PushUp,
    RevealLeft,
    RevealRight,
    SlideDown,
    SlideLeft,
    SlideRight,
    SlideUp,
    ZoomIn,
    ZoomOut,
)
from pymotion.utils.color import Color
from pymotion.utils.math import Vec2, Vec3

__all__ = [
    # Composition
    "Composition",
    "Track",
    # Clips
    "AudioClip",
    "ColorClip",
    "GradientClip",
    "ImageClip",
    "ShapeClip",
    "TextClip",
    "VideoClip",
    # Text helpers
    "Shadow",
    # Core types
    "AnimatableValue",
    "BlendMode",
    "Color",
    "Resolution",
    "RenderContext",
    "TimeRange",
    "Vec2",
    "Vec3",
    # Animation
    "EasingFn",
    "Keyframe",
    "KeyframeTrack",
    "cubic_bezier",
    "get_easing",
    "interpolate",
    "spring",
    "steps",
    # Effects
    "Effect",
    "GaussianBlur",
    "Vignette",
    # Audio effects
    "AudioClipData",
    "AudioMixer",
    "Compressor",
    "EQ",
    "EQBand",
    "Limiter",
    # Transitions
    "Transition",
    "CoverLeft",
    "CoverRight",
    "CrossDissolve",
    "Cut",
    "DipToColor",
    "Fade",
    "FadeToBlack",
    "FadeToWhite",
    "PushDown",
    "PushLeft",
    "PushRight",
    "PushUp",
    "RevealLeft",
    "RevealRight",
    "SlideDown",
    "SlideLeft",
    "SlideRight",
    "SlideUp",
    "ZoomIn",
    "ZoomOut",
    # Export
    "OutputPreset",
    "get_preset",
]

__version__ = "0.2.0-alpha"
