import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import json
import hashlib

from backend.main import app
from backend.database import SessionLocal, engine, Base
from backend.models import Case, Evidence, ElectronicRecordCertificate, ChainEvent, User
from backend.crypto.hashing import sha256_bytes

@pytest.fixture(scope="function", autouse=True)
def setup_teardown():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def mock_investigator(monkeypatch):
    """Mock the auth dependency to bypass JWT checking for tests."""
    from backend.auth import get_current_investigator, get_current_user
    
    dummy_user = User(
        id="u1", 
        username="test_investigator", 
        role="investigator", 
        hashed_password="xxx", 
        is_active=True
    )
    
    app.dependency_overrides[get_current_investigator] = lambda: dummy_user
    app.dependency_overrides[get_current_user] = lambda: dummy_user
    
    yield dummy_user
    app.dependency_overrides.clear()

def test_certificate_creation(mock_investigator):
    client = TestClient(app)
    db = SessionLocal()
    c = Case(id="c1", case_number="C1", title="T", investigator="I")
    e = Evidence(id="e1", case_id="c1", filename="v.mp4", original_filename="v.mp4", storage_path="/dev/null", sha256="abc123hash", size=1024, evidence_type="video")
    db.add(c)
    db.add(e)
    db.commit()
    
    # 1. Test creation
    payload = {
        "evidence_id": "e1",
        "electronic_record_identifier": "VID-001",
        "electronic_record_description": "CCTV Footage",
    }
    res = client.post("/api/cases/c1/certificates", json=payload)
    assert res.status_code == 200, res.text
    cert = res.json()
    
    assert cert["case_id"] == "c1"
    assert cert["evidence_id"] == "e1"
    assert cert["electronic_record_identifier"] == "VID-001"
    assert cert["record_format"] == "video"
    assert cert["record_size"] == 1024
    assert cert["record_sha256"] == "abc123hash"
    
    # Unknown values handling
    assert cert["device_operational_status"] == "NOT VERIFIED"
    assert cert["regular_use_context"] == "NOT RECORDED"
    assert cert["method_of_production"] == "NOT RECORDED"
    assert cert["signatory_name"] == "NOT PROVIDED"
    
    # Signature remains unsigned/review required
    assert cert["certificate_status"] == "REVIEW_REQUIRED"
    assert cert["signature_status"] == "UNSIGNED"
    
    # Check Ledger
    event = db.query(ChainEvent).filter(ChainEvent.event_type == "BSA_CERTIFICATE_CREATED").first()
    assert event is not None
    assert event.case_id == "c1"
    assert event.evidence_id == "e1"
    assert event.meta_data["payload_hash"] == cert["certificate_content_hash"]
    assert event.meta_data["certificate_id"] == cert["certificate_id"]
    
    # 2. Test fetching
    res2 = client.get(f"/api/certificates/{cert['certificate_id']}")
    assert res2.status_code == 200
    assert res2.json()["certificate_id"] == cert["certificate_id"]
    
    db.close()

def test_certificate_verification(mock_investigator):
    client = TestClient(app)
    db = SessionLocal()
    c = Case(id="c2", case_number="C2", title="T", investigator="I")
    e = Evidence(id="e2", case_id="c2", filename="v.mp4", original_filename="v.mp4", storage_path="/dev/null", sha256="hash2", size=1024)
    db.add(c)
    db.add(e)
    db.commit()
    
    res = client.post("/api/cases/c2/certificates", json={
        "evidence_id": "e2",
        "electronic_record_identifier": "VID-002"
    })
    cert_id = res.json()["certificate_id"]
    
    # Verify valid
    ver = client.get(f"/api/certificates/{cert_id}/verify").json()
    assert ver["certificate_exists"] is True
    assert ver["certificate_content_hash_valid"] is True
    assert ver["evidence_hash_matches"] is True
    assert ver["overall_integrity_status"] == "CONSISTENT"
    
    # Tamper certificate content hash
    cert_obj = db.query(ElectronicRecordCertificate).filter_by(certificate_id=cert_id).first()
    cert_obj.certificate_content_hash = "fakehash"
    db.commit()
    
    ver2 = client.get(f"/api/certificates/{cert_id}/verify").json()
    assert ver2["certificate_content_hash_valid"] is False
    assert ver2["overall_integrity_status"] == "INVALID"
    
    # Tamper evidence hash
    cert_obj.certificate_content_hash = res.json()["certificate_content_hash"] # restore
    db.commit()
    
    e_obj = db.query(Evidence).filter_by(id="e2").first()
    e_obj.sha256 = "tamperedhash"
    db.commit()
    
    ver3 = client.get(f"/api/certificates/{cert_id}/verify").json()
    assert ver3["evidence_hash_matches"] is False
    assert ver3["overall_integrity_status"] == "INVALID"
    
    db.close()

def test_pdf_generation_with_certificate(mock_investigator):
    client = TestClient(app)
    db = SessionLocal()
    c = Case(id="c3", case_number="C3", title="T", investigator="I")
    e = Evidence(id="e3", case_id="c3", filename="v.mp4", original_filename="v.mp4", storage_path="/dev/null", sha256="hash3", size=1024)
    db.add(c)
    db.add(e)
    db.commit()
    
    # Create certificate
    res = client.post("/api/cases/c3/certificates", json={
        "evidence_id": "e3",
        "electronic_record_identifier": "VID-003"
    })
    cert = res.json()
    
    # Generate report
    rep = client.post("/api/cases/c3/report")
    assert rep.status_code == 200
    
    from backend.config import settings
    from pathlib import Path
    pdf_path = Path(settings.evidence_storage_path) / "c3" / "report.pdf"
    assert pdf_path.exists()
    
    # Verify PDF content by trying to extract text
    try:
        import PyPDF2
        with open(pdf_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            text = text.replace('\n', ' ')

            assert "BSA Section 63(4) Certificate Draft" in text
            assert "It does not itself determine admissibility" in text
            assert "VID-003" in text
            assert "hash3" in text
            assert "REVIEW_REQUIRED" in text
    except ImportError:
        pass # If PyPDF2 is not installed in the environment, we skip the text check, but pdf generated.
    
    db.close()
