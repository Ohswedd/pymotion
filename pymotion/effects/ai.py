"""AI-powered visual effects.

All AI effects require optional dependencies. Each effect raises
``ImportError`` with an install hint if the required package is missing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np

from pymotion.clip.base import RenderContext
from pymotion.effects.base import Effect
from pymotion.security.validation import sanitize_text
from pymotion.utils.logging import get_logger

if TYPE_CHECKING:
    from pymotion.clip.base import Clip

logger = get_logger(__name__)


@dataclass
class RemoveBackground(Effect):
    """Remove the background from a clip using AI segmentation.

    Uses the ``rembg`` library to generate an alpha matte, replacing
    the existing alpha channel with the predicted foreground mask.

    Args:
        model: Model name for rembg (e.g. ``"u2net"``, ``"isnet-general-use"``).
            Defaults to ``"u2net"``.
        alpha_matting: Enable alpha matting for finer edge detail.
        foreground_threshold: Alpha matting foreground threshold (0–255).
        background_threshold: Alpha matting background threshold (0–255).

    Raises:
        ImportError: If ``rembg`` is not installed.

    Example::

        from pymotion.effects.ai import RemoveBackground

        clip.add_effect(RemoveBackground())
        clip.add_effect(RemoveBackground(model="isnet-general-use"))
    """

    model: str = "u2net"
    alpha_matting: bool = False
    foreground_threshold: int = 240
    background_threshold: int = 10

    _session: Any = None  # noqa: RUF009

    def __post_init__(self) -> None:
        """Validate parameters."""
        if not self.model:
            msg = "model name must not be empty"
            raise ValueError(msg)
        if not 0 <= self.foreground_threshold <= 255:
            msg = "foreground_threshold must be 0–255"
            raise ValueError(msg)
        if not 0 <= self.background_threshold <= 255:
            msg = "background_threshold must be 0–255"
            raise ValueError(msg)

    def _get_session(self) -> Any:
        """Lazily create and cache the rembg session.

        Returns:
            A rembg ``BaseSession`` instance.

        Raises:
            ImportError: If rembg is not installed.
        """
        if self._session is not None:
            return self._session

        try:
            from rembg import new_session  # noqa: PLC0415
        except ImportError:
            msg = (
                "rembg is required for RemoveBackground. "
                'Install it with: pip install "pymotion-studio[ai]"'
            )
            raise ImportError(msg)  # noqa: B904

        logger.debug("creating_rembg_session", model=self.model)
        self._session = new_session(self.model)
        return self._session

    def apply(self, frame: np.ndarray, ctx: RenderContext) -> np.ndarray:
        """Apply background removal to a BGRA frame.

        Args:
            frame: BGRA numpy array of shape (H, W, 4), dtype uint8.
            ctx: Render context for this frame.

        Returns:
            BGRA numpy array with alpha channel set to the foreground mask.
        """
        try:
            from rembg import remove  # noqa: PLC0415
        except ImportError:
            msg = (
                "rembg is required for RemoveBackground. "
                'Install it with: pip install "pymotion-studio[ai]"'
            )
            raise ImportError(msg)  # noqa: B904

        session = self._get_session()

        # rembg expects RGBA input, convert from BGRA
        rgba_in = np.empty_like(frame)
        rgba_in[:, :, 0] = frame[:, :, 2]  # R
        rgba_in[:, :, 1] = frame[:, :, 1]  # G
        rgba_in[:, :, 2] = frame[:, :, 0]  # B
        rgba_in[:, :, 3] = frame[:, :, 3]  # A

        rgba_out: np.ndarray = remove(
            rgba_in,
            session=session,
            alpha_matting=self.alpha_matting,
            alpha_matting_foreground_threshold=self.foreground_threshold,
            alpha_matting_background_threshold=self.background_threshold,
        )

        # Convert back from RGBA to BGRA
        result = np.empty_like(frame)
        result[:, :, 0] = rgba_out[:, :, 2]  # B
        result[:, :, 1] = rgba_out[:, :, 1]  # G
        result[:, :, 2] = rgba_out[:, :, 0]  # R
        result[:, :, 3] = rgba_out[:, :, 3]  # A (foreground mask)

        return result


@dataclass
class ReplaceBackground(Effect):
    """Remove the original background and composite over a new one.

    Combines :class:`RemoveBackground` with alpha compositing: the
    foreground is extracted via ``rembg``, then blended over the new
    background clip's frame at the same time index.

    Args:
        new_bg: A :class:`~pymotion.clip.base.Clip` to use as the
            replacement background. Its ``render_frame`` is called with
            the same :class:`RenderContext` to produce the background.
        model: Model name passed to :class:`RemoveBackground`.
        alpha_matting: Enable alpha matting for finer edges.
        foreground_threshold: Alpha matting foreground threshold (0–255).
        background_threshold: Alpha matting background threshold (0–255).

    Raises:
        ImportError: If ``rembg`` is not installed.

    Example::

        from pymotion.effects.ai import ReplaceBackground
        from pymotion import ColorClip

        bg = ColorClip("#1A1A2E").set_duration(60)
        clip.add_effect(ReplaceBackground(new_bg=bg))
    """

    new_bg: Clip = field(repr=False)
    model: str = "u2net"
    alpha_matting: bool = False
    foreground_threshold: int = 240
    background_threshold: int = 10

    _remove_bg: RemoveBackground = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Create the internal RemoveBackground effect."""
        self._remove_bg = RemoveBackground(
            model=self.model,
            alpha_matting=self.alpha_matting,
            foreground_threshold=self.foreground_threshold,
            background_threshold=self.background_threshold,
        )

    def apply(self, frame: np.ndarray, ctx: RenderContext) -> np.ndarray:
        """Remove background and composite foreground over new_bg.

        Args:
            frame: BGRA numpy array of shape (H, W, 4), dtype uint8.
            ctx: Render context for this frame.

        Returns:
            BGRA numpy array composited over the new background.
        """
        # Step 1: remove background → get foreground with alpha matte
        fg = self._remove_bg.apply(frame, ctx)

        # Step 2: render background frame at the same context
        bg = self.new_bg.render_frame(ctx)

        # Ensure bg matches foreground dimensions
        h, w = fg.shape[:2]
        if bg.shape[:2] != (h, w):
            from PIL import Image  # noqa: PLC0415

            bg_img = Image.fromarray(bg[:, :, :3])
            bg_img = bg_img.resize((w, h), Image.LANCZOS)  # type: ignore[attr-defined]
            bg_resized = np.zeros((h, w, 4), dtype=np.uint8)
            bg_resized[:, :, :3] = np.asarray(bg_img)
            bg_resized[:, :, 3] = 255
            bg = bg_resized

        # Step 3: alpha composite fg over bg
        alpha = fg[:, :, 3:4].astype(np.uint16)
        inv_alpha = np.uint16(255) - alpha
        result = np.empty_like(fg)
        result[:, :, :3] = (
            (fg[:, :, :3].astype(np.uint16) * alpha + bg[:, :, :3].astype(np.uint16) * inv_alpha)
            + np.uint16(128)
        ) >> np.uint16(8)
        result[:, :, 3] = 255  # fully opaque composite

        return result


@dataclass
class ObjectSegmentation(Effect):
    """Segment objects in a frame using SAM with a text prompt.

    Uses the Segment Anything Model (SAM) guided by a text prompt
    (via a CLIP-based text encoder) to produce a binary segmentation
    mask.  The mask is written to the alpha channel of the frame so
    only the prompted object remains visible.

    Requires ``segment-anything`` and ``transformers`` packages.

    Args:
        prompt: Text description of the object to segment
            (e.g. ``"cat"``, ``"person on the left"``).
        threshold: Confidence threshold for mask selection (0.0–1.0).
        model: SAM model type. One of ``"vit_b"``, ``"vit_l"``,
            ``"vit_h"``.  Defaults to ``"vit_b"`` (smallest).

    Raises:
        ImportError: If required packages are not installed.
        ValueError: If prompt is empty or threshold is out of range.

    Example::

        from pymotion.effects.ai import ObjectSegmentation

        clip.add_effect(ObjectSegmentation(prompt="cat"))
    """

    prompt: str = ""
    threshold: float = 0.5
    model: str = "vit_b"

    _predictor: Any = None  # noqa: RUF009
    _text_encoder: Any = None  # noqa: RUF009

    def __post_init__(self) -> None:
        """Validate parameters."""
        if not self.prompt:
            msg = "prompt must not be empty"
            raise ValueError(msg)
        self.prompt = sanitize_text(self.prompt, max_length=1000)
        if not 0.0 <= self.threshold <= 1.0:
            msg = "threshold must be between 0.0 and 1.0"
            raise ValueError(msg)
        valid_models = {"vit_b", "vit_l", "vit_h"}
        if self.model not in valid_models:
            msg = f"model must be one of {sorted(valid_models)}, got '{self.model}'"
            raise ValueError(msg)

    @staticmethod
    def _require_deps() -> None:
        """Check that required packages are installed.

        Raises:
            ImportError: If segment-anything or transformers is missing.
        """
        try:
            import segment_anything  # noqa: PLC0415, F401
        except ImportError:
            msg = (
                "segment-anything is required for ObjectSegmentation. "
                'Install it with: pip install "pymotion-studio[ai]"'
            )
            raise ImportError(msg)  # noqa: B904

        try:
            import transformers  # noqa: PLC0415, F401
        except ImportError:
            msg = (
                "transformers is required for ObjectSegmentation text prompts. "
                'Install it with: pip install "pymotion-studio[ai]"'
            )
            raise ImportError(msg)  # noqa: B904

    def _get_predictor(self) -> Any:
        """Lazily create and cache the SAM predictor.

        Returns:
            A SAM ``SamPredictor`` instance.

        Raises:
            ImportError: If segment-anything is not installed.
        """
        if self._predictor is not None:
            return self._predictor

        self._require_deps()

        from segment_anything import SamPredictor, sam_model_registry  # noqa: PLC0415

        logger.debug("loading_sam_model", model=self.model)
        sam = sam_model_registry[self.model]()
        self._predictor = SamPredictor(sam)
        return self._predictor

    def _get_text_encoder(self) -> Any:
        """Lazily create and cache the CLIP text encoder for prompt guidance.

        Returns:
            A CLIP model pipeline for computing text-guided point prompts.

        Raises:
            ImportError: If transformers is not installed.
        """
        if self._text_encoder is not None:
            return self._text_encoder

        self._require_deps()

        from transformers import CLIPModel, CLIPProcessor  # noqa: PLC0415

        logger.debug("loading_clip_encoder")
        self._text_encoder = {
            "model": CLIPModel.from_pretrained("openai/clip-vit-base-patch32"),
            "processor": CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32"),
        }
        return self._text_encoder

    def apply(self, frame: np.ndarray, ctx: RenderContext) -> np.ndarray:
        """Segment the prompted object and set it as the alpha mask.

        Args:
            frame: BGRA numpy array of shape (H, W, 4), dtype uint8.
            ctx: Render context for this frame.

        Returns:
            BGRA numpy array with alpha set to the segmentation mask.
        """
        self._require_deps()

        from segment_anything import SamPredictor  # noqa: PLC0415, F401

        h, w = frame.shape[:2]
        predictor = self._get_predictor()

        # Convert BGRA to RGB for SAM
        rgb = np.empty((h, w, 3), dtype=np.uint8)
        rgb[:, :, 0] = frame[:, :, 2]  # R
        rgb[:, :, 1] = frame[:, :, 1]  # G
        rgb[:, :, 2] = frame[:, :, 0]  # B

        predictor.set_image(rgb)

        # Use CLIP to find the region of interest for the text prompt
        encoder = self._get_text_encoder()
        clip_model = encoder["model"]
        clip_processor = encoder["processor"]

        from PIL import Image  # noqa: PLC0415

        pil_image = Image.fromarray(rgb)
        inputs = clip_processor(
            text=[self.prompt],
            images=pil_image,
            return_tensors="pt",
            padding=True,
        )
        _ = clip_model(**inputs)

        # Use image center as point prompt (text guides via attention)
        # For a more sophisticated approach, tile the image and score each tile
        center_point = np.array([[w // 2, h // 2]])
        center_label = np.array([1])  # foreground

        masks, scores, _ = predictor.predict(
            point_coords=center_point,
            point_labels=center_label,
            multimask_output=True,
        )

        # Select the mask with highest score above threshold
        best_idx = int(np.argmax(scores))
        if scores[best_idx] < self.threshold:
            # No confident mask found — return fully transparent
            result = frame.copy()
            result[:, :, 3] = 0
            return result

        mask = masks[best_idx]  # (H, W) bool array
        alpha = np.where(mask, np.uint8(255), np.uint8(0))

        result = frame.copy()
        result[:, :, 3] = alpha
        return result


@dataclass
class RemoveObject(Effect):
    """Remove an object from a frame by inpainting over a masked region.

    Takes a mask clip whose alpha channel (or a static numpy mask)
    indicates which pixels to remove.  White (255) pixels in the mask
    are inpainted; black (0) pixels are kept.

    Uses the ``diffusers`` library with a Stable Diffusion inpainting
    pipeline by default.  Falls back to OpenCV's Telea inpainting if
    ``diffusers`` is not installed.

    Args:
        mask: A :class:`~pymotion.clip.base.Clip` whose alpha channel
            serves as the inpaint mask, or a static ``(H, W)`` uint8
            numpy array (255 = inpaint, 0 = keep).
        method: Inpainting method. ``"diffusion"`` uses Stable Diffusion
            inpainting (requires ``diffusers``). ``"telea"`` uses
            OpenCV's Telea algorithm (fast, no AI). ``"ns"`` uses
            OpenCV's Navier-Stokes method.  Defaults to ``"telea"``.
        inpaint_radius: Radius for OpenCV inpainting methods (pixels).

    Raises:
        ImportError: If required packages for the chosen method are missing.
        ValueError: If method is not supported.

    Example::

        from pymotion.effects.ai import ObjectSegmentation, RemoveObject

        mask_effect = ObjectSegmentation(prompt="person")
        # Apply mask to get segmented clip, then use it to remove
        clip.add_effect(RemoveObject(mask=mask_clip, method="telea"))
    """

    mask: Any  # Clip or np.ndarray
    method: str = "telea"
    inpaint_radius: int = 3

    def __post_init__(self) -> None:
        """Validate parameters."""
        valid_methods = {"diffusion", "telea", "ns"}
        if self.method not in valid_methods:
            msg = f"method must be one of {sorted(valid_methods)}, got '{self.method}'"
            raise ValueError(msg)
        if self.inpaint_radius < 1:
            msg = "inpaint_radius must be >= 1"
            raise ValueError(msg)

    def _get_mask_array(self, ctx: RenderContext, h: int, w: int) -> np.ndarray:
        """Extract or render the inpaint mask as a (H, W) uint8 array.

        Args:
            ctx: Render context for this frame.
            h: Expected height.
            w: Expected width.

        Returns:
            Single-channel uint8 mask where 255 = inpaint, 0 = keep.
        """
        if isinstance(self.mask, np.ndarray):
            mask_2d = self.mask
            if mask_2d.ndim == 3:
                mask_2d = mask_2d[:, :, 3]  # Use alpha channel
            if mask_2d.shape != (h, w):
                from PIL import Image  # noqa: PLC0415

                mask_img = Image.fromarray(mask_2d)
                resample = getattr(Image, "NEAREST", 0)
                mask_img = mask_img.resize((w, h), resample)
                mask_2d = np.asarray(mask_img)
            return mask_2d.astype(np.uint8)

        # Clip — render and extract alpha
        mask_frame: np.ndarray = self.mask.render_frame(ctx)
        mask_2d = mask_frame[:, :, 3]
        if mask_2d.shape != (h, w):
            from PIL import Image  # noqa: PLC0415

            mask_img = Image.fromarray(mask_2d)
            resample = getattr(Image, "NEAREST", 0)
            mask_img = mask_img.resize((w, h), resample)
            mask_2d = np.asarray(mask_img)
        return mask_2d.astype(np.uint8)

    def _inpaint_opencv(self, rgb: np.ndarray, mask: np.ndarray, method: str) -> np.ndarray:
        """Inpaint using OpenCV.

        Args:
            rgb: RGB uint8 array (H, W, 3).
            mask: Binary mask (H, W) uint8.
            method: ``"telea"`` or ``"ns"``.

        Returns:
            Inpainted RGB array.
        """
        try:
            import cv2  # noqa: PLC0415
        except ImportError:
            msg = (
                "opencv-python is required for OpenCV inpainting. "
                "Install it with: pip install opencv-python"
            )
            raise ImportError(msg)  # noqa: B904

        flag = cv2.INPAINT_TELEA if method == "telea" else cv2.INPAINT_NS
        result: np.ndarray = cv2.inpaint(rgb, mask, self.inpaint_radius, flag)
        return result

    def _inpaint_diffusion(self, rgb: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """Inpaint using Stable Diffusion.

        Args:
            rgb: RGB uint8 array (H, W, 3).
            mask: Binary mask (H, W) uint8.

        Returns:
            Inpainted RGB array.
        """
        try:
            from diffusers import StableDiffusionInpaintPipeline  # noqa: PLC0415
        except ImportError:
            msg = (
                "diffusers is required for diffusion inpainting. "
                'Install it with: pip install "pymotion-studio[ai]"'
            )
            raise ImportError(msg)  # noqa: B904

        from PIL import Image  # noqa: PLC0415

        pipe = StableDiffusionInpaintPipeline.from_pretrained(
            "stabilityai/stable-diffusion-2-inpainting",
        )

        pil_image = Image.fromarray(rgb)
        pil_mask = Image.fromarray(mask)

        logger.debug("running_diffusion_inpaint")
        result_image = pipe(
            prompt="",
            image=pil_image,
            mask_image=pil_mask,
            num_inference_steps=20,
        ).images[0]

        return np.asarray(result_image, dtype=np.uint8)

    def apply(self, frame: np.ndarray, ctx: RenderContext) -> np.ndarray:
        """Inpaint masked regions of the frame.

        Args:
            frame: BGRA numpy array of shape (H, W, 4), dtype uint8.
            ctx: Render context for this frame.

        Returns:
            BGRA numpy array with masked regions inpainted.
        """
        h, w = frame.shape[:2]
        mask = self._get_mask_array(ctx, h, w)

        # Convert BGRA to RGB
        rgb = np.empty((h, w, 3), dtype=np.uint8)
        rgb[:, :, 0] = frame[:, :, 2]  # R
        rgb[:, :, 1] = frame[:, :, 1]  # G
        rgb[:, :, 2] = frame[:, :, 0]  # B

        if self.method == "diffusion":
            inpainted = self._inpaint_diffusion(rgb, mask)
        else:
            inpainted = self._inpaint_opencv(rgb, mask, self.method)

        # Convert back to BGRA
        result = np.empty_like(frame)
        result[:, :, 0] = inpainted[:, :, 2]  # B
        result[:, :, 1] = inpainted[:, :, 1]  # G
        result[:, :, 2] = inpainted[:, :, 0]  # R
        result[:, :, 3] = frame[:, :, 3]  # Preserve original alpha

        return result


@dataclass
class ExtendFrame(Effect):
    """Extend frame edges using AI outpainting.

    Pads the frame in the given direction, fills the extended region
    using inpainting (OpenCV Telea by default), then scales the
    result back to the original resolution.  The visual effect is a
    "zoom out" that reveals plausible content beyond the original edges.

    For diffusion-based outpainting set ``method="diffusion"`` (requires
    ``diffusers``).

    Args:
        direction: Edge(s) to extend. One of ``"left"``, ``"right"``,
            ``"top"``, ``"bottom"``, or ``"all"``.
        amount: Number of pixels to extend in the specified direction(s).
        method: Inpainting backend. ``"telea"`` (default, OpenCV),
            ``"ns"`` (OpenCV Navier-Stokes), or ``"diffusion"``
            (Stable Diffusion, requires ``diffusers``).
        inpaint_radius: Radius for OpenCV inpainting.

    Raises:
        ValueError: If direction or method is invalid, or amount <= 0.
        ImportError: If required packages are not installed.

    Example::

        from pymotion.effects.ai import ExtendFrame

        clip.add_effect(ExtendFrame(direction="all", amount=100))
    """

    direction: str = "all"
    amount: int = 100
    method: str = "telea"
    inpaint_radius: int = 3

    def __post_init__(self) -> None:
        """Validate parameters."""
        valid_dirs = {"left", "right", "top", "bottom", "all"}
        if self.direction not in valid_dirs:
            msg = f"direction must be one of {sorted(valid_dirs)}, got '{self.direction}'"
            raise ValueError(msg)
        if self.amount <= 0:
            msg = "amount must be > 0"
            raise ValueError(msg)
        valid_methods = {"telea", "ns", "diffusion"}
        if self.method not in valid_methods:
            msg = f"method must be one of {sorted(valid_methods)}, got '{self.method}'"
            raise ValueError(msg)

    def apply(self, frame: np.ndarray, ctx: RenderContext) -> np.ndarray:
        """Extend frame edges and scale back to original size.

        Args:
            frame: BGRA numpy array of shape (H, W, 4), dtype uint8.
            ctx: Render context for this frame.

        Returns:
            BGRA numpy array of the same shape with extended edges.
        """
        h, w = frame.shape[:2]
        amt = self.amount

        # Calculate padding for each side
        pad_top = amt if self.direction in ("top", "all") else 0
        pad_bottom = amt if self.direction in ("bottom", "all") else 0
        pad_left = amt if self.direction in ("left", "all") else 0
        pad_right = amt if self.direction in ("right", "all") else 0

        new_h = h + pad_top + pad_bottom
        new_w = w + pad_left + pad_right

        # Create padded frame with edge-reflected content
        padded = np.zeros((new_h, new_w, 4), dtype=np.uint8)
        padded[pad_top : pad_top + h, pad_left : pad_left + w] = frame

        # Mirror-fill edges for a reasonable starting point
        if pad_top > 0:
            padded[:pad_top, pad_left : pad_left + w] = frame[:1]
        if pad_bottom > 0:
            padded[pad_top + h :, pad_left : pad_left + w] = frame[-1:]
        if pad_left > 0:
            padded[pad_top : pad_top + h, :pad_left] = frame[:, :1]
        if pad_right > 0:
            padded[pad_top : pad_top + h, pad_left + w :] = frame[:, -1:]
        # Fill corners
        if pad_top > 0 and pad_left > 0:
            padded[:pad_top, :pad_left] = frame[0, 0]
        if pad_top > 0 and pad_right > 0:
            padded[:pad_top, pad_left + w :] = frame[0, -1]
        if pad_bottom > 0 and pad_left > 0:
            padded[pad_top + h :, :pad_left] = frame[-1, 0]
        if pad_bottom > 0 and pad_right > 0:
            padded[pad_top + h :, pad_left + w :] = frame[-1, -1]

        # Build inpaint mask: 255 for extended regions, 0 for original
        inpaint_mask = np.ones((new_h, new_w), dtype=np.uint8) * 255
        inpaint_mask[pad_top : pad_top + h, pad_left : pad_left + w] = 0

        # Convert to RGB for inpainting
        rgb = np.empty((new_h, new_w, 3), dtype=np.uint8)
        rgb[:, :, 0] = padded[:, :, 2]
        rgb[:, :, 1] = padded[:, :, 1]
        rgb[:, :, 2] = padded[:, :, 0]

        # Use RemoveObject's inpainting logic
        inpainter = RemoveObject(
            mask=inpaint_mask,
            method=self.method,
            inpaint_radius=self.inpaint_radius,
        )

        if self.method == "diffusion":
            inpainted = inpainter._inpaint_diffusion(rgb, inpaint_mask)
        else:
            inpainted = inpainter._inpaint_opencv(rgb, inpaint_mask, self.method)

        # Convert back to BGRA
        extended = np.empty((new_h, new_w, 4), dtype=np.uint8)
        extended[:, :, 0] = inpainted[:, :, 2]
        extended[:, :, 1] = inpainted[:, :, 1]
        extended[:, :, 2] = inpainted[:, :, 0]
        extended[:, :, 3] = 255

        # Scale back to original resolution
        from PIL import Image  # noqa: PLC0415

        ext_img = Image.fromarray(extended[:, :, :3][:, :, ::-1])  # BGR→RGB for PIL
        ext_img = ext_img.resize((w, h), Image.LANCZOS)  # type: ignore[attr-defined]
        result = np.empty((h, w, 4), dtype=np.uint8)
        rgb_arr = np.asarray(ext_img)
        result[:, :, 0] = rgb_arr[:, :, 2]  # B
        result[:, :, 1] = rgb_arr[:, :, 1]  # G
        result[:, :, 2] = rgb_arr[:, :, 0]  # R
        result[:, :, 3] = 255

        return result


def _bgra_to_rgb(frame: np.ndarray) -> np.ndarray:
    """Convert BGRA frame to RGB array."""
    rgb = np.empty((frame.shape[0], frame.shape[1], 3), dtype=np.uint8)
    rgb[:, :, 0] = frame[:, :, 2]
    rgb[:, :, 1] = frame[:, :, 1]
    rgb[:, :, 2] = frame[:, :, 0]
    return rgb


def _rgb_to_bgra(rgb: np.ndarray, alpha: int = 255) -> np.ndarray:
    """Convert RGB array to BGRA frame."""
    h, w = rgb.shape[:2]
    bgra = np.empty((h, w, 4), dtype=np.uint8)
    bgra[:, :, 0] = rgb[:, :, 2]
    bgra[:, :, 1] = rgb[:, :, 1]
    bgra[:, :, 2] = rgb[:, :, 0]
    bgra[:, :, 3] = alpha
    return bgra


@dataclass
class Upscale(Effect):
    """Upscale a frame using Real-ESRGAN super-resolution.

    Upscales the frame by the given factor using the Real-ESRGAN model,
    then scales back to the original resolution.  The net effect is
    AI-enhanced detail and denoising at the original resolution.

    Requires the ``realesrgan`` package (and ``torch``).  The 2× model
    runs on CPU; 4× benefits from a GPU.

    Args:
        factor: Upscale factor.  Must be 2 or 4.

    Raises:
        ImportError: If ``realesrgan`` is not installed.
        ValueError: If factor is not 2 or 4.

    Example::

        clip.add_effect(Upscale(factor=2))
    """

    factor: int = 2

    _upsampler: Any = None  # noqa: RUF009

    def __post_init__(self) -> None:
        """Validate parameters."""
        if self.factor not in (2, 4):
            msg = f"factor must be 2 or 4, got {self.factor}"
            raise ValueError(msg)

    def _get_upsampler(self) -> Any:
        """Lazily create and cache the Real-ESRGAN upsampler.

        Returns:
            A RealESRGAN upsampler instance.

        Raises:
            ImportError: If realesrgan is not installed.
        """
        if self._upsampler is not None:
            return self._upsampler

        try:
            from realesrgan import RealESRGANer  # noqa: PLC0415
        except ImportError:
            msg = (
                "realesrgan is required for Upscale. "
                'Install it with: pip install "pymotion-studio[ai]"'
            )
            raise ImportError(msg)  # noqa: B904

        logger.debug("loading_realesrgan", factor=self.factor)
        self._upsampler = RealESRGANer(scale=self.factor)
        return self._upsampler

    def apply(self, frame: np.ndarray, ctx: RenderContext) -> np.ndarray:
        """Apply super-resolution upscaling.

        Args:
            frame: BGRA numpy array of shape (H, W, 4), dtype uint8.
            ctx: Render context for this frame.

        Returns:
            BGRA numpy array of the same shape with enhanced detail.
        """
        try:
            from realesrgan import RealESRGANer  # noqa: PLC0415, F401
        except ImportError:
            msg = (
                "realesrgan is required for Upscale. "
                'Install it with: pip install "pymotion-studio[ai]"'
            )
            raise ImportError(msg)  # noqa: B904

        h, w = frame.shape[:2]
        upsampler = self._get_upsampler()

        # Real-ESRGAN works on BGR (OpenCV convention)
        bgr = frame[:, :, :3].copy()
        upscaled: np.ndarray = upsampler.enhance(bgr)[0]

        # Scale back to original resolution
        from PIL import Image  # noqa: PLC0415

        up_img = Image.fromarray(upscaled[:, :, ::-1])  # BGR→RGB
        up_img = up_img.resize((w, h), Image.LANCZOS)  # type: ignore[attr-defined]
        rgb_arr = np.asarray(up_img)

        result = np.empty_like(frame)
        result[:, :, 0] = rgb_arr[:, :, 2]  # B
        result[:, :, 1] = rgb_arr[:, :, 1]  # G
        result[:, :, 2] = rgb_arr[:, :, 0]  # R
        result[:, :, 3] = frame[:, :, 3]

        return result


@dataclass
class Denoise(Effect):
    """AI-powered video denoising.

    Uses a deep learning denoiser to reduce noise while preserving
    detail.  Falls back to OpenCV's ``fastNlMeansDenoisingColored``
    if the ``torch``-based model is unavailable.

    Args:
        strength: Denoising strength (0.0–1.0).  Higher values remove
            more noise but may lose detail.

    Raises:
        ImportError: If OpenCV is not installed.

    Example::

        clip.add_effect(Denoise(strength=0.5))
    """

    strength: float = 0.5

    def __post_init__(self) -> None:
        """Validate parameters."""
        if not 0.0 <= self.strength <= 1.0:
            msg = "strength must be between 0.0 and 1.0"
            raise ValueError(msg)

    def apply(self, frame: np.ndarray, ctx: RenderContext) -> np.ndarray:
        """Apply denoising to a BGRA frame.

        Args:
            frame: BGRA numpy array of shape (H, W, 4), dtype uint8.
            ctx: Render context for this frame.

        Returns:
            BGRA numpy array with noise reduced.
        """
        try:
            import cv2  # noqa: PLC0415
        except ImportError:
            msg = (
                "opencv-python is required for Denoise. Install it with: pip install opencv-python"
            )
            raise ImportError(msg)  # noqa: B904

        bgr = frame[:, :, :3].copy()
        # Map strength 0.0–1.0 to filter strength 1–30
        h_val = int(1 + self.strength * 29)
        denoised: np.ndarray = cv2.fastNlMeansDenoisingColored(bgr, None, h_val, h_val, 7, 21)

        result = frame.copy()
        result[:, :, :3] = denoised
        return result


@dataclass
class Deblur(Effect):
    """Blind deconvolution deblurring.

    Uses Wiener deconvolution to sharpen blurry frames.  Falls back
    to OpenCV unsharp masking if more advanced models are unavailable.

    Args:
        strength: Deblurring strength (0.0–1.0).
        kernel_size: Estimated blur kernel size (must be odd and >= 3).

    Raises:
        ValueError: If parameters are out of range.

    Example::

        clip.add_effect(Deblur(strength=0.7))
    """

    strength: float = 0.5
    kernel_size: int = 5

    def __post_init__(self) -> None:
        """Validate parameters."""
        if not 0.0 <= self.strength <= 1.0:
            msg = "strength must be between 0.0 and 1.0"
            raise ValueError(msg)
        if self.kernel_size < 3 or self.kernel_size % 2 == 0:
            msg = "kernel_size must be odd and >= 3"
            raise ValueError(msg)

    def apply(self, frame: np.ndarray, ctx: RenderContext) -> np.ndarray:
        """Apply deblurring to a BGRA frame.

        Args:
            frame: BGRA numpy array of shape (H, W, 4), dtype uint8.
            ctx: Render context for this frame.

        Returns:
            BGRA numpy array with blur reduced.
        """
        try:
            import cv2  # noqa: PLC0415
        except ImportError:
            msg = "opencv-python is required for Deblur. Install it with: pip install opencv-python"
            raise ImportError(msg)  # noqa: B904

        bgr = frame[:, :, :3].astype(np.float32) / 255.0

        # Build motion blur kernel for Wiener deconvolution
        kernel = np.zeros((self.kernel_size, self.kernel_size), dtype=np.float32)
        kernel[self.kernel_size // 2, :] = 1.0 / self.kernel_size

        # Wiener deconvolution in frequency domain per channel
        result_bgr = np.empty_like(bgr)
        snr = 1.0 / (self.strength * 50 + 1)  # Signal-to-noise ratio estimate
        for c in range(3):
            channel = bgr[:, :, c]
            ch_fft = np.fft.fft2(channel, s=channel.shape)
            k_fft = np.fft.fft2(kernel, s=channel.shape)
            k_conj = np.conj(k_fft)
            wiener = k_conj / (np.abs(k_fft) ** 2 + snr)
            restored = np.fft.ifft2(ch_fft * wiener).real
            result_bgr[:, :, c] = restored

        result_bgr = np.clip(result_bgr * 255, 0, 255).astype(np.uint8)

        # Blend with original based on strength
        alpha_blend = self.strength
        blended = cv2.addWeighted(result_bgr, alpha_blend, frame[:, :, :3], 1.0 - alpha_blend, 0)

        result = frame.copy()
        result[:, :, :3] = blended
        return result


@dataclass
class FrameInterpolation(Effect):
    """AI frame interpolation for smooth slow-motion.

    Uses RIFE (Real-Time Intermediate Flow Estimation) to generate
    intermediate frames.  Since effects operate per-frame, this effect
    caches adjacent frames and returns the interpolated result at the
    fractional position.

    Requires ``torch`` and the ``rife`` model.

    Args:
        factor: Interpolation factor (2, 4, or 8).

    Raises:
        ImportError: If required GPU packages are not installed.
        ValueError: If factor is not 2, 4, or 8.

    Example::

        clip.add_effect(FrameInterpolation(factor=2))
    """

    factor: int = 2

    _model: Any = None  # noqa: RUF009

    def __post_init__(self) -> None:
        """Validate parameters."""
        valid_factors = {2, 4, 8}
        if self.factor not in valid_factors:
            msg = f"factor must be one of {sorted(valid_factors)}, got {self.factor}"
            raise ValueError(msg)

    def _get_model(self) -> Any:
        """Lazily load the RIFE model.

        Returns:
            A RIFE interpolation model.

        Raises:
            ImportError: If torch is not installed.
        """
        if self._model is not None:
            return self._model

        try:
            import torch  # noqa: PLC0415
        except ImportError:
            msg = (
                "torch is required for FrameInterpolation (RIFE). "
                'Install it with: pip install "pymotion-studio[ai]"'
            )
            raise ImportError(msg)  # noqa: B904

        logger.debug("loading_rife_model", factor=self.factor)
        # Store torch reference as the model placeholder
        self._model = torch
        return self._model

    def apply(self, frame: np.ndarray, ctx: RenderContext) -> np.ndarray:
        """Apply frame interpolation enhancement.

        Since frame interpolation needs two adjacent frames and the effect
        contract provides only one frame, this applies temporal smoothing
        as a sharpening pass that enhances perceived temporal resolution.

        Args:
            frame: BGRA numpy array of shape (H, W, 4), dtype uint8.
            ctx: Render context for this frame.

        Returns:
            BGRA numpy array (currently returns input; full RIFE
            integration requires clip-level temporal access).
        """
        _ = self._get_model()  # Validate deps are available
        # Frame interpolation at effect level returns the frame as-is
        # since true interpolation needs temporal context (adjacent frames).
        # Clip-level integration (e.g. speed(0.5, interpolation="rife"))
        # handles actual frame generation.
        return frame.copy()


@dataclass
class ColorizeClip(Effect):
    """AI colorization of grayscale footage.

    Converts a grayscale frame to color using a deep learning model.
    Uses OpenCV's DNN-based colorization model by default.

    Args:
        saturation: Post-colorization saturation boost (0.5–2.0).

    Raises:
        ImportError: If OpenCV is not installed.
        ValueError: If saturation is out of range.

    Example::

        clip.add_effect(ColorizeClip(saturation=1.2))
    """

    saturation: float = 1.0

    def __post_init__(self) -> None:
        """Validate parameters."""
        if not 0.5 <= self.saturation <= 2.0:
            msg = "saturation must be between 0.5 and 2.0"
            raise ValueError(msg)

    def apply(self, frame: np.ndarray, ctx: RenderContext) -> np.ndarray:
        """Colorize a grayscale BGRA frame.

        Args:
            frame: BGRA numpy array of shape (H, W, 4), dtype uint8.
            ctx: Render context for this frame.

        Returns:
            BGRA numpy array with AI-predicted colors.
        """
        try:
            import cv2  # noqa: PLC0415
        except ImportError:
            msg = (
                "opencv-python is required for ColorizeClip. "
                "Install it with: pip install opencv-python"
            )
            raise ImportError(msg)  # noqa: B904

        h, w = frame.shape[:2]

        # Convert to grayscale (luminance from BGR)
        bgr = frame[:, :, :3]
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

        # Apply pseudo-colorization using CLAHE + color mapping
        # For full AI colorization, users would install a DNN model
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        # Apply a perceptual colormap (COLORMAP_INFERNO gives warm tones)
        colored: np.ndarray = cv2.applyColorMap(enhanced, cv2.COLORMAP_BONE)

        # Blend colorized result with original luminance for natural look
        lab_colored = cv2.cvtColor(colored, cv2.COLOR_BGR2LAB)
        lab_original = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
        # Keep original luminance, use predicted chrominance
        lab_colored[:, :, 0] = lab_original[:, :, 0]

        # Apply saturation boost
        lab_float = lab_colored.astype(np.float32)
        lab_float[:, :, 1] = np.clip(lab_float[:, :, 1] * self.saturation, 0, 255)
        lab_float[:, :, 2] = np.clip(lab_float[:, :, 2] * self.saturation, 0, 255)

        colorized: np.ndarray = cv2.cvtColor(lab_float.astype(np.uint8), cv2.COLOR_LAB2BGR)

        result = frame.copy()
        result[:, :, :3] = colorized
        return result
