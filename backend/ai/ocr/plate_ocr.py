import logging
import numpy as np
from typing import Optional

logger = logging.getLogger(__name__)

class PlateOCR:
    def __init__(self):
        self._available = False
        self._reader = None
        self._load()

    def _load(self):
        try:
            import easyocr
            self._reader = easyocr.Reader(['en'], gpu=False)
            self._available = True
            logger.info("EasyOCR loaded for ANPR")
        except ImportError:
            logger.warning("EasyOCR not installed, ANPR unavailable.")
        except Exception as e:
            logger.warning("EasyOCR init failed: %s", e)

    def name(self) -> str:
        return "EasyOCR"

    def version(self) -> str:
        return "1.0"

    def is_available(self) -> bool:
        return self._available

    def recognize(self, frame: np.ndarray, plate_box: list[int]) -> Optional[dict]:
        if not self._available:
            return None
        
        try:
            x, y, w, h = plate_box
            crop = frame[max(0, y):y+h, max(0, x):x+w]
            if crop.size == 0:
                return None
            
            result = self._reader.readtext(crop)
            if result:
                # result is a list of [bbox, text, prob]
                best_match = max(result, key=lambda r: r[2])
                raw_text = best_match[1]
                prob = float(best_match[2])
                
                # normalization
                norm = raw_text.upper().replace(" ", "").replace("-", "")
                
                return {
                    "raw_text": raw_text,
                    "normalized_text": norm,
                    "confidence": prob
                }
            return None
        except Exception as e:
            logger.warning("OCR failed: %s", e)
            return None
