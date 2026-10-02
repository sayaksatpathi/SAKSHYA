# SAKSHYA AI Pipeline

## Overview

SAKSHYA uses real, local AI inference for forensic video analysis.
All AI outputs are **investigative aids**, not definitive identifications.

## Execution Modes

| Mode | Environment Variable | Behaviour |
|------|---------------------|-----------|
| **Real** (default) | `SAKSHYA_AI_MODE=real` | Uses real model inference on evidence video. Returns `503` if no models are installed. |
| **Demo** | `SAKSHYA_AI_MODE=demo` | Uses synthetic/demo results for development and testing. All results are clearly marked `demo: true`. |

The system **never** silently falls from Real to Demo mode.

## Models

| Model ID | Name | Task | Framework | License |
|----------|------|------|-----------|---------|
| `object_detector` | YOLOv4-tiny | Object Detection | OpenCV DNN (Darknet) | MIT |
| `face_detector` | YuNet | Face Detection | OpenCV DNN (ONNX) | MIT |
| `face_embedding` | SFace | Face Recognition/Embedding | OpenCV DNN (ONNX) | MIT |
| `plate_detector` | HaarCascade | Plate Detection | OpenCV | BSD |
| `plate_ocr` | EasyOCR | OCR | PyTorch | Apache 2.0 |
| `tracker` | IOUTracker-Stub | Multi-Object Tracking | NumPy | MIT |

Model installation instructions are in [`models/README.md`](../models/README.md).

## Pipeline Architecture

```
Evidence Video
     ↓
FFmpeg/OpenCV VideoCapture
     ↓
Frame Sampling (configurable: FRAME_SAMPLE_RATE)
     ↓
┌─────────────────────────────────────────────┐
│  Per-Frame Inference                         │
│                                              │
│  Face Detection (YuNet)                      │
│  Object Detection (YOLOv4-tiny)              │
│  Plate Detection (HaarCascade)               │
│                                              │
│  → Tracker (IOU-based assignment)            │
│  → Plate OCR (EasyOCR, if detected)          │
│  → Face Embedding (SFace, if detected)       │
└─────────────────────────────────────────────┘
     ↓
Normalized Detections
     ↓
Database Persistence (AIResult table)
     ↓
Analysis Provenance (Ledger Event)
     ↓
Investigation UI / Timeline / Reports
```

## Detection Result Schema

Every detection persisted to the database contains:

```json
{
  "evidence_id": "...",
  "frame_number": 42,
  "timestamp": 1.68,
  "detection_type": "object",
  "label": "car",
  "confidence": 0.91,
  "bounding_box": [100, 200, 200, 150],
  "track_id": "7",
  "model_name": "YOLOv4-tiny",
  "model_version": "darknet-opencv",
  "meta_data": {
    "bbox": {"x1": 100, "y1": 200, "x2": 300, "y2": 350},
    "model_id": "yolov4_tiny",
    "model_sha256": "cf9fbfd0f6d4..."
  }
}
```

## Provenance

Every analysis job creates a chain-of-custody event:

```json
{
  "event_type": "AI_ANALYSIS_COMPLETED",
  "meta_data": {
    "analysis_id": "uuid",
    "start_time": "ISO-8601",
    "end_time": "ISO-8601",
    "status": "READY | NO_DETECTIONS",
    "total_detections": 47,
    "frames_analyzed": 120,
    "frame_sample_rate": 5,
    "confidence_threshold": 0.35,
    "models_used": ["YOLOv4-tiny", "YuNet"],
    "analysis_result_hash": "sha256-of-canonical-json",
    "software_version": "1.0.0"
  }
}
```

The `analysis_result_hash` is computed over the canonical JSON of all detection results,
creating a tamper-evident link between AI outputs and the integrity chain.

## Timestamp Calculation

```
timestamp = frame_number / FPS
```

Timestamps are derived from the actual frame position in the video.
They are never invented or approximated.

## Frame Processing

- Videos are processed via streaming `VideoCapture` — never loaded entirely into RAM.
- `FRAME_SAMPLE_RATE` controls how many frames to skip between inference passes.
- `MAX_ANALYSIS_FRAMES` limits total frames processed (0 = unlimited).

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `SAKSHYA_AI_MODE` | `real` | `real` or `demo` |
| `MODEL_BASE_PATH` | `./models` | Directory containing model files |
| `DETECTION_CONFIDENCE` | `0.35` | Minimum confidence threshold |
| `YOLO_IOU` | `0.45` | NMS IOU threshold |
| `FRAME_SAMPLE_RATE` | `5` | Process every Nth frame |
| `MAX_ANALYSIS_FRAMES` | `0` | Maximum frames to process (0 = unlimited) |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/evidence/{id}/analyze` | POST | Run AI analysis on evidence |
| `/api/evidence/{id}/detections` | GET | Get persisted detection results |
| `/api/cases/{id}/detections` | GET | Get all detections in a case |
| `/api/ai/models` | GET | Get model registry status |
| `/api/investigation/face-search` | POST | Search face embeddings |
| `/api/investigation/plate-search` | POST | Search plate detections |
| `/api/investigation/search` | GET | Unified search across detections |

## Limitations

- **Cross-camera re-identification** is not yet implemented (requires OSNet or similar).
- **ANPR** requires EasyOCR which may not be installed in all environments.
- **Face search** quality depends heavily on face alignment quality.
- **Object detection** uses YOLOv4-tiny which prioritizes speed over accuracy.
- AI results are investigative aids. **Similarity ≠ identity proof.**
