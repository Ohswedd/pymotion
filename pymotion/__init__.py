"""PyMotion — A Python-native, code-first video generation framework.

Public API exports for v1.0.
"""

from pymotion.ai import (
    AutoColor,
    AutoEdit,
    ContentAwareCrop,
    FaceBlur,
    FaceDetector,
    FaceTracker,
    HighlightDetector,
    MusicGeneration,
    SceneDetector,
    SilenceRemover,
    SoundFXGeneration,
    VoiceConversion,
)
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
    ConvolutionReverb,
    Delay,
    EQBand,
    HighPassFilter,
    Limiter,
    LowPassFilter,
    MultibandCompressor,
    NoiseReduction,
    PitchShift,
    Reverb,
    audio_crossfade,
)
from pymotion.audio.mixer import (
    STEREO_CHANNELS,
    SURROUND_51_CHANNELS,
    AudioBus,
    AudioClipData,
    AudioMixer,
    ChannelLayout,
    SurroundChannel,
)
from pymotion.captions import (
    AutoCaptions,
    CaptionSegment,
    SubtitleClip,
    WordTimestamp,
    export_subtitles,
    get_caption_style,
    import_subtitles,
    parse_ass,
    parse_srt,
    parse_vtt,
)
from pymotion.clip.audio import AudioClip, Silence
from pymotion.clip.audio_viz import (
    AudioReactiveEffect,
    SpectrogramClip,
    SpectrumClip,
    WaveformClip,
)
from pymotion.clip.base import Align, BlendMode, NullObject, RenderContext, Resolution, TimeRange
from pymotion.clip.chart import (
    AreaChartClip,
    BarChartClip,
    LineChartClip,
    NumberCounter,
    PieChartClip,
    ProgressBar,
    RadarChartClip,
    ScatterPlotClip,
)
from pymotion.clip.color import ColorClip, GradientClip
from pymotion.clip.image import ImageClip
from pymotion.clip.mockup import BrowserMockup, DesktopMockup, PhoneMockup
from pymotion.clip.motion_graphics import (
    CallToAction,
    Countdown,
    Divider,
    LogoReveal,
    LowerThird,
    QuoteCard,
    SocialHandle,
    TransitionTitle,
    Watermark,
)
from pymotion.clip.operations import (
    ConcatenatedClip,
    FreezeFrameClip,
    JoinedClip,
    RepeatedClip,
    ReversedClip,
    SpeedClip,
    SpeedRampClip,
    SubClip,
    TimeRemappedClip,
    concatenate,
)
from pymotion.clip.scene3d import Scene3D, Scene3DClip
from pymotion.clip.shape import ShapeClip
from pymotion.clip.text import Shadow, TextClip, download_google_font
from pymotion.clip.video import VideoClip
from pymotion.color_science import (
    HDR10_PRESET,
    HLG_PRESET,
    ColorMatch,
    HistogramClip,
    HSLSecondary,
    ParadeScopeClip,
    VectorscopeClip,
    WaveformScopeClip,
    aces_to_srgb,
    srgb_to_aces,
)
from pymotion.composition import AdjustmentLayer, Composition, CompositionClip, Track
from pymotion.config import PyMotionConfig, get_config, reset_config, set_config
from pymotion.effects.ai import (
    ColorizeClip,
    Deblur,
    Denoise,
    ExtendFrame,
    FrameInterpolation,
    ObjectSegmentation,
    RemoveBackground,
    RemoveObject,
    ReplaceBackground,
    Upscale,
)
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
from pymotion.effects.keying import ChromaKey, ColorKey, DifferenceKey, LumaKey
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
from pymotion.expressions import ExpressionContext, ExpressionFn, loop_in, loop_out, wiggle
from pymotion.layout import grid, pip, split_screen, stack
from pymotion.masking import (
    BezierMask,
    BezierPoint,
    LinearGradientMask,
    Mask,
    MaskGroup,
    MaskOp,
    RadialGradientMask,
    TextMask,
    TrackMatte,
)
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
from pymotion.path_animation import StrokeClip, follow_path, morph_paths
from pymotion.proxy import ProxyClip, clear_proxy_cache, proxy_cache_size
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
from pymotion.render.gpu_compositor import GPUCompositor, get_gpu_compositor
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
from pymotion.tracking import MotionTracker, StabilizedClip
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
from pymotion.tts import TTSClip
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
    "AdjustmentLayer",
    "Composition",
    "CompositionClip",
    "Track",
    # Clips
    "AreaChartClip",
    "AudioClip",
    "BarChartClip",
    "BrowserMockup",
    "CallToAction",
    "Countdown",
    "DesktopMockup",
    "Divider",
    "LineChartClip",
    "LogoReveal",
    "LowerThird",
    "NumberCounter",
    "PhoneMockup",
    "PieChartClip",
    "ProgressBar",
    "QuoteCard",
    "RadarChartClip",
    "ScatterPlotClip",
    "SocialHandle",
    "TransitionTitle",
    "Watermark",
    "ColorClip",
    "GradientClip",
    "ImageClip",
    "Scene3DClip",
    "ShapeClip",
    "TextClip",
    "VideoClip",
    # Clip operations
    "ConcatenatedClip",
    "FreezeFrameClip",
    "JoinedClip",
    "RepeatedClip",
    "ReversedClip",
    "SpeedClip",
    "SpeedRampClip",
    "SubClip",
    "TimeRemappedClip",
    "concatenate",
    # Captions & Subtitles
    "AutoCaptions",
    "CaptionSegment",
    "SubtitleClip",
    "WordTimestamp",
    "export_subtitles",
    "get_caption_style",
    "import_subtitles",
    "parse_ass",
    "parse_srt",
    "parse_vtt",
    # TTS
    "TTSClip",
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
    # Expressions
    "ExpressionContext",
    "ExpressionFn",
    "loop_in",
    "loop_out",
    "wiggle",
    # Path animation
    "StrokeClip",
    "follow_path",
    "morph_paths",
    # Parenting
    "NullObject",
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
    # AI helpers
    "AutoColor",
    "AutoEdit",
    "ContentAwareCrop",
    "FaceBlur",
    "FaceDetector",
    "FaceTracker",
    "HighlightDetector",
    "MusicGeneration",
    "SceneDetector",
    "SilenceRemover",
    "SoundFXGeneration",
    "VoiceConversion",
    # AI effects
    "ColorizeClip",
    "Deblur",
    "Denoise",
    "ExtendFrame",
    "FrameInterpolation",
    "ObjectSegmentation",
    "RemoveBackground",
    "RemoveObject",
    "ReplaceBackground",
    "Upscale",
    # Keying effects
    "ChromaKey",
    "ColorKey",
    "DifferenceKey",
    "LumaKey",
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
    "AudioBus",
    "AudioClipData",
    "AudioReactiveEffect",
    "AudioMixer",
    "ChannelLayout",
    "SurroundChannel",
    "STEREO_CHANNELS",
    "SURROUND_51_CHANNELS",
    "BeatDetector",
    "Compressor",
    "ConvolutionReverb",
    "Delay",
    "EQ",
    "EQBand",
    "HighPassFilter",
    "Limiter",
    "LowPassFilter",
    "MultibandCompressor",
    "NoiseReduction",
    "OnsetDetector",
    "PitchShift",
    "Reverb",
    "WaveformExtractor",
    "audio_crossfade",
    "SpectrogramClip",
    "SpectrumClip",
    "WaveformClip",
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
    # Layout helpers
    "pip",
    "grid",
    "split_screen",
    "stack",
    # Masking
    "BezierMask",
    "BezierPoint",
    "LinearGradientMask",
    "Mask",
    "MaskGroup",
    "MaskOp",
    "RadialGradientMask",
    "TextMask",
    "TrackMatte",
    # Proxy
    "ProxyClip",
    "clear_proxy_cache",
    "proxy_cache_size",
    # Tracking
    "MotionTracker",
    "StabilizedClip",
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
    # GPU Compositing
    "GPUCompositor",
    "get_gpu_compositor",
    # Tone mapping
    "tone_map_aces",
    "tone_map_filmic",
    "tone_map_reinhard",
    # Color science
    "ColorMatch",
    "HDR10_PRESET",
    "HLG_PRESET",
    "HSLSecondary",
    "HistogramClip",
    "ParadeScopeClip",
    "VectorscopeClip",
    "WaveformScopeClip",
    "aces_to_srgb",
    "srgb_to_aces",
    # CountUp (text)
    "CountUp",
]

__version__ = "2.0.0"
