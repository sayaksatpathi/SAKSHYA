# SAKSHYA — RELEASE READINESS MATRIX

| Capability | Status | Evidence | Limitation |
| :--- | :--- | :--- | :--- |
| **Authentication** | VERIFIED | `test_auth_rbac.py`, Frontend Login Guard | Fallback JWT secret exists in config |
| **RBAC** | VERIFIED | API Endpoint `Depends(get_current_investigator)` tests passing | None |
| **Case Management** | VERIFIED | `test_api.py`, Frontend API hooks | Lack of per-user Case Isolation (IDOR) |
| **Evidence Ingestion** | VERIFIED | `test_api.py`, File storage logic | No strict file-type whitelisting on raw upload |
| **Hashing** | VERIFIED | `test_crypto.py` tests | Memory constraints on massively large files |
| **AI Detection** | VERIFIED | `test_real_object_detection.py` | Heuristic/Probabilistic nature requires human validation |
| **Tracking** | VERIFIED | `test_tracking_integration.py` | May lose IDs across significant occlusions |
| **ANPR** | UNAVAILABLE | Hardcoded module missing models | Requires EasyOCR/Tesseract models to be installed |
| **Face Search** | UNAVAILABLE | Hardcoded module missing models | Requires SFace/InsightFace models to be installed |
| **Re-ID** | UNAVAILABLE | Stubbed endpoint | Cross-camera Re-ID requires advanced metric learning models |
| **Video Forensics** | VERIFIED | `test_forensics.py` structural checks | Advanced binary carving not yet implemented |
| **Recovery** | PARTIAL | Basic container recovery (`test_recovery_engine.py`) | Fails on proprietary DVR formats (e.g. raw `.dav`) |
| **Timeline** | VERIFIED | Interactive UI and timeline aggregation endpoint | None |
| **Search** | PARTIAL | Basic SQL filters in list endpoints | Missing dedicated Full-Text Search engine |
| **Chain of Custody** | VERIFIED | `test_bsa_certificate.py`, LedgerService | None |
| **Merkle** | VERIFIED | `test_crypto.py` canonical tree generation | None |
| **Trust** | VERIFIED | TrustReceipt API generation | Missing remote TSA (Time Stamping Authority) integration |
| **Certificate** | VERIFIED | `test_bsa_certificate.py` (Creation & Validation) | Only produces an unsigned "Draft", no e-Sign integrated |
| **Reports** | VERIFIED | PDF generation includes all modules | Formatting breaks on very long anomalous findings |
| **Tamper Detection** | VERIFIED | `test_bsa_certificate.py` correctly flags manual hash tampering | None |
| **Async Jobs** | VERIFIED | `test_async_jobs.py` (Deduplication & State Management) | Dependent on FastAPI server lifecycle; not distributed |
| **Offline Operation** | PARTIAL | Core processing runs entirely locally | Assumes single-node local environment |
| **Frontend** | VERIFIED | Vite `build` and `lint` succeed | Browser E2E smoke tests not fully verified via automation |
| **Deployment** | VERIFIED | Docker-compose runs | Needs external DB/Queue for multi-node prod deployment |
| **Documentation** | VERIFIED | Comprehensive guides in `/docs` | None |
