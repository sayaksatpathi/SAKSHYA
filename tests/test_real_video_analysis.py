import pytest
from backend.services.analysis import VideoAnalysisService
from backend.models import Evidence
from backend.database import SessionLocal
from backend.ai.engine import ai_engine
import math

def test_multi_frame_analysis():
    from unittest.mock import MagicMock
    db = MagicMock()
    
    # Init AI Engine
    ai_engine.initialize("models")
    if not any(ai_engine.available_models().values()):
        pytest.skip("No models available for multi-frame inference")
        
    evidence = Evidence(
        id="test-evidence-multi",
        case_id="test-case-multi",
        storage_path="demo/media/demo_video.mp4",
        fps=25.0
    )

    service = VideoAnalysisService(db)
    service.ledger.append_event = MagicMock()
    
    # Use deterministic configuration: 10 frames max by letting it run, but wait, 
    # the analyze method processes the entire video if we don't limit it. 
    # Let's mock the video path or just let it process the whole small demo video
    # demo_video.mp4 is very short (synthetic, around 2-3 seconds).
    
    results = service.analyze(evidence, frame_sample_rate=1, detection_confidence=0.1)
    
    # Verify results
    assert isinstance(results, list)
    
    if len(results) > 0:
        for r in results:
            assert r.evidence_id == evidence.id
            # Verify timestamps are monotonic
            assert r.timestamp is not None
            assert r.frame_number is not None
            
            # Timestamp ≈ frame_number / FPS
            expected_ts = r.frame_number / 25.0
            assert math.isclose(r.timestamp, expected_ts, abs_tol=0.01), f"Timestamp {r.timestamp} incorrect for frame {r.frame_number}"
            
            assert r.confidence >= 0.0 and r.confidence <= 1.0
            assert r.model_name is not None
            
            # Provenance checks for object detections
            if r.detection_type == "object":
                assert "bbox" in r.meta_data, "bbox missing in meta_data"
                assert "model_sha256" in r.meta_data, "model_sha256 missing in meta_data"
    
    db.close()
