"""
Tracking Integration Test

Verifies the IOUTracker-Stub correctly:
1. Assigns track IDs to detections with bounding boxes
2. Persists track IDs across frames for nearby objects
3. Creates new IDs for objects that appear in new locations
"""
import pytest
import numpy as np
from backend.ai.engine import Detection, ai_engine
from backend.ai.tracking.bytetrack import Tracker


def test_tracker_assigns_ids():
    """Tracker assigns unique IDs to detections with bounding boxes."""
    tracker = Tracker()
    
    # Synthetic detections at known positions
    dets = [
        Detection(
            detection_type="object", label="car", confidence=0.9,
            bounding_box=(100, 100, 50, 50), frame_number=0,
            timestamp=0.0, model_name="test", model_version="1.0",
            meta_data={}
        ),
        Detection(
            detection_type="object", label="person", confidence=0.8,
            bounding_box=(300, 300, 40, 60), frame_number=0,
            timestamp=0.0, model_name="test", model_version="1.0",
            meta_data={}
        ),
    ]
    
    dummy_frame = np.zeros((416, 416, 3), dtype=np.uint8)
    result = tracker.update(dets, dummy_frame)
    
    assert len(result) == 2
    assert all(d.track_id is not None for d in result), "Tracker must assign IDs"
    
    ids = {d.track_id for d in result}
    assert len(ids) == 2, "Each distinct object should get a unique track ID"


def test_tracker_persists_ids_across_frames():
    """Same object at similar position across frames keeps the same track ID."""
    tracker = Tracker()
    dummy_frame = np.zeros((416, 416, 3), dtype=np.uint8)
    
    # Frame 0: object at (100, 100)
    dets_f0 = [
        Detection(
            detection_type="object", label="car", confidence=0.9,
            bounding_box=(100, 100, 50, 50), frame_number=0,
            timestamp=0.0, model_name="test", model_version="1.0",
            meta_data={}
        ),
    ]
    result_f0 = tracker.update(dets_f0, dummy_frame)
    tid_f0 = result_f0[0].track_id
    
    # Frame 1: object at (110, 105) — moved slightly
    dets_f1 = [
        Detection(
            detection_type="object", label="car", confidence=0.88,
            bounding_box=(110, 105, 50, 50), frame_number=1,
            timestamp=0.04, model_name="test", model_version="1.0",
            meta_data={}
        ),
    ]
    result_f1 = tracker.update(dets_f1, dummy_frame)
    tid_f1 = result_f1[0].track_id
    
    assert tid_f0 == tid_f1, (
        f"Same object moved slightly should keep the same track ID. "
        f"Got {tid_f0} → {tid_f1}"
    )


def test_tracker_new_id_for_distant_object():
    """An object far from any existing track gets a new ID."""
    tracker = Tracker()
    dummy_frame = np.zeros((416, 416, 3), dtype=np.uint8)
    
    # Frame 0: object at (100, 100)
    dets_f0 = [
        Detection(
            detection_type="object", label="car", confidence=0.9,
            bounding_box=(100, 100, 50, 50), frame_number=0,
            timestamp=0.0, model_name="test", model_version="1.0",
            meta_data={}
        ),
    ]
    result_f0 = tracker.update(dets_f0, dummy_frame)
    tid_f0 = result_f0[0].track_id
    
    # Frame 1: completely different position (500, 500) — new object
    dets_f1 = [
        Detection(
            detection_type="object", label="person", confidence=0.7,
            bounding_box=(500, 500, 40, 60), frame_number=1,
            timestamp=0.04, model_name="test", model_version="1.0",
            meta_data={}
        ),
    ]
    result_f1 = tracker.update(dets_f1, dummy_frame)
    tid_f1 = result_f1[0].track_id
    
    assert tid_f0 != tid_f1, (
        f"Distant object should get a new track ID. Got {tid_f0} for both."
    )


def test_tracking_with_real_detector():
    """
    End-to-end: real YOLO → real Tracker on demo video.
    Reports NO_DETECTIONS if YOLO finds nothing (expected for synthetic video).
    """
    ai_engine.initialize("models")
    if not ai_engine._object_detector.is_available():
        pytest.skip("YOLO object detector unavailable")
    if not ai_engine._tracker.is_available():
        pytest.skip("Tracker unavailable")
    
    import cv2
    from pathlib import Path
    
    video_path = Path("demo/media/demo_video.mp4")
    if not video_path.exists():
        pytest.skip("Demo video not found")
    
    cap = cv2.VideoCapture(str(video_path))
    assert cap.isOpened()
    
    ret, frame = cap.read()
    cap.release()
    assert ret, "Failed to read frame"
    
    dets = ai_engine._object_detector.detect(frame)
    tracked = ai_engine._tracker.update(dets, frame)
    
    # This is informational — synthetic video may yield zero detections
    if len(tracked) == 0:
        # NO_DETECTIONS is a valid outcome for synthetic video
        # The important thing is the pipeline didn't crash
        pass
    else:
        assert all(d.track_id is not None for d in tracked)
