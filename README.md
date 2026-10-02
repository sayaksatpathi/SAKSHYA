---
title: SAKSHYA
emoji: 🛡️
colorFrom: indigo
colorTo: green
sdk: static
pinned: false
---

# SAKSHYA — Vendor-Agnostic CCTV Forensic Evidence Platform

**Smart India Hackathon 2026 · Problem Statement SIH26150 · Team Aroeminds**

SAKSHYA is a standardized, offline-first, vendor-agnostic forensic platform for multi-vendor DVR/NVR surveillance evidence. It provides a complete pipeline for evidence ingestion, AI triage, deleted-clip recovery, and tamper-evident cryptographic ledgers, culminating in a BSA Section 63(4)-oriented certificate draft.

---

## Architecture
The system consists of two primary layers:
1.  **FastAPI Backend (Python)**: Handles video forensics, AI models, cryptography, and PostgreSQL/SQLite state management.
2.  **React/Vite Frontend (TypeScript)**: Provides an investigator dashboard, timeline views, and integrity verification portals.

## Setup & Deployment
### Development / Local Run
```bash
# Backend Setup
pip install -r requirements.txt
python -m uvicorn backend.main:app --reload

# Frontend Setup
cd frontend
npm install
npm run dev
```

### Production Considerations
- **Storage**: Currently defaults to local filesystem (`./evidence_storage`). Must be migrated to Object Storage (S3) for clustered deployments.
- **Database**: Defaults to SQLite. Must be configured for PostgreSQL using `DATABASE_URL` for multi-node deployments.
- **Async Queue**: Currently uses `FastAPI BackgroundTasks`. For a highly scalable production setup, this must be refactored to use Celery + Redis.
- **Keys**: `SAKSHYA_SECRET_KEY` must be injected via environment variables; do not use the hardcoded default.

---

## Capabilities

### Authentication & RBAC
- Token-based JWT authentication protects the API.
- Strict Role-Based Access Control separates `investigator` (upload/analyze) from `auditor` (read-only verification).

### Evidence Workflow
- Cases are securely segmented by case numbers.
- Ingestion immediately calculates SHA-256 bounds.
- All actions on evidence append an immutable event to the Chain of Custody ledger.

### AI Modes & Forensics
- **Object Detection & Tracking**: Core capabilities are active and `VERIFIED`.
- **ANPR, Face Search, Re-ID**: Currently marked as `UNAVAILABLE` unless optional deep-learning models (EasyOCR, InsightFace) are manually loaded.
- **Video Forensics**: Implements structural FFprobe anomaly detection and frame integrity checks.
- **Recovery**: Capable of basic container recovery; advanced proprietary `.dav`/`.h264` parsing is deferred.

### Integrity & Trust Architecture
- **Ledger**: Every action logs an immutable event with a chained hash.
- **Merkle Tree**: Compiles the entire ledger into a single Merkle Root.
- **Trust Service**: An independent module that issues cryptographically verifiable receipts for the Merkle Root, anchoring it in time.

### Certificate & Reports
- **BSA Section 63(4)**: SAKSHYA automatically builds a structured electronic record certificate draft containing all hardware, integrity, and software provenance details.
- **Reports**: Exports an all-in-one PDF containing findings, timeline, and cryptographic receipts.

---

## Current Limitations

1. **FastAPI BackgroundTasks** is not a durable distributed queue. Server restarts will drop queued jobs.
2. **Local filesystem storage** is not equivalent to production object storage and prevents horizontal scaling without NFS/EFS.
3. **Some AI capabilities** (ANPR, Face Search) may be unavailable without heavy optional models.
4. **Proprietary DVR formats** may not yet be fully parsed or recovered.
5. **Browser E2E Tests** may be environment-limited due to Playwright dependencies on Windows.
6. **The BSA Section 63(4)-oriented certificate is an unsigned draft**. The responsible person must review, complete and authenticate it as appropriate; SAKSHYA does not itself determine legal admissibility.
7. **No Per-User Case Isolation (IDOR)**: Currently, all authenticated users with the `investigator` role can read and modify all cases. Multi-tenant/per-user case isolation is a roadmap feature and not yet implemented.
---

## Demo
Please see [docs/FINAL_DEMO.md](docs/FINAL_DEMO.md) for the official SIH evaluation deterministic workflow script.
