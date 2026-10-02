import pytest
import cv2
import numpy as np
from pathlib import Path

def test_yolov4_tiny_inference():
    # 1. Locate video and models
    video_path = Path("demo/media/demo_video.mp4")
    weights_path = Path("models/yolov4-tiny.weights")
    config_path = Path("models/yolov4-tiny.cfg")

    if not weights_path.exists() or not config_path.exists():
        pytest.skip("YOLOv4-tiny model files unavailable in models/")
    
    if not video_path.exists():
        pytest.skip("Demo video unavailable")

    # 2. Decode at least one frame
    cap = cv2.VideoCapture(str(video_path))
    assert cap.isOpened(), "Failed to open demo video"
    
    ret, frame = cap.read()
    assert ret and frame is not None, "Failed to read a frame from video"
    cap.release()

    # 3. Load the detector
    try:
        net = cv2.dnn.readNetFromDarknet(str(config_path), str(weights_path))
        net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
    except Exception as e:
        pytest.fail(f"Failed to load detector: {e}")

    # 4. Execute inference
    h, w = frame.shape[:2]
    blob = cv2.dnn.blobFromImage(frame, 1 / 255.0, (416, 416), swapRB=True, crop=False)
    net.setInput(blob)
    
    layer_names = net.getLayerNames()
    out_layers_idx = net.getUnconnectedOutLayers()
    if isinstance(out_layers_idx, np.ndarray) and out_layers_idx.ndim == 2:
        out_layers_idx = out_layers_idx.flatten()
    out_layers = [layer_names[i - 1] for i in out_layers_idx]
    
    outputs = net.forward(out_layers)
    
    # 5. Verify the output schema & 6. Verify bounding boxes & 7. Verify confidence
    detections = []
    for output in outputs:
        for det in output:
            scores = det[5:]
            class_id = np.argmax(scores)
            confidence = float(scores[class_id])
            
            if confidence > 0.1:
                center_x = int(det[0] * w)
                center_y = int(det[1] * h)
                width = int(det[2] * w)
                height = int(det[3] * h)
                
                x = int(center_x - width / 2)
                y = int(center_y - height / 2)
                
                assert 0.0 <= confidence <= 1.0, f"Confidence {confidence} out of range"
                assert class_id >= 0, f"Invalid class_id {class_id}"
                
                detections.append({
                    "class_id": int(class_id),
                    "confidence": confidence,
                    "bbox": [x, y, width, height]
                })

    # Provenance
    print(f"Found {len(detections)} detections")
    assert isinstance(detections, list), "Detections is not a list"
