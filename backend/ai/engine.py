"""
SAKSHYA AI Engine

Abstraction layer for AI models. Each detector/recognizer is a pluggable
component that can be replaced without changing application logic.

IMPORTANT: AI outputs are investigative aids, not facts of identity.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Any

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class Detection:
    """A single AI detection result."""
    detection_type: str          # face, person, vehicle, plate, object
    label: Optional[str] = None
    confidence: float = 0.0
    bounding_box: Optional[list[float]] = None  # [x, y, w, h]
    frame_number: Optional[int] = None
    timestamp: Optional[float] = None
    track_id: Optional[str] = None
    embedding: Optional[np.ndarray] = None
    model_name: Optional[str] = None
    model_version: Optional[str] = None
    meta_data: dict[str, Any] = field(default_factory=dict)


class BaseDetector(ABC):
    """Abstract base for all AI detectors."""

    @abstractmethod
    def name(self) -> str:
        """Model/detector name."""
        ...

    @abstractmethod
    def version(self) -> str:
        """Model version string."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the model is loaded and ready."""
        ...

    @abstractmethod
    def detect(self, frame: np.ndarray, **kwargs) -> list[Detection]:
        """
        Run detection on a single frame.

        Args:
            frame: BGR image as numpy array (OpenCV format).

        Returns:
            List of Detection objects.
        """
        ...


class FaceDetector(BaseDetector):
    """
    Face detection using OpenCV's YuNet model.

    Falls back to Haar cascades if YuNet model file is unavailable.
    """

    def __init__(self, model_path: Optional[str] = None, confidence_threshold: float = 0.5):
        self._model = None
        self._model_path = model_path
        self._confidence = confidence_threshold
        self._available = False
        self._load()

    def _load(self) -> None:
        try:
            import cv2
            if self._model_path and Path(self._model_path).exists():
                self._model = cv2.FaceDetectorYN.create(
                    self._model_path, "", (320, 320),
                    self._confidence, 0.3, 5000,
                )
                self._available = True
                logger.info("YuNet face detector loaded")
            else:
                # Fallback to Haar cascade
                cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
                self._model = cv2.CascadeClassifier(cascade_path)
                if not self._model.empty():
                    self._available = True
                    logger.info("Haar cascade face detector loaded (fallback)")
                else:
                    logger.warning("No face detection model available")
        except Exception as e:
            logger.warning("Face detector initialization failed: %s", e)

    def name(self) -> str:
        return "YuNet" if hasattr(self._model, 'detect') and not isinstance(self._model, type(None)) else "HaarCascade"

    def version(self) -> str:
        return "opencv-builtin"

    def is_available(self) -> bool:
        return self._available

    def detect(self, frame: np.ndarray, **kwargs) -> list[Detection]:
        import cv2
        if not self._available:
            return []

        detections = []
        h, w = frame.shape[:2]

        try:
            if hasattr(self._model, 'detect') and hasattr(self._model, 'setInputSize'):
                # YuNet path
                self._model.setInputSize((w, h))
                _, faces = self._model.detect(frame)
                if faces is not None:
                    for face in faces:
                        x, y, fw, fh = int(face[0]), int(face[1]), int(face[2]), int(face[3])
                        conf = float(face[-1])
                        if conf >= self._confidence:
                            detections.append(Detection(
                                detection_type="face",
                                label="face",
                                confidence=conf,
                                bounding_box=[x, y, fw, fh],
                                model_name="YuNet",
                                model_version="opencv-builtin",
                            ))
            else:
                # Haar cascade fallback
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = self._model.detectMultiScale(gray, 1.3, 5)
                for (x, y, fw, fh) in faces:
                    detections.append(Detection(
                        detection_type="face",
                        label="face",
                        confidence=0.7,  # Haar doesn't provide confidence
                        bounding_box=[int(x), int(y), int(fw), int(fh)],
                        model_name="HaarCascade",
                        model_version="opencv-builtin",
                        meta_data={"note": "Haar cascade does not provide per-detection confidence"},
                    ))
        except Exception as e:
            logger.error("Face detection error: %s", e)

        return detections


class ObjectDetector(BaseDetector):
    """
    Object detection using YOLO (via OpenCV DNN).

    Supports configurable model paths for YOLOv4-tiny or similar
    lightweight models suitable for local machines.
    """

    COCO_CLASSES = [
        "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train",
        "truck", "boat", "traffic light", "fire hydrant", "stop sign",
        "parking meter", "bench", "bird", "cat", "dog", "horse", "sheep",
        "cow", "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella",
        "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard",
        "sports ball", "kite", "baseball bat", "baseball glove", "skateboard",
        "surfboard", "tennis racket", "bottle", "wine glass", "cup", "fork",
        "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange",
        "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair",
        "couch", "potted plant", "bed", "dining table", "toilet", "tv",
        "laptop", "mouse", "remote", "keyboard", "cell phone", "microwave",
        "oven", "toaster", "sink", "refrigerator", "book", "clock", "vase",
        "scissors", "teddy bear", "hair drier", "toothbrush",
    ]

    # Surveillance-relevant classes
    SURVEILLANCE_CLASSES = {"person", "car", "motorcycle", "bus", "truck", "bicycle", "backpack", "handbag", "suitcase"}

    def __init__(
        self,
        weights_path: Optional[str] = None,
        config_path: Optional[str] = None,
        confidence_threshold: float = 0.5,
        nms_threshold: float = 0.4,
    ):
        self._model = None
        self._weights_path = weights_path
        self._config_path = config_path
        self._confidence = confidence_threshold
        self._nms = nms_threshold
        self._available = False
        self._load()

    def _load(self) -> None:
        try:
            import cv2
            if (
                self._weights_path
                and self._config_path
                and Path(self._weights_path).exists()
                and Path(self._config_path).exists()
            ):
                self._model = cv2.dnn.readNetFromDarknet(
                    self._config_path, self._weights_path
                )
                self._model.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
                self._model.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
                
                # Calculate actual hash of model file for provenance
                import hashlib
                sha256 = hashlib.sha256()
                with open(self._weights_path, "rb") as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        sha256.update(chunk)
                self._model_sha256 = sha256.hexdigest()
                
                self._available = True
                logger.info("YOLO object detector loaded (SHA256: %s)", self._model_sha256)
            else:
                logger.info("YOLO model files not found — object detection unavailable. "
                           "See models/README.md for download instructions.")
        except Exception as e:
            logger.warning("Object detector initialization failed: %s", e)

    def name(self) -> str:
        return "YOLOv4-tiny"

    def version(self) -> str:
        return "darknet-opencv"

    def is_available(self) -> bool:
        return self._available

    def detect(self, frame: np.ndarray, **kwargs) -> list[Detection]:
        import cv2
        if not self._available:
            return []

        h, w = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(frame, 1 / 255.0, (416, 416), swapRB=True, crop=False)
        self._model.setInput(blob)

        layer_names = self._model.getLayerNames()
        out_layers = [layer_names[i - 1] for i in self._model.getUnconnectedOutLayers()]
        outputs = self._model.forward(out_layers)

        boxes = []
        confidences = []
        class_ids = []

        for output in outputs:
            for det in output:
                scores = det[5:]
                class_id = int(np.argmax(scores))
                conf = float(scores[class_id])
                if conf >= self._confidence:
                    cx, cy, bw, bh = det[0] * w, det[1] * h, det[2] * w, det[3] * h
                    x = int(cx - bw / 2)
                    y = int(cy - bh / 2)
                    boxes.append([x, y, int(bw), int(bh)])
                    confidences.append(conf)
                    class_ids.append(class_id)

        indices = cv2.dnn.NMSBoxes(boxes, confidences, self._confidence, self._nms)

        detections = []
        if len(indices) > 0:
            for i in indices.flatten():
                class_name = self.COCO_CLASSES[class_ids[i]] if class_ids[i] < len(self.COCO_CLASSES) else "unknown"
                x, y, w, h = boxes[i]
                meta_data = {
                    "class_id": int(class_ids[i]),
                    "class_name": class_name,
                    "bbox": {
                        "x1": x,
                        "y1": y,
                        "x2": x + w,
                        "y2": y + h
                    },
                    "model_id": "yolov4_tiny",
                    "model_sha256": getattr(self, "_model_sha256", "unknown")
                }
                detections.append(Detection(
                    detection_type="object",
                    label=class_name,
                    confidence=confidences[i],
                    bounding_box=boxes[i],
                    model_name="YOLOv4-tiny",
                    model_version="darknet-opencv",
                    meta_data=meta_data
                ))

        return detections


class PlateDetector(BaseDetector):
    """
    License plate detection stub.

    Detects potential license plate regions using cascade classifiers
    or contour analysis. OCR is performed separately.
    """

    def __init__(self, cascade_path: Optional[str] = None):
        self._available = False
        self._cascade = None
        self._load(cascade_path)

    def _load(self, cascade_path: Optional[str]) -> None:
        try:
            import cv2
            if cascade_path and Path(cascade_path).exists():
                self._cascade = cv2.CascadeClassifier(cascade_path)
                if not self._cascade.empty():
                    self._available = True
            else:
                # Try OpenCV's built-in Russian plate cascade as a fallback
                try:
                    built_in = cv2.data.haarcascades + "haarcascade_russian_plate_number.xml"
                    self._cascade = cv2.CascadeClassifier(built_in)
                    if not self._cascade.empty():
                        self._available = True
                        logger.info("Plate detector loaded (Haar cascade fallback)")
                except Exception:
                    pass
        except Exception as e:
            logger.warning("Plate detector initialization failed: %s", e)

    def name(self) -> str:
        return "HaarCascade-Plate"

    def version(self) -> str:
        return "opencv-builtin"

    def is_available(self) -> bool:
        return self._available

    def detect(self, frame: np.ndarray, **kwargs) -> list[Detection]:
        import cv2
        if not self._available:
            return []

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        plates = self._cascade.detectMultiScale(gray, 1.1, 4, minSize=(60, 20))

        detections = []
        for (x, y, w, h) in plates:
            detections.append(Detection(
                detection_type="plate",
                label="license_plate",
                confidence=0.6,
                bounding_box=[int(x), int(y), int(w), int(h)],
                model_name="HaarCascade-Plate",
                model_version="opencv-builtin",
                meta_data={"note": "Haar cascade — lower accuracy than dedicated plate detectors"},
            ))

        return detections


# Import Path here for the model loading checks
from pathlib import Path


class AIEngine:
    """
    Central AI engine that coordinates all detectors.

    Provides lazy loading and model availability checks.
    """

    def __init__(self):
        self._face_detector: Optional[FaceDetector] = None
        self._object_detector: Optional[ObjectDetector] = None
        self._plate_detector: Optional[PlateDetector] = None
        self._tracker = None
        self._face_recognizer = None
        self._plate_ocr = None
        self._initialized = False

    def initialize(self, model_base_path: str = "./models") -> None:
        """Load all available models."""
        base = Path(model_base_path)

        self._face_detector = FaceDetector(
            model_path=str(base / "face_detection_yunet_2023mar.onnx")
        )
        self._object_detector = ObjectDetector(
            weights_path=str(base / "yolov4-tiny.weights"),
            config_path=str(base / "yolov4-tiny.cfg"),
        )
        self._plate_detector = PlateDetector()
        
        from backend.ai.tracking.bytetrack import Tracker
        from backend.ai.recognition.face_embedding import FaceRecognizer
        from backend.ai.ocr.plate_ocr import PlateOCR
        
        self._tracker = Tracker()
        self._face_recognizer = FaceRecognizer(
            model_path=str(base / "face_recognition_sface_2021dec.onnx")
        )
        self._plate_ocr = PlateOCR()
        
        # Update registry status
        from backend.ai.registry import model_registry
        model_registry.update_status("face_detector", "AVAILABLE" if self._face_detector.is_available() else "UNAVAILABLE")
        model_registry.update_status("object_detector", "AVAILABLE" if self._object_detector.is_available() else "UNAVAILABLE")
        model_registry.update_status("plate_detector", "AVAILABLE" if self._plate_detector.is_available() else "UNAVAILABLE")
        model_registry.update_status("tracker", "AVAILABLE" if self._tracker.is_available() else "UNAVAILABLE")
        model_registry.update_status("face_embedding", "AVAILABLE" if self._face_recognizer.is_available() else "UNAVAILABLE")
        model_registry.update_status("plate_ocr", "AVAILABLE" if self._plate_ocr.is_available() else "UNAVAILABLE")

        self._initialized = True

    @property
    def face_detector(self) -> FaceDetector:
        if self._face_detector is None:
            self._face_detector = FaceDetector()
        return self._face_detector

    @property
    def object_detector(self) -> ObjectDetector:
        if self._object_detector is None:
            self._object_detector = ObjectDetector()
        return self._object_detector

    @property
    def plate_detector(self) -> PlateDetector:
        if self._plate_detector is None:
            self._plate_detector = PlateDetector()
        return self._plate_detector

    def available_models(self) -> dict[str, bool]:
        """Return availability status of all models."""
        return {
            "face_detector": self.face_detector.is_available(),
            "object_detector": self.object_detector.is_available(),
            "plate_detector": self.plate_detector.is_available(),
            "tracker": self._tracker.is_available() if self._tracker else False,
            "face_embedding": self._face_recognizer.is_available() if self._face_recognizer else False,
            "plate_ocr": self._plate_ocr.is_available() if self._plate_ocr else False,
        }

    def version(self) -> str:
        """Return engine version string for provenance records."""
        return "1.0.0"

    def detect_all(self, frame: np.ndarray, **kwargs) -> list[Detection]:
        """Run all available detectors on a frame, apply tracking and recognition."""
        results = []
        for detector in [self.face_detector, self.object_detector, self.plate_detector]:
            if detector.is_available():
                try:
                    results.extend(detector.detect(frame, **kwargs))
                except Exception as e:
                    logger.error("Detector %s failed: %s", detector.name(), e)
                    
        # Apply Tracking
        if self._tracker and self._tracker.is_available():
            results = self._tracker.update(results, frame)
            
        # Apply OCR to plates
        if self._plate_ocr and self._plate_ocr.is_available():
            for d in results:
                if d.detection_type == "plate" and d.bounding_box:
                    ocr_res = self._plate_ocr.recognize(frame, d.bounding_box)
                    if ocr_res:
                        d.label = ocr_res["normalized_text"]
                        d.meta_data.update(ocr_res)
                        
        # Apply Face Embeddings
        if self._face_recognizer and self._face_recognizer.is_available():
            for d in results:
                if d.detection_type == "face" and d.bounding_box:
                    emb = self._face_recognizer.compute_embedding(frame, d.bounding_box)
                    if emb is not None:
                        # Convert to list for JSON serialization downstream or keep as ndarray
                        d.embedding = emb
                        
        return results


# Global AI engine instance
ai_engine = AIEngine()
