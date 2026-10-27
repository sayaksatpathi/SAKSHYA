"""
SAKSHYA Person Re-Identification (Re-ID)

Computes an appearance embedding for a detected person crop so the same
individual can be matched across non-overlapping cameras (cross-camera search).

Follows SAKSHYA's honesty-first model contract: if the OSNet model file is not
present, the component reports UNAVAILABLE and never fabricates an embedding.
Matches produced from these embeddings are always labelled POSSIBLE_MATCH —
appearance similarity does not independently establish identity.
"""

import logging
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# OSNet x1_0 standard input geometry (height x width) and ImageNet stats.
_REID_INPUT_H = 256
_REID_INPUT_W = 128
_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


class PersonReIdentifier:
    """OSNet-based person appearance embedder (ONNX via OpenCV DNN)."""

    def __init__(self, model_path: Optional[str] = None):
        self._net = None
        self._available = False
        self._model_path = model_path
        self._load()

    def _load(self) -> None:
        try:
            import cv2

            if self._model_path and Path(self._model_path).exists():
                self._net = cv2.dnn.readNetFromONNX(self._model_path)
                self._available = True
                logger.info("OSNet Re-ID model loaded from %s", self._model_path)
            else:
                logger.warning(
                    "OSNet Re-ID model not found (%s) — cross-camera Re-ID unavailable.",
                    self._model_path,
                )
        except Exception as e:  # pragma: no cover - depends on optional model file
            logger.warning("Person Re-ID init failed: %s", e)

    def name(self) -> str:
        return "OSNet"

    def version(self) -> str:
        return "osnet_x1_0-onnx"

    def is_available(self) -> bool:
        return self._available

    def compute_embedding(
        self, frame: np.ndarray, person_box: list[int]
    ) -> Optional[np.ndarray]:
        """Return an L2-normalised appearance embedding for a person crop.

        ``person_box`` is ``[x, y, w, h]`` in pixel coordinates. Returns ``None``
        when the model is unavailable or the crop is empty.
        """
        if not self._available:
            return None
        try:
            import cv2

            x, y, w, h = person_box
            x, y = max(0, int(x)), max(0, int(y))
            crop = frame[y : y + int(h), x : x + int(w)]
            if crop.size == 0:
                return None

            # Resize to OSNet geometry and normalise (RGB, ImageNet stats).
            resized = cv2.resize(crop, (_REID_INPUT_W, _REID_INPUT_H))
            rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
            rgb = (rgb - _MEAN) / _STD
            blob = np.transpose(rgb, (2, 0, 1))[np.newaxis, ...]  # NCHW

            self._net.setInput(blob)
            feature = self._net.forward().flatten().astype(np.float32)

            norm = np.linalg.norm(feature)
            if norm < 1e-8:
                return None
            return feature / norm
        except Exception as e:  # pragma: no cover - depends on optional model file
            logger.warning("Re-ID embedding generation failed: %s", e)
            return None
