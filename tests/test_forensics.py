import pytest
from backend.models import Evidence, ForensicFinding
from backend.services.forensics import VideoForensicsService

def test_video_forensics():
    from unittest.mock import MagicMock
    from backend.models import Evidence
    
    db_session = MagicMock()
    ev = Evidence(
        case_id="fake_case",
        filename="missing.mp4",
        original_filename="missing.mp4",
        size=1024,
        sha256="fakehash",
        storage_path="/non/existent/path.mp4",
        fps=25.0
    )
    db_session.add(ev)
    db_session.commit()
    
    service = VideoForensicsService(db_session)
    findings = service.analyze_evidence(ev)
    
    assert len(findings) == 0, "Should return no findings for missing file"
