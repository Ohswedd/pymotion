# Hardware Encoding

PyMotion v2.5 adds hardware-accelerated video encoding presets for
NVIDIA (NVENC), Intel (QSV), and AMD (AMF) GPUs. The framework
auto-detects available encoders and falls back to software encoding
when hardware is not available.

## Hardware presets

Four hardware presets are included:

| Preset | Encoder | GPU |
|--------|---------|-----|
| `H264_NVENC` | `h264_nvenc` | NVIDIA |
| `H265_NVENC` | `hevc_nvenc` | NVIDIA |
| `H264_QSV` | `h264_qsv` | Intel |
| `H264_AMF` | `h264_amf` | AMD |

Use them like any other preset:

```python
from pymotion import Composition

comp = Composition(1920, 1080, fps=30, duration=300)
# ... build composition ...
comp.render("output.mp4", preset="h264_nvenc")
```

## Auto-detection

Detect which hardware encoders are available on your system:

```python
from pymotion import detect_hardware_encoders

available = detect_hardware_encoders()
print(available)
# e.g. ['h264_nvenc', 'hevc_nvenc'] on NVIDIA
# e.g. ['h264_qsv'] on Intel
# e.g. [] on CPU-only machines
```

This probes FFmpeg for supported encoders. It only returns encoders
that FFmpeg can actually use (not just compiled-in).

## Transparent fallback

Use `resolve_preset_with_fallback()` to get a hardware preset when
available, or its software equivalent otherwise:

```python
from pymotion import resolve_preset_with_fallback

# Returns H264_NVENC if available, otherwise falls back to h264_1080p
preset = resolve_preset_with_fallback("h264_nvenc")
print(f"Using: {preset.name}")
```

The fallback mapping:

| Hardware preset | Software fallback |
|-----------------|-------------------|
| `h264_nvenc` | `h264_1080p` |
| `hevc_nvenc` | `h265_1080p` |
| `h264_qsv` | `h264_1080p` |
| `h264_amf` | `h264_1080p` |

## Using in production

A common pattern for production renders:

```python
from pymotion import Composition, detect_hardware_encoders, resolve_preset_with_fallback

comp = Composition(1920, 1080, fps=30, duration=300)
# ... build composition ...

# Prefer NVENC, fall back to software
hw = detect_hardware_encoders()
if "h264_nvenc" in hw:
    preset_name = "h264_nvenc"
elif "h264_qsv" in hw:
    preset_name = "h264_qsv"
else:
    preset_name = "h264_1080p"

preset = resolve_preset_with_fallback(preset_name)
comp.render("output.mp4", preset=preset.name)
```

## Performance

Hardware encoding is typically 3-5x faster than software encoding for
H.264 and H.265. The quality is comparable at medium-to-high bitrates.
For archival quality, software encoding with CRF may still be preferred.
