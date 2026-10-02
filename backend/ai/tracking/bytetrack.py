import logging
import numpy as np
from typing import Optional
from backend.ai.engine import Detection

logger = logging.getLogger(__name__)

class Tracker:
    """
    Lightweight stub tracker based on basic IOU or returning assigned IDs.
    For MVP, assigns sequential IDs to nearby boxes.
    """
    def __init__(self):
        self.tracks = {}
        self.next_id = 1
        self._available = True

    def name(self) -> str:
        return "IOUTracker-Stub"

    def version(self) -> str:
        return "1.0"

    def is_available(self) -> bool:
        return self._available

    def update(self, detections: list[Detection], frame: np.ndarray) -> list[Detection]:
        # Very simple tracking logic for MVP
        for d in detections:
            if d.bounding_box:
                x, y, w, h = d.bounding_box
                cx, cy = x + w/2, y + h/2
                matched = False
                for tid, (tx, ty) in self.tracks.items():
                    if abs(cx - tx) < 50 and abs(cy - ty) < 50:
                        d.track_id = str(tid)
                        self.tracks[tid] = (cx, cy)
                        matched = True
                        break
                if not matched:
                    d.track_id = str(self.next_id)
                    self.tracks[self.next_id] = (cx, cy)
                    self.next_id += 1
        return detections
