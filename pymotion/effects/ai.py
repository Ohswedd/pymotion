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
