# SAKSHYA — FINAL SIH DEMONSTRATION SCRIPT

This document details the deterministic, end-to-end demonstration script for SAKSHYA.

## Prerequisites
1. Ensure the application is deployed and services (backend/frontend) are running.
2. Ensure you have the test sample video (e.g., `sample_video.mp4`) accessible.

---

## The Workflow

### 1. Login
*   Navigate to the web interface.
*   Log in using Investigator credentials (e.g., `test` / `test` if mock auth is enabled, or standard credentials).
*   **Expected**: Redirects to the Dashboard.

### 2. Create/Open Case
*   Navigate to **Cases** from the sidebar.
*   Click **New Case**.
*   Enter `DEMO-2026-001`, Title `Hit & Run Investigation`.
*   Click **Submit**.
*   **Expected**: The new case appears in the list. Click on it to open.

### 3. Add Evidence
*   Navigate to the **Evidence** tab within the Case view.
*   Click **Upload Evidence**.
*   Select `sample_video.mp4`.
*   **Expected**: The file uploads, and SAKSHYA automatically extracts metadata (codec, size, resolution, duration).

### 4. Show SHA-256
*   Once uploaded, hover over or inspect the newly created Evidence item.
*   **Expected**: The cryptographic SHA-256 hash is immediately visible on the UI, securing the chain of custody from the start.

### 5. Start AI Analysis
*   Go to the **Investigation** tab or click **Analyze** on the Evidence item.
*   Select the target video.
*   Click **Run AI Analysis**.
*   **Expected**: The UI indicates the job has been `QUEUED`.

### 6. Show Async Job
*   Observe the status badge.
*   **Expected**: The status automatically updates to `PROCESSING` as the FastAPI BackgroundTask picks it up, and eventually `COMPLETED`. (If a duplicate job is submitted concurrently, it should return the existing job ID.)

### 7. Show Detection/Tracking Status
*   Once the analysis is complete, navigate to the **Investigation > Detections** view.
*   **Expected**: Object detection overlays (bounding boxes/labels) and Tracking IDs appear. *(Note: Face Search and ANPR may display as `UNAVAILABLE` depending on optional models).*

### 8. Show Video Forensics
*   Navigate to the **Forensics** tab.
*   Click **Run Integrity Analysis** on the video.
*   **Expected**: Structural validation (FFprobe), missing frame detection, and metadata anomaly detection runs. The results display either `VERIFIED` or `TAMPERED` safely.

### 9. Show Recovery
*   Navigate to the **Recovery** tab.
*   Select the corrupted or target raw file (if applicable).
*   **Expected**: The system identifies standard supported media (`.mp4`, `.mkv`) and performs basic extraction. *Proprietary `.dav` extraction is currently intentionally limited and not falsely reported as recovered.*

### 10. Create Investigation Finding
*   In the Investigation view, select an AI detection bounding box or timeline event.
*   Click **Save as Finding**. Provide notes: *"Suspect vehicle matched visually"*.
*   **Expected**: Finding is saved and attached to the evidence.

### 11. Show Timeline
*   Navigate to the **Timeline** tab.
*   **Expected**: All events—Evidence Acquisition, Analysis Completed, Forensic Finding Created—are plotted chronologically on the interactive timeline.

### 12. Show Chain of Custody
*   Navigate to the **Integrity** tab.
*   Scroll to the **Chain of Custody Ledger**.
*   **Expected**: Append-only events (e.g., `EVIDENCE_INGESTED`, `ANALYSIS_STARTED`) are displayed with sequential hashes.

### 13. Show Merkle Root
*   In the **Integrity** tab, locate the **Merkle Tree Status**.
*   Click **Compute Merkle Root**.
*   **Expected**: The system computes a single cryptographic Merkle Root representing the entire state of the case evidence and ledger.

### 14. Show Trust Status
*   Below the Merkle Root, view the **Trust Service**.
*   Click **Issue Trust Receipt**.
*   **Expected**: A cryptographically signed timestamp (receipt) is simulated/generated, anchoring the chain head.

### 15. Generate Certificate Draft
*   In the **Integrity** tab, click **Generate BSA 63(4) Certificate**.
*   Provide placeholder details for the source device and operating context.
*   **Expected**: SAKSHYA outputs a highly structured electronic-record certificate draft.

### 16. Verify Certificate
*   Click **Verify Certificate** next to the newly created certificate.
*   **Expected**: The system cross-references the content hash, evidence hash, and Merkle linkage. It displays `CONSISTENT` (because it is unsigned).

### 17. Generate Report
*   Navigate to the **Reports** tab.
*   Click **Generate Forensic PDF**.
*   **Expected**: A comprehensive PDF downloads containing all Evidence Hashes, AI Findings, Chain of Custody, the Merkle Root, and the BSA Section 63(4) Certificate Draft with its required disclaimers.

### 18. Demonstrate Tamper Detection
*   Using backend scripts/DB access (or simulating via a tamper endpoint if exposed for demo purposes), alter the `sha256` hash of the evidence in the database.
*   Return to the **Integrity** tab and click **Verify Certificate** again.
*   **Expected**: The system loudly rejects the state and flags the verification as `INVALID` (Chain Broken).
