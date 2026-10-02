# SAKSHYA SIH Demo Script

## 1. Setup & Environment
Ensure backend services and frontend are running:
```bash
python -m uvicorn backend.main:app --port 8000
python trust_service/app.py
cd frontend && npm run dev
```

## 2. Platform Overview
* **Welcome Screen**: Introduce SAKSHYA as a robust, verifiable AI forensics platform designed for zero-hallucination tracking.
* **Dashboard**: Highlight the key metrics and the high-level case view.

## 3. Case Creation & Evidence Ingestion
* **Action**: Create a new mock case (e.g. `SIH-DEMO-001`).
* **Action**: Ingest a video snippet. Emphasize that the ingest process creates a cryptographic hash (SHA-256) of the file instantly, recorded on the ledger.

## 4. AI Analysis & Real Tracking
* **Action**: Trigger the AI Analysis process.
* **Talking Point**: Point out that the detection runs on a real local YOLO inference model, not fabricated API responses. If models are missing, the system gracefully reports `MODEL UNAVAILABLE`. Show the bounding boxes and track persistence on the investigation view.

## 5. Forensics & Recovery
* **Action**: Show the Camera map and Forensic timeline.
* **Talking Point**: Discuss the frame-level analysis where `ffprobe` pulls out timestamp discontinuities and drops to indicate device malfunctions or interference.

## 6. Cryptographic Sealing & Trust
* **Action**: Show the Merkle Tree creation for the case.
* **Talking Point**: Explain how all evidence hashes roll up into a Merkle root, establishing an tamper-evident state.
* **Action**: Trigger the Trust Receipt. Explain the independent Trust Service that signs the Merkle Root with an RSA key (mimicking an external trusted authority).

## 7. Reporting & Tamper Detection
* **Action**: Download the PDF report containing all forensic findings and the cryptographic Trust signature.
* **Action**: Run the Tamper Simulator endpoint. Wait for the UI alert indicating "Verification Failed: Hash Mismatch".
* **Conclusion**: Prove that any single bit change in the file immediately alerts investigators and invalidates the Trust Receipt.
