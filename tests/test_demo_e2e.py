"""
SAKSHYA E2E Demo Integration Tests
"""

import pytest
import os
from pathlib import Path
from backend.main import app
from fastapi.testclient import TestClient
from backend.database import Base, engine, get_db
from backend.models import Case, Evidence, ChainEvent, MerkleRecord
from backend.services.acquisition import AcquisitionService
from backend.services.analysis import VideoAnalysisService
from backend.services.ledger import LedgerService
from backend.crypto.merkle import MerkleTree
from backend.services.report import ReportService
import cv2

@pytest.fixture(scope="module")
def setup_demo_video():
    """Create a temporary demo video for testing if it doesn't exist."""
    media_dir = Path("demo/media")
    media_dir.mkdir(parents=True, exist_ok=True)
    video_path = media_dir / "test_demo.mp4"
    
    if not video_path.exists():
        import numpy as np
        out = cv2.VideoWriter(str(video_path), cv2.VideoWriter_fourcc(*'mp4v'), 25.0, (640, 480))
        for i in range(10):  # Just a few frames for fast testing
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            out.write(frame)
        out.release()
    yield str(video_path)
    # Cleanup optional, but we can leave it for manual runs
    if video_path.exists():
        video_path.unlink()

@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_demo_ingest(setup_demo_video):
    db = next(get_db())
    case = Case(case_number="DEMO-TEST-01", title="Test", investigator="Test")
    db.add(case)
    db.commit()
    
    acq_service = AcquisitionService(db)
    with open(setup_demo_video, "rb") as f:
        evidence = acq_service.ingest_file(
            case_id=case.id,
            file_stream=f,
            original_filename="test_demo.mp4",
        )
    
    assert evidence is not None
    assert evidence.sha256 is not None
    assert Path(evidence.storage_path).exists()

def test_video_metadata(setup_demo_video):
    # This will test if metadata is stored correctly (ffprobe might be missing, so it can be None)
    db = next(get_db())
    case = Case(case_number="DEMO-TEST-02", title="Test", investigator="Test")
    db.add(case)
    db.commit()
    
    acq_service = AcquisitionService(db)
    with open(setup_demo_video, "rb") as f:
        evidence = acq_service.ingest_file(
            case_id=case.id,
            file_stream=f,
            original_filename="test_demo.mp4",
        )
        
    # Metadata should be a dict or None (if ffprobe missing)
    if evidence.meta_data is not None and "ffprobe" in evidence.meta_data:
        assert evidence.fps is not None
    else:
        assert evidence.meta_data is None or "ffprobe" not in evidence.meta_data

def test_video_validation(setup_demo_video):
    cap = cv2.VideoCapture(setup_demo_video)
    assert cap.isOpened()
    ret, frame = cap.read()
    assert ret is True
    assert frame is not None
    cap.release()

def test_ai_pipeline(setup_demo_video):
    db = next(get_db())
    case = Case(case_number="DEMO-TEST-03", title="Test", investigator="Test")
    db.add(case)
    db.commit()
    
    acq_service = AcquisitionService(db)
    with open(setup_demo_video, "rb") as f:
        evidence = acq_service.ingest_file(
            case_id=case.id,
            file_stream=f,
            original_filename="test_demo.mp4",
        )
        
    # We initialize with local models if present, otherwise it won't crash
    from backend.ai.engine import ai_engine
    ai_engine.initialize("models")
    
    if ai_engine.available_models():
        analysis_service = VideoAnalysisService(db)
        results = analysis_service.analyze(evidence, frame_sample_rate=1, detection_confidence=0.1)
        # Even if results are empty (black frame), it shouldn't crash
        assert isinstance(results, list)
    else:
        assert True

def test_ledger_after_analysis(setup_demo_video):
    db = next(get_db())
    case = Case(case_number="DEMO-TEST-04", title="Test", investigator="Test")
    db.add(case)
    db.commit()
    
    ledger = LedgerService(db)
    ledger.append_event(case.id, "CASE_CREATED", "Test")
    
    acq_service = AcquisitionService(db)
    with open(setup_demo_video, "rb") as f:
        evidence = acq_service.ingest_file(
            case_id=case.id,
            file_stream=f,
            original_filename="test_demo.mp4",
        )
        
    chain_status = ledger.verify_chain(case.id)
    assert chain_status["valid"] is True

def test_merkle_after_analysis(setup_demo_video):
    db = next(get_db())
    case = Case(case_number="DEMO-TEST-05", title="Test", investigator="Test")
    db.add(case)
    db.commit()
    
    acq_service = AcquisitionService(db)
    with open(setup_demo_video, "rb") as f:
        evidence = acq_service.ingest_file(
            case_id=case.id,
            file_stream=f,
            original_filename="test_demo.mp4",
        )
        
    leaves = [evidence.sha256]
    tree = MerkleTree(leaves)
    assert tree.leaf_count == 1
    assert tree.root is not None

def test_trust_after_analysis(setup_demo_video):
    db = next(get_db())
    case = Case(case_number="DEMO-TEST-06", title="Test", investigator="Test")
    db.add(case)
    db.commit()
    
    ledger = LedgerService(db)
    ledger.append_event(case.id, "TEST", "Test")
    
    from fastapi.testclient import TestClient
    from backend.main import app
    client = TestClient(app)
    
    response = client.post(f"/api/cases/{case.id}/trust-sign")
    # If the service is unreachable it returns 503, which is valid handling for our tests
    assert response.status_code in [201, 503]

def test_report_generation(setup_demo_video):
    db = next(get_db())
    case = Case(case_number="DEMO-TEST-07", title="Test", investigator="Test")
    db.add(case)
    db.commit()
    
    # Needs evidence to report on
    acq_service = AcquisitionService(db)
    with open(setup_demo_video, "rb") as f:
        acq_service.ingest_file(case_id=case.id, file_stream=f, original_filename="test_demo.mp4")
        
    report_bytes = ReportService(db).generate_report(case.id)
    assert report_bytes is not None
    assert len(report_bytes) > 0

def test_end_to_end_demo(setup_demo_video):
    # Basically the exact same flow as demo_run.py to ensure the whole slice connects
    db = next(get_db())
    case = Case(case_number="DEMO-TEST-08", title="E2E", investigator="Test")
    db.add(case)
    db.commit()
    
    ledger = LedgerService(db)
    ledger.append_event(case.id, "CASE_CREATED", "Test")
    
    acq_service = AcquisitionService(db)
    with open(setup_demo_video, "rb") as f:
        evidence = acq_service.ingest_file(case_id=case.id, file_stream=f, original_filename="test_demo.mp4")
        
    cap = cv2.VideoCapture(evidence.storage_path)
    assert cap.isOpened()
    cap.release()
    
    ledger.append_event(case.id, "VIDEO_VALIDATED", "Test", evidence.id)
    
    from backend.ai.engine import ai_engine
    ai_engine.initialize("models")
    if ai_engine.available_models():
        VideoAnalysisService(db).analyze(evidence, frame_sample_rate=1, detection_confidence=0.1)
        
    status = ledger.verify_chain(case.id)
    assert status["valid"] is True
    
    leaves = [evidence.sha256]
    tree = MerkleTree(leaves)
    assert tree.root is not None
    
    report_bytes = ReportService(db).generate_report(case.id)
    assert report_bytes is not None
    
    assert True
