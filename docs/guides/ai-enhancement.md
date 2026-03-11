# AI Enhancement & Restoration

PyMotion v2.0 includes AI effects for upscaling, denoising,
deblurring, frame interpolation, and colorization. All are optional
extras — install with `pip install "pymotion-studio[ai]"`.

## Upscaling

`Upscale` uses Real-ESRGAN to super-resolve footage at 2× or 4×:

```python
from pymotion import Upscale

effect = Upscale(factor=2)  # 2× or 4×
# The effect upscales the frame, then resizes back to original
# dimensions to maintain composition layout
```

The `factor` parameter must be `2` or `4`. The 2× model runs on CPU;
4× benefits from GPU acceleration. The model is loaded once and cached
for subsequent frames.

## Denoising

`Denoise` applies a deep learning denoiser to clean up noisy footage:

```python
from pymotion import Denoise

effect = Denoise(strength=0.5)  # 0.0–1.0
```

The `strength` parameter controls how aggressively noise is removed.
Lower values preserve more detail; higher values produce smoother
results.

## Deblurring

`Deblur` performs blind deconvolution deblurring to recover sharp
detail from motion-blurred frames:

```python
from pymotion import Deblur

effect = Deblur(strength=0.5)  # 0.0–1.0
```

Works best on uniform motion blur. Heavy defocus blur may require
multiple passes with moderate strength.

## Frame interpolation

`FrameInterpolation` uses RIFE-based models to generate intermediate
frames for smooth slow-motion:

```python
from pymotion import FrameInterpolation

effect = FrameInterpolation(factor=2)  # 2× frame count
```

The `factor` must be `2`, `4`, or `8`. This effect requires GPU
acceleration for real-time performance. As a per-frame effect, it
currently operates as a placeholder — true temporal interpolation
requires clip-level access to adjacent frames.

## Colorization

`ColorizeClip` converts grayscale footage to color using AI:

```python
from pymotion import ColorizeClip

effect = ColorizeClip()
# Converts B&W frames to plausible color using a pretrained model
```

The effect uses a transformer-based colorization model. It detects
grayscale input and applies learned color distributions. Results
vary depending on scene content — outdoor scenes and faces tend to
colorize well.
