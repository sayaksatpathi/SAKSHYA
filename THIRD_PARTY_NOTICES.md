# SAKSHYA — Third-Party Notices

This file documents all third-party libraries, models, and assets used by SAKSHYA.

## Python Libraries (Source Code)

| Library | Purpose | License | Source |
|---------|---------|---------|--------|
| FastAPI | Web framework / REST API | MIT | [tiangolo/fastapi](https://github.com/tiangolo/fastapi) |
| Pydantic | Data validation / schemas | MIT | [pydantic/pydantic](https://github.com/pydantic/pydantic) |
| SQLAlchemy | Database ORM | MIT | [sqlalchemy/sqlalchemy](https://github.com/sqlalchemy/sqlalchemy) |
| Uvicorn | ASGI server | BSD-3-Clause | [encode/uvicorn](https://github.com/encode/uvicorn) |
| OpenCV | Computer vision | Apache-2.0 | [opencv/opencv](https://github.com/opencv/opencv) |
| NumPy | Numerical computing | BSD-3-Clause | [numpy/numpy](https://github.com/numpy/numpy) |
| ReportLab | PDF generation | BSD | [reportlab/reportlab](https://www.reportlab.com/) |
| HTTPX | HTTP client | BSD-3-Clause | [encode/httpx](https://github.com/encode/httpx) |
| python-multipart | File upload parsing | Apache-2.0 | [andrew-d/python-multipart](https://github.com/andrew-d/python-multipart) |
| python-dotenv | Environment file loading | BSD-3-Clause | [theskumar/python-dotenv](https://github.com/theskumar/python-dotenv) |

## AI Models

| Model | Purpose | Code License | Weights License | Source / URLs |
|-------|---------|--------------|-----------------|---------------|
| YuNet (v2) | Face detection | Apache-2.0 | Apache-2.0 | [OpenCV Zoo - YuNet](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet) |
| Haar Cascades | Legacy detection | BSD | BSD | [OpenCV](https://github.com/opencv/opencv) |
| YOLOv4-tiny | Object detection | MIT (Darknet) | CC0 (Public Domain) | [AlexeyAB/darknet](https://github.com/AlexeyAB/darknet) |
| SFace | Face recognition | Apache-2.0 | Apache-2.0 | [OpenCV Zoo - SFace](https://github.com/opencv/opencv_zoo/tree/main/models/face_recognition_sface) |

*Note: SAKSHYA relies on the OpenCV Zoo implementations for ONNX-based inference. All models selected have permissive open-source weight licenses suitable for inclusion.*

## Fonts

| Font | Purpose | License | Source |
|------|---------|---------|--------|
| Inter | UI typography | SIL Open Font License | [Google Fonts](https://fonts.google.com/specimen/Inter) |
| JetBrains Mono | Monospace / hash display | SIL Open Font License | [JetBrains](https://github.com/JetBrains/JetBrainsMono) |

## Algorithms

The following standard algorithms are implemented independently:
- SHA-256 (using Python standard library `hashlib`)
- HMAC-SHA256 (using Python standard library `hmac`)
- Merkle Tree (original implementation)
- Append-only chain (original implementation)
- JSON canonicalization (original implementation)

## Important Notes

- No competitor SIH repository code has been copied or reused.
- All implementations are original unless attributed above.
- Standard algorithms and publicly documented techniques have been implemented independently following their published specifications.
