import pytest
from backend.services.analysis import VideoAnalysisService
from backend.models import Evidence, Case
from backend.database import SessionLocal
from backend.ai.engine import ai_engine
from backend.crypto.hashing import sha256_string, canonicalize_json

def test_ai_result_tamper_detection():
    from backend.database import SessionLocal, Base, engine
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    ai_engine.initialize("models")
    if not any(ai_engine.available_models().values()):
        pytest.skip("No AI models available to test tampering")
        
    case = Case(id="case-tamper-test", case_number="TAMP-123", title="Tamper")
    db.merge(case) # Use merge in case it already exists in DB
    
    evidence = Evidence(
        id="evidence-tamper-test",
        case_id="case-tamper-test",
        storage_path="demo/media/demo_video.mp4",
        fps=25.0
    )
    db.merge(evidence)
    try:
        db.commit()
    except Exception:
        db.rollback()
        
    service = VideoAnalysisService(db)
    
    # 1. Complete AI Analysis
    results = service.analyze(evidence, frame_sample_rate=1, detection_confidence=0.1)
    if not results:
        pytest.skip("No detections to tamper with")
        
    # 2. Recompute valid hash
    ai_data_list = []
    for r in results:
        ai_data_list.append({
            "detection_type": r.detection_type,
            "label": r.label,
            "confidence": r.confidence,
            "frame_number": r.frame_number,
            "timestamp": r.timestamp,
            "bounding_box": r.bounding_box,
            "track_id": r.track_id,
            "meta_data": r.meta_data
        })
    valid_hash = sha256_string(canonicalize_json(ai_data_list))
    
    # Verify the hash matches what was placed in the ledger
    ledger_event = service.ledger.get_chain(case.id)[-1]
    assert ledger_event.event_type == "AI_ANALYSIS_COMPLETED"
    assert ledger_event.meta_data["analysis_result_hash"] == valid_hash
    
    # 3. Modify one detection field
    ai_data_list[0]["confidence"] = 0.999
    
    # 4. Recompute verification
    tampered_hash = sha256_string(canonicalize_json(ai_data_list))
    
    # 5. Confirm integrity check fails
    assert tampered_hash != valid_hash, "Tampered hash must differ from original hash"
    assert ledger_event.meta_data["analysis_result_hash"] != tampered_hash
    
    db.close()
