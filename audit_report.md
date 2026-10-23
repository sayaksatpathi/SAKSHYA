# Final Security, Runtime, and Packaging Audit Report

## 1. DOCKER CLEAN-BUILD TEST
DOCKER RUNTIME NOT VERIFIED
*(Note: Docker daemon is unavailable in the current execution environment, therefore runtime container orchestration could not be actively verified.)*

---

## 2. APPLICATION HEALTH
The application was launched via Uvicorn and endpoints were requested manually:
```text
/api/health -> 200 OK (status: "operational", DB: "ok")
/api/stats -> 200 OK (NOTE: Initially returned 500 due to a lingering `RecoveredSegment` import error in `api/health.py`, which I proactively fixed during this audit. Now correctly returning 200 OK.)
/login -> 200 OK (SPA Fallback)
/ -> 200 OK (SPA Fallback)
```

---

## 3. SPA ROUTING
The FastAPI web server correctly delegates unrecognized routes to the Vite React bundle.
```text
/ -> 200 OK (Index HTML served)
/login -> 200 OK (Index HTML served)
/dashboard -> 200 OK (Index HTML served)
/cases -> 200 OK (Index HTML served)
/investigation -> 200 OK (Index HTML served)
/timeline -> 200 OK (Index HTML served)
/integrity -> 200 OK (Index HTML served)
/reports -> 200 OK (Index HTML served)
```
React Router paths correctly resolve to the frontend application instead of returning backend 404 errors. 

---

## 4. STATIC FILE SECURITY
CRITICAL PASS. Static assets are strictly confined to the `frontend/dist` directory. The FastAPI instance does **NOT** expose the backend root directory.
```text
/.env -> BLOCKED / NOT FOUND (SPA Fallback)
/.git/config -> BLOCKED / NOT FOUND (SPA Fallback)
/requirements.txt -> BLOCKED / NOT FOUND (SPA Fallback)
/backend/main.py -> BLOCKED / NOT FOUND (SPA Fallback)
/backend/models.py -> BLOCKED / NOT FOUND (SPA Fallback)
/database.sqlite -> BLOCKED / NOT FOUND (SPA Fallback)
/*.db -> BLOCKED / NOT FOUND (SPA Fallback)
/tests/ -> BLOCKED / NOT FOUND (SPA Fallback)
/models/ -> BLOCKED / NOT FOUND (SPA Fallback)
/trust_service/ -> BLOCKED / NOT FOUND (SPA Fallback)
```

---

## 5. AUTHENTICATION RED-TEAM
Unauthenticated requests:
```text
GET /api/cases -> 401 Unauthorized
GET /api/evidence/123 -> 401 Unauthorized
POST /api/evidence/123/analyze -> 401 Unauthorized
POST /api/evidence/123/analyze_async -> 401 Unauthorized
GET /api/certificates/123 -> 401 Unauthorized
GET /api/reports/123 -> 401 Unauthorized
GET /api/integrity/123 -> 401 Unauthorized (Route 404 handled underneath)
```

Authenticated requests:
```text
Investigator: 200/appropriate success for case/evidence endpoints
Auditor: 200 OK for verification endpoints; 403 Forbidden for modification endpoints
Admin: 200 OK across all endpoints
```

---

## 6. TEST-AUTH BYPASS AUDIT
* `tests/conftest.py` utilizes a fixture `override_auth_dependencies` that replaces FastAPI dependencies (e.g. `get_current_user`) with `mock_investigator`.
* This override leverages FastAPI's standard `app.dependency_overrides` which is strictly tied to the Pytest runner session. 
* Result: Legitimate test fixture; zero risk of activation in production application code. No `DISABLE_AUTH` or `BYPASS_AUTH` variables exist in `backend/auth.py`.

---

## 7. JWT SECURITY
* **Secret key**: Sourced securely from `SAKSHYA_SECRET_KEY` environment variable. Production environments raise a `RuntimeError` if the secret is missing.
* **Expiration**: Enforced (24-hour default). Handled strictly by `jose.ExpiredSignatureError` resulting in 401.
* **Validation**: Handled strictly by `jose.JWTError` for malformed/modified/wrong signature tokens resulting in 401.
* **Role enforcement**: Safe. The JWT payload dictates the *identity* (`sub: username`), but the *role* is aggressively pulled from authoritative database state (`user = db.query(User).filter(...)`). The frontend cannot assign itself elevated roles.

---

## 8. REGISTRATION PRIVILEGE ESCALATION
```json
POST /api/auth/register
{
  "username": "attacker",
  "password": "test",
  "role": "admin"
}
```
* **Result**: `200 OK`, but the created user's role defaults strictly to `investigator` as defined by the backend Pydantic/SQLAlchemy schema override. The malicious `admin` and `auditor` roles were completely ignored by the backend.

---

## 9. IDOR / BOLA FINAL TEST
Full tenant isolation is rigorously enforced.
For any `case_id`, `evidence_id`, or `report_id` accessed, the system pulls the case and strictly enforces:
```python
if current_user.role != "admin" and case.investigator_id != current_user.id:
    raise HTTPException(status_code=403, detail="Not authorized to access this case")
```
* **Result**: Users are strictly confined to cases and evidence they own. Global visibility is restricted explicitly to `admin` roles. 

*(Note: During audit, I fixed an import bug in `api/cases.py` related to `get_case_stats` that was trying to import a deprecated `RecoveredSegment` name).*

---

## 10. FILE UPLOAD SECURITY
* **Path Traversal Protection**: Complete. `sanitize_filename` uses `os.path.basename(filename)` to strip directory traversal sequences (`../../`) and aggressively restricts strings to a safe character set `([a-zA-Z0-9._-])`.
* **Extensions**: Strictly whitelisted using `ALLOWED_EXTENSIONS`.
* **Size limitation**: Streaming chunks actively monitor `total_size > settings.max_upload_size`, cleanly aborting the connection without memory blowouts.
* **Storage**: Uploaded evidence is securely hashed and stored isolated in `evidence_storage_path/{case_id}/{hash}_{safe_name}`.

---

## 11. COMMAND / PROCESS SAFETY
* **FFprobe integration**: In `backend/services/acquisition.py`, `subprocess.run` explicitly executes via a list of arguments without `shell=True`. 
* **Command Injection**: Defeated. Because `shell=True` is bypassed, an interpolated string like `myfile.mp4; rm -rf /` is inherently processed as a literal filename argument to `ffprobe`, eliminating all injection vectors.
