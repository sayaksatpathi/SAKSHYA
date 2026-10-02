# SAKSHYA — FINAL SECURITY / FORENSIC RISK REGISTER

## Security Risks

### 1. Incomplete Authorization Boundary (IDOR/BOLA)
**Risk:** All authenticated users with the `investigator` or `admin` role can read and modify all cases, evidence, and jobs. There is currently no per-user case isolation (tenant isolation) implemented.
**Impact:** Medium to High (Internal confidentiality). An investigator could intentionally or accidentally alter evidence or analysis belonging to another investigator's case.
**Current mitigation:** Role-Based Access Control (RBAC) correctly prevents `auditor` and unauthenticated users from modifying cases.
**Recommended future mitigation:** Implement strict ownership rules and assignment lists (e.g., `case.investigators = [...]`) and enforce IDOR checks on all `/api/cases/{id}` and dependent routes using the `get_current_user` dependency context.

### 2. Secrets Management
**Risk:** SAKSHYA depends on symmetric keys (like `SAKSHYA_SECRET_KEY`) for JWT signing, which default to hardcoded fallback strings in `config.py` if not set in the environment.
**Impact:** High. If the fallback string is used in production, any attacker knowing the open-source repository can forge JWT tokens.
**Current mitigation:** JWT is enforced across the board, and a warning is logged when defaults are used.
**Recommended future mitigation:** Force application startup to crash if `SAKSHYA_SECRET_KEY` is not explicitly provided in the production environment.

### 3. File System Traversal / Storage Boundaries
**Risk:** Uploaded evidence is stored using generated paths, but metadata components or endpoints serving files could theoretically be subject to path traversal if raw filenames are ever concatenated directly.
**Impact:** Medium.
**Current mitigation:** Evidence files are stored via safe UUID-based identifiers (e.g., `/{case_id}/{evidence_id}.mp4`).
**Recommended future mitigation:** Conduct a deep source-code audit on all `storage_path` derivations, especially within the forensic recovery module which writes extracted binaries.

## Forensic & Data Integrity Risks

### 4. Heuristic AI and Probabilistic Detections
**Risk:** AI Object Detection and Facial Recognition features use probabilistic confidence scores. If users interpret these as definitive absolute facts, the investigation may draw incorrect legal conclusions.
**Impact:** Medium (Procedural/Legal).
**Current mitigation:** The forensic report and UI clearly display a disclaimer: *"AI results are investigative aids and not definitive identifications. Similarity scores do not prove identity."*
**Recommended future mitigation:** Integrate a "Human Validation" step where an investigator must click "Verify" on an AI detection before it is included in the final certificate or timeline.

### 5. Asynchronous Job Platform Constraints
**Risk:** The system currently relies on FastAPI `BackgroundTasks` for long-running AI inference and forensic analysis.
**Impact:** Medium. If the FastAPI process restarts, crashes, or is killed, all queued and currently processing jobs will be permanently lost and left in a zombie state in the database.
**Current mitigation:** The backend checks the database for existing running jobs to prevent duplicate expensive processes, and logs states aggressively.
**Recommended future mitigation:** Migrate to a durable distributed queue (such as Celery backed by Redis or RabbitMQ) for production deployments to ensure job persistence across server restarts.

### 6. Missing Proprietary Video Formats
**Risk:** The forensic recovery engine explicitly lacks deep parsing for proprietary surveillance formats (e.g., specific `.dav` multiplexed streams or encrypted `.h264` chunks).
**Impact:** High (Operational). Recovery on non-standard DVR extractions may fail silently or produce unplayable files.
**Current mitigation:** The API accurately distinguishes `video/mp4` and `video/x-matroska`, and the system refuses to "recover" files it cannot parse, avoiding corrupted synthetic evidence.
**Recommended future mitigation:** Implement deep binary carving and proprietary header parsing (Phase 6) specific to major Indian DVR manufacturers (Hikvision, Dahua, CP Plus).

### 7. Certificate Admissibility Status
**Risk:** Users may mistake the SAKSHYA "BSA Section 63(4)" certificate for a legally binding, court-ready document without a human signature.
**Impact:** High (Legal).
**Current mitigation:** The certificate is generated and explicitly labelled as a "Draft". A mandatory disclaimer notes that SAKSHYA itself does not determine legal admissibility. The signature status defaults to `UNSIGNED`.
**Recommended future mitigation:** Integrate digital e-Sign workflows (e.g., Aadhaar eSign or DSC token integration) to allow authorized officers to cryptographically sign the draft into a legally binding certificate.
