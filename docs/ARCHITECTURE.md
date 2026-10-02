# SAKSHYA Architecture

SAKSHYA is a vendor-agnostic forensic evidence and AI investigation platform designed for SIH26150. It enables investigators to recover, process, and analyze video evidence while cryptographically preserving the chain of custody.

## High-Level Architecture

The system follows a classic layered architecture, decoupled to allow independent scaling of the web API, database, and background workers.

### Local Forensic Mode (Target Deployment)

```text
Frontend
   ↓
FastAPI
   ↓
Services
   ├── SQLite
   ├── Evidence Storage
   ├── Local AI Models
   ├── Ledger
   └── Trust Service
```

### Demo Deployment Mode

The existing demo is deployed as a static-site (e.g., on Hugging Face or GitHub Pages). A static frontend deployment is NOT equivalent to the complete offline forensic system, as it relies on mock APIs or a remote backend which fundamentally changes the offline-first security guarantees. The Local Forensic Mode is the canonical architecture.

## Core Components

### 1. Database (SQLAlchemy)
Uses SQLite for local, offline-first portability (vital for forensic isolation). The schema is completely relational, storing Cases, Evidence, AI Results, and Chain of Custody events.

### 2. File Storage
Raw evidence and processed segments are stored directly on the file system (`storage/evidence/`). Only metadata and cryptographic hashes are kept in the database.

### 3. REST API (FastAPI)
Exposes endpoints under `/api/v1` for managing cases, uploading evidence, triggering AI analysis, and verifying chain of custody. 

### 4. Service Layer
- **AcquisitionService**: Handles safe ingest, hashing (SHA-256), and vendor-agnostic validation.
- **LedgerService**: Append-only chain of custody. Every action triggers an event linked to the previous event's hash.
- **MerkleService**: Computes Merkle Roots over evidence and chain events for aggregate integrity.
- **TrustService**: Independent trust anchor signing chain heads.
- **ReportService**: Generates cryptographic PDF reports via ReportLab.

## AI Engine Architecture

The AI module is designed for modular investigative assistance. **AI output is investigative assistance rather than definitive identity determination.** Outputs are labeled as "SIMILARITY CANDIDATE", "POSSIBLE MATCH", or "AI DETECTION".

```text
AI Engine
├── Face Detection
│   └── YuNet
├── Face Embeddings
│   └── SFace
├── Object Detection
│   └── YOLO-compatible detector
├── Multi-object Tracking
│   └── ByteTrack or compatible tracker
├── ANPR
│   ├── plate detection
│   └── OCR
└── Cross-camera Re-ID
    └── OSNet or compatible Re-ID model
```

*(Note: Haar Cascades may be used as an optional fallback CV technique, but it is not the main ANPR or facial recognition capability. ANPR relies on vehicle detection -> license plate localization -> OCR -> normalization -> confidence -> investigator verification).*

## Auditability and Model Provenance
Every AI result provides an auditable trail of its execution:
* model name
* model version
* model file hash (where practical)
* inference timestamp
* confidence
* processing configuration

## Security Constraints

- **Logical Immutability**: Logical immutability is enforced by application design; OS-level write protection is deployment-dependent. Original evidence is never modified in-place.
- **Offline-First**: Can run fully air-gapped using local models.
- **Auditability**: Every action generates an event on the append-only ledger.
