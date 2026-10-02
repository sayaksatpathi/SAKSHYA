# SAKSHYA AI Models

This directory stores AI model files used by SAKSHYA.

> **Important**: Large model files are NOT committed to the repository.
> Download them using the instructions below.

## Required Models

| Model | Purpose | Source | License | Expected Filename | SHA-256 |
|-------|---------|--------|---------|-------------------|---------|
| YuNet | Face detection | [OpenCV Zoo](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet) | Apache-2.0 | `face_detection_yunet_2023mar.onnx` | See source |
| YOLOv4-tiny | Object detection | [AlexeyAB/darknet](https://github.com/AlexeyAB/darknet) | MIT | `yolov4-tiny.weights` + `yolov4-tiny.cfg` | See source |
| SFace | Face recognition | [OpenCV Zoo](https://github.com/opencv/opencv_zoo/tree/main/models/face_recognition_sface) | Apache-2.0 | `face_recognition_sface_2021dec.onnx` | See source |

## Download Instructions

### YuNet (Face Detection)
```bash
wget https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx -O models/face_detection_yunet_2023mar.onnx
```

### YOLOv4-tiny (Object Detection)
```bash
wget https://github.com/AlexeyAB/darknet/releases/download/yolov4/yolov4-tiny.weights -O models/yolov4-tiny.weights
wget https://raw.githubusercontent.com/AlexeyAB/darknet/master/cfg/yolov4-tiny.cfg -O models/yolov4-tiny.cfg
```

### SFace (Face Recognition)
```bash
wget https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx -O models/face_recognition_sface_2021dec.onnx
```

## Model Verification

Before loading, SAKSHYA verifies model file existence. When models are
not available, the system falls back to:
- Haar cascade classifiers (built into OpenCV) for face detection
- Demo/synthetic results for object detection

## Adding New Models

1. Place the model file in this directory
2. Update `backend/config.py` with the model path
3. Implement or update the detector in `backend/ai/engine.py`
4. Update this README with model details
5. Verify the model's license is compatible

## License Compliance

All models listed here use permissive open-source licenses (Apache-2.0, MIT).
See `THIRD_PARTY_NOTICES.md` for complete attribution.
