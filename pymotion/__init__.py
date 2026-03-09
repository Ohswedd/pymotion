"""PyMotion — A Python-native, code-first video generation framework.

Public API exports for v1.0.
"""

from pymotion.animation.easing import (
    EasingFn,
    cubic_bezier,
    get_easing,
    steps,
)
from pymotion.animation.interpolator import AnimatableValue, interpolate
from pymotion.animation.keyframe import Keyframe, KeyframeTrack, animate
from pymotion.animation.spring import spring
from pymotion.audio.analysis import (
    BeatDetector,
    OnsetDetector,
    WaveformExtractor,
    waveform_to_keyframes,
)
from pymotion.audio.effects import (
    EQ,
    Compressor,
    Delay,
    EQBand,
    HighPassFilter,
    Limiter,
    LowPassFilter,
    NoiseReduction,
    PitchShift,
    Reverb,
)
from pymotion.audio.mixer import AudioClipData, AudioMixer
from pymotion.clip.audio import AudioClip, Silence
from pymotion.clip.base import Align, BlendMode, RenderContext, Resolution, TimeRange
from pymotion.clip.color import ColorClip, GradientClip
from pymotion.clip.image import ImageClip
from pymotion.clip.scene3d import Scene3D, Scene3DClip
from pymotion.clip.shape import ShapeClip
from pymotion.clip.text import Shadow, TextClip, download_google_font
from pymotion.clip.video import VideoClip
from pymotion.composition import Composition, Track
from pymotion.config import PyMotionConfig, get_config, reset_config, set_config
from pymotion.effects.base import Effect
from pymotion.effects.color import (
    BleachBypass,
    Brightness,
    ColorBalance,
    Contrast,
    Curves,
    HueSaturationLuminance,
    LUTEffect,
    Saturation,
    SplitToning,
)
from pymotion.effects.distortion import (
    Fisheye,
    PerspectiveWarp,
    Ripple,
    Twirl,
    WaveWarp,
)
from pymotion.effects.light import (
    GodRays,
    LensFlareLight,
    LightLeak,
    NeonGlow,
)
from pymotion.effects.visual import (
    Bloom,
    ChromaticAberration,
    FilmGrain,
    GaussianBlur,
    Glow,
    LensFlare,
    MotionBlur,
    Sharpen,
    Vignette,
)
from pymotion.export.presets import OutputPreset, get_preset
from pymotion.particle.system import (
    Emitter,
    ParticleSystem,
    confetti,
    fire,
    rain,
    smoke,
    sparkles,
    stars,
)
from pymotion.render.backend_3d import (
    AmbientLight,
    Camera,
    DirectionalLight,
    HDRIEnvironment,
    PBRMaterial,
    PointLight,
    SpotLight,
)
from pymotion.render.color_pipeline import (
    tone_map_aces,
    tone_map_filmic,
    tone_map_reinhard,
)
from pymotion.template.base import Template, TemplateValidationError
from pymotion.text.animated import (
    CountDown,
    CountUp,
    GlitchText,
    KineticText,
    LetterByLetter,
    Scramble,
    SplitReveal,
    Typewriter,
    WordByWord,
)
from pymotion.transition.base import Transition
from pymotion.transition.library import (
    CircularWipe,
    CoverDown,
    CoverLeft,
    CoverRight,
    CoverUp,
    CrossDissolve,
    Cut,
    DipToColor,
    Fade,
    FadeToBlack,
    FadeToWhite,
    FilmBurn,
    Glitch,
    IrisIn,
    IrisOut,
    MorphWarp,
    PageTurn,
    PixelDissolve,
    PushDown,
    PushLeft,
    PushRight,
    PushUp,
    RevealDown,
    RevealLeft,
    RevealRight,
    RevealUp,
    ScaleDissolve,
    Shatter,
    SlideDown,
    SlideLeft,
    SlideRight,
    SlideUp,
    Vortex,
    WipeDiagonal,
    WipeLeft,
    WipeRight,
    ZoomBlur,
    ZoomIn,
    ZoomOut,
)
from pymotion.utils.color import Color
from pymotion.utils.math import Vec2, Vec3

# Particle preset aliases (PRD uses capitalized names)
Sparkles = sparkles
Confetti = confetti
Fire = fire
Smoke = smoke
Rain = rain
Stars = stars

# Text preset alias (PRD uses ScrambleText)
ScrambleText = Scramble

__all__ = [
    # Composition
    "Composition",
    "Track",
    # Clips
    "AudioClip",
    "ColorClip",
    "GradientClip",
    "ImageClip",
    "Scene3DClip",
    "ShapeClip",
    "TextClip",
    "VideoClip",
    # Helpers
    "Silence",
    "Keyframe",
    "animate",
    # 3D
    "Scene3D",
    "Camera",
    "PointLight",
    "DirectionalLight",
    "SpotLight",
    "AmbientLight",
    "HDRIEnvironment",
    "PBRMaterial",
    # Text helpers
    "Shadow",
    "download_google_font",
    # Animated text presets
    "CountDown",
    "CountUp",
    "GlitchText",
    "KineticText",
    "LetterByLetter",
    "Scramble",
    "ScrambleText",
    "SplitReveal",
    "Typewriter",
    "WordByWord",
    # Core types
    "Align",
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
    "KeyframeTrack",
    "cubic_bezier",
    "get_easing",
    "interpolate",
    "spring",
    "steps",
    # Visual effects
    "Effect",
    "Bloom",
    "ChromaticAberration",
    "FilmGrain",
    "GaussianBlur",
    "Glow",
    "LensFlare",
    "MotionBlur",
    "Sharpen",
    "Vignette",
    # Color effects
    "BleachBypass",
    "Brightness",
    "ColorBalance",
    "Contrast",
    "Curves",
    "HueSaturationLuminance",
    "LUTEffect",
    "Saturation",
    "SplitToning",
    # Distortion effects
    "Fisheye",
    "PerspectiveWarp",
    "Ripple",
    "Twirl",
    "WaveWarp",
    # Light effects
    "GodRays",
    "LensFlareLight",
    "LightLeak",
    "NeonGlow",
    # Audio effects
    "AudioClipData",
    "AudioMixer",
    "BeatDetector",
    "Compressor",
    "Delay",
    "EQ",
    "EQBand",
    "HighPassFilter",
    "Limiter",
    "LowPassFilter",
    "NoiseReduction",
    "OnsetDetector",
    "PitchShift",
    "Reverb",
    "WaveformExtractor",
    "waveform_to_keyframes",
    # Transitions
    "Transition",
    "CircularWipe",
    "CoverDown",
    "CoverLeft",
    "CoverRight",
    "CoverUp",
    "CrossDissolve",
    "Cut",
    "DipToColor",
    "Fade",
    "FadeToBlack",
    "FadeToWhite",
    "FilmBurn",
    "Glitch",
    "IrisIn",
    "IrisOut",
    "MorphWarp",
    "PageTurn",
    "PixelDissolve",
    "PushDown",
    "PushLeft",
    "PushRight",
    "PushUp",
    "RevealDown",
    "RevealLeft",
    "RevealRight",
    "RevealUp",
    "ScaleDissolve",
    "Shatter",
    "SlideDown",
    "SlideLeft",
    "SlideRight",
    "SlideUp",
    "Vortex",
    "WipeDiagonal",
    "WipeLeft",
    "WipeRight",
    "ZoomBlur",
    "ZoomIn",
    "ZoomOut",
    # Particles
    "ParticleSystem",
    "Emitter",
    "Sparkles",
    "Confetti",
    "Fire",
    "Smoke",
    "Rain",
    "Stars",
    "sparkles",
    "confetti",
    "fire",
    "smoke",
    "rain",
    "stars",
    # Export
    "OutputPreset",
    "get_preset",
    # Template
    "Template",
    "TemplateValidationError",
    # Config
    "PyMotionConfig",
    "get_config",
    "set_config",
    "reset_config",
    # Tone mapping
    "tone_map_aces",
    "tone_map_filmic",
    "tone_map_reinhard",
    # CountUp (text)
    "CountUp",
]

__version__ = "1.0.0"
