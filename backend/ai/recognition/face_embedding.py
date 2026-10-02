import logging
import numpy as np
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class FaceRecognizer:
    def __init__(self, model_path: Optional[str] = None):
        self._model = None
        self._available = False
        self._model_path = model_path
        self._load()

    def _load(self):
        try:
            import cv2
            if self._model_path and Path(self._model_path).exists():
                self._model = cv2.FaceRecognizerSF.create(self._model_path, "")
                self._available = True
                logger.info("SFace recognizer loaded")
            else:
                logger.warning("SFace model not found, face recognition unavailable.")
        except Exception as e:
            logger.warning("Face recognizer init failed: %s", e)

    def name(self) -> str:
        return "SFace"

    def version(self) -> str:
        return "opencv-dnn"

    def is_available(self) -> bool:
        return self._available

    def compute_embedding(self, frame: np.ndarray, face_box: list[int]) -> Optional[np.ndarray]:
        if not self._available:
            return None
        # Compute real SFace embedding from face crop
        try:
            x, y, w, h = face_box
            face_crop = frame[max(0, y):y+h, max(0, x):x+w]
            if face_crop.size == 0:
                return None
            
            # SFace expects 112x112 aligned face. For MVP we'll just resize.
            import cv2
            aligned = cv2.resize(face_crop, (112, 112))
            feature = self._model.feature(aligned)
            return feature[0] # Returns 128-d float32 array
        except Exception as e:
            logger.warning("Embedding generation failed: %s", e)
            return None
