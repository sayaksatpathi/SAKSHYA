import pytest
import os
import json
from pathlib import Path
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from backend.main import app
from backend.models import Case, Evidence, AIResult, ForensicFinding, ChainEvent, MerkleRecord, TrustReceipt
from backend.services.ledger import LedgerService
from backend.crypto.hashing import sha256_bytes

from backend.database import Base, engine, get_db
import cv2

client = TestClient(app)

@pytest.fixture(scope="module")
def setup_demo_video():
    """Create a temporary demo video for testing if it doesn't exist."""
    media_dir = Path("demo/media")
    media_dir.mkdir(parents=True, exist_ok=True)
    video_path = media_dir / "test_full_e2e.mp4"
    
    if not video_path.exists():
        import numpy as np
        out = cv2.VideoWriter(str(video_path), cv2.VideoWriter_fourcc(*'mp4v'), 25.0, (640, 480))
        for i in range(10):  # Just a few frames for fast testing
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            out.write(frame)
        out.release()
    yield str(video_path)
    if video_path.exists():
        video_path.unlink()

@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_full_e2e_pipeline_and_integrity(setup_demo_video):
    """
    Test the full E2E pipeline from case creation to report verification,
    and then verify that tampering is detected.
    """
    db_session = next(get_db())
    # 1. CREATE CASE
    case_resp = client.post("/api/cases", json={
        "case_number": "E2E-FULL-001",
        "title": "Full E2E Test Case",
        "description": "Testing the entire pipeline",
        "investigator": "Test Investigator"
    })
    assert case_resp.status_code == 201
    case_id = case_resp.json()["id"]

    # 2. INGEST EVIDENCE
    with open(setup_demo_video, "rb") as f:
        ev_resp = client.post(
            f"/api/cases/{case_id}/evidence",
            data={"evidence_type": "video", "source_device": "Camera1"},
            files={"file": ("demo_video.mp4", f, "video/mp4")}
        )
    assert ev_resp.status_code == 201
    evidence_id = ev_resp.json()["id"]

    # 3. RUN REAL ANALYSIS (AI)
    analyze_resp = client.post(f"/api/evidence/{evidence_id}/analyze")
    assert analyze_resp.status_code == 200

    # Wait for job (mocked or fast enough in tests)
    import time
    time.sleep(2)

    # 4. RUN VIDEO FORENSICS
    forensic_resp = client.post(f"/api/evidence/{evidence_id}/forensics")
    assert forensic_resp.status_code == 200

    # 5. RUN RECOVERY
    recovery_resp = client.post(f"/api/evidence/{evidence_id}/recover")
    assert recovery_resp.status_code == 200

    # 6. VERIFY INTEGRITY CHAIN (BEFORE TAMPERING)
    ledger = LedgerService(db_session)
    chain_status = ledger.verify_chain(case_id)
    assert chain_status["valid"] is True

    # 7. BUILD MERKLE TREE
    merkle_resp = client.post(f"/api/cases/{case_id}/merkle")
    assert merkle_resp.status_code == 201

    # 8. CREATE TRUST RECEIPT
    trust_resp = client.post(f"/api/cases/{case_id}/trust-sign")
    assert trust_resp.status_code == 201

    # 9. GENERATE PDF REPORT
    report_resp = client.post(f"/api/cases/{case_id}/report")
    assert report_resp.status_code == 200

    # ==========================
    # 10. TAMPER DETECTION
    # ==========================
    
    # Tamper with an AI result
    ai_result = db_session.query(AIResult).filter(AIResult.evidence_id == evidence_id).first()
    if ai_result:
        ai_result.confidence = 0.999
        db_session.commit()

    # Tamper with a ChainEvent to test ledger detection
    chain_event = db_session.query(ChainEvent).filter(ChainEvent.case_id == case_id).first()
    if chain_event:
        # Change a field that is supposed to be immutable
        chain_event.meta_data = {"tampered": True}
        db_session.commit()

    # Re-verify integrity
    chain_status_after = ledger.verify_chain(case_id)
    assert chain_status_after["valid"] is False
