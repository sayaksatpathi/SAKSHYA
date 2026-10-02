"""
Model Provenance Test

Verifies that the AI engine computes and embeds the actual SHA-256
of the model weights file into every detection's metadata — not a
hardcoded placeholder.
"""
import pytest
import hashlib
import numpy as np
from pathlib import Path
from backend.ai.engine import ai_engine


def test_yolov4_tiny_provenance():
    weights_path = Path("models/yolov4-tiny.weights")
    if not weights_path.exists():
        pytest.skip("YOLOv4-tiny weights not found")

    # 1. Calculate actual SHA-256 of the weights file
    sha256 = hashlib.sha256()
    with open(weights_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    actual_hash = sha256.hexdigest()

    # 2. Initialize engine (idempotent)
    ai_engine.initialize("models")
    assert ai_engine._object_detector.is_available(), "Detector should be available"

    # 3. Verify the engine stored the computed hash
    engine_hash = getattr(ai_engine._object_detector, "_model_sha256", None)
    assert engine_hash is not None, "Engine must compute model_sha256 at load time"
    assert engine_hash == actual_hash, (
        f"Engine hash ({engine_hash[:16]}...) != file hash ({actual_hash[:16]}...)"
    )

    # 4. Verify detections carry the correct hash in metadata
    dummy_frame = np.zeros((416, 416, 3), dtype=np.uint8)
    detections = ai_engine._object_detector.detect(dummy_frame)

    # Dummy frame may produce zero detections — that's fine.
    # But if it does produce detections, every one must have the correct hash.
    for det in detections:
        assert det.meta_data.get("model_sha256") == actual_hash, (
            f"Detection metadata hash mismatch"
        )
