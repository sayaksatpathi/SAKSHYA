"""
SAKSHYA AI Interfaces
"""
from abc import ABC, abstractmethod
from typing import Optional, Any
import numpy as np

from backend.ai.engine import Detection

class BaseDetector(ABC):
    """Abstract base for all AI detectors."""

    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def version(self) -> str:
        ...

    @abstractmethod
    def is_available(self) -> bool:
        ...

    @abstractmethod
    def detect(self, frame: np.ndarray, **kwargs) -> list[Detection]:
        ...
