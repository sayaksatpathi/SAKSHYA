# SAKSHYA: End-to-End Forensic Demo

This guide explains how to run the end-to-end vertical slice demonstration for SAKSHYA.

The demonstration executes a full end-to-end processing pipeline on a synthetic or provided demo video to prove the technical functionality of the core architecture: **RECOVER → UNDERSTAND → PROVE**.

## Prerequisites

- **Python 3.10+**
- **Virtual Environment** (recommended)

### Optional Dependencies
The system gracefully degrades if the following dependencies are missing, clearly reporting `UNAVAILABLE`:
- **FFprobe**: Requires `ffmpeg` suite in the system PATH. (Without this, basic video metadata is skipped).
- **YOLOv4-tiny**: Requires the YOLO weights and config inside the `models/` folder.
- **OpenCV AI Models**: Haar cascades are loaded by default. YuNet ONNX models can be placed in `models/` for advanced face detection.

## Setting Up

Ensure all dependencies from `requirements.txt` are installed.

```bash
pip install -r requirements.txt
```

## Running the Trust Authority (Optional)

The Trust Authority is intentionally implemented as an independent microservice to demonstrate an independent anchor of trust. If it is offline, the demo pipeline will report `UNAVAILABLE (Trust Service offline)`.

To run the Trust Service in the background (Default on port 8001):
```bash
python trust_service/app.py
```

## Running the End-to-End Demo

Execute the demo using the provided CLI script. This script automatically generates a small synthetic demo video and passes it through the full forensic lifecycle.

```bash
python -m scripts.demo_run
```

### What Happens During the Demo:

1. **Creating Case**: A local sandbox SQLite database is spun up and a demo case is instantiated.
2. **Ingesting Evidence**: The video is ingested into the evidence storage.
3. **Computing SHA-256**: A cryptographic hash is calculated to lock the initial integrity state.
4. **Extracting Metadata**: FFprobe parses stream metadata (codec, resolution, duration) if available.
5. **Validating Video**: OpenCV decodes the first frame to ensure the stream is readable and not corrupted.
6. **Running AI Analysis**: Available AI models (YOLO, YuNet, Haar Cascades) perform object and face detections, emitting results for the investigator.
7. **Building Ledger**: A cryptographic chain of custody is established across all actions.
8. **Building Merkle Tree**: A root hash is computed based on all acquired evidence items.
9. **Obtaining Trust Seal**: If the trust service is online, an asymmetric digital signature is requested to prove the chain state existed at this point in time, followed by independent cryptographic verification on the client side.
10. **Generating Report**: A forensic PDF report is generated containing all findings, hashes, metadata, and the chain of custody.
11. **Tamper Demonstration**: The script deliberately modifies the raw evidence file with malicious bytes and re-runs the integrity checker to trigger a `FAILED ALARM` and demonstrate breach detection.

## Output

After a successful run, your demo folder will look like this:

```text
demo/
├── media/
│   └── demo_video.mp4       # The input synthetic evidence
└── cases/
    └── DEMO-<id>_report.pdf # The generated comprehensive PDF report
```
