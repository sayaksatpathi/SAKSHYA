"""
SAKSHYA Model Registry
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

@dataclass
class ModelInfo:
    model_id: str
    name: str
    version: str
    task: str
    framework: str
    path: str
    sha256: str
    license: str
    source: str
    status: str = "UNAVAILABLE"

class ModelRegistry:
    def __init__(self):
        self.models: Dict[str, ModelInfo] = {}

    def register(self, model: ModelInfo):
        self.models[model.model_id] = model

    def get_all(self) -> list[ModelInfo]:
        return list(self.models.values())

    def update_status(self, model_id: str, status: str):
        if model_id in self.models:
            self.models[model_id].status = status

model_registry = ModelRegistry()

model_registry.register(ModelInfo(
    model_id="object_detector",
    name="YOLOv4-tiny",
    version="darknet-opencv",
    task="object_detection",
    framework="opencv-dnn",
    path="models/yolov4-tiny.weights",
    sha256="",
    license="MIT",
    source="ultralytics"
))
model_registry.register(ModelInfo(
    model_id="face_detector",
    name="YuNet",
    version="opencv-builtin",
    task="face_detection",
    framework="opencv-dnn",
    path="models/face_detection_yunet_2023mar.onnx",
    sha256="",
    license="MIT",
    source="opencv"
))
model_registry.register(ModelInfo(
    model_id="plate_detector",
    name="HaarCascade-Plate",
    version="opencv-builtin",
    task="plate_detection",
    framework="opencv",
    path="",
    sha256="",
    license="BSD",
    source="opencv"
))
model_registry.register(ModelInfo(
    model_id="face_embedding",
    name="SFace",
    version="opencv-dnn",
    task="face_recognition",
    framework="opencv-dnn",
    path="models/face_recognition_sface_2021dec.onnx",
    sha256="",
    license="MIT",
    source="opencv"
))
model_registry.register(ModelInfo(
    model_id="plate_ocr",
    name="EasyOCR",
    version="1.0",
    task="ocr",
    framework="pytorch",
    path="",
    sha256="",
    license="Apache 2.0",
    source="easyocr"
))
model_registry.register(ModelInfo(
    model_id="tracker",
    name="ByteTrack-Stub",
    version="1.0",
    task="tracking",
    framework="numpy",
    path="",
    sha256="",
    license="MIT",
    source="custom"
))
model_registry.register(ModelInfo(
    model_id="reid",
    name="OSNet",
    version="1.0",
    task="reid",
    framework="pytorch",
    path="models/osnet_x1_0.pth",
    sha256="",
    license="MIT",
    source="torchreid",
    status="UNAVAILABLE"
))
